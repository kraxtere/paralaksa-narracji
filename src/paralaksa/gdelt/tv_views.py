"""Working views built only on the TV reports (`tv.py`): data for the site's Telewizja page (`site/assets/tv.js`).

Board of the day (new names × channels), one topic across blocs (with who stays silent), two channels side by side,
one channel over the week, and a phrase search over every sentence. Draft views to decide what a TV page should be;
the page is only on the password-protected internal site. Sentences are the reports' (Gemini) wording in English, not the channels' own."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
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
PL_WORKERS = 6        # raportów tłumaczonych naraz (każdy jeszcze w porcjach równolegle)


def glance_count(text: str) -> int:
    """How many first sentences make the 'Day at a glance' excerpt (the same count serves the translation)."""
    part = text.split("MAJOR DEVELOPMENTS")[0]
    n, size = 0, 0
    for s in tv.sentences(part):
        if n and size + len(s) > GLANCE:
            break
        n, size = n + 1, size + len(s) + 1
    return n


def glance(text: str) -> str:
    """The first sentences of 'Day at a glance'."""
    return " ".join(tv.sentences(text)[:glance_count(text)])


def _pl_report(r: tv.Report, pl: dict | None) -> dict:
    """Polish fields of a report: title, excerpt and sentences aligned with the English ones (None where missing)."""
    if not pl:
        return {}
    sents = pl["sentences"]
    n = glance_count(r.text)
    return {"title_pl": pl.get("title"), "sentences_pl": sents,
            "glance_pl": " ".join(s for s in sents[:n] if s) if all(sents[:n]) else None}


def day_data(today: dict[str, tv.Report], before: dict[str, tv.Report], pl: dict[str, dict] | None = None,
             stories: list[dict] | None = None) -> dict:
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
                        "shows": len(set(r.shows)), **_pl_report(r, (pl or {}).get(c))} for c, r in today.items()},
        "groups": [{k: g[k] for k in ("label", "keys", "channels", "before", "snippets", "snip_idx")}
                   for g in (tv.trends(today, before) if before else [])],
        "names": {c: {k: n for k, n in counts[c].items() if k in display and n >= SHARED_MIN} for c in today},
        "display": display,
        "df": {k: sum(1 for c in today if counts[c][k]) for k in display},
        "diary": diary,
        "stories": stories,   # None: nie zbudowano (tv_stories), [] : brak różnic tego dnia
    }


def build(days: list[str], cache: Path, pl_for=None, stories_for=None) -> dict:
    """Data for the views from cached reports; a day without cached reports is skipped. `pl_for(day, report)` returns
    the Polish translation of a report (or None: the views show the English original); `stories_for(day, reports, pl)`
    the stories of the day (default: only saved ones, `tv_stories.cached`)."""
    from paralaksa.gdelt import tv_stories

    load = {d: tv.load(d, tv.CHANNELS, cache, lambda url: None) for d in [tv.previous_day(days[0]), *days]}
    pl: dict[tuple[str, str], dict | None] = {}
    if pl_for:
        pairs = [(d, r) for d in days for r in load[d].values()]
        with ThreadPoolExecutor(PL_WORKERS) as pool:
            for (d, r), res in zip(pairs, pool.map(lambda dr: pl_for(*dr), pairs)):
                pl[(d, r.code)] = res
    out = {}
    for d in days:
        if load[d]:
            day_pl = {c: pl.get((d, c)) for c in load[d]}
            stories = (stories_for(d, load[d], day_pl) if stories_for
                       else tv_stories.cached(cache, d, load[d]))
            out[d] = day_data(load[d], load[tv.previous_day(d)], day_pl, stories)
    return {
        "channels": {c: {"kraj": k, "nazwa": n} for c, (k, n) in tv.CHANNELS.items()},
        "blocs": [{"nazwa": b, "kanaly": cs} for b, cs in BLOCS],
        "days": sorted(out, reverse=True),
        "data": out,
        "pdf": tv.URL,
        "types": tv_stories.TYPES,
        "top": tv_stories.MAX_STORIES,
    }


def render(payload: dict) -> str:
    """Standalone page with the site's look (the same shell as the internal site's Telewizja tab)."""
    from paralaksa.site.build import page

    return page("Telewizja", "tv", payload, "")
