"""Ad hoc prototyp „widoku obywatelskiego”: jedna infografika dnia 2×3 (tematy) przez Codex, panele wykrywane w kodzie
i nakładane jako linki; poziom 2 = strona tematu z krajami i nagłówkami (linki do artykułów).

  python scripts/v2/widok_obrazkowy.py obraz    # generuje start.png przez Codex (limit konta)
  python scripts/v2/widok_obrazkowy.py strona   # wykrywa panele, składa index.html + temat-*.html + podgląd z ramkami
Wynik: data/widok/2026-09-29/
"""

import html
import hashlib
import os
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from komiks_codex import codex_exe  # noqa: E402
from widok_tresci import (WELCOME_VERSION, read_cache, save_cache, validate_welcome,
                         welcome_input, welcome_prompt)  # noqa: E402

from paralaksa.board.render import find_browser  # noqa: E402
from paralaksa.config import load_sources  # noqa: E402
from paralaksa.site import titles  # noqa: E402
from paralaksa.site.build import FAVICON  # noqa: E402

DAY = os.environ.get("DZIEN", "2026-09-29")   # DZIEN=2026-09-30 python scripts/v2/widok_obrazkowy.py ...
OUT = Path("data/widok") / DAY
# nazwa sekcji spraw na okładce: od 02.10 „Wydarzenia dnia” (decyzja właściciela), wcześniejsze okładki zostają jak są
EVENTS_HEADER = "Wydarzenia dnia" if DAY >= "2026-10-02" else "Sprawy dnia"
OPISY = Path("data/dzien_prasy") / DAY / "opisy.json"
SOURCES = {x.id: x.name for x in load_sources()}
LOGOS = Path("data/logos")          # scripts/v2/loga.py
TEXT_MODEL = ["-m", "gpt-6-luna", "-c", 'model_reasoning_effort="medium"']   # teksty i odczyt obrazu: słabszy model, mniej limitu


def src_name(sid: str) -> str:
    return SOURCES.get(sid, sid)


def src_html(sid: str) -> str:
    """Logo (copied next to the page as logo-<id>.png) + full name of the outlet."""
    logo = LOGOS / f"{sid}.png"
    if logo.exists():
        (OUT / f"logo-{sid}.png").write_bytes(logo.read_bytes())
        return f'<span class="src"><img src="logo-{sid}.png" alt="">{esc(src_name(sid))}</span>'
    return f'<span class="src">{esc(src_name(sid))}</span>'


NAMES = {"PL": "Polska", "UA": "Ukraina", "DE": "Niemcy", "UK": "Wielka Brytania", "US": "USA", "CN": "Chiny",
         "HK": "Hongkong", "IL": "Izrael", "PS": "Palestyna", "TR": "Turcja", "IN": "Indie", "BR": "Brazylia", "QA": "Katar", "RU": "Rosja"}
FLAGS = {"PL": "white-red", "UA": "blue-yellow", "DE": "black-red-gold", "UK": "Union Jack", "US": "Stars and Stripes",
         "CN": "red with yellow stars", "HK": "red with white bauhinia", "IL": "white with blue Star of David",
         "PS": "Palestinian", "TR": "red with white crescent", "IN": "Indian tricolour", "BR": "Brazilian", "QA": "Qatar (maroon with a white serrated band on the left, NOT red-white)",
         "RU": "white-blue-red"}
SCENES = {
    "middle_east": "a stylised map of the Middle East with a dove and olive branch hovering over it",
    "us_policy": "the US Capitol dome with a large ballot and gavel",
    "hybrid_info": "a shadowy laptop with a broken padlock and a cable being cut",
    "ukraine_war": "a map outline of Ukraine with a shield",
    "alliances": "several hands joining around a round table with flags",
    "economy_sanctions": "a balance scale with coins and a shipping container",
    "russia": "the Kremlin towers on a hill",
    "elections_politics": "a ballot box with voting slips",
    "china_indo_pacific": "a stylised map of East Asia and the Western Pacific with small ships and a compass rose",
    "security_defense": "a large shield in front of a radar dish and a watchtower",
}


def n_kraje(n: int) -> str:
    """„4 kraje”, „5 krajów” (23.09: sprawy i tematy z 3–4 krajami)."""
    return f"{n} kraje" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else f"{n} krajów"


def themes(opisy: dict, n: int = 6) -> list[dict]:
    by = {}
    for c, x in opisy["dane"].items():
        for b in x["tematy"]:
            t = by.setdefault(b["temat"], {"temat": b["temat"], "nazwa": b["nazwa"], "kraje": {}})
            t["kraje"][c] = b["udzial"]
    ranked = sorted(by.values(), key=lambda t: (-len(t["kraje"]), -sum(t["kraje"].values())))[:n]
    for t in ranked:
        t["kraje"] = dict(sorted(t["kraje"].items(), key=lambda kv: -kv[1]))
    return ranked


