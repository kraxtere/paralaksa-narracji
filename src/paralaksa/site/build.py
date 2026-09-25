"""Static internal site: one self-contained HTML file per page (CSS, JS and data inlined), works from file://."""
from __future__ import annotations

import html
import json
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from paralaksa.events.check import CardError, card_paths
from paralaksa.site.data import COUNTRY_NAMES, daily_days, daily_payload, daily_summary, event_payload, event_summary, load_report

ASSETS = Path(__file__).parent / "assets"
LOGO_RING = "#e0643c"


@dataclass
class SiteResult:
    out_dir: Path
    events: list[str] = field(default_factory=list)
    days: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _asset(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def logo_mark(ink: str = "currentColor", ring: str = LOGO_RING) -> str:
    """The same point seen from two places: a disc and its displaced outline (32×32 grid)."""
    return (f'<circle cx="12.5" cy="16" r="8" fill="{ink}"/>'
            f'<circle cx="19.5" cy="16" r="8" fill="none" stroke="{ring}" stroke-width="2.6"/>')


def logo_svg(ink: str = "#1c1c1a", background: str | None = None) -> str:
    bg = f'<rect width="32" height="32" rx="7" fill="{background}"/>' if background else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">{bg}{logo_mark(ink)}</svg>'


FAVICON = "data:image/svg+xml," + quote(logo_svg("#fff", "#1c1c1a"))
# przed pierwszym malowaniem: zapamiętany wybór albo ustawienie systemu
THEME_INIT = ('try{document.documentElement.dataset.theme=localStorage.getItem("plx-theme")||'
              '(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light")}catch(e){}')


def page(title: str, kind: str, payload: dict, root: str) -> str:
    """HTML shell; `kind` picks the page script (event, daily, index)."""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{html.escape(title)} · Paralaksa</title>
<link rel="icon" href="{FAVICON}">
<script>{THEME_INIT}</script>
<style>{_asset("site.css")}</style>
</head>
<body data-kind="{kind}" data-root="{root}">
<header class="top">
  <a class="brand" href="{root}index.html"><svg viewBox="0 0 32 32" aria-hidden="true">{logo_mark()}</svg>Paralaksa</a>
  <nav><a href="{root}index.html#zdarzenia">Zdarzenia</a><a href="{root}index.html#dziennik">Dziennik</a></nav>
  <span class="internal">wersja wewnętrzna, do oceny</span>
  <button class="theme" id="theme" type="button" title="Tryb jasny albo ciemny"><span aria-hidden="true">◐</span><span class="lbl">tryb</span></button>
</header>
<main id="app"></main>
<script type="application/json" id="data">{data}</script>
<script>{_asset("common.js")}
{_asset(kind + ".js")}</script>
</body>
</html>
"""


def build_site(out_dir: Path, events_dir: Path, reports_dir: Path, conn: sqlite3.Connection | None,
               theme_names: dict[str, str], stories_for=None) -> SiteResult:
    """`stories_for(day, eligible_ids)` returns the cached or freshly generated stories of the day (or None)."""
    res = SiteResult(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "zdarzenia").mkdir(parents=True)
    (out_dir / "dziennik").mkdir(parents=True)

    events = []
    for path in card_paths([events_dir]):
        try:
            ev = event_payload(path, conn)
        except CardError as e:
            res.errors.append(str(e))
            continue
        events.append(ev)
    events.sort(key=lambda e: e["id"], reverse=True)
    summaries = [event_summary(e) for e in events]

    days = []
    if conn is not None:
        for day in daily_days(conn):
            p = daily_payload(conn, day, load_report(reports_dir, day), theme_names, summaries, stories_for)
            (out_dir / "dziennik" / f"{day}.html").write_text(page(f"Dziennik {day}", "daily", p, "../"),
                                                             encoding="utf-8")
            days.append(daily_summary(p))
            res.days.append(day)
    days.reverse()

    for ev in events:
        ev["dni_bazy"] = res.days
        (out_dir / "zdarzenia" / f"{ev['id']}.html").write_text(page(ev["tytul"] or ev["id"], "event", ev, "../"),
                                                               encoding="utf-8")
        res.events.append(ev["id"])

    index = {"zdarzenia": summaries, "dni": days, "kraje": COUNTRY_NAMES,
             "zbudowano": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    (out_dir / "index.html").write_text(page("Przegląd", "index", index, ""), encoding="utf-8")
    (out_dir / "logo.svg").write_text(logo_svg(), encoding="utf-8")
    (out_dir / "logo-ciemne-tlo.svg").write_text(logo_svg("#fff", "#1c1c1a"), encoding="utf-8")
    return res


def zip_site(out_dir: Path) -> Path:
    return Path(shutil.make_archive(str(out_dir), "zip", root_dir=out_dir.parent, base_dir=out_dir.name))
