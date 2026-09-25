"""Page payloads for the internal site: event cards and daily reports (headlines, links, our summaries; no full texts)."""
from __future__ import annotations

import html
import json
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from paralaksa.aggregate.sample import publication_meta
from paralaksa.events.check import load_card, parse_time
from paralaksa.ingest.dedup import url_hash

COUNTRY_NAMES = {
    "PL": "Polska", "UA": "Ukraina", "DE": "Niemcy", "UK": "Wielka Brytania", "US": "USA", "BR": "Brazylia",
    "CN": "Chiny", "HK": "Hongkong", "QA": "Katar", "IL": "Izrael", "RU": "Rosja", "ES": "Hiszpania", "FR": "Francja",
    "IT": "Włochy", "IN": "Indie", "TR": "Turcja", "CL": "Chile", "AR": "Argentyna", "BY": "Białoruś", "JP": "Japonia",
    "KR": "Korea Płd.", "IR": "Iran", "PS": "Palestyna", "AZ": "Azerbejdżan", "SE": "Szwecja", "NL": "Holandia",
    "PT": "Portugalia", "BE": "Belgia", "CZ": "Czechy", "SK": "Słowacja", "HU": "Węgry", "LT": "Litwa", "EU": "UE",
}

REPORT_SECTIONS = [
    ("w_skrocie", "W skrócie"),
    ("wzorce_zbieznosci", "Wzorce zbieżności"),
    ("rozbieznosci", "Rozbieżne przekazy"),
    ("autoobraz", "Autoobraz"),
    ("co_sie_przesuwa", "Co się przesuwa"),
    ("nieobecne_w_polsce", "Nieobecne w Polsce"),
    ("slabe_sygnaly", "Słabe sygnały"),
]

_FRONT = re.compile(r"\A---\s*\n.*?\n---\s*(\n|\Z)", re.S)


# --- events -----------------------------------------------------------------------------------------------------------

def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _ms(value: Any) -> int | None:
    dt = parse_time(value)
    return int(dt.timestamp() * 1000) if dt else None


def card_body(path: Path) -> str:
    return _FRONT.sub("", path.read_text(encoding="utf-8"), count=1)


def db_article(conn: sqlite3.Connection | None, url: str | None) -> dict | None:
    """Our copy of a card's link: article id and the fetch day, which names the daily page."""
    if conn is None or not url:
        return None
    row = conn.execute(
        "SELECT id, source_id, substr(fetched_at,1,10) FROM articles WHERE url_hash = ?", (url_hash(url),)
    ).fetchone()
    return {"id": row[0], "source_id": row[1], "day": row[2]} if row else None


def event_payload(path: Path, conn: sqlite3.Connection | None = None) -> dict:
    card = load_card(path)
    fakt = card.get("fakt") or {}
    rels = []
    for r in card.get("relacje") or []:
        arch = r.get("archiwum") or {}
        checked = str(r.get("sprawdzil") or "")
        rels.append({
            "id": r.get("id"), "kraj": r.get("kraj"), "kto": r.get("kto"), "typ": r.get("typ"),
            "rola": r.get("rola"), "gatunek": r.get("gatunek"), "link": r.get("link"),
            "publikacja": _iso(r.get("publikacja")), "t": _ms(r.get("publikacja")),
            "aktualizacja": _iso(r.get("aktualizacja")), "tu": _ms(r.get("aktualizacja")),
            "wersja": r.get("porownywana_wersja"),
            "archiwum": arch.get("link"), "archiwum_czas": _iso(arch.get("wykonano")),
            "naglowek": r.get("naglowek"), "tlumaczenie": r.get("tlumaczenie"),
            "zostawia_z": r.get("zostawia_z"), "sprawdzil": checked or None,
            "czlowiek": "człowiek" in checked.lower(), "watek": r.get("watek"),
            "baza": db_article(conn, r.get("link")),
        })
    timeline = [{"czas": _iso(o.get("czas")), "t": _ms(o.get("czas")), "co_wiadomo": o.get("co_wiadomo"),
                 "zrodlo": o.get("zrodlo")} for o in card.get("os_czasu") or []]
    return {
        "id": card["id"], "tytul": card.get("tytul"), "status": card.get("status"),
        "powod_odrzucenia": card.get("powod_odrzucenia"), "droga": card.get("droga"),
        "dziedzina": card.get("dziedzina") or [], "forma": card.get("forma"),
        "fakt": {"czas": _iso(fakt.get("czas")), "t": _ms(fakt.get("czas")), "opis": fakt.get("opis"),
                 "zrodlo": fakt.get("zrodlo_pierwotne")},
        "stan_wiedzy_zmienial_sie": bool(card.get("stan_wiedzy_zmienial_sie")),
        "os_czasu": timeline, "watki": card.get("watki") or [], "relacje": rels,
        "kontrasty": [{"miedzy": k.get("miedzy") or [], "rodzaj": k.get("rodzaj"), "opis": k.get("opis"),
                       "zastrzezenia": k.get("zastrzezenia")} for k in card.get("kontrasty") or []],
        "jak_szukano": card.get("jak_szukano") or [],
        "opis_html": markdown_html(card_body(path)),
        "kraje": COUNTRY_NAMES,
    }