def prompt(ts: list[dict]) -> str:
    panels = "\n".join(
        f"Panel {i} ({'left' if i % 2 else 'right'} column, row {(i + 1) // 2}): illustration of {SCENES.get(t['temat'], t['nazwa'])}. "
        f"Label at the top of the panel, exactly: \"{t['nazwa']}\". Small line under the label, exactly: "
        f"\"{n_kraje(len(t['kraje']))}\". Along the bottom edge of the panel a row of small round flag badges, in this order: "
        + ", ".join(f"{FLAGS[c]}" for c in list(t["kraje"])[:6]) + "."
        for i, t in enumerate(ts, 1))
    return ("Use your built-in image generation tool to create ONE image from the prompt below, then copy it into the "
            "current directory as start.png. Do not write code or other files. Reply only with the file name.\n\nPROMPT:\n"
            "Vertical 9:16 editorial infographic poster, clean flat illustration, warm paper background (#f4f0e8), dark ink, "
            "muted palette with brick red accents (#8a3b2a). Title at the very top, exactly: \"Czym żyła prasa "
            f"{DAY[8:10]}.{DAY[5:7]}\". Subtitle, exactly: \"{len(json.loads(OPISY.read_text(encoding='utf-8'))['dane'])} krajów · "
            f"{len(ts)} tematów dnia\". Below the title: a STRICT grid of 2 columns × 3 rows of equal "
            "rectangular panels, each panel framed with a thick dark border, separated by clear light gutters; nothing drawn "
            "across the gutters.\n" + panels +
            "\nFooter small text, exactly: \"Kliknij temat · Opis przekazu analizowanych źródeł, nie faktów · Paralaksa\". "
            "Use correct Polish diacritics. No other text anywhere. No realistic people.")


def detect_panels(png: Path, expect: int = 6) -> list[tuple[float, float, float, float]]:
    """Panel rectangles (x0, y0, x1, y1 as fractions) from dark frame lines; fallback: equal grid below the title."""
    from PIL import Image
    im = Image.open(png).convert("L")
    w, h = im.size
    px = im.load()
    dark = [[px[x, y] < 90 for x in range(w)] for y in range(h)]

    def runs(flags):
        out, start = [], None
        for i, f in enumerate(flags + [False]):
            if f and start is None:
                start = i
            elif not f and start is not None:
                out.append((start, i - 1))
                start = None
        return out

    def longest(flags):
        best = cur = 0
        for f in flags:
            cur = cur + 1 if f else 0
            best = max(best, cur)
        return best

    # ramka = długi CIĄGŁY ciemny odcinek (litery tytułu dają krótkie odcinki): poziomo ≥ 35% szerokości
    # (bok panelu to ok. 45%), pionowo ≥ 20% wysokości (panel to ok. 28%)
    hlines = [(a + b) / 2 for a, b in runs([longest(r) >= 0.35 * w for r in dark])]
    spans = [[(a, b) for a, b in runs([dark[y][x] for y in range(h)]) if b - a >= 0.20 * h] for x in range(w)]
    scores = [sum(b - a for a, b in col) for col in spans]
    candidates = [max(range(a, b + 1), key=lambda x: scores[x]) for a, b in runs([bool(col) for col in spans])]
    # Elementy ilustracji mogą przypominać boki. Ramki obejmują wszystkie rzędy, więc mają najdłuższą łączną linię.
    vlines = sorted(sorted(candidates, key=lambda x: -scores[x])[:4])
    rects = []
    if len(vlines) == 4:
        # wysokości paneli z boków: długie ciemne odcinki w kolumnie lewej ramki
        col = [dark[y][int(vlines[0])] for y in range(h)]
        rowspans = [(a, b) for a, b in runs(col) if b - a >= 0.20 * h]
        colspans = [(vlines[0], vlines[1]), (vlines[2], vlines[3])]
        rects = [(x0 / w, y0 / h, x1 / w, y1 / h) for (y0, y1) in rowspans for (x0, x1) in colspans]
    else:
        print(f"linie poziome {len(hlines)}, pionowe {len(vlines)}")
    if len(rects) != expect:
        if expect < 2 or expect % 2:
            raise ValueError("Plakat wymaga parzystej liczby paneli")
        top, bottom = 0.14, 0.95
        rows = expect // 2
        rh = (bottom - top) / rows
        rects = [(0.03 + c * 0.485, top + r * rh, 0.485 + c * 0.485, top + (r + 1) * rh - 0.01)
                 for r in range(rows) for c in range(2)]
        print(f"{png.name}: wykrywanie ramek nie dało {expect} paneli, użyto siatki zapasowej")
    return rects


def esc(s) -> str:
    return html.escape(str(s))


def headline_excerpt(text: str) -> str:
    """Keep quoted headlines within the project's 15-word limit."""
    words = text.split()
    return " ".join(words[:15]) + "…" if len(words) > 15 else text


def article_info(ids: set[int]) -> dict[int, dict]:
    if not ids:
        return {}
    conn = sqlite3.connect("file:data/prod.db?mode=ro", uri=True)
    q = f"SELECT a.id, a.url, a.title, a.source_id FROM articles a WHERE a.id IN ({','.join(map(str, ids))})"
    return {r[0]: {"url": r[1], "title": r[2], "src": r[3]} for r in conn.execute(q)}


def theme_articles(t: dict, opisy: dict, c: str) -> list[dict]:
    """Articles of a country on THIS theme (signals of the theme, not the day's mixed threads)."""
    for b in opisy["dane"][c]["tematy"]:
        if b["temat"] == t["temat"]:
            return b["sygnaly"]
    return []


def bar(back: str | None) -> str:
    """Miejsce na wspólny pasek i stopkę (v2/pasek.js z plx site): logo, wybór dnia albo powrót, link do starej wersji.
    Zmiana paska to zmiana jednego pliku w repo (src/paralaksa/site/assets/pasek.js), bez przebudowy stron."""
    return (f'<div id="pasek" data-dzien="{DAY}"{" data-wstecz" if back else ""}></div>'
            '<script src="../pasek.js"></script>')


def overlay(img: str, alt: str, items: list[tuple[str, str]], rects, section: str = "") -> str:
    if len(items) != len(rects):
        raise ValueError(f"{img}: niezgodna liczba linków i paneli")
    links = "".join(
        f'<a class="hot" href="{esc(href)}" title="{esc(label)}" aria-label="{esc(label)}" '
        f'style="left:{x0 * 100:.2f}%;top:{y0 * 100:.2f}%;width:{(x1 - x0) * 100:.2f}%;height:{(y1 - y0) * 100:.2f}%"></a>'
        for (href, label), (x0, y0, x1, y1) in zip(items, rects))
    attr = f' data-sekcja="{section}"' if section else ""
    return f'<div class="wrap"{attr}><img src="{img}" alt="{esc(alt)}">{links}</div>'


