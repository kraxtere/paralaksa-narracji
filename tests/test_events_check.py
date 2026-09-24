import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from paralaksa import cli, db
from paralaksa.events.check import (
    CardError,
    card_paths,
    check_card,
    headline_matches,
    load_card,
    parse_meta,
    pick,
    relation_day,
    render_check,
    Snapshot,
    title_variants,
)
from paralaksa.ingest.dedup import url_hash
from paralaksa.ingest.http import PoliteClient

URL = "https://news.example/a/1"

CARD = """---
id: 2026-01-09-test
tytul: Zdarzenie testowe
status: kandydat
forma: dwie_opowiesci
fakt: {czas: null, opis: test, zrodlo_pierwotne: null}
relacje:
  - id: r1
    kto: Gazeta
    rola: redakcja
    gatunek: wiadomosc
    link: https://news.example/a/1
    publikacja: '2026-01-09T12:00+01:00'
    aktualizacja: null
    archiwum: {link: null, wykonano: null}
    naglowek: 'Pierwszy nagłówek o zdarzeniu…'
    sprawdzil: null
  - id: r2
    kto: Bez linku
    link: null
kontrasty: []
---

## Fakt
"""


def page(h1: str, og: str | None = None, published: str = "2026-01-09T11:00:00Z") -> str:
    og_tag = f'<meta property="og:title" content="{og}">' if og else ""
    ld = json.dumps({"@type": "NewsArticle", "datePublished": published, "dateModified": published})
    return (f"<html><head>{og_tag}<script type=\"application/ld+json\">{ld}</script></head>"
            f"<body><h1><a href='/'></a></h1><h1>{h1}</h1></body></html>")


