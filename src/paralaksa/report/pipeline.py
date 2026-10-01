"""aggregate -> package -> synthesis -> Markdown file + `reports` row (used by `plx report` and `run-daily`)."""

from __future__ import annotations

import sqlite3
import json
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from paralaksa import db
from paralaksa.aggregate.metrics import compute_daily_metrics
from paralaksa.aggregate.package import build_data_package, known_article_ids
from paralaksa.config import Settings, Source, Theme
from paralaksa.report.render import collect_meta, render_markdown
from paralaksa.report.schema import ReportOutput
from paralaksa.report.synthesize import COVER_PROMPT, DEFAULT_PROMPT, SynthStats, cover_package, load_prompt, run_synthesis


# Brak więcej niż 1/3 aktywnych źródeł blokuje przebieg; mniej to ostrzeżenie informacyjne.
MAX_MISSING_SOURCES_DIVISOR = 3


@dataclass
class ReportResult:
    path: Path
    synth: SynthStats
    day_cost_usd: float
    n_signals: int
    complete: bool = False


def material_checks(conn: sqlite3.Connection, day: str, sources: list[Source], package: dict
                    ) -> tuple[list[str], list[str]]:
    """Warnings about the day's material and the blocking subset (incomplete extraction, over 1/3 sources missing)."""
    warnings, blocking = [], []
    failures = [f"{r['source_id']}: {r['pending']} oczekujących, {r['failed']} błędów" for r in package['mianowniki_zrodel']
                if r['pending'] or r['failed']]
    if failures:
        warnings.append('niepełna ekstrakcja: ' + '; '.join(failures))
        blocking.append(warnings[-1])
    active = [s.id for s in sources if s.active]
    observed = {r['source_id'] for r in package['mianowniki_zrodel']}
    missing_sources = [s for s in active if s not in observed]
    if missing_sources:
        warnings.append('brak materiałów z aktywnych źródeł: ' + ', '.join(missing_sources))
        if len(missing_sources) * MAX_MISSING_SOURCES_DIVISOR > len(active):
            blocking.append(warnings[-1])
    feed_errors = conn.execute("SELECT DISTINCT source_id FROM fetch_log WHERE substr(fetched_at,1,10)=? AND status != 'ok'", (day,)).fetchall()
    if feed_errors:
        warnings.append('błędy kanałów: ' + ', '.join(r[0] for r in feed_errors))
    return warnings, blocking


def material_status(conn: sqlite3.Connection, settings: Settings, sources: list[Source], themes: list[Theme],
                    day: str, out_dir: Path) -> dict:
    """Daily run without synthesis: metrics and material checks only, written to <day>.status.json.

    Since 2026-10-01 the report is made locally (Codex, `plx report`), so Actions only gathers and extracts.
    A later local report overwrites this status."""
    db.upsert_sources(conn, sources)
    compute_daily_metrics(conn, day)
    package = build_data_package(conn, day, settings, themes)
    warnings, blocking = material_checks(conn, day, sources, package)
    pending = conn.execute("SELECT COUNT(*) FROM articles WHERE extracted = 0 AND substr(fetched_at, 1, 10) = ?",
                           (day,)).fetchone()[0]
    if pending:
        blocking.append(f"{pending} artykułów bez ekstrakcji")
    status = {"date": day, "complete": not blocking, "synthesis": "lokalnie (plx report)",
              "n_signals": sum(c["n_sygnalow"] for c in package["kraje"].values()),
              "cost_usd": db.spent_on(conn, day), "warnings": warnings, "blocking": blocking,
              "sources": package['mianowniki_zrodel']}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{day}.status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    return status