def shell(title: str, body: str, debug: bool = False) -> str:
    outline = "outline:4px solid #e0003c;background:rgba(224,0,60,.12)" if debug else ""
    return (f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            f'<meta name="robots" content="noindex"><title>{esc(title)}</title><link rel="icon" href="{FAVICON}">'
            f'<link rel="manifest" href="../../manifest.webmanifest"><link rel="apple-touch-icon" href="../../apple-touch-icon.png">'
            f'<meta name="theme-color" content="#1d1b18"><style>body{{margin:0;background:#f4f0e8;'
            f'color:#1d1b18;font-family:Segoe UI,sans-serif}}.wrap{{position:relative;max-width:720px;margin:auto}}'
            f'.wrap img{{width:100%;display:block}}.hot{{position:absolute;{outline}}}.hot:hover{{background:rgba(138,59,42,.12)}}'
            f'.hot:focus-visible{{outline:3px solid #8a3b2a;outline-offset:-3px;background:rgba(138,59,42,.12)}}'
            f'.detail-image{{position:relative;overflow:hidden;max-width:720px;margin:16px auto 0}}'
            f'.detail-image img{{position:absolute;max-width:none;height:auto;display:block}}'
            f'.list{{max-width:720px;margin:auto;padding:8px 14px 40px}}h1{{color:#8a3b2a}}section{{background:#fbf8f2;'
            f'border:1px solid #ddd5c7;border-radius:12px;padding:10px 14px;margin:12px 0}}.s{{color:#7a746a;font-size:.8em;'
            f'font-weight:400}}.list a{{color:#1d1b18}}.src{{display:inline-flex;align-items:center;gap:4px;margin-left:8px;'
            f'color:#7a746a;font-size:.8em;font-weight:400;white-space:nowrap}}.src img{{width:16px;height:16px;border-radius:3px}}'
            f'.list p{{line-height:1.5}}.list li{{line-height:1.4;margin:4px 0}}.list .ciag{{border-left:4px solid #8a3b2a;'
            f'background:#fbf8f2;padding:8px 12px;border-radius:0 8px 8px 0}}.ciag b{{color:#8a3b2a}}.list .ciag a{{color:#8a3b2a}}'
            f'h2 .src{{font-size:.55em}}.list h3{{margin:14px 0 2px;font-size:1.05em}}.kraje-link{{display:flex;justify-content:space-between;align-items:center;max-width:720px;margin:10px auto;box-sizing:border-box;border:2px solid #1d1b18;border-radius:6px;background:#fbf8f2;color:#1d1b18;text-decoration:none;padding:8px 12px}}.kraje-link b{{color:#8a3b2a;font:700 1.2em Georgia,serif}}.kraje-link:hover{{box-shadow:0 0 0 3px rgba(138,59,42,.25)}}@media(max-width:740px){{.kraje-link{{margin:8px 6px}}}}.il{{width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:3px}}</style></head><body>{body}</body></html>')


def main_theme(ids: set[int]) -> dict[int, str]:
    """Główny temat artykułu = temat o największej sumie intensywności jego sygnałów (ekstrakcja daje kilka tematów)."""
    if not ids:
        return {}
    conn = sqlite3.connect("file:data/prod.db?mode=ro", uri=True)
    rows = conn.execute(f"SELECT article_id, theme_id, SUM(intensity) FROM signals WHERE article_id IN "
                        f"({','.join(map(str, ids))}) GROUP BY article_id, theme_id").fetchall()
    best: dict[int, tuple[int, str]] = {}
    for aid, theme, score in rows:
        if aid not in best or score > best[aid][0]:
            best[aid] = (score, theme)
    return {aid: theme for aid, (_, theme) in best.items()}


_DAY_SIGS: list | None = None