def wayback(snapshots: dict[str, str], cdx_status: int = 200):
    """Mock web.archive.org: CDX lists `snapshots` (timestamp → HTML); /web/<ts>id_/ serves them."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/cdx/search/cdx":
            if cdx_status != 200:
                return httpx.Response(cdx_status, text="This type of CDX query requires authorization.")
            rows = [["timestamp", "original"]] + [[ts, URL] for ts in sorted(snapshots)]
            return httpx.Response(200, json=rows)
        m = re.match(r"/web/(\d{8})(\d{6})id_/(.*)", request.url.path)
        if m:
            ts = m.group(1) + m.group(2)
            if ts in snapshots:
                return httpx.Response(200, text=snapshots[ts])
            # przybliżenie przekierowania Wayback: najbliższa kopia
            nearest = min(snapshots, key=lambda s: abs(int(s) - int(ts)))
            return httpx.Response(302, headers={"Location": f"https://web.archive.org/web/{nearest}id_/{URL}"})
        return httpx.Response(404)
    return handler


def client_for(handler) -> PoliteClient:
    return PoliteClient("test-agent", per_domain_delay_s=0, transport=httpx.MockTransport(handler), sleep=lambda s: None)


@pytest.fixture
def card_file(tmp_path: Path) -> Path:
    p = tmp_path / "2026-01-09-test.md"
    p.write_text(CARD, encoding="utf-8")
    return p


def test_load_card_and_relation_day(card_file):
    card = load_card(card_file)
    assert card["id"] == "2026-01-09-test"
    assert relation_day(card, card["relacje"][0]) == date(2026, 1, 9)
    assert relation_day(card, card["relacje"][1]) == date(2026, 1, 9)  # z id karty


def test_load_card_without_front_matter(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("# bez nagłówka\n", encoding="utf-8")
    with pytest.raises(CardError):
        load_card(p)


def test_card_paths_skip_template_readme_and_yaml(tmp_path):
    for name in ["_szablon_zdarzenia.md", "README.md", "a.yaml", "2026-01-01-a.md"]:
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert [p.name for p in card_paths([tmp_path])] == ["2026-01-01-a.md"]


def test_parse_meta_skips_empty_h1_and_reads_json_ld():
    m = parse_meta(page("Nagłówek &amp; więcej", og="Tytuł do udostępnień", published="2026-01-09T11:05:00Z"))
    assert m.h1 == "Nagłówek & więcej"
    assert m.og_title == "Tytuł do udostępnień"
    assert m.published == "2026-01-09T11:05:00Z"


def test_headline_matches_prefix_only_when_card_is_shortened():
    assert headline_matches("Pierwszy nagłówek…", "Pierwszy nagłówek o zdarzeniu")
    assert not headline_matches("Pierwszy nagłówek", "Pierwszy nagłówek o zdarzeniu")
    assert headline_matches("It’s “big”", "It's \"big\"")


def test_site_logo_h1_falls_back_to_og_title_without_site_name():
    m = parse_meta('<meta property="og:title" content="Komunikat MON w sprawie granicy - Ministerstwo - Portal Gov.pl">'
                   "<h1>gov.pl Serwis Rzeczypospolitej Polskiej</h1>")
    assert m.headline == "Komunikat MON w sprawie granicy"
    assert title_variants("A – B - C") == ["A – B - C", "A – B", "A"]


def test_pick_keeps_first_and_last():
    snaps = [Snapshot(f"2026010912{i:02d}00", URL) for i in range(10)]
    chosen = pick(snaps, 3)
    assert chosen[0] == snaps[0] and chosen[-1] == snaps[-1] and len(chosen) == 3


def test_check_detects_headline_change_and_proposes_archive(card_file, conn):
    snaps = {
        "20260109105000": page("Stary nagłówek", published="2026-01-09T10:50:00Z"),  # przed publikacją z karty
        "20260109113000": page("Pierwszy nagłówek o zdarzeniu", published="2026-01-09T11:00:00Z"),
        "20260109160000": page("Nowy nagłówek po aktualizacji", published="2026-01-09T11:00:00Z"),
    }
    before = card_file.read_bytes()
    with client_for(wayback(snaps)) as client:
        cc = check_card(card_file, client, None)
    assert card_file.read_bytes() == before  # karta nietknięta
    r1, r2 = cc.relations
    hints = "\n".join(r1.hints)
    assert len(r1.snapshots) == 3 and len(r1.captures) == 3
    assert "zmieniał się w oknie (3 wersje" in hints
    assert "propozycja archiwum: https://web.archive.org/web/20260109113000/" in hints  # pierwsza po publikacji
    assert "pierwsza kopia" in hints  # kopia 11:55 (+01) wcześniejsza niż publikacja 12:00
    assert "sprawdzil" not in hints
    assert r2.hints == ["brak linku: relacji nie da się sprawdzić (zasada 1)"]
    report = render_check(cc, checked_at=datetime(2026, 9, 24, tzinfo=timezone.utc))
    assert "Karta nie została zmieniona" in report
    assert "2026-01-09 12:30 (+01:00)" in report  # czas kopii w strefie z karty


def test_check_flags_alternating_headlines_as_ab_not_change(card_file):
    a = page("Pierwszy nagłówek o zdarzeniu", published="2026-01-09T11:00:00Z")
    b = page("Wersja B", published="2026-01-09T11:04:00Z")
    snaps = {"20260109113000": a, "20260109113500": b, "20260109114000": a, "20260109114500": b}
    with client_for(wayback(snaps)) as client:
        cc = check_card(card_file, client, None)
    hints = "\n".join(cc.relations[0].hints)
    assert "NA PRZEMIAN" in hints and "zmieniał się" not in hints


def test_check_warns_when_card_headline_not_in_any_capture(card_file):
    snaps = {"20260109113000": page("Zupełnie inny tytuł", published="2026-01-09T11:00:00Z")}
    with client_for(wayback(snaps)) as client:
        cc = check_card(card_file, client, None)
    assert any("nie występuje w żadnej" in h for h in cc.relations[0].hints)


def test_check_flags_republication_time(card_file):
    snaps = {"20260109150000": page("Pierwszy nagłówek o zdarzeniu", published="2026-01-09T08:17:00Z")}
    with client_for(wayback(snaps)) as client:
        cc = check_card(card_file, client, None)
    assert any("ponowna publikacja" in h for h in cc.relations[0].hints)


def test_whole_hour_difference_is_reported_as_mislabeled_zone(card_file):
    # publikacja 12:00+01:00 = 11:00Z; strona podaje czas lokalny 12:00 oznaczony jako „Z”
    snaps = {"20260109113000": page("Pierwszy nagłówek o zdarzeniu", published="2026-01-09T12:00:00Z")}
    with client_for(wayback(snaps)) as client:
        cc = check_card(card_file, client, None)
    hints = "\n".join(cc.relations[0].hints)
    assert "złą strefą" in hints and "ponowna publikacja" not in hints


def test_card_headline_matches_og_title_with_site_suffix(card_file):
    snaps = {"20260109113000": page("gov.pl Serwis", og="Pierwszy nagłówek o zdarzeniu - Ministerstwo - Portal")}
    with client_for(wayback(snaps)) as client:
        cc = check_card(card_file, client, None)
    assert not any("nie występuje" in h for h in cc.relations[0].hints)


def test_cdx_refusal_falls_back_to_nearest_captures(card_file):
    snaps = {
        "20260109113000": page("Pierwszy nagłówek o zdarzeniu"),
        "20260110200000": page("Pierwszy nagłówek o zdarzeniu"),
    }
    with client_for(wayback(snaps, cdx_status=403)) as client:
        cc = check_card(card_file, client, None)
    r1 = cc.relations[0]
    assert [s.timestamp for s in r1.snapshots] == ["20260109113000", "20260110200000"]
    assert "CDX odmówił (HTTP 403)" in r1.note


def test_no_captures_suggests_own_copy(card_file):
    def handler(request):
        if request.url.path == "/cdx/search/cdx":
            return httpx.Response(200, text="")
        return httpx.Response(404)
    with client_for(handler) as client:
        cc = check_card(card_file, client, None)
    assert any("zrobić własną kopię" in h for h in cc.relations[0].hints)


def test_db_lookup_shows_title_as_we_fetched_it(card_file, conn, make_source):
    db.upsert_sources(conn, [make_source(id="gz")])
    db.insert_article(conn, db.ArticleRow(
        source_id="gz", url=URL, url_hash=url_hash(URL), title="Tytuł z naszego RSS", lead=None, language="pl",
        published_at="2026-01-09T11:00:00+00:00", fetched_at="2026-01-10T05:00:00+00:00",
    ))
    snaps = {"20260109113000": page("Pierwszy nagłówek o zdarzeniu")}
    with client_for(wayback(snaps)) as client:
        cc = check_card(card_file, client, conn)
    assert cc.relations[0].db_hit.title == "Tytuł z naszego RSS"
    assert "Tytuł z naszego RSS" in render_check(cc)


def test_cli_events_check_writes_report_and_fails_on_bad_card(card_file, tmp_path, monkeypatch):
    snaps = {"20260109113000": page("Pierwszy nagłówek o zdarzeniu")}
    real = PoliteClient

    def fake(*args, **kwargs):
        return real("test-agent", per_domain_delay_s=0, transport=httpx.MockTransport(wayback(snaps)),
                    sleep=lambda s: None)
    monkeypatch.setattr(cli, "PoliteClient", fake)
    out = tmp_path / "checks"
    runner = CliRunner()
    result = runner.invoke(cli.app, ["events", "check", str(card_file), "-o", str(out),
                                     "--db", str(tmp_path / "brak.db")])
    assert result.exit_code == 0, result.output
    assert (out / "2026-01-09-test.md").exists()
    assert not (tmp_path / "brak.db").exists()  # sprawdzenie nie zakłada pustej bazy

    bad = tmp_path / "zla.md"
    bad.write_text("brak nagłówka", encoding="utf-8")
    result = runner.invoke(cli.app, ["events", "check", str(bad), "-o", str(out), "--db", str(tmp_path / "brak.db")])
    assert result.exit_code == 1
