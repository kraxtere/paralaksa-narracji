"""Static internal site: one self-contained HTML file per page (CSS, JS and data inlined), works from file://."""
from __future__ import annotations

import html
import json
import re
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from paralaksa.events.check import CardError, card_paths
from paralaksa.site import icons
from paralaksa.site.data import COUNTRY_NAMES, daily_days, daily_payload, daily_summary, event_payload, event_summary, load_report

ASSETS = Path(__file__).parent / "assets"
LOGO = ASSETS / "logo"          # logo „Gazeta w kadrze” (E1), wybrane 2026-10-01; litery jako krzywe
TOP_BG = "#1c1c1a"


@dataclass
class SiteResult:
    out_dir: Path
    events: list[str] = field(default_factory=list)
    days: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _asset(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def logo_file(name: str) -> str:
    """SVG from assets/logo: logo-jasne-tlo, logo-ciemne-tlo (znak i nazwa), ikona-jasne-tlo, ikona-ciemne-tlo."""
    return (LOGO / f"{name}.svg").read_text(encoding="utf-8")


def logo_inline(name: str = "logo-ciemne-tlo", prefix: str = "plx") -> str:
    """Logo to put inside HTML: own mask ids (several SVGs on one page), hidden from screen readers (the link has a label)."""
    svg = re.sub(r"<title[^>]*>.*?</title>", "", logo_file(name))
    svg = svg.replace(' role="img" aria-labelledby="title"', ' aria-hidden="true" focusable="false"')
    for mask in ("back", "front"):
        svg = svg.replace(f'id="{mask}"', f'id="{prefix}-{mask}"').replace(f"url(#{mask})", f"url(#{prefix}-{mask})")
    return svg


def icon_svg(background: str = TOP_BG) -> str:
    """The sign alone on a rounded dark square (favicon)."""
    inner = re.search(r"<svg[^>]*>(.*)</svg>", logo_file("ikona-ciemne-tlo"), re.S).group(1)
    inner = re.sub(r"<title[^>]*>.*?</title>", "", inner)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" '
            f'fill="{background}"/>{inner}</svg>')


FAVICON = "data:image/svg+xml," + quote(icon_svg())
# przed pierwszym malowaniem: zapamiętany wybór albo ustawienie systemu
THEME_INIT = ('try{document.documentElement.dataset.theme=localStorage.getItem("plx-theme")||'
              '(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light")}catch(e){}')


def page(title: str, kind: str, payload: dict, root: str, tv: bool = False) -> str:
    """HTML shell; `kind` picks the page script (event, daily, index); `tv` adds the Telewizja tab."""
    tv_link = f'<a href="{root}telewizja.html">Telewizja</a>' if tv else ""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{html.escape(title)} · Paralaksa</title>