def day_candidates(theme: str, country: str) -> list[dict]:
    """All articles of the day (publication window as in daily) of a country whose MAIN theme is `theme`, strongest first."""
    global _DAY_SIGS
    if _DAY_SIGS is None:
        from paralaksa.aggregate.metrics import day_signals
        conn = sqlite3.connect("file:data/prod.db?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        _DAY_SIGS = day_signals(conn, DAY)
    score: dict[int, dict[str, int]] = {}
    meta = {}
    for s in _DAY_SIGS:
        score.setdefault(s.article_id, {}).setdefault(s.theme_id, 0)
        score[s.article_id][s.theme_id] += s.intensity
        meta[s.article_id] = (s.country, s.source_id)
    out = []
    for aid, per in score.items():
        main = max(per, key=per.get)
        if main == theme and meta[aid][0] == country:
            out.append({"article_id": aid, "zrodlo": meta[aid][1], "sila": per[main]})
    return sorted(out, key=lambda a: -a["sila"])


def poster_countries(t: dict, opisy: dict, pl: dict, max_len: int = 120) -> list[dict]:
    """Up to 6 countries (2×N grid), each with one real Polish headline. First choice: an article whose MAIN theme is this
    one; only countries without such an article fall back to any article with a signal of the theme."""
    picked: dict[str, dict] = {}
    for c in t["kraje"]:
        for sg in day_candidates(t["temat"], c):
            head = pl.get(sg["article_id"])
            if head and len(head) <= max_len and len(head.split()) <= 15:
                picked[c] = {"kraj": c, "naglowek": head, "zrodlo": sg["zrodlo"], "article_id": sg["article_id"]}
                break
    if len(picked) < min(4, len(t["kraje"])):
        for c in t["kraje"]:
            if c in picked:
                continue
            for sg in theme_articles(t, opisy, c):
                head = pl.get(sg["article_id"])
                if head and len(head) <= max_len and len(head.split()) <= 15:
                    picked[c] = {"kraj": c, "naglowek": head, "zrodlo": sg["zrodlo"], "article_id": sg["article_id"]}
                    break
    out = [picked[c] for c in t["kraje"] if c in picked][:6]
    if len(out) % 2:          # pełne rzędy siatki 2×N
        out = out[:-1]
    return out if len(out) >= 2 else []


# Styl gazetki dla osób z nagłówków (decyzja właściciela 2026-10-01): uproszczone postacie z atrybutami, bez wiernej twarzy
# 2026-09-26: tylko wariant z pustym owalem zamiast twarzy przeszedł moderację (scripts/v2/widok_warianty.py)
PEOPLE_STYLE = ("People named in the text may appear only as simple paper-cut silhouette figures with a plain blank oval "
                "instead of a face (no eyes, no facial features at all), each recognisable by one attribute such as a "
                "hairstyle shape, a wide-brimmed hat or a clothing colour; neutral and dignified. Everyone else is a small "
                "generic stylised figure.")


def poster_prompt(t: dict, cs: list[dict]) -> str:
    rows = len(cs) // 2
    panels = "\n".join(
        f"Panel {i}: a scene illustrating this headline: \"{x['naglowek']}\" (places, objects, symbolic action). In a lower corner a SMALL {NAMES[x['kraj']]} mascot (scarf {FLAGS[x['kraj']]}, about "
        "one fifth of the panel height, facial expression matching the headline's mood) with a speech bubble containing "
        f"EXACTLY: \"{x['naglowek']}\". Caption under the panel, exactly: \"{NAMES[x['kraj']]} · {src_name(x['zrodlo'])}\"."
        for i, x in enumerate(cs, 1))
    return ("Use your built-in image generation tool to create ONE image from the prompt below, then copy it into the "
            "current directory as plakat.png. Do not write code or other files. Reply only with the file name.\n\nPROMPT:\n"
            "Vertical 9:16 editorial comic poster, clean flat illustration, warm paper background (#f4f0e8), dark ink, "
            "muted palette with brick red accents (#8a3b2a). Countries appear only as friendly cartoon mascots: a folded "
            "newspaper with a simple face wearing a scarf in the country's flag colours; no ethnic features. " + PEOPLE_STYLE +
            f" Title at the top, exactly: \"{t['nazwa']} · {DAY[8:10]}.{DAY[5:7]}\". Subtitle, exactly: "
            f"\"Nagłówki prasy z {len(cs)} krajów\". Below: a STRICT grid of 2 columns × {rows} rows of equal rectangular "
            "panels, each framed with a thick dark border, separated by clear light gutters; nothing drawn across gutters.\n"
            + panels + "\nFooter small text, exactly: \"Kliknij kraj · nagłówki w tłumaczeniu roboczym · Paralaksa\". "
            "Use correct Polish diacritics. No other text anywhere.")


def limit_guard() -> None:
    """Stop before a Codex call when an account window is nearly used up (beyond it work would draw on paid credits)."""
    from codex_limit import usage
    used = {k: v for k, v in usage().items() if not k.endswith("reset")}
    print("limit Codex:", ", ".join(f"{k} {v}%" for k, v in used.items()))
    if any(v is not None and v >= 95 for v in used.values()):
        raise SystemExit("limit Codex prawie wyczerpany (>= 95%): przerywam, żeby nie iść z kredytów")


def run_codex(folder: Path, prompt_text: str, image: Path | None = None) -> None:
    """`image`: attached to the prompt (edits of an existing picture); the flag goes last so it cannot swallow the prompt."""
    limit_guard()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "polecenie.txt").write_text(prompt_text, encoding="utf-8")
    with open(folder / "codex.log", "w", encoding="utf-8") as log:
        subprocess.run([codex_exe(), "exec", "--skip-git-repo-check", "-C", str(folder.resolve()), "--sandbox",
                        "workspace-write", "-c", 'model_reasoning_effort="medium"',
                        "Read the file polecenie.txt in the current directory (UTF-8) and follow its instructions exactly.",
                        *(["-i", str(image.resolve())] if image else [])],
                       stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=900)


def theme_country_data(t: dict, pl: dict, cs: list[dict]) -> dict[str, dict]:
    """Per country: signals of THIS theme from the day's publication window (frame, stance, summary, headline)."""
    day_candidates(t["temat"], "")                      # wczytuje _DAY_SIGS
    poster = {x["kraj"]: x for x in cs}
    out: dict[str, dict] = {}
    for s in _DAY_SIGS:
        if s.theme_id != t["temat"] or s.country not in t["kraje"]:
            continue
        d = out.setdefault(s.country, {"na_plakacie": poster.get(s.country, {}).get("naglowek"), "sygnaly": []})
        d["sygnaly"].append({"article_id": s.article_id, "zrodlo": src_name(s.source_id), "naglowek": pl.get(s.article_id), "rama": s.frame,
                             "stanowisko": s.stance, "streszczenie": s.summary_pl})
    return out


def codex_text(work: Path, prompt_text: str, image: Path | None = None) -> str:
    """One read-only Codex call on the weaker text model; returns the last message."""
    limit_guard()
    work.mkdir(parents=True, exist_ok=True)
    (work / "polecenie.txt").write_text(prompt_text, encoding="utf-8")
    subprocess.run([codex_exe(), "exec", "--skip-git-repo-check", "--ephemeral", "-C", str(work.resolve()), "--sandbox",
                    "read-only", *TEXT_MODEL, "-o", str((work / "odp.txt").resolve()),
                    *(["-i", str(image.resolve())] if image else []), "-"],
                   input=prompt_text.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900, check=True)
    return (work / "odp.txt").read_text(encoding="utf-8")


