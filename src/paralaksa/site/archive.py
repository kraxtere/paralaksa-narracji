"""Archiwum 2.0 (v2/archiwum/): wyszukiwarka wszystkich artykułów bazy, statyczne paczki JSON na dzień.

Artykuły jak w dzienniku: dzień = dzień pobrania (fetched_at, UTC), tylko okno publikacji dnia (`publication_meta`
w `daily_payload`); zaległość RSS dnia inicjalnego (publikacja przed oknem, śmieciowe daty) też odpada. Bez pełnych
tekstów i leadów: źródło, tytuł, polski nagłówek, link i sygnały (temat, ton, aktor, rama, summary_pl).
Paczka na dzień `D.json.gz` (`D.json` dla przeglądarek bez DecompressionStream); spis dni w stronie, przeglądarka
pobiera tylko dni wybranego okresu (miesiąc to ok. 20 MB JSON, za dużo na telefon)."""
from __future__ import annotations

import gzip
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from paralaksa.site.data import COUNTRY_NAMES
from paralaksa.site.slowa import lemmas, rising

CATEGORIES_FILE = Path("data/widok/kategorie.json")      # {id artykułu: kategoria}, scripts/v2/kategorie.py (lokalnie, Codex)
RISING_WORDS = 12


def load_categories(path: Path = CATEGORIES_FILE) -> dict[int, str]:
    try:
        return {int(k): v for k, v in json.loads(path.read_text(encoding="utf-8")).items()}
    except (OSError, ValueError):
        return {}


def _utc(stamp: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(stamp).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def records(payload: dict, categories: dict[int, str] | None = None) -> list[list]:
    """Compact rows of one day from `daily_payload`: [source, title, Polish title or "", url,
    [[theme, stance, actor, frame, summary_pl], ...], lemmas of the Polish title (space-separated, "" without one),
    general category (only for articles without signals, "" otherwise)]; articles published before the window are dropped."""
    start = _utc(payload["publikacja"]["publication_window_start"])
    rows = []
    for a in payload["artykuly"]:
        pub = _utc(a["pub"])
        if pub is not None and pub < start:
            continue
        pl = a.get("pl") or ""
        polish = pl or (a["tytul"] if a.get("kraj") == "PL" else "")        # źródła polskie: tytuł oryginalny jest polski
        sig = [[s["th"], s["st"], s["actor"], s["frame"], s["sum"]] for s in a["s"]]
        rows.append([a["src"], a["tytul"], "" if pl == a["tytul"] else pl, a["url"], sig,
                     " ".join(lemmas(polish)), "" if sig else (categories or {}).get(a["id"], "")])
    return rows


def rising_words(days: dict[str, list[list]], sources: dict[str, dict]) -> dict:
    """Words rising on the newest day vs the mean of the previous 7 days: {"": global top, "PL": per country top}.
    Counts articles (a lemma once per title); a country needs at least 3 mentions today, global 5."""
    if not days:
        return {}
    ordered = sorted(days, reverse=True)

    def counts(day: str, country: str | None) -> Counter:
        c: Counter = Counter()
        for r in days[day]:
            if r[5] and (country is None or (sources.get(r[0]) or {}).get("kraj") == country):
                c.update(set(r[5].split()))
        return c

    previous = ordered[1:8]
    out = {"": rising(counts(ordered[0], None), [counts(d, None) for d in previous], 5)[:RISING_WORDS]}
    for country in sorted({(sources.get(r[0]) or {}).get("kraj") for r in days[ordered[0]]} - {None}):
        top = rising(counts(ordered[0], country), [counts(d, country) for d in previous], 3)[:RISING_WORDS]
        if top:
            out[country] = top
    return out


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def write(dest: Path, days: dict[str, list[list]], sources: dict[str, dict], theme_names: dict[str, str],
          favicon: str, script: str) -> dict:
    """Writes the day packs and index.html with the list of days (newest first) and the dictionaries of the filters;
    returns the list (`spis`). `sources` as in `daily_payload` (id → name, kraj), `theme_names` the fixed themes."""
    dest.mkdir(parents=True, exist_ok=True)
    used = set()
    listing = []
    for day in sorted(days, reverse=True):
        rows = days[day]
        data = _dump(rows).encode("utf-8")
        (dest / f"{day}.json").write_bytes(data)
        (dest / f"{day}.json.gz").write_bytes(gzip.compress(data, mtime=0))
        used.update(r[0] for r in rows)
        listing.append({"d": day, "n": len(rows)})
    spis = {"dni": listing, "tematy": theme_names, "kraje": COUNTRY_NAMES,
            "zrodla": {s: [sources[s]["name"], sources[s]["kraj"]] for s in sorted(used) if s in sources},
            "rosnace": rising_words(days, sources), "rosnace_dzien": listing[0]["d"] if listing else ""}
    (dest / "index.html").write_text(page(spis, favicon, script), encoding="utf-8")
    return spis


def page(spis: dict, favicon: str, script: str) -> str:
    """Strona wyszukiwarki: wspólny pasek 2.0 (powrót do dnia z ?dzien=, inaczej do najnowszego), dane i skrypt w środku."""
    newest = spis["dni"][0]["d"] if spis["dni"] else ""
    data = _dump(spis).replace("</", "<\\/")
    return (
        '<!doctype html><html lang="pl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex, nofollow"><title>Archiwum · Paralaksa</title>'
        f'<link rel="icon" href="{html.escape(favicon)}"><link rel="manifest" href="../../manifest.webmanifest">'
        '<link rel="apple-touch-icon" href="../../apple-touch-icon.png"><meta name="theme-color" content="#1d1b18"></head>'
        f'<body><div id="pasek" data-dzien="{newest}" data-wstecz></div>'
        # powrót do dnia, z którego przyszło wejście (kafel na dole strony dnia dodaje ?dzien=)
        '<script>(() => { const d = new URLSearchParams(location.search).get("dzien");'
        ' if (/^\\d{4}-\\d{2}-\\d{2}$/.test(d || "")) document.getElementById("pasek").dataset.dzien = d; })();</script>'
        '<script src="../pasek.js"></script><main id="arch" class="arch"></main>'
        f'<script type="application/json" id="spis">{data}</script><script>{script}</script></body></html>')
