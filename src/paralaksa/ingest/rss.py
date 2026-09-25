"""RSS/Atom ingest: fetch feeds, normalize entries, deduplicate, store."""

from __future__ import annotations

import html
import logging
import re
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

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


WP_FOOTER = re.compile(r"\s*The post .{1,300}? appeared first on .{1,120}?\.?\s*$", re.S)


def strip_wp_footer(lead: str | None) -> str | None:
    """Drop WordPress's `The post <title> appeared first on <site>.` added to RSS summaries."""
    return (WP_FOOTER.sub("", lead) or None) if lead else lead


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


SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9", "news": "http://www.google.com/schemas/sitemap-news/0.9"}


def slug_title(url: str) -> str:
    """Headline from the last URL segment: `.../news/2026/9/25/tekst-naglowka-154628` -> `tekst naglowka`."""
    slug = unquote(urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1])
    slug = re.sub(r"[-_]\d+$", "", re.sub(r"\.[a-z]{2,5}$", "", slug))
    words = [w for w in re.split(r"[-_]+", slug) if w]
    return " ".join(words) if len(words) >= 3 else ""


def feed_urls(url: str, now: datetime) -> list[str]:
    """Expand a daily feed template (`{yyyy}`, `{mm}`, `{dd}`, no zero padding) for days D-1 and D UTC."""
    if "{yyyy}" not in url:
        return [url]
    days = [(now - timedelta(days=1)).date(), now.date()]
    return [url.format(yyyy=d.year, mm=d.month, dd=d.day) for d in days]


def parse_news_sitemap(content: bytes | str) -> list[FeedEntry]:
    """Google News sitemap (`<urlset>` with `news:title` and `news:publication_date`), e.g. Global Times."""
    root = ElementTree.fromstring(content.encode("utf-8") if isinstance(content, str) else content)
    entries = []
    for node in root.findall("sm:url", SITEMAP_NS):
        url = clean_link((node.findtext("sm:loc", "", SITEMAP_NS) or "").strip())
        title = clean_html(node.findtext("news:news/news:title", None, SITEMAP_NS)) or ""
        plain = node.find("news:news", SITEMAP_NS) is None
        if plain and not title:
            title = slug_title(url)  # zwykła mapa strony (np. WAFA): nagłówek tylko w adresie
        if not url or not title:
            continue
        published = None
        raw = (node.findtext("news:news/news:publication_date", "", SITEMAP_NS) or "").strip()
        if plain:
            raw = (node.findtext("sm:lastmod", "", SITEMAP_NS) or "").strip()
        if raw:
            try:
                published = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                published = None
        keywords = node.findtext("news:news/news:keywords", "", SITEMAP_NS) or ""
        entries.append(FeedEntry(url=url, title=title, lead=None, published=published,
                                 categories=[k.strip() for k in keywords.split(",") if k.strip()]))
    return entries


def parse_feed(content: bytes | str) -> list[FeedEntry]:
    """Parse RSS 2.0 / RSS 1.0 (RDF) / Atom, or a Google News sitemap, into normalized entries."""
    head = content[:600].decode("utf-8", "ignore") if isinstance(content, bytes) else content[:600]
    if "<urlset" in head:
        return parse_news_sitemap(content)
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
                lead=strip_wp_footer(clean_html(e.get("summary") or e.get("description"))),
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
    url: str | None = None,
) -> list[tuple[int, str]]:
    """Ingest a single feed (or one expanded daily URL); returns (article_id, url) pairs of new articles."""
    fetched_at = db.to_iso(now)
    url = url or feed.url
    try:
        resp = client.get(url)
        entries = parse_feed(resp.content)
    except RobotsDisallowed:
        msg = f"robots.txt blokuje kanał {url}"
        result.errors.append(msg)
        db.log_fetch(conn, source.id, url, fetched_at, "robots_disallowed", error=msg)
        conn.commit()
        return []
    except (httpx.HTTPError, ValueError) as e:
        msg = f"{url}: {e}"
        result.errors.append(msg)
        db.log_fetch(conn, source.id, url, fetched_at, "error", error=str(e)[:500])
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
            published_at=db.to_iso(entry.published) if entry.published else None,
            section=feed.section,
            genre=("opinion" if set(c.casefold() for c in entry.categories) & {"opinion", "opinions", "editorial", "blogs"} else feed.genre),
            fetched_at=fetched_at,
        )
        article_id = db.insert_article(conn, row)
        if article_id is None:
            result.duplicates += 1
            continue
        recent.append(entry.title)
        inserted.append((article_id, row.url))
    result.new += len(inserted)
    db.log_fetch(conn, source.id, url, fetched_at, "ok", n_items=len(entries), n_new=len(inserted))
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
            for feed_url in feed_urls(feed.url, now):
                new = ingest_feed(conn, client, source, feed, settings, result, now, feed_url)
                if fulltext and source.fulltext:
                    pending_fulltext.extend((source.id, aid, url) for aid, url in new)

    for source_id, article_id, url in _round_robin_by_host(pending_fulltext):
        text = fetch_fulltext(client, url, settings.ingest.max_fulltext_words)
        if text:
            db.set_fulltext(conn, article_id, text)
            results[source_id].fulltext_ok += 1
        conn.commit()
    from paralaksa.ingest.dedup import mark_syndication
    mark_syndication(conn)
    return list(results.values())