def summaries(t: dict, pl: dict, cs: list[dict]) -> dict:
    """2–4 sentences per country on how its press covered the theme; Codex (account limit), cached in OUT."""
    path = OUT / f"podsumowania-{t['temat']}.json"
    data = theme_country_data(t, pl, cs)
    names = {c: NAMES[c] for c in data}
    prompt_text = (
        "Jesteś redaktorem serwisu, który opisuje PRZEKAZ prasy z różnych krajów, nie fakty. Dane niżej to sygnały "
        f"z artykułów z {DAY} w temacie „{t['nazwa']}” (rama, stanowisko, streszczenie, nagłówek po polsku), "
        "pogrupowane po krajach.\n"
        "Dla KAŻDEGO kraju napisz podsumowanie po polsku, 1–2 zdania, najwyżej 40 słów, rzeczowo: o czym pisała prasa tego kraju w tym temacie, "
        "jakim tonem i z jakiej perspektywy, a jeśli źródła kraju się różnią, to czym. Jeśli podano 'na_plakacie', zacznij "
        "od tej sprawy, własnymi słowami (nie pisz, że to nagłówek, plakat ani temat nagłówkowy). Nazywaj redakcje (pole zrodlo). Tylko na podstawie danych, bez własnej wiedzy, "
        "bez ocen prawdziwości i bez prognoz; pisz „według X”, „X przedstawia”. Cytaty najwyżej 15 słów. "
        "Nie używaj myślników jako przecinków.\n"
        "Dodaj _opis: zwięzły, rzeczowy wstęp 3–4 zdania (około 60–90 słów), bez zdań wprowadzających i bez wyliczania "
        "wszystkich redakcji; nazwij tylko te, które najlepiej pokazują różnice. Porównuje konkretne wątki i redakcje "
        "z różnych krajów, oraz _article_ids: identyfikatory artykułów wspierających ten wstęp. "
        "Wstęp ma wyjaśniać, kto pisał o czym i czym różnił się dobór spraw; nie sugeruj, że wszystkie artykuły "
        "dotyczą tego samego wydarzenia. Nie uogólniaj pojedynczej redakcji na całą prasę kraju. "
        "Odpowiedz WYŁĄCZNIE obiektem JSON {\"_opis\":\"...\",\"_article_ids\":[123],\"KOD_KRAJU\": \"podsumowanie\", ...} z kluczami krajów: "
        + ", ".join(f"{c} ({n})" for c, n in names.items()) + ".\n\nDANE:\n"
        + json.dumps(data, ensure_ascii=False, indent=1))
    inputs = {"prompt": prompt_text, "model": TEXT_MODEL}
    cached = read_cache(path, inputs, "temat-opisy-v1", adopt=True)
    if cached is not None:
        return cached
    work = OUT / f"_pods-{t['temat']}"
    raw = codex_text(work, prompt_text)
    res = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
    allowed = {s["article_id"] for c in data.values() for s in c["sygnaly"]}
    if (set(res) != set(data) | {"_opis", "_article_ids"}
            or not all(isinstance(res[c], str) and res[c].strip() for c in data)
            or not isinstance(res.get("_opis"), str) or not res["_opis"].strip()
            or not res.get("_article_ids") or not set(res["_article_ids"]) <= allowed):
        raise ValueError(f"{t['temat']}: niekompletne podsumowania krajów")
    save_cache(path, res, inputs, "temat-opisy-v1")
    return res


def with_logos(text: str, sids: list[str]) -> str:
    """Escaped text with a small logo in front of each outlet name (the name stays: favicons alone are ambiguous)."""
    out = esc(text)
    for sid in sorted(sids, key=lambda x: -len(src_name(x))):
        if (LOGOS / f"{sid}.png").exists():
            src_html(sid)                                   # kopiuje logo obok strony
            out = out.replace(esc(src_name(sid)), f'<img class="il" src="logo-{sid}.png" alt="">{esc(src_name(sid))}')
    return out