def generate_report(
    conn: sqlite3.Connection, llm, settings: Settings, sources: list[Source], themes: list[Theme],
    day: str, out_dir: Path, now: datetime | None = None,
) -> ReportResult:
    now = now or db.utc_now()
    db.upsert_sources(conn, sources)
    compute_daily_metrics(conn, day)
    package = build_data_package(conn, day, settings, themes)
    n_signals = sum(c["n_sygnalow"] for c in package["kraje"].values())
    if n_signals == 0:
        report = ReportOutput()
        stats = SynthStats(model=settings.models.synthesize, prompt_version=load_prompt()[1],
                           warnings=["brak sygnałów z tego dnia – synteza pominięta"])
    else:
        cover = settings.report.form == "okladka"
        report, stats = run_synthesis(conn, llm, settings, cover_package(package) if cover else package,
                                      known_article_ids(conn, day), now=now,
                                      prompt_path=COVER_PROMPT if cover else DEFAULT_PROMPT)

    if not any(report.model_dump().values()):
        stats.warnings.append("synteza nie dostarczyła żadnych tez; raport jest niepełny")
    # Blokujące: synteza/walidacja/ekstrakcja. Informacyjne (pojedyncze źródło, kanał) nie
    # oznaczają nieudanego przebiegu, ale są widoczne w raporcie i statusie.
    # Sanityzacja po nieudanym ponowieniu usuwa tylko wadliwe tezy; reszta raportu jest zwalidowana.
    blocking = [w for w in stats.warnings if not w.startswith('walidacja po ponowieniu')]
    material_warnings, material_blocking = material_checks(conn, day, sources, package)
    stats.warnings += material_warnings
    blocking += material_blocking
    meta = collect_meta(conn, day, settings, sources, themes, package, stats.model, stats.prompt_version,
                        stats.warnings)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{day}.md"
    path.write_text(render_markdown(report, package, meta), encoding="utf-8")
    db.save_report(conn, day, str(path), meta.total_cost, stats.warnings, now=now)
    from paralaksa.report.validate import evidence_items
    # Exact validated output is kept for reproducible audit; no article bodies or quotes.
    output = report.model_dump()
    (out_dir / f"{day}.json").write_text(json.dumps({"report": output, "publication": package['publikacje'],
        "semantic_review": "pending", "warnings": stats.warnings}, ensure_ascii=False, indent=2), encoding='utf-8')
    registry = {s['signal_id']: s for s in package['dowody']}
    audit = [{"path": p, "claim": item.model_dump(),
              "context": output[p.split(".")[0]][int(p.split(".")[1])], "signals": [registry[e.signal_id] for e in item.dowody],
              "review": "pending"} for p,item,_,_ in evidence_items(report)]
    random.Random(day).shuffle(audit)
    (out_dir / f"{day}.audit.json").write_text(json.dumps({"seed": day, "sample": audit[:30],
        "claims_total": len(audit), "meaning": "czy sygnały wspierają opis przekazu, nie prawdziwość zdarzeń"},
        ensure_ascii=False, indent=2), encoding='utf-8')
    summary = [f"# Paralaksa narracji – skrót {day}", "", f"[Pełny raport]({day}.md)", ""]
    from paralaksa.report.render import _refs, CONFIDENCE_PL
    for item in report.w_skrocie[:3]:
        summary.append(f"- {item.tekst} (pewność: {CONFIDENCE_PL[item.pewnosc]}) {_refs(item.article_ids,meta)}")
    if not report.w_skrocie:
        summary.append("Brak zweryfikowanych punktów skrótu.")
    summary += ["", f"Ograniczenia: raport {package['publikacje']['status']}; daty publikacji "
                f"{package['publikacje']['published_min']} — {package['publikacje']['published_max']}. "
                "Próbka źródeł, nie całe media krajów. Audyt semantyczny oczekuje. "
                "Wynik opisuje przekaz, nie dowodzi zdarzeń ani ich nie prognozuje."]
    if not package['linia_bazowa']['dostepna']:
        summary += ["Brak linii bazowej: nie formułujemy trendów."]
    summary += [f"Ostrzeżenie: {w}" for w in stats.warnings]
    (out_dir / f"{day}.short.md").write_text('\n'.join(summary)+'\n', encoding='utf-8')
    complete = bool(stats.calls and any(output.values()) and not blocking and not meta.pending_articles)
    status = {"date": day, "complete": complete, "synthesis_calls": stats.calls,
              "cost_usd": meta.total_cost, "elapsed_s": stats.elapsed_s,
              "semantic_review": "pending", "warnings": stats.warnings, "blocking": blocking,
              "sources": package['mianowniki_zrodel']}
    (out_dir / f"{day}.status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2), encoding='utf-8')
    return ReportResult(path, stats, meta.total_cost, n_signals, complete)
