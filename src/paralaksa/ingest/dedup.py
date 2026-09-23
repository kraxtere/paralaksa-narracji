"""URL normalization and duplicate detection."""

from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"fbclid", "gclid", "dclid", "msclkid", "yclid", "mc_cid", "mc_eid", "ocid"}
TRACKING_PREFIXES = ("utm_", "at_")


def _query_without_tracking(query: str) -> list[tuple[str, str]]:
    return [
        (k, v)
        for k, v in parse_qsl(query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith(TRACKING_PREFIXES)
    ]


def clean_url(url: str) -> str:
    """URL to store and link to: tracking params and fragment removed, path untouched.

    The path is kept as-is on purpose: some sites answer 403/404 without the trailing slash.
    """
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(_query_without_tracking(parts.query)), ""))


def normalize_url(url: str) -> str:
    """Canonical form used only for deduplication: https, lowercase host, no trailing slash, sorted query."""
    parts = urlsplit(url.strip())
    scheme = "https" if parts.scheme in ("http", "https", "") else parts.scheme
    host = parts.netloc.lower()
    if host.endswith(":443") or host.endswith(":80"):
        host = host.rsplit(":", 1)[0]
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    return urlunsplit((scheme, host, path, urlencode(sorted(_query_without_tracking(parts.query))), ""))


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def _norm_title(title: str) -> str:
    return re.sub(r"\W+", " ", title.casefold()).strip()


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm_title(a), _norm_title(b)).ratio()


def is_similar_title(title: str, others: list[str], threshold: float) -> bool:
    norm = _norm_title(title)
    if not norm:
        return False
    return any(title_similarity(title, o) >= threshold for o in others)


def mark_syndication(conn):
    """Conservative exact-text groups; never infer shared origin merely from a shared subject.

    Full texts >=80 words or leads >=40 words are hashed separately. Short/translated/edited
    agency copies remain an explicit limitation; no fuzzy cross-language identity is claimed.
    """
    rows = conn.execute('SELECT id,lead,fulltext FROM articles').fetchall()
    for row in rows:
        text = row['fulltext'] or row['lead'] or ''
        words = re.sub(r'\W+', ' ', text.casefold()).split()
        minimum = 80 if row['fulltext'] else 40
        group = hashlib.sha256(' '.join(words).encode()).hexdigest() if len(words) >= minimum else None
        conn.execute('UPDATE articles SET content_group=? WHERE id=?', (group, row['id']))
    conn.commit()