def theme_page(t: dict, opisy: dict, pl: dict, cs: list[dict], debug: bool = False) -> str:
    poster = {x["kraj"]: x for x in cs}
    ids = {sg["article_id"] for c in t["kraje"] for sg in theme_articles(t, opisy, c)} | {x["article_id"] for x in cs}
    info = article_info(ids)
    pods = summaries(t, pl, cs)
    order = [x["kraj"] for x in cs] + [c for c in t["kraje"] if c not in poster]   # najpierw kraje z plakatu
    blocks = []
    for c in order:
        share = t["kraje"][c]
        top = poster.get(c)
        rest = [a for a in theme_articles(t, opisy, c) if a["article_id"] in info
                and (not top or a["article_id"] != top["article_id"])]
        if top and top["article_id"] in info:                 # artykuł z plakatu na początku listy
            rest.insert(0, {"article_id": top["article_id"], "zrodlo": top["zrodlo"]})
        opis = (f"<p>{with_logos(pods[c], opisy['dane'][c]['zrodla'])}</p>" if pods.get(c) else
                "".join(f"<p>{esc(w['zdanie'])}</p>" for w in opisy["opisy"].get(c, {}).get("watki", [])
                        if w["temat"] == t["temat"]))
        arts = "".join(f'<li><a href="{esc(info[a["article_id"]]["url"])}" data-a="{a["article_id"]}">'
                       f'{esc(headline_excerpt(pl.get(a["article_id"]) or info[a["article_id"]]["title"]))}</a> '
                       f'{src_html(a["zrodlo"])}</li>' for a in rest)
        blocks.append(f'<section id="kraj-{c}"><h2>{esc(NAMES[c])} <span class="s">{round(100 * share)}% artykułów'
                      f'</span>{"".join(src_html(z) for z in opisy["dane"][c]["zrodla"])}</h2>'
                      + opis + (f"<ul>{arts}</ul>" if arts else "") + "</section>")
    poster = ""
    img = OUT / f"plakat-{t['temat']}.png"
    if cs and img.exists():
        rects = detect_panels(img, expect=len(cs))
        poster = overlay(img.name, f"{t['nazwa']}: nagłówki prasy",
                         [(f"#kraj-{x['kraj']}", NAMES[x["kraj"]]) for x in cs], rects)
    elif (OUT / "start.png").exists():
        # Przy braku osobnego plakatu zachowujemy ilustrację tematu z głównego widoku.
        tile = next(i for i, item in enumerate(themes(opisy)) if item["temat"] == t["temat"])
        poster = card_image(t["nazwa"], detect_panels(OUT / "start.png")[tile], "start.png")
    body = (bar("index.html") + poster + f'<div class="list"><h1>{esc(t["nazwa"])}</h1><p>{len(t["kraje"])} krajów pisało '
            f'o tym temacie ({DAY}). Opis przekazu analizowanych źródeł, nie faktów.</p>'
            + (f'<p>{with_logos(pods["_opis"], list(SOURCES))}</p>' if pods.get("_opis") else "")
            + '<p class="s">Nagłówki w tłumaczeniu roboczym; dłuższe skrócone do 15 słów.</p>' + "".join(blocks) + "</div>")
    return shell(f"{t['nazwa']} · {DAY}", body, debug)


WELCOME_KEYS = ["sprawa-1", "sprawa-2", "sprawa-3", "roznica-1", "roznica-2", "obraz-kraju"]


