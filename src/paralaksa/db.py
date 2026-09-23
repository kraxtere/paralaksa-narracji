"""SQLite schema and data access."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from paralaksa.config import Source

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY, name TEXT, country TEXT, language TEXT, type TEXT
);

CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY,
  source_id TEXT REFERENCES sources(id),
  url TEXT UNIQUE,
  url_hash TEXT UNIQUE,
  title TEXT,
  lead TEXT,
  fulltext TEXT,
  language TEXT,
  published_at TEXT,
  fetched_at TEXT,
  extracted INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_articles_source_published
  ON articles(source_id, published_at);

CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY,
  article_id INTEGER REFERENCES articles(id),
  theme_id TEXT,
  subject_actor TEXT,
  frame TEXT,
  stance TEXT,
  intensity INTEGER,
  signal_type TEXT,
  summary_pl TEXT,
  evidence_span TEXT,
  model TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS daily_metrics (
  date TEXT, theme_id TEXT, country TEXT,
  article_share REAL,
  n_articles INTEGER, n_sources INTEGER,
  dominant_frame TEXT, mean_intensity REAL,
  PRIMARY KEY (date, theme_id, country)
);

CREATE TABLE IF NOT EXISTS reports (
  date TEXT PRIMARY KEY, path TEXT, created_at TEXT, cost_usd REAL
);

-- Dziennik pobrań kanałów (ostrzeżenia o źródłach bez nowych artykułów).
CREATE TABLE IF NOT EXISTS fetch_log (
  id INTEGER PRIMARY KEY,
  source_id TEXT REFERENCES sources(id),
  feed_url TEXT,
  fetched_at TEXT,
  status TEXT,        -- ok | error | robots_disallowed
  n_items INTEGER,
  n_new INTEGER,
  error TEXT
);
CREATE INDEX IF NOT EXISTS idx_fetch_log_source ON fetch_log(source_id, fetched_at);
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 0:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    conn.commit()


def upsert_sources(conn: sqlite3.Connection, sources: Iterable[Source]) -> None:
    conn.executemany(
        """
        INSERT INTO sources (id, name, country, language, type) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          name = excluded.name, country = excluded.country,
          language = excluded.language, type = excluded.type
        """,
        [(s.id, s.name, s.country, s.language, s.type) for s in sources],
    )
    conn.commit()


@dataclass
class ArticleRow:
    source_id: str
    url: str
    url_hash: str
    title: str
    lead: str | None
    language: str
    published_at: str
    fetched_at: str
    fulltext: str | None = None


def insert_article(conn: sqlite3.Connection, a: ArticleRow) -> int | None:
    """Insert an article; return its id, or None if the URL is already stored."""
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO articles
          (source_id, url, url_hash, title, lead, fulltext, language, published_at, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (a.source_id, a.url, a.url_hash, a.title, a.lead, a.fulltext,
         a.language, a.published_at, a.fetched_at),
    )
    return cur.lastrowid if cur.rowcount else None


def url_hash_exists(conn: sqlite3.Connection, url_hash: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM articles WHERE url_hash = ?", (url_hash,)
    ).fetchone() is not None


def recent_titles(conn: sqlite3.Connection, source_id: str, since: datetime) -> list[str]:
    rows = conn.execute(
        "SELECT title FROM articles WHERE source_id = ? AND published_at >= ?",
        (source_id, to_iso(since)),
    ).fetchall()
    return [r["title"] for r in rows if r["title"]]


def set_fulltext(conn: sqlite3.Connection, article_id: int, text: str | None) -> None:
    conn.execute("UPDATE articles SET fulltext = ? WHERE id = ?", (text, article_id))


def log_fetch(
    conn: sqlite3.Connection,
    source_id: str,
    feed_url: str,
    fetched_at: str,
    status: str,
    n_items: int = 0,
    n_new: int = 0,
    error: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO fetch_log (source_id, feed_url, fetched_at, status, n_items, n_new, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (source_id, feed_url, fetched_at, status, n_items, n_new, error),
    )


def stale_sources(
    conn: sqlite3.Connection, source_ids: Iterable[str], days: int, now: datetime | None = None
) -> list[str]:
    """Sources observed for at least `days` days that yielded no new articles in that window."""
    now = now or utc_now()
    cutoff = to_iso(now - timedelta(days=days))
    stale = []
    for sid in source_ids:
        row = conn.execute(
            """
            SELECT MIN(fetched_at) AS first_fetch,
                   MAX(CASE WHEN n_new > 0 THEN fetched_at END) AS last_new
            FROM fetch_log WHERE source_id = ?
            """,
            (sid,),
        ).fetchone()
        if row["first_fetch"] is None or row["first_fetch"] > cutoff:
            continue
        if row["last_new"] is None or row["last_new"] < cutoff:
            stale.append(sid)
    return stale
