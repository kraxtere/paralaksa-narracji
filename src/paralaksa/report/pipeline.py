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
from paralaksa.report.synthesize import SynthStats, load_prompt, run_synthesis


@dataclass
class ReportResult:
    path: Path
    synth: SynthStats
    day_cost_usd: float
    n_signals: int
    complete: bool = False


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
        report, stats = run_synthesis(conn, llm, settings, package, known_article_ids(conn, day), now=now)

    if not any(report.model_dump().values()):
        stats.warnings.append("synteza nie dostarczyła żadnych tez; raport jest niepełny")
    observed = {r['source_id'] for r in package['mianowniki_zrodel']}
    missing_sources = [s.id for s in sources if s.active and s.id not in observed]
    if missing_sources:
        stats.warnings.append('brak materiałów z aktywnych źródeł: ' + ', '.join(missing_sources))
    failures = [f"{r['source_id']}: {r['pending']} oczekujących, {r['failed']} błędów" for r in package['mianowniki_zrodel']
                if r['pending'] or r['failed']]
    if failures:
        stats.warnings.append('niepełna ekstrakcja: ' + '; '.join(failures))
    feed_errors = conn.execute("SELECT DISTINCT source_id FROM fetch_log WHERE substr(fetched_at,1,10)=? AND status != 'ok'", (day,)).fetchall()
    if feed_errors:
        stats.warnings.append('błędy kanałów: ' + ', '.join(r[0] for r in feed_errors))
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
    complete = bool(stats.calls and any(output.values()) and not stats.warnings and not meta.pending_articles)
    status = {"date": day, "complete": complete, "synthesis_calls": stats.calls,
              "cost_usd": meta.total_cost, "elapsed_s": stats.elapsed_s,
              "semantic_review": "pending", "warnings": stats.warnings,
              "sources": package['mianowniki_zrodel']}
    (out_dir / f"{day}.status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2), encoding='utf-8')
    return ReportResult(path, stats, meta.total_cost, n_signals, complete)
