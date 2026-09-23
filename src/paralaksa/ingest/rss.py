"""RSS/Atom ingest: fetch feeds, normalize entries, deduplicate, store."""

from __future__ import annotations

import html
import logging
import re
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import feedparser
import httpx

from paralaksa import db
from paralaksa.config import Feed, Settings, Source
from paralaksa.ingest.dedup import clean_url, is_similar_title, url_hash
from paralaksa.ingest.fulltext import fetch_fulltext
from paralaksa.ingest.http import PoliteClient, RobotsDisallowed
from paralaksa.ingest.prefilter import is_offtopic

log = logging.getLogger(__name__)

MAX_LEAD_CHARS = 2000


@dataclass
class FeedEntry:
    url: str
    title: str
    lead: str | None
    published: datetime | None
    categories: list[str] = field(default_factory=list)


@dataclass
class SourceResult:
    source_id: str
    fetched: int = 0
    new: int = 0
    filtered: int = 0
    duplicates: int = 0
    errors: list[str] = field(default_factory=list)
    fulltext_ok: int = 0


def clean_html(text: str | None) -> str | None:
    if not text:
        return None
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text[:MAX_LEAD_CHARS] or None


def clean_link(url: str) -> str | None:
    """Fix feed links like 'https://site.uahttps://other/...' (seen in Ukrinform); reject non-http."""
    url = url.strip()
    last = max(url.rfind("http://"), url.rfind("https://"))
    if last > 0:
        url = url[last:]
    return url if url.startswith(("http://", "https://")) else None


def _entry_datetime(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def parse_feed(content: bytes | str) -> list[FeedEntry]:
    """Parse RSS 2.0 / RSS 1.0 (RDF) / Atom into normalized entries."""
    parsed = feedparser.parse(content)
    if not parsed.entries and (parsed.bozo or not parsed.version):
        # np. strona HTML zwrócona z kodem 200 zamiast kanału
        reason = parsed.get("bozo_exception") or "odpowiedź nie jest kanałem RSS/Atom"
        raise ValueError(f"niepoprawny kanał: {reason}")
    entries = []
    for e in parsed.entries:
        url = clean_link(e.get("link") or "")
        title = clean_html(e.get("title")) or ""
        if not url or not title:
            continue
        entries.append(
            FeedEntry(
                url=url,
                title=title,
                lead=clean_html(e.get("summary") or e.get("description")),
                published=_entry_datetime(e),
                categories=[t.get("term", "") for t in e.get("tags", []) if t.get("term")],
            )
        )
    return entries


def ingest_feed(
    conn: sqlite3.Connection,
    client: PoliteClient,
    source: Source,
    feed: Feed,
    settings: Settings,
    result: SourceResult,
    now: datetime,
) -> list[tuple[int, str]]:
    """Ingest a single feed; returns (article_id, url) pairs of newly inserted articles."""
    fetched_at = db.to_iso(now)
    try:
        resp = client.get(feed.url)
        entries = parse_feed(resp.content)
    except RobotsDisallowed:
        msg = f"robots.txt blokuje kanał {feed.url}"
        result.errors.append(msg)
        db.log_fetch(conn, source.id, feed.url, fetched_at, "robots_disallowed", error=msg)
        conn.commit()
        return []
    except (httpx.HTTPError, ValueError) as e:
        msg = f"{feed.url}: {e}"
        result.errors.append(msg)
        db.log_fetch(conn, source.id, feed.url, fetched_at, "error", error=str(e)[:500])
        conn.commit()
        return []

    cfg = settings.ingest
    recent = db.recent_titles(conn, source.id, now - timedelta(hours=cfg.title_dedup_hours))
    inserted: list[tuple[int, str]] = []
    for entry in entries:
        result.fetched += 1
        if is_offtopic(entry.url, entry.title, entry.categories, feed.section):
            result.filtered += 1
            continue
        h = url_hash(entry.url)
        if db.url_hash_exists(conn, h) or is_similar_title(entry.title, recent, cfg.title_similarity):
            result.duplicates += 1
            continue
        row = db.ArticleRow(
            source_id=source.id,
            url=clean_url(entry.url),
            url_hash=h,
            title=entry.title,
            lead=entry.lead,
            language=source.language,
            published_at=db.to_iso(entry.published or now),
            fetched_at=fetched_at,
        )
        article_id = db.insert_article(conn, row)
        if article_id is None:
            result.duplicates += 1
            continue
        recent.append(entry.title)
        inserted.append((article_id, row.url))
    result.new += len(inserted)
    db.log_fetch(conn, source.id, feed.url, fetched_at, "ok", n_items=len(entries), n_new=len(inserted))
    conn.commit()
    return inserted


def _round_robin_by_host(items: list[tuple[str, int, str]]) -> list[tuple[str, int, str]]:
    """Interleave (source_id, article_id, url) by host so per-domain delays overlap."""
    queues: dict[str, deque] = defaultdict(deque)
    for item in items:
        queues[urlsplit(item[2]).netloc].append(item)
    ordered = []
    while queues:
        for host in list(queues):
            ordered.append(queues[host].popleft())
            if not queues[host]:
                del queues[host]
    return ordered


def ingest_sources(
    conn: sqlite3.Connection,
    client: PoliteClient,
    sources: list[Source],
    settings: Settings,
    fulltext: bool = True,
    now: datetime | None = None,
) -> list[SourceResult]:
    now = now or db.utc_now()
    db.upsert_sources(conn, sources)
    results: dict[str, SourceResult] = {}
    pending_fulltext: list[tuple[str, int, str]] = []
    for source in sources:
        result = results[source.id] = SourceResult(source.id)
        for feed in source.feeds:
            new = ingest_feed(conn, client, source, feed, settings, result, now)
            if fulltext and source.fulltext:
                pending_fulltext.extend((source.id, aid, url) for aid, url in new)

    for source_id, article_id, url in _round_robin_by_host(pending_fulltext):
        text = fetch_fulltext(client, url, settings.ingest.max_fulltext_words)
        if text:
            db.set_fulltext(conn, article_id, text)
            results[source_id].fulltext_ok += 1
        conn.commit()
    return list(results.values())