def teaser(ev: dict) -> list[dict]:
    """Two headlines for the index card: the first contrast, else the first relation of the first two threads."""
    by_id = {r["id"]: r for r in ev["relacje"]}
    picked = [by_id[i] for i in (ev["kontrasty"][0]["miedzy"] if ev["kontrasty"] else []) if i in by_id][:2]
    if len(picked) < 2:
        for w in ev["watki"]:
            first = next((r for r in ev["relacje"] if r.get("watek") == w["id"] and r not in picked), None)
            if first:
                picked.append(first)
            if len(picked) == 2:
                break
    return [{"kraj": r["kraj"], "kto": r["kto"], "typ": r["typ"], "naglowek": r["tlumaczenie"] or r["naglowek"]}
            for r in picked]


def event_summary(ev: dict) -> dict:
    """Index entry."""
    countries = sorted({r["kraj"] for r in ev["relacje"] if r.get("kraj")})
    return {"id": ev["id"], "tytul": ev["tytul"], "status": ev["status"], "forma": ev["forma"],
            "dziedzina": ev["dziedzina"], "n_relacji": len(ev["relacje"]), "kraje": countries,
            "n_kontrastow": len(ev["kontrasty"]), "watki": len(ev["watki"]),
            "czlowiek": sum(r["czlowiek"] for r in ev["relacje"]), "zapowiedz": teaser(ev),
            "rodzaj": ev["kontrasty"][0]["rodzaj"] if ev["kontrasty"] else None}


# --- daily ------------------------------------------------------------------------------------------------------------

def theme_name(theme_id: str, names: dict[str, str]) -> str:
    if theme_id in names:
        return names[theme_id]
    if theme_id.startswith("emergent:"):
        return "nowy: " + theme_id.split(":", 1)[1].replace("-", " ")
    return theme_id


