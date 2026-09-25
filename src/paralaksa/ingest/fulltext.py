"""Full-text extraction (trafilatura). Stored locally for analysis only, never published."""

from __future__ import annotations

import logging
import re

import httpx
import trafilatura

from paralaksa.ingest.http import PoliteClient, RobotsDisallowed

log = logging.getLogger(__name__)


_COOKIE_LINE = re.compile(
    r"(use of cookies|we use cookies|uses cookies|cookie (settings|policy|consent)"
    r"|pliki(em|ów)? cookies?|Cookie-Einstellungen|verwendet Cookies|файли cookie)",
    re.IGNORECASE,
)


def strip_boilerplate(text: str) -> str:
    """Drop cookie-consent lines that trafilatura sometimes keeps (e.g. CGTN)."""
    lines = [ln for ln in text.splitlines() if not (_COOKIE_LINE.search(ln) and len(ln.split()) < 80)]
    return "\n".join(lines).strip()


_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")
CJK_CHARS_PER_WORD = 1.3  # chiński bez spacji: limit słów liczony w znakach (1500 słów ≈ 1950 znaków)


def truncate_words(text: str, max_words: int) -> str:
    if len(_CJK.findall(text)) > 0.3 * len(text.replace(" ", "")):
        max_chars = int(max_words * CJK_CHARS_PER_WORD)
        return text if len(text) <= max_chars else text[:max_chars]
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words])


def extract_text(html: str, url: str | None = None) -> str | None:
    text = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
    text = strip_boilerplate(text) if text else ""
    return text or None


def fetch_fulltext(client: PoliteClient, url: str, max_words: int) -> str | None:
    """Download and extract article text; None on any failure (article keeps title + lead)."""
    try:
        resp = client.get(url)
    except RobotsDisallowed:
        log.info("robots.txt blokuje pełny tekst: %s", url)
        return None
    except httpx.HTTPError as e:
        log.info("Nie udało się pobrać pełnego tekstu %s: %s", url, e)
        return None
    text = extract_text(resp.text, url=url)
    return truncate_words(text, max_words) if text else None
