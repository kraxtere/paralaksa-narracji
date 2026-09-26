"""Working views built only on the TV reports (`tv.py`): data for the site's Telewizja page (`site/assets/tv.js`).

Board of the day (new names × channels), one topic across blocs (with who stays silent), two channels side by side,
one channel over the week, and a phrase search over every sentence. Draft views to decide what a TV page should be;
the page is only on the password-protected internal site. Sentences are the reports' (Gemini) wording in English, not the channels' own."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from paralaksa.gdelt import tv

BLOCS: list[tuple[str, list[str]]] = [
    ("Polska i Ukraina", ["TVPINFO", "ESPRESO"]),
    ("Rosja i Białoruś", ["RUSSIA1", "RUSSIA24", "1TV", "NTV", "BELARUSTV"]),
    ("Po rosyjsku spoza Rosji", ["CURRENTTIME"]),
    ("Europa", ["LRT", "DR1", "M1", "BBCNEWS", "FRANCE24"]),
    ("Bliski Wschód i Turcja", ["KAN11", "PRESSTV", "TRTWORLD"]),
    ("Chiny", ["CCTV13"]),
]
GLANCE = 520          # znaków streszczenia dnia w widokach
DIARY_NAMES = 8       # nowych nazw kanału na dzień
SHARED_MIN = 1        # nazwa w obu stacjach co najmniej tyle razy


def glance(text: str) -> str:
    """The first sentences of 'Day at a glance'."""
    part = text.split("MAJOR DEVELOPMENTS")[0].replace("DAY-AT -A-GLANCE", "").replace("DAY-AT-A-GLANCE", "").strip()
    out = ""
    for s in tv.sentences(part):
        if out and len(out) + len(s) > GLANCE:
            break
        out = f"{out} {s}".strip()
    return out


def day_data(today: dict[str, tv.Report], before: dict[str, tv.Report]) -> dict:
    names, counts = tv.vocabulary(today.values())
    _, counts_before = tv.vocabulary(before.values())
    forms: dict[str, Counter] = {}
    for r in today.values():
        for w in tv.WORD.findall(r.text):
            k = tv.key(w)
            if k in names:
                forms.setdefault(k, Counter())[w] += 1
    display = {k: c.most_common(1)[0][0] for k, c in forms.items() if c.most_common(1)[0][0][0].isupper()}
    diary = {}
    for code in today:
        prev = counts_before.get(code, Counter())
        fresh = [(n, k) for k, n in counts[code].items() if k in display and n >= 2 and not prev[k]] if before else []
        diary[code] = [display[k] for n, k in sorted(fresh, key=lambda x: (-x[0], x[1]))[:DIARY_NAMES]]
    return {
        "reports": {c: {"title": r.title, "glance": glance(r.text), "sentences": tv.sentences(r.text),
                        "shows": len(set(r.shows))} for c, r in today.items()},
        "groups": [{k: g[k] for k in ("label", "keys", "channels", "before", "snippets")}
                   for g in (tv.trends(today, before) if before else [])],
        "names": {c: {k: n for k, n in counts[c].items() if k in display and n >= SHARED_MIN} for c in today},
        "display": display,
        "df": {k: sum(1 for c in today if counts[c][k]) for k in display},
        "diary": diary,
    }


def build(days: list[str], cache: Path) -> dict:
    """Data for the views from cached reports; a day without cached reports is skipped."""
    load = {d: tv.load(d, tv.CHANNELS, cache, lambda url: None) for d in [tv.previous_day(days[0]), *days]}
    out = {}
    for d in days:
        if load[d]:
            out[d] = day_data(load[d], load[tv.previous_day(d)])
    return {
        "channels": {c: {"kraj": k, "nazwa": n} for c, (k, n) in tv.CHANNELS.items()},
        "blocs": [{"nazwa": b, "kanaly": cs} for b, cs in BLOCS],
        "days": sorted(out, reverse=True),
        "data": out,
        "pdf": tv.URL,
    }


def render(payload: dict) -> str:
    """Standalone page with the site's look (the same shell as the internal site's Telewizja tab)."""
    from paralaksa.site.build import page

    return page("Telewizja", "tv", payload, "")