def daily_days(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT date FROM daily_metrics ORDER BY date")]


STANDOUT_MIN_ARTICLES = 10   # kraj z mniejszą próbką nie wchodzi do porównania
STANDOUT_LIMIT = 6


def standouts(metrics: list[dict], country_counts: dict[str, int], country_sources: dict[str, int]) -> list[dict]:
    """Largest gaps between a country's share of a theme and the mean of the other countries (taxonomy themes only).

    More: the country gives the theme at least 15% and twice the others' mean. Less: the others give it at least 15%
    on average and the country at most a third of that. At most two entries per country."""
    countries = [c for c, n in country_counts.items() if n >= STANDOUT_MIN_ARTICLES]
    if len(countries) < 3:
        return []
    by: dict[str, dict[str, dict]] = {}
    for m in metrics:
        if not m["theme_id"].startswith("emergent:"):
            by.setdefault(m["theme_id"], {})[m["country"]] = m
    found = []
    for theme, rows in by.items():
        for c in countries:
            share = rows[c]["article_share"] if c in rows else 0.0
            others = [rows[o]["article_share"] if o in rows else 0.0 for o in countries if o != c]
            mean = sum(others) / len(others)
            n = rows[c]["n_articles"] if c in rows else 0
            if share >= 0.15 and share >= 2 * mean and n >= 3:
                kind = "wiecej"
            elif mean >= 0.15 and share <= mean / 3:
                kind = "mniej"
            else:
                continue
            found.append({"kraj": c, "temat": theme, "kierunek": kind, "udzial": round(share, 3), "srednia": round(mean, 3),
                          "n": n, "n_kraj": country_counts[c], "zrodla": country_sources.get(c, 0),
                          "roznica": abs(share - mean)})
    found.sort(key=lambda f: -f["roznica"])
    out, per_country = [], {}
    for f in found:
        if per_country.get(f["kraj"], 0) < 2:
            per_country[f["kraj"]] = per_country.get(f["kraj"], 0) + 1
            out.append(f)
        if len(out) == STANDOUT_LIMIT:
            break
    return out


def daily_payload(conn: sqlite3.Connection, day: str, report: dict | None, theme_names: dict[str, str],
                  events: list[dict], stories_for=None) -> dict:
    conn.row_factory = sqlite3.Row
    pub = publication_meta(conn, day)
    eligible = set(pub.pop("eligible_ids"))
    sources = {r["id"]: {"id": r["id"], "name": r["name"], "kraj": r["country"], "typ": r["type"]}
               for r in conn.execute("SELECT id, name, country, type FROM sources")}
    arts: dict[int, dict] = {}
    for r in conn.execute(
        """SELECT a.id, a.source_id, a.title, a.url, a.published_at, a.genre, a.fulltext IS NOT NULL
                  AND a.fulltext != '' AS full, s.country
           FROM articles a JOIN sources s ON s.id = a.source_id
           WHERE substr(a.fetched_at,1,10) = ? ORDER BY a.published_at DESC""", (day,)):
        if r["id"] in eligible:
            arts[r["id"]] = {"id": r["id"], "src": r["source_id"], "kraj": r["country"], "tytul": r["title"],
                             "url": r["url"], "pub": r["published_at"], "gatunek": r["genre"],
                             "lead": not r["full"], "s": []}
    if arts:
        marks = ",".join("?" * len(arts))
        for s in conn.execute(
            f"""SELECT article_id, theme_id, subject_actor, frame, stance, intensity, signal_type, summary_pl
                FROM signals WHERE article_id IN ({marks}) ORDER BY id""", list(arts)):
            arts[s["article_id"]]["s"].append({
                "th": s["theme_id"], "actor": s["subject_actor"], "frame": s["frame"], "st": s["stance"],
                "int": s["intensity"], "typ": s["signal_type"], "sum": s["summary_pl"]})
    metrics = [dict(r) for r in conn.execute(
        "SELECT theme_id, country, article_share, n_articles, n_sources, dominant_frame, mean_intensity "
        "FROM daily_metrics WHERE date = ?", (day,))]
    history: dict[str, dict[str, list]] = {}
    for r in conn.execute("SELECT date, theme_id, country, article_share FROM daily_metrics ORDER BY date"):
        history.setdefault(r["theme_id"], {}).setdefault(r["country"], []).append([r["date"], r["article_share"]])
    cost = {r["purpose"]: round(r["c"] or 0, 3) for r in conn.execute(
        "SELECT purpose, SUM(cost_usd) AS c FROM api_usage WHERE date = ? GROUP BY purpose", (day,))}

    used_themes = {m["theme_id"] for m in metrics} | {s["th"] for a in arts.values() for s in a["s"]}
    sections = []
    if report:
        body = report.get("report") or {}
        for key, label in REPORT_SECTIONS:
            items = [report_item(it) for it in body.get(key) or []]
            sections.append({"klucz": key, "nazwa": label, "pozycje": items})
    counts: dict[str, int] = {}
    srcs: dict[str, set] = {}
    for a in arts.values():
        counts[a["kraj"]] = counts.get(a["kraj"], 0) + 1
        srcs.setdefault(a["kraj"], set()).add(a["src"])
    stories = stories_for(day, eligible) if stories_for and arts else None
    lo = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
    related = [e for e in events if lo <= e["id"][:10] <= day]
    return {
        "dzien": day, "publikacja": pub, "zrodla": sources, "artykuly": list(arts.values()),
        "metryki": metrics, "historia": history,
        "tematy": {t: theme_name(t, theme_names) for t in sorted(used_themes)},
        "raport": sections, "ostrzezenia": (report or {}).get("warnings") or [],
        "audyt": (report or {}).get("semantic_review"), "koszt": cost,
        "zdarzenia": [{"id": e["id"], "tytul": e["tytul"]} for e in related],
        "kraje": COUNTRY_NAMES,
        "wyroznia": standouts(metrics, counts, {c: len(v) for c, v in srcs.items()}),
        "historie": (stories or {}).get("historie") or [],
        "historie_meta": {k: stories[k] for k in ("model", "created", "cost_usd")} if stories else None,
    }


def _article_ids(obj: Any) -> set[int]:
    ids: set[int] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "article_ids" and isinstance(v, list):
                ids.update(i for i in v if isinstance(i, int))
            elif k == "article_id" and isinstance(v, int):
                ids.add(v)
            else:
                ids |= _article_ids(v)
    elif isinstance(obj, list):
        for v in obj:
            ids |= _article_ids(v)
    return ids


def report_item(it: dict) -> dict:
    """One claim of any report section, flattened for display (sections differ in shape, see report/schema.py)."""
    conf = it.get("pewnosc")
    if isinstance(conf, dict):
        conf, why = conf.get("poziom"), conf.get("uzasadnienie")
    else:
        why = None
    text = it.get("tekst") or it.get("wspolny_kierunek")
    extra = []
    if "jak_opisuje_siebie" in it:
        extra = [("Jak opisuje siebie", it.get("jak_opisuje_siebie")),
                 ("Jak opisują go inni", it.get("jak_opisuja_go_inni")), ("Komentarz", it.get("komentarz"))]
    if it.get("trend"):
        extra.append(("Trend", it["trend"]))
    if isinstance(it.get("sygnaly_przeciwne"), dict):
        extra.append(("Sygnały przeciwne", it["sygnaly_przeciwne"].get("tekst")))
    return {
        "temat": it.get("theme_id") or it.get("temat"), "kraj": it.get("kraj"), "kierunek": it.get("kierunek"),
        "tekst": text, "pewnosc": conf, "uzasadnienie": why, "dodatki": [[k, v] for k, v in extra if v],
        "kraje": [{"kraj": c.get("kraj"), "n": c.get("n_zrodel"), "rama": c.get("rama"), "stance": c.get("stance"),
                   "artykuly": c.get("article_ids") or []} for c in it.get("kraje") or []],
        "artykuly": sorted(_article_ids(it)),
    }


def daily_summary(p: dict) -> dict:
    return {"dzien": p["dzien"], "status": p["publikacja"]["status"], "artykuly": len(p["artykuly"]),
            "pobrane": p["publikacja"]["fetched_articles"], "kraje": sorted({a["kraj"] for a in p["artykuly"]}),
            "sygnaly": sum(len(a["s"]) for a in p["artykuly"]), "raport": bool(p["raport"]),
            "koszt": round(sum(p["koszt"].values()), 2),
            "historie": [{"tytul": h["tytul"], "kraje": [k["kraj"] for k in h["kraje"]]} for h in p["historie"][:3]]}


def load_report(reports_dir: Path, day: str) -> dict | None:
    path = reports_dir / f"{day}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


# --- markdown (card bodies only: headings, lists, checkboxes, bold, code, bare links) ---------------------------------

_LINK = re.compile(r"(https?://[^\s<)]+)")


def _inline(text: str) -> str:
    t = html.escape(text, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    return _LINK.sub(r'<a href="\1" target="_blank" rel="noopener">\1</a>', t)


def markdown_html(md: str) -> str:
    out: list[str] = []
    para: list[str] = []
    in_list = False

    def flush_para() -> None:
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para.clear()

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in md.splitlines():
        line = raw.rstrip()
        m_head = re.match(r"^(#{1,4})\s+(.*)", line)
        m_item = re.match(r"^\s*[-*]\s+(\[( |x|X)\]\s+)?(.*)", line)
        if not line.strip():
            flush_para()
            close_list()
        elif m_head:
            flush_para()
            close_list()
            level = min(len(m_head.group(1)) + 1, 5)
            out.append(f"<h{level}>{_inline(m_head.group(2))}</h{level}>")
        elif m_item:
            flush_para()
            if not in_list:
                out.append("<ul>")
                in_list = True
            box = ""
            if m_item.group(1):
                box = '<span class="box">☑</span> ' if m_item.group(2).lower() == "x" else '<span class="box">☐</span> '
            out.append(f"<li>{box}{_inline(m_item.group(3))}</li>")
        elif in_list and raw.startswith("  "):
            out[-1] = out[-1][:-5] + " " + _inline(line.strip()) + "</li>"
        else:
            close_list()
            para.append(line.strip())
    flush_para()
    close_list()
    return "\n".join(out)