def welcome_regions() -> dict[str, list[float]]:
    """Boxes (fractions of width/height) of the welcome poster's sections, read from the image by Codex; cached."""
    path = OUT / "powitanie-regiony.json"
    image_path = OUT / "powitanie.png"
    prompt_text = (
        "The attached image is an infographic poster. Find these regions and return their bounding boxes as fractions of "
        "the image width and height [x0, y0, x1, y1] (0..1, top-left origin):\n"
        "sprawa-1, sprawa-2, sprawa-3: the three stacked event panels under the header '" + EVENTS_HEADER + "', top to bottom "
        "(whole panel: label, flags and picture);\n"
        "roznica-1, roznica-2: the boxes under 'Gdzie prasa się różni', left and right (whole box; if there is only "
        "one box, return only roznica-1);\n"
        "obraz-kraju: the whole box under 'Jak kraj widzi siebie'.\n"
        "Reply ONLY with a JSON object {\"sprawa-1\": [x0, y0, x1, y1], ...}. Do not write files.")
    inputs = {"image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(), "prompt": prompt_text, "model": TEXT_MODEL}
    res = read_cache(path, inputs, "regiony-v1", adopt=True)
    if res is None:
        raw = codex_text(OUT / "_regiony", prompt_text, image_path)
        res = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
        save_cache(path, res, inputs, "regiony-v1")
    for key, rect in res.items():
        if key not in WELCOME_KEYS or len(rect) != 4 or not (0 <= rect[0] < rect[2] <= 1 and 0 <= rect[1] < rect[3] <= 1):
            raise ValueError(f"Nieprawidłowy region powitania: {key}")
    return res


def welcome_cards(pl: dict) -> dict:
    return welcome_input(DAY, pl, NAMES, SOURCES)


def card_regions(cards: dict) -> dict:
    """Use the same active areas for links and detail images, including a single wide difference panel."""
    reg = welcome_regions()
    if "roznica-1" in cards and "roznica-2" not in cards and "roznica-2" in reg:
        a, b = reg["roznica-1"], reg["roznica-2"]
        reg["roznica-1"] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
    active = {k: reg[k] for k in cards if k in reg}
    if set(active) != set(cards):
        raise ValueError("Na powitaniu brakuje regionu którejś karty")
    return active


def card_image(title: str, rect: list[float], image_name: str = "powitanie.png") -> str:
    """Display the existing welcome image's panel through CSS; preserve the PNG bytes."""
    from PIL import Image
    with Image.open(OUT / image_name) as im:
        w, h = im.size
    x0, y0, x1, y1 = rect
    dx, dy = x1 - x0, y1 - y0
    return (f'<div class="detail-image" style="aspect-ratio:{w * dx:.4f}/{h * dy:.4f}">'
            f'<img src="{esc(image_name)}" alt="{esc(title)}" style="width:{100 / dx:.6f}%;'
            f'left:{-100 * x0 / dx:.6f}%;top:{-100 * y0 / dy:.6f}%"></div>')


PAIR = re.compile(r'"((?:[^"\\]|\\.)*)"\s*:\s*("(?:[^"\\]|\\.)*"|\[[\d,\s]*\]|[\[{])')


def parse_welcome(raw: str) -> dict:
    """Welcome descriptions from a model reply. Luna often mis-nests this JSON (skips `]` or `}` between cards, each time
    elsewhere), so on a parse error the keys are read in order (card -> country -> paragraph), ignoring brackets.
    validate_welcome still checks cards, countries and article ids."""
    text = raw[raw.index("{"):raw.rindex("}") + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    res, card, paras, para = {}, None, None, None
    for m in PAIR.finditer(text):
        key, val = json.loads(f'"{m[1]}"'), m[2]
        if key in WELCOME_KEYS:
            card, paras, para = res.setdefault(key, {"kraje": {}}), None, None
        elif card is None:
            continue
        elif key in ("opis", "tytul") and val.startswith('"'):
            card[key] = json.loads(val)
        elif re.fullmatch(r"[A-Z]{2}", key) and val == "[":
            paras = card["kraje"].setdefault(key, [])
        elif key == "tekst" and paras is not None and val.startswith('"'):
            para = {"tekst": json.loads(val)}
            paras.append(para)
        elif key == "article_ids" and para is not None and val.startswith("["):
            para["article_ids"] = json.loads(val)
    return res


def welcome_summaries(inputs: dict) -> dict:
    path = OUT / "podsumowania-powitanie.json"
    signature = {"data": inputs, "prompt_version": WELCOME_VERSION, "model": TEXT_MODEL,
                 "instructions": welcome_prompt({})}
    res = read_cache(path, signature, WELCOME_VERSION)
    if res is None:
        raw = codex_text(OUT / "_pods-powitanie", welcome_prompt(inputs))
        res = parse_welcome(raw)
        validate_welcome(res, inputs)
        save_cache(path, res, signature, WELCOME_VERSION)
    validate_welcome(res, inputs)
    return res


def article_list(ids: list[int], pl: dict) -> str:
    info = article_info(set(ids))
    # data-a: id artykułu dla streszczenia po kliknięciu (scripts/v2/streszczenia.py, v2/pasek.js)
    return "<ul>" + "".join(f'<li><a href="{esc(info[a]["url"])}" data-a="{a}">{esc(headline_excerpt(pl.get(a) or info[a]["title"]))}</a>'
                            f'{src_html(info[a]["src"])}</li>' for a in dict.fromkeys(ids) if a in info) + "</ul>"


def continued() -> dict:
    """Stories of the day that continue a case from earlier days (scripts/v2/os_czasu.py ciag)."""
    path = Path("data/widok/os/ciag") / f"{DAY}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def continued_note(c: dict) -> str:
    target = f"../os/index.html#d={c['od']}" + (f"&w={c['watek']}" if c.get("watek") else "")
    return (f'<p class="ciag"><b>Ciąg dalszy</b> sprawy z {c["od"][8:10]}.{c["od"][5:7]}. Co nowego: {esc(c["nowe"])} '
            f'<a href="{esc(target)}">Cała sprawa na osi czasu →</a></p>')


def welcome_pages(pl: dict) -> None:
    """Detail pages with the matching image panel and descriptions grounded in article references."""
    inputs = welcome_cards(pl)
    cards = inputs["karty"]
    regions = card_regions(cards)
    summaries = welcome_summaries(inputs)
    cont = continued()
    note = ('<p class="s">Opis przekazu analizowanych źródeł, nie faktów. '
            'Nagłówki w tłumaczeniu roboczym; dłuższe skrócone do 15 słów.</p>')
    for key, card in cards.items():
        summary = summaries[key]
        blocks = []
        for country, paragraphs in summary["kraje"].items():
            ids = list(dict.fromkeys(aid for p in paragraphs for aid in p["article_ids"]))
            by_id = {a["article_id"]: a for a in card["kraje"][country]}
            sids = list(dict.fromkeys(by_id[aid]["zrodlo_id"] for aid in ids))
            label = ""
            if card["typ"] == "autoobraz":
                label = ' <span class="s">' + ("o sobie" if country == card["kraj"] else "z zewnątrz") + '</span>'
            description = "".join(f'<p>{with_logos(p["tekst"], sids)}</p>' for p in paragraphs)
            blocks.append(f'<section id="kraj-{country}"><h2>{esc(NAMES.get(country, country))}{label}'
                          f'{"".join(src_html(sid) for sid in sids)}</h2>{description}{article_list(ids, pl)}</section>')
        confidence = ""
        if card.get("pewnosc"):
            c = card["pewnosc"]
            level = c.get("poziom", "") if isinstance(c, dict) else c
            reason = c.get("uzasadnienie", "") if isinstance(c, dict) else ""
            confidence = f'<p class="s">Pewność porównania: {esc(level)}. {esc(reason)}</p>'
        title = summary.get("tytul") or card["tytul"]
        body = (bar("index.html") + card_image(title, regions[key]) + f'<div class="list"><h1>{esc(title)}</h1>'
                + (continued_note(cont[key]) if key in cont else "") +
                f'<p>{esc(summary["opis"])}</p><p>{len(summary["kraje"])} krajów w tym zestawieniu.</p>'
                + note + confidence + "".join(blocks) + '</div>')
        (OUT / f"{key}.html").write_text(shell(title, body), encoding="utf-8")


def countries_data() -> dict:
    """Topics present only in one country's press (scripts/v2/kraje.py), Poland first."""
    path = Path("data/widok/kraje") / f"{DAY}.json"
    return json.loads(path.read_text(encoding="utf-8"))["kraje"] if path.exists() else {}


def countries_page(pl: dict) -> str:
    """„Tylko tutaj”: per country, national topics outside the multi-country events of the day."""
    data = countries_data()
    info = article_info({i for ts in data.values() for t in ts for i in t["ids"]})
    blocks = []
    for country in sorted(data, key=lambda c: (c != "PL", NAMES.get(c, c))):
        if not data[country]:
            continue
        sids = list(dict.fromkeys(info[i]["src"] for t in data[country] for i in t["ids"] if i in info))
        topics = "".join(f'<h3>{esc(t["tytul"])}</h3><p>{esc(t["opis"])}</p>{article_list(t["ids"], pl)}'
                         for t in data[country])
        blocks.append(f'<section id="kraj-{country}"><h2>{esc(NAMES.get(country, country))}'
                      f'{"".join(src_html(sid) for sid in sids)}</h2>{topics}</section>')
    title = f"Tylko tutaj · {DAY[8:10]}.{DAY[5:7]}"
    body = (bar("index.html") + f'<div class="list" data-sekcja="kraje"><h1>{esc(title)}</h1>'
            '<p>Sprawy obecne w prasie jednego kraju, nieobecne w Wydarzeniach dnia.</p>'
            '<p class="s">Tematy i opisy wybrane przez AI z nagłówków prasy; nagłówki w tłumaczeniu roboczym, '
            'dłuższe skrócone do 15 słów.</p>' + "".join(blocks) + '</div>')
    return shell(title, body)


def countries_link() -> str:
    """Strip under the cover leading to kraje.html (only when the day has national topics)."""
    if not any(countries_data().values()):
        return ""
    return ('<a class="kraje-link" href="kraje.html" data-sekcja="kraje"><b>Tylko tutaj</b>'
            '<span>Sprawy z prasy jednego kraju ›</span></a>')


def index_page(ts: list[dict], rects, debug: bool = False) -> str:
    welcome = ""
    if (OUT / "powitanie.png").exists():
        pl = {**polish_titles(), **titles.cached(Path("data/tytuly"), DAY)}
        inputs = welcome_cards(pl)
        cards = inputs["karty"]
        summaries = welcome_summaries(inputs)
        reg = card_regions(cards)
        welcome = overlay("powitanie.png", f"Przegląd prasy {DAY}: {EVENTS_HEADER.lower()} i różnice",
                          [(f"{k}.html", summaries[k].get("tytul") or cards[k]["tytul"]) for k in WELCOME_KEYS if k in reg],
                          [reg[k] for k in WELCOME_KEYS if k in reg], "okladka")
    body = bar(None) + welcome + countries_link() + overlay("start.png", f"Czym żyła prasa {DAY}: " + ", ".join(t["nazwa"] for t in ts),
                               [(f"temat-{t['temat']}.html", t["nazwa"]) for t in ts], rects, "tematy")
    return shell(f"Paralaksa · {DAY}", body, debug)


def shot(name: str, size: str) -> Path:
    png = OUT / f"_zrzut-{name}.png"
    subprocess.run([find_browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--window-size={size}", f"--screenshot={png.resolve()}", (OUT / f"{name}.html").resolve().as_uri()],
                   check=True, capture_output=True, timeout=60)
    return png


def polish_titles() -> dict[int, str]:
    """Headlines of Polish-language sources: the site's translation cache skips them, the original is already Polish."""
    conn = sqlite3.connect("file:data/prod.db?mode=ro", uri=True)
    return {r[0]: r[1] for r in conn.execute(
        "SELECT a.id, a.title FROM articles a JOIN sources s ON s.id = a.source_id "
        "WHERE s.language = 'pl' AND substr(a.fetched_at, 1, 10) = ?", (DAY,))}


def main():
    opisy = json.loads(OPISY.read_text(encoding="utf-8"))
    ts = themes(opisy)
    pl = {**polish_titles(), **titles.cached(Path("data/tytuly"), DAY)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tematy.json").write_text(json.dumps(ts, ensure_ascii=False, indent=1), encoding="utf-8")
    cmd = sys.argv[1]
    if cmd == "obraz":
        run_codex(OUT / "_gen-start", prompt(ts))
        (OUT / "_gen-start" / "start.png").replace(OUT / "start.png")
        print("start.png")
        return
    if cmd == "plakat":                      # plakat THEME_ID
        t = next(t for t in ts if t["temat"] == sys.argv[2])
        cs = poster_countries(t, opisy, pl)
        if not cs:
            raise SystemExit(f"{t['temat']}: za mało krajów z nagłówkiem, plakatu nie rysuję")
        (OUT / f"plakat-{t['temat']}.json").write_text(json.dumps(cs, ensure_ascii=False, indent=1), encoding="utf-8")
        run_codex(OUT / f"_gen-{t['temat']}", poster_prompt(t, cs))
        (OUT / f"_gen-{t['temat']}" / "plakat.png").replace(OUT / f"plakat-{t['temat']}.png")
        print(f"plakat-{t['temat']}.png")
        return
    rects = detect_panels(OUT / "start.png")
    if cmd == "indeks":                      # tylko strona dnia (np. nowy układ okładki), bez stron tematów i spraw
        (OUT / "index.html").write_text(index_page(ts, rects), encoding="utf-8")
        if countries_data():
            (OUT / "kraje.html").write_text(countries_page(pl), encoding="utf-8")
        print("index.html")
        return
    for t in ts:
        saved = OUT / f"plakat-{t['temat']}.json"      # kraje i nagłówki dokładnie jak na narysowanym plakacie
        cs = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else poster_countries(t, opisy, pl)
        (OUT / f"temat-{t['temat']}.html").write_text(theme_page(t, opisy, pl, cs), encoding="utf-8")
        (OUT / f"_podglad-temat-{t['temat']}.html").write_text(theme_page(t, opisy, pl, cs, debug=True), encoding="utf-8")
    if (OUT / "powitanie.png").exists():
        welcome_pages(pl)
    if countries_data():
        (OUT / "kraje.html").write_text(countries_page(pl), encoding="utf-8")
    (OUT / "index.html").write_text(index_page(ts, rects), encoding="utf-8")
    (OUT / "_podglad-index.html").write_text(index_page(ts, rects, debug=True), encoding="utf-8")
    if len(sys.argv) > 2:
        print(shot(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "720,1400"))
    print("gotowe:", OUT)


if __name__ == "__main__":
    main()
