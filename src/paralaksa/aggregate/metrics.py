"""Daily metrics per theme × country (SPEC §7 `daily_metrics`, §9.3).

fetched_at identifies a collection run. Regular comparisons use the explicit two-calendar-day
publication window from sample.py; older and undated supplements remain visible in metadata.
"""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass

from paralaksa import db
from paralaksa.aggregate.sample import sample_articles, publication_meta, independence_count


@dataclass(frozen=True)
class SignalRow:
    id: int
    article_id: int
    theme_id: str
    subject_actor: str
    frame: str
    stance: str
    intensity: int
    signal_type: str
    summary_pl: str
    source_depth: str | None
    source_id: str
    country: str
    source_type: str
    url: str
    content_group: str | None = None
    publisher_group: str | None = None


def day_signals(conn: sqlite3.Connection, day: str) -> list[SignalRow]:
    rows = conn.execute(
        """
        SELECT g.id, g.article_id, g.theme_id, g.subject_actor, g.frame, g.stance, g.intensity,
               g.signal_type, g.summary_pl, g.source_depth, a.source_id, s.country, s.type, a.url, a.content_group, json_extract(s.metadata, '$.publisher_group')
        FROM signals g
        JOIN articles a ON a.id = g.article_id
        JOIN sources s ON s.id = a.source_id
        WHERE substr(a.fetched_at, 1, 10) = ?
        ORDER BY g.id
        """,
        (day,),
    ).fetchall()
    eligible = set(publication_meta(conn, day)["eligible_ids"])
    return [SignalRow(*r) for r in rows if r[1] in eligible]


def country_article_counts(conn: sqlite3.Connection, day: str) -> dict[str, int]:
    """All articles of the day per country (the volume that shares are normalized to)."""
    return dict(Counter(a["country"] for a in sample_articles(conn, day)))



def top_frames(signals: list[SignalRow], n: int = 3) -> list[tuple[str, int, int, list[int]]]:
    """(frame, n_articles, n_sources, article_ids), most articles first; ties alphabetically."""
    by_frame: dict[str, set[int]] = defaultdict(set)
    sources: dict[str, set[str]] = defaultdict(set)
    for s in signals:
        by_frame[s.frame].add(s.article_id)
        sources[s.frame].add(s.source_id)
    ranked = sorted(by_frame, key=lambda f: (-len(by_frame[f]), f))
    return [(f, len(by_frame[f]), independence_count([s for s in signals if s.frame == f]), sorted(by_frame[f])) for f in ranked[:n]]


def compute_daily_metrics(conn: sqlite3.Connection, day: str, save: bool = True) -> list[dict]:
    totals = country_article_counts(conn, day)
    groups: dict[tuple[str, str], list[SignalRow]] = defaultdict(list)
    for s in day_signals(conn, day):
        groups[(s.theme_id, s.country)].append(s)

    rows = []
    for (theme_id, country), sigs in sorted(groups.items()):
        articles = {s.article_id for s in sigs}
        frames = Counter(s.frame for s in sigs)
        dominant = sorted(frames, key=lambda f: (-frames[f], f))[0]
        rows.append({
            "date": day, "theme_id": theme_id, "country": country,
            "article_share": len(articles) / totals[country],
            "n_articles": len(articles),
            "n_sources": independence_count(sigs),
            "dominant_frame": dominant,
            "mean_intensity": sum(s.intensity for s in sigs) / len(sigs),
        })
    if save:
        db.upsert_daily_metrics(conn, day, rows)
    return rows
