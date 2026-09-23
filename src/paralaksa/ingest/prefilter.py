"""Cheap pre-filter: drop sport, entertainment, weather and horoscopes before LLM extraction.

Deliberately conservative: generic words ("football", "celebrity") are only trusted in
URL sections and feed categories, not in titles – a political story may mention them.
"""

from __future__ import annotations

import re

# Całe segmenty ścieżki URL lub etykiety hosta (pl, uk, de, en), np. /sport/, sport.onet.pl.
OFFTOPIC_SECTIONS = {
    "sport", "sports", "sportowefakty", "pilka-nozna", "football", "fussball", "soccer",
    "entertainment", "rozrywka", "celebrity", "showbiz", "lifestyle", "gwiazdy",
    "unterhaltung", "leute",
    "pogoda", "weather", "wetter",
    "horoskop", "horoscope", "horoskope", "goroskop",
}

# Fragmenty sluga URL, jednoznacznie poza zakresem.
OFFTOPIC_SLUG_PHRASES = ("prognoza-pogody", "horoskop", "horoscope", "weather-forecast", "wettervorhersage")

# Kategorie z kanału (dopasowanie całej kategorii, bez rozróżniania wielkości liter).
OFFTOPIC_CATEGORIES = OFFTOPIC_SECTIONS | {
    "piłka nożna", "football", "tennis", "cricket", "formula 1", "film", "music", "celebrities",
    "спорт", "футбол",
}

# Wzorce w tytule: tylko jednoznaczne frazy.
_TITLE_PATTERNS = [
    r"horoskop\w*", r"horoscope\w*", r"гороскоп\w*",
    r"prognoz\w* pogody", r"jaka (?:będzie )?pogoda", r"pogoda na (?:weekend|jutro|dziś)",
    r"прогноз погоди", r"wettervorhersage", r"wetterbericht", r"weather forecast",
    r"ekstraklas\w*", r"bundesliga", r"premier league", r"champions league", r"liga mistrzów",
]
_TITLE_RE = re.compile(r"(?<!\w)(?:" + "|".join(_TITLE_PATTERNS) + r")(?!\w)", re.IGNORECASE)


def _url_parts(url: str) -> tuple[set[str], str]:
    """Host labels + whole path segments, and the path itself (lowercase, no query)."""
    host, _, path = re.sub(r"^https?://", "", url.lower()).partition("/")
    path = path.split("?")[0]
    return set(host.split(".")) | set(path.split("/")), path


def is_offtopic(url: str, title: str, categories: list[str] | None = None, section: str | None = None) -> bool:
    """True if the entry is clearly outside the scope of the analysis."""
    segments, path = _url_parts(url)
    if segments & OFFTOPIC_SECTIONS:
        return True
    if any(p in path for p in OFFTOPIC_SLUG_PHRASES):
        return True
    if section and section.lower() in OFFTOPIC_SECTIONS:
        return True
    if any(c.strip().lower() in OFFTOPIC_CATEGORIES for c in categories or []):
        return True
    return bool(_TITLE_RE.search(title or ""))
