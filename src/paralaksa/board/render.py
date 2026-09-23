"""Collect headlines for an event spec and render a vertical (1080×1920) comic-style board."""

from __future__ import annotations

import html
import os
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from paralaksa.board.spec import EventSpec

MAX_QUOTE_WORDS = 15   # SPEC §16: cytaty maks. 15 słów
WIDTH, HEIGHT = 1080, 1920

COUNTRY_PL = {
    "PL": "Polska", "UA": "Ukraina", "DE": "Niemcy", "UK": "Wielka Brytania", "QA": "Katar", "CN": "Chiny",
    "US": "USA", "BR": "Brazylia", "IL": "Izrael", "PS": "Palestyna", "TR": "Turcja", "IN": "Indie",
}
TYPE_PL = {"private": "prywatne", "public": "publiczne", "government": "państwowe", "agency": "agencja"}


class BoardError(ValueError):
    pass


@dataclass
class Headline:
    article_id: int
    source_name: str
    source_type: str
    country: str
    language: str
    title: str
    translation: str | None
    url: str
    published_at: str | None


@dataclass
class CountryGroup:
    country: str
    headlines: list[Headline] = field(default_factory=list)


@dataclass
class Board:
    spec: EventSpec
    groups: list[CountryGroup]

    @property
    def n_headlines(self) -> int:
        return sum(len(g.headlines) for g in self.groups)


def clip_words(text: str, limit: int = MAX_QUOTE_WORDS) -> str:
    words = text.split()
    return text if len(words) <= limit else " ".join(words[:limit]) + " …"


def collect_board(conn: sqlite3.Connection, spec: EventSpec) -> Board:
    ids = [i.article_id for i in spec.items]
    if len(set(ids)) != len(ids):
        raise BoardError("powtórzony article_id w specyfikacji zdarzenia")
    rows = {
        r["id"]: r for r in conn.execute(
            f"""SELECT a.id, a.title, a.url, a.published_at, COALESCE(a.language, s.language) AS language,
                       s.name, s.type, s.country
                FROM articles a JOIN sources s ON s.id = a.source_id
                WHERE a.id IN ({",".join("?" * len(ids))})""", ids)
    }
    missing = [i for i in ids if i not in rows]
    if missing:
        raise BoardError(f"brak artykułów w bazie: {missing}")
    headlines = []
    for item in spec.items:
        r = rows[item.article_id]
        if r["language"] != "pl" and not item.translation_pl:
            raise BoardError(f"artykuł {item.article_id} ({r['name']}, {r['language']}) wymaga translation_pl")
        headlines.append(Headline(
            article_id=r["id"], source_name=r["name"], source_type=r["type"], country=r["country"],
            language=r["language"], title=clip_words(r["title"]),
            translation=item.translation_pl if r["language"] != "pl" else None,
            url=r["url"], published_at=r["published_at"],
        ))
    # Kolejność neutralna: kraje i nagłówki według czasu publikacji (kto napisał pierwszy).
    headlines.sort(key=lambda h: h.published_at or "9999")
    groups: dict[str, CountryGroup] = {}
    for h in headlines:
        groups.setdefault(h.country, CountryGroup(h.country)).headlines.append(h)
    return Board(spec, list(groups.values()))


def plural_pl(n: int, one: str, few: str, many: str) -> str:
    if n == 1:
        return f"{n} {one}"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"


# Zmniejsza --s, aż plansza zmieści się w kadrze (przed zrzutem ekranu).
FIT_JS = """
(function () {
  var s = 1.0, root = document.body;
  while (document.documentElement.scrollHeight > %(h)d && s > 0.6) {
    s -= 0.02; root.style.setProperty('--s', s.toFixed(2));
  }
})();
"""


def _when(iso: str | None) -> str:
    if not iso:
        return "brak daty publikacji"
    return datetime.fromisoformat(iso).strftime("%d.%m, %H:%M UTC")


def _domain(url: str) -> str:
    host = urlparse(url).netloc
    return host[4:] if host.startswith("www.") else host


CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: %(w)dpx; }
html { overflow: hidden; }
body {
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; color: #111;
  background-color: #f3ead3;
  background-image: radial-gradient(rgba(0,0,0,.13) 1.3px, transparent 1.4px);
  background-size: 11px 11px;
  padding: 44px 46px 36px;
}
.board { min-height: %(inner)dpx; display: flex; flex-direction: column; gap: calc(22px * var(--s)); }
.brand {
  align-self: flex-start; background: #111; color: #f3ead3; font-family: "Arial Black", Impact, sans-serif;
  letter-spacing: .12em; font-size: 30px; padding: 8px 18px; transform: rotate(-1.2deg);
}
.event {
  background: #fff; border: 6px solid #111; box-shadow: 10px 10px 0 #111; padding: 26px 30px;
}
.event h1 { font-family: "Arial Black", Impact, sans-serif; font-size: calc(50px * var(--s)); line-height: 1.08; }
.event .meta { margin-top: 12px; font-size: 26px; font-weight: 600; color: #444; }
.panel {
  position: relative; background: #fff; border: 5px solid #111; box-shadow: 8px 8px 0 #111;
  padding: calc(40px * var(--s)) 28px calc(18px * var(--s));
}
.panel:nth-child(odd) { transform: rotate(-.45deg); }
.panel:nth-child(even) { transform: rotate(.45deg); }
.caption {
  position: absolute; top: -22px; left: 22px; background: #ffd23f; border: 4px solid #111;
  font-family: "Arial Black", Impact, sans-serif; font-size: 26px; padding: 2px 14px; text-transform: uppercase;
}
.hl + .hl { margin-top: calc(16px * var(--s)); padding-top: calc(14px * var(--s)); border-top: 3px dashed #111; }
.outlet { font-size: calc(22px * var(--s)); font-weight: 700; color: #555; }
.outlet b { color: #111; }
.orig { font-size: calc(24px * var(--s)); font-style: italic; color: #333; margin-top: 4px; line-height: 1.25; }
.pl { font-size: calc(33px * var(--s)); font-weight: 800; line-height: 1.18; margin-top: 4px; }
.pl a, .orig a { color: inherit; text-decoration: none; }
.panels { display: flex; flex-direction: column; gap: calc(40px * var(--s)); margin-top: 16px; }
.foot { margin-top: auto; font-size: calc(20px * var(--s)); color: #333; line-height: 1.35; background: rgba(243,234,211,.92);
        border-top: 4px solid #111; padding-top: 12px; }
.foot .punch { font-family: "Arial Black", Impact, sans-serif; font-size: 30px; color: #111; margin-bottom: 6px; }
"""


def render_html(board: Board) -> str:
    n = board.n_headlines
    esc = html.escape
    panels = []
    for g in board.groups:
        items = []
        for h in g.headlines:
            outlet = (f"<div class='outlet'><b>{esc(h.source_name)}</b> · {esc(TYPE_PL.get(h.source_type, h.source_type))}"
                      f" · {esc(_when(h.published_at))} · {esc(_domain(h.url))}</div>")
            quote = f"<a href='{esc(h.url)}'>„{esc(h.title)}”</a>"
            if h.translation:
                body = f"<div class='orig'>{quote}</div><div class='pl'>{esc(h.translation)}</div>"
            else:
                body = f"<div class='pl'>{quote}</div>"
            items.append(f"<div class='hl'>{outlet}{body}</div>")
        panels.append(f"<section class='panel'><div class='caption'>{esc(COUNTRY_PL.get(g.country, g.country))}</div>"
                      f"{''.join(items)}</section>")
    spec = board.spec
    css = CSS % {"w": WIDTH, "inner": HEIGHT - 80}
    return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><title>{esc(spec.title)}</title>
<style>{css}</style></head>
<body style="--s: 1"><div class="board">
<div class="brand">PARALAKSA ZDARZEŃ</div>
<header class="event"><h1>{esc(spec.title)}</h1>
<div class="meta">{esc(spec.when)} · {plural_pl(len(board.groups), "kraj", "kraje", "krajów")} · {plural_pl(n, "nagłówek", "nagłówki", "nagłówków")}</div></header>
<div class="panels">{''.join(panels)}</div>
<footer class="foot"><div class="punch">Bez komentarza. Oceń sam.</div>
Nagłówki w oryginale z kanałów redakcji, tłumaczenie robocze. Dobór: {esc(spec.rule)}</footer>
</div><script>{FIT_JS % {"h": HEIGHT}}</script></body></html>
"""


def find_browser() -> str | None:
    if os.environ.get("PLX_BROWSER"):
        return os.environ["PLX_BROWSER"]
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome", "msedge"):
        if found := shutil.which(name):
            return found
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              "/opt/pw-browsers/chromium"):
        if Path(p).exists():
            return p
    return None


def screenshot(html_path: Path, png_path: Path, browser: str) -> None:
    """Render the board to PNG with a headless Chromium-family browser."""
    subprocess.run(
        [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
         f"--window-size={WIDTH},{HEIGHT}", f"--screenshot={png_path.resolve()}", html_path.resolve().as_uri()],
        check=True, capture_output=True, timeout=60,
    )
    if not png_path.exists():
        raise BoardError(f"przeglądarka nie zapisała {png_path}")