<link rel="icon" href="{FAVICON}">
<link rel="manifest" href="{root}manifest.webmanifest">
<link rel="apple-touch-icon" href="{root}apple-touch-icon.png">
<meta name="theme-color" content="#1c1c1a">
<script>{THEME_INIT}</script>
<style>{_asset("site.css")}</style>
</head>
<body data-kind="{kind}" data-root="{root}">
<header class="top">
  <a class="brand" href="{root}index.html" aria-label="Paralaksa">{logo_inline()}</a>
  <nav><a href="{root}index.html#zdarzenia">Zdarzenia</a><a href="{root}index.html#dziennik">Dziennik</a>{tv_link}<a href="{root}v2/index.html">2.0</a></nav>
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
               theme_names: dict[str, str], stories_for=None, titles_for=None, tv_payload: dict | None = None,
               v2_dir: Path | None = None) -> SiteResult:
    """`stories_for(day, eligible_ids)` returns the cached or freshly generated stories of the day (or None),
    `titles_for(day, article_ids)` Polish headlines by article id, `tv_payload` the data of the Telewizja page
    (`gdelt.tv_views.build`; None: no Telewizja page and no tab, the default since 2026-10-01)."""
    tv_on = tv_payload is not None
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
            p = daily_payload(conn, day, load_report(reports_dir, day), theme_names, summaries, stories_for, titles_for)
            (out_dir / "dziennik" / f"{day}.html").write_text(page(f"Dziennik {day}", "daily", p, "../", tv_on),
                                                             encoding="utf-8")
            days.append(daily_summary(p))
            res.days.append(day)
    days.reverse()

    for ev in events:
        ev["dni_bazy"] = res.days
        (out_dir / "zdarzenia" / f"{ev['id']}.html").write_text(page(ev["tytul"] or ev["id"], "event", ev, "../", tv_on),
                                                               encoding="utf-8")
        res.events.append(ev["id"])

    index = {"zdarzenia": summaries, "dni": days, "kraje": COUNTRY_NAMES,
             "zbudowano": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    (out_dir / "index.html").write_text(page("Przegląd", "index", index, "", tv_on), encoding="utf-8")
    if tv_on:
        tv = tv_payload if tv_payload.get("days") else {"channels": {}, "blocs": [], "days": [], "data": {}, "pdf": ""}
        (out_dir / "telewizja.html").write_text(page("Telewizja", "tv", tv, "", True), encoding="utf-8")
    (out_dir / "logo.svg").write_text(logo_file("logo-jasne-tlo"), encoding="utf-8")
    (out_dir / "logo-ciemne-tlo.svg").write_text(logo_file("logo-ciemne-tlo"), encoding="utf-8")
    # instalacja jako aplikacja (Chrome, Edge, Android; iOS: „Do ekranu początkowego”)
    (out_dir / "manifest.webmanifest").write_text(icons.manifest(), encoding="utf-8")
    for name in icons.ICONS:
        (out_dir / name).write_bytes(icons.icon_png(name))
    (out_dir / "sw.js").write_text(_asset("sw.js"), encoding="utf-8")     # instalacja i powiadomienia, zakres „/”
    copy_v2(v2_dir, out_dir / "v2")
    return res


def edition_note(day: str, stories_dir: Path) -> dict:
    """Push notification text about the newest day (sent by the server after the deploy, hosting/powiadomienia.py):
    the day and the first three Wydarzenia dnia."""
    titles: list[str] = []
    try:
        titles = [h["tytul"] for h in json.loads((stories_dir / f"{day}.json").read_text(encoding="utf-8"))["historie"][:3]]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {"dzien": day, "tytul": f"Paralaksa · przegląd prasy {day[8:10]}.{day[5:7]}",
            "tresc": "; ".join(titles) if titles else "Nowe wydanie jest gotowe."}


def copy_v2(src: Path | None, dest: Path) -> list[str]:
    """Wersja 2.0 (prototyp obrazkowy, data/widok/<dzień>/ z data/widok_obrazkowy.py): kopiuje gotowe strony i obrazy,
    bez plików roboczych (nazwy od „_”), i dopisuje v2/index.html z listą dni (najnowszy otwiera się od razu),
    v2/dni.json i wspólny pasek v2/pasek.js. Ciągła oś wydarzeń (data/os_czasu.py, widok/os/) trafia do v2/os/,
    a jej skrót (zakres dni, miniatury) do v2/os.json: z niego pasek pokazuje wejście na stronach dnia.
    Streszczenia artykułów (widok/streszczenia/*.json) trafiają do v2/streszczenia/."""
    def found(root: Path) -> list[str]:
        return sorted((d.name for d in root.iterdir() if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name)
                       and (d / "index.html").exists()), reverse=True) if root.exists() else []

    def copy(folder: Path, to: Path) -> None:
        to.mkdir(parents=True, exist_ok=True)
        for f in folder.iterdir():
            if f.is_file() and not f.name.startswith("_") and f.suffix in (".html", ".png", ".webp"):
                shutil.copy2(f, to / f.name)

    days = found(src) if src else []
    for day in days:
        copy(src / day, dest / day)
    axis = src / "os" if days else None
    if axis and (axis / "index.html").exists() and (axis / "skrot.json").exists():
        copy(axis, dest / "os")
        shutil.copy2(axis / "skrot.json", dest / "os.json")
    # oś kraju „tylko tutaj” (scripts/v2/kraje.py strona): widok/kraje/KRAJ.html z logo i paski dni widok/kraje/D/*.webp
    countries = src / "kraje" if days else None
    if countries and any(countries.glob("*.html")):
        copy(countries, dest / "kraje")
        for d in countries.iterdir():
            if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name):
                copy(d, dest / "kraje" / d.name)
    # streszczenia artykułów pod nagłówkami (scripts/v2/streszczenia.py), pasek.js pobiera plik przy kliknięciu
    summaries = src / "streszczenia" if days else None
    if summaries and summaries.exists():
        (dest / "streszczenia").mkdir(parents=True, exist_ok=True)
        for f in summaries.glob("*.json"):
            shutil.copy2(f, dest / "streszczenia" / f.name)
    if days:
        (dest / "dni.json").write_text(json.dumps(days), encoding="utf-8")   # przełącznik dni na stronach dnia
        (dest / "powiadomienie.json").write_text(json.dumps(edition_note(days[0], src.parent / "stories"), ensure_ascii=False),
                                                 encoding="utf-8")
        # wspólny pasek i stopka wszystkich stron 2.0 (strony mają tylko <div id="pasek"> i ten skrypt)
        (dest / "pasek.js").write_text(_asset("pasek.js").replace('"__LOGO__"', json.dumps(logo_inline("logo-ciemne-tlo", "plx"))),
                                       encoding="utf-8")
        links ="".join(f'<li><a href="{d}/index.html">{d}</a></li>' for d in days)
        (dest / "index.html").write_text(
            f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="robots" content="noindex">'
            f'<meta http-equiv="refresh" content="0; url={days[0]}/index.html"><title>Paralaksa 2.0</title></head>'
            f'<body><p>Paralaksa 2.0 (prototyp): <a href="{days[0]}/index.html">najnowszy dzień</a></p><ul>{links}</ul>'
            f'<p><a href="../index.html">Stara wersja</a></p></body></html>', encoding="utf-8")
    return days


def zip_site(out_dir: Path) -> Path:
    return Path(shutil.make_archive(str(out_dir), "zip", root_dir=out_dir.parent, base_dir=out_dir.name))
