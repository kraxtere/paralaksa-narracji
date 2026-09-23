"""Synthetic articles/signals for aggregation and report tests."""

from __future__ import annotations

import itertools

from paralaksa import db
from paralaksa.config import Source

DAY = "2026-09-23"
_counter = itertools.count(1)

SOURCES = [
    # (id, country, type, fulltext)
    ("pl1", "PL", "private", True), ("pl2", "PL", "private", False),
    ("ua1", "UA", "agency", True), ("ua2", "UA", "private", True),
    ("de1", "DE", "public", True), ("de2", "DE", "private", False),
    ("uk1", "UK", "public", True), ("uk2", "UK", "private", True),
    ("qa1", "QA", "public", True),
]


def seed_sources(conn) -> list[Source]:
    sources = [Source(id=i, name=i.upper(), country=c, language="en", type=t,
                      feeds=[{"url": f"https://{i}.example/rss"}], fulltext=f) for i, c, t, f in SOURCES]
    db.upsert_sources(conn, sources)
    return sources


def article(conn, source_id: str, day: str = DAY, extracted: int = 1) -> int:
    n = next(_counter)
    aid = db.insert_article(conn, db.ArticleRow(
        source_id=source_id, url=f"https://{source_id}.example/a/{n}", url_hash=f"h-{n}",
        title=f"Artykuł {n}", lead="Lead.", language="en",
        published_at=f"{day}T04:00:00+00:00", fetched_at=f"{day}T05:00:00+00:00",
    ))
    conn.execute("UPDATE articles SET extracted = ? WHERE id = ?", (extracted, aid))
    return aid


def signal(conn, article_id: int, theme: str = "ukraine_war", actor: str = "UA", frame: str = "rama",
           stance: str = "neutralny", intensity: int = 3, depth: str = "fulltext") -> None:
    conn.execute(
        """
        INSERT INTO signals (article_id, theme_id, subject_actor, frame, stance, intensity, signal_type,
                             summary_pl, evidence_span, model, created_at, source_depth, prompt_version)
        VALUES (?, ?, ?, ?, ?, ?, 'ocena', ?, 'dowód', 'deepseek-v4-pro', ?, ?, 'extract_signals@test')
        """,
        (article_id, theme, actor, frame, stance, intensity, f"Streszczenie sygnału {article_id}.",
         f"{DAY}T06:00:00+00:00", depth),
    )


def article_with(conn, source_id: str, day: str = DAY, **signal_kw) -> int:
    aid = article(conn, source_id, day)
    signal(conn, aid, **signal_kw)
    return aid


def seed_alarm_convergence(conn) -> dict[str, list[int]]:
    """security_defense in PL/UA/DE/UK with alarm, 2 sources each; UK also has one reassuring signal."""
    ids: dict[str, list[int]] = {}
    for country in ("pl", "ua", "de", "uk"):
        ids[country] = [
            article_with(conn, f"{country}1", theme="security_defense", actor="RU",
                         frame="zagrożenie ze wschodu", stance="alarm", intensity=4),
            article_with(conn, f"{country}2", theme="security_defense", actor="RU",
                         frame="zbrojenia", stance="krytyka", intensity=3),
        ]
    ids["counter"] = [article_with(conn, "uk2", theme="security_defense", actor="NATO",
                                   frame="sojusz odstrasza", stance="uspokojenie", intensity=2)]
    conn.commit()
    return ids
