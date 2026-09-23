"""aggregate -> package -> synthesis -> Markdown file + `reports` row (used by `plx report` and `run-daily`)."""

from __future__ import annotations

import sqlite3
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


def generate_report(
    conn: sqlite3.Connection, llm, settings: Settings, sources: list[Source], themes: list[Theme],
    day: str, out_dir: Path, now: datetime | None = None,
) -> ReportResult:
    now = now or db.utc_now()
    compute_daily_metrics(conn, day)
    package = build_data_package(conn, day, settings, themes)
    n_signals = sum(c["n_sygnalow"] for c in package["kraje"].values())
    if n_signals == 0:
        report = ReportOutput()
        stats = SynthStats(model=settings.models.synthesize, prompt_version=load_prompt()[1],
                           warnings=["brak sygnałów z tego dnia – synteza pominięta"])
    else:
        report, stats = run_synthesis(conn, llm, settings, package, known_article_ids(conn, day), now=now)

    meta = collect_meta(conn, day, settings, sources, themes, package, stats.model, stats.prompt_version,
                        stats.warnings)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{day}.md"
    path.write_text(render_markdown(report, package, meta), encoding="utf-8")
    db.save_report(conn, day, str(path), meta.total_cost, stats.warnings, now=now)
    return ReportResult(path, stats, meta.total_cost, n_signals)
