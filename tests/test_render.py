from datetime import datetime, timezone

import pytest

from fake_llm import FakeAnthropic, message
from paralaksa import db
from paralaksa.aggregate.package import build_data_package
from paralaksa.config import load_themes
from paralaksa.extract.llm_client import LLMClient
from paralaksa.report.pipeline import generate_report
from paralaksa.report.render import collect_meta, render_markdown
from paralaksa.report.schema import ReportOutput, parse_report
from report_fixtures import as_text, valid_report
from seed import DAY, article, article_with, seed_alarm_convergence, seed_sources

THEMES = load_themes()
NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def seeded(conn):
    sources = seed_sources(conn)
    ids = seed_alarm_convergence(conn)
    return sources, ids


def render(conn, settings, sources, report: ReportOutput, warnings=()):
    package = build_data_package(conn, DAY, settings, THEMES)
    meta = collect_meta(conn, DAY, settings, sources, THEMES, package, "claude-sonnet-5",
                        "synthesize_report@abc", list(warnings))
    return render_markdown(report, package, meta)


def test_sections_links_and_metadata(conn, settings, seeded):
    sources, ids = seeded
    report, _ = parse_report(as_text(valid_report(ids)))
    db.record_usage(conn, "deepseek-v4-pro", "direct", "extract", 10, 10, 0.12, now=NOW)
    md = render(conn, settings, sources, report)

    for heading in ("# Paralaksa narracji – 2026-09-23", "## W skrócie", "## Wzorce zbieżności",
                    "### Obronność: alarm i zbrojenia", "## Rozbieżne przekazy",
                    "## Autoobraz vs obraz zewnętrzny", "## Co się przesuwa", "## Nieobecne w Polsce",
                    "## Słabe sygnały (poniżej progów)", "## Metadane"):
        assert heading in md, heading
    assert "Ciekawostki" not in md                                    # KM4
    url = conn.execute("SELECT url FROM articles WHERE id = ?", (ids["pl"][0],)).fetchone()[0]
    assert f"[#{ids['pl'][0]}]({url})" in md
    assert "**Sygnały przeciwne:** Brytyjskie medium" in md and "**Pewność:** średni – 4 kraje" in md
    assert "Brak linii bazowej: 0 dni historii" in md
    assert "Koszt API dnia: $0.120 (extract $0.120)" in md
    assert "synteza claude-sonnet-5" in md and "extract_signals@test; synthesize_report@abc" in md
    assert "| PL | pl1, pl2 | 2 | 2 | 0% |" in md
    assert "pl1 (PL)" not in md                                       # nieaktywnych brak w seedzie


def test_empty_report_and_warnings(conn, settings, seeded):
    sources, _ = seeded
    md = render(conn, settings, sources, ReportOutput(), warnings=["synteza nieudana: x"])
    assert "> - synteza nieudana: x" in md
    assert "_Brak wzorców spełniających progi (3 kraje, 2 źródła na kraj)._" in md
    assert "_Synteza nie zwróciła podsumowania._" in md


def test_self_image_table_uses_package_js(conn, settings, seeded):
    sources, _ = seeded
    for n in (1, 2, 1):
        article_with(conn, f"de{n}", theme="elections_politics", actor="DE", stance="poparcie")
    for src in ("uk1", "uk2", "ua1"):
        aid = article_with(conn, src, theme="elections_politics", actor="DE", stance="krytyka")
    conn.commit()
    report = ReportOutput.model_validate({"autoobraz": [{
        "kraj": "DE", "jak_opisuje_siebie": "stabilna | demokracja", "jak_opisuja_go_inni": "kryzys",
        "komentarz": "rozjazd", "article_ids": [aid]}]})
    md = render(conn, settings, sources, report)
    assert "| DE | stabilna \\| demokracja | kryzys | 1.00 | 3/3 | rozjazd [" in md


def test_incomplete_material_flag(conn, settings, seeded):
    sources, _ = seeded
    article_with(conn, "qa1", theme="energy", depth="lead_only")
    article(conn, "qa1", extracted=0)
    conn.commit()
    md = render(conn, settings, sources, ReportOutput())
    assert "**Materiał niepełny:** QA: 100% sygnałów tylko z tytułu i leadu; 1 artykułów bez ekstrakcji" in md


def test_generate_report_end_to_end(conn, settings, seeded, tmp_path):
    sources, ids = seeded
    fake = FakeAnthropic(lambda p: message(as_text(valid_report(ids)), 30_000, 3_000))
    result = generate_report(conn, LLMClient(settings.pricing, client=fake), settings, sources, THEMES,
                             DAY, tmp_path / "reports", now=NOW)
    assert result.path == tmp_path / "reports" / "2026-09-23.md" and result.path.exists()
    assert "### Obronność: alarm i zbrojenia" in result.path.read_text(encoding="utf-8")
    row = conn.execute("SELECT path, cost_usd, warnings FROM reports WHERE date = ?", (DAY,)).fetchone()
    assert row["path"] == str(result.path) and row["cost_usd"] == pytest.approx(result.synth.cost_usd)
    assert row["warnings"] is None
    assert conn.execute("SELECT COUNT(*) FROM daily_metrics WHERE date = ?", (DAY,)).fetchone()[0] == 4


def test_generate_report_without_signals_skips_llm(conn, settings, tmp_path):
    sources = seed_sources(conn)
    fake = FakeAnthropic()
    result = generate_report(conn, LLMClient(settings.pricing, client=fake), settings, sources, THEMES,
                             DAY, tmp_path, now=NOW)
    assert fake.messages.calls == [] and "brak sygnałów" in result.synth.warnings[0]
    assert conn.execute("SELECT warnings FROM reports").fetchone()[0].startswith("brak sygnałów")
