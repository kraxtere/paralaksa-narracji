"""Ad hoc prototyp „widoku obywatelskiego”: jedna infografika dnia 2×3 (tematy) przez Codex, panele wykrywane w kodzie
i nakładane jako linki; poziom 2 = strona tematu z krajami i nagłówkami (linki do artykułów).

  python scripts/v2/widok_obrazkowy.py obraz    # generuje start.png przez Codex (limit konta)
  python scripts/v2/widok_obrazkowy.py paski    # od 01.10: okładka pasami + paski krajów (Codex, scripts/v2/paski.py)
  python scripts/v2/widok_obrazkowy.py strona   # wykrywa panele, składa index.html + temat-*.html + podgląd z ramkami
Wynik: data/widok/2026-09-29/
"""

import html
import hashlib
import os
import json
import re
import shutil
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
            f'h2 .src{{font-size:.55em}}.list h3{{margin:14px 0 2px;font-size:1.05em}}.osk{{font-size:.55em;font-weight:400;margin-left:8px;color:#8a3b2a;white-space:nowrap}}.pas{{display:block;width:100%;height:auto;border-radius:10px;margin:18px 0 6px}}.il{{width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:3px}}{STRIPS_CSS}</style></head><body>{body}</body></html>')


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
        arts = [art_card(info[a["article_id"]]["url"], a["article_id"],
                         headline_excerpt(pl.get(a["article_id"]) or info[a["article_id"]]["title"]), src_html(a["zrodlo"]))
                 for a in rest]
        strip = ""
        if strips_mode():
            if country_strip(t, c).exists():
                strip = f'<img class="pas-kraju" src="{country_strip(t, c).name}" alt="" loading="lazy">'
                if top:                                        # dymek: nagłówek kraju z plakat-TEMAT.json (wybór jak na plakacie)
                    strip += f'<div class="dymek">{esc(top["naglowek"])}</div>'
        blocks.append(f'<section id="kraj-{c}" data-czytaj="kraj">{strip}<h2>{country_pill(c, big=True)} <span class="s">{round(100 * share)}% artykułów'
                      f'</span>{"".join(src_html(z) for z in opisy["dane"][c]["zrodla"])}</h2>'
                      + opis + art_list(arts) + "</section>")
    poster = ""
    img = OUT / f"plakat-{t['temat']}.png"
    if strips_mode():                                         # 2.0 pasami: bez plakatu, pas tematu nad tytułem
        pass
    elif cs and img.exists():
        rects = detect_panels(img, expect=len(cs))
        poster = overlay(img.name, f"{t['nazwa']}: nagłówki prasy",
                         [(f"#kraj-{x['kraj']}", NAMES[x["kraj"]]) for x in cs], rects)
    elif (OUT / "start.png").exists():
        # Przy braku osobnego plakatu zachowujemy ilustrację tematu z głównego widoku.
        tile = next(i for i, item in enumerate(themes(opisy)) if item["temat"] == t["temat"])
        poster = card_image(t["nazwa"], detect_panels(OUT / "start.png")[tile], "start.png")
    head = (f'<img class="pas-tematu" src="{theme_strip(t).name}" alt="">'
            if strips_mode() and theme_strip(t).exists() else "")
    # pigułki krajów: kotwice do kart niżej, w tej samej kolejności
    nav = ('<nav class="kraje-nav">' + "".join(country_pill(c, "a", f'href="#kraj-{c}" data-k="{c}"') for c in order)
           + "</nav>")
    body = (bar("index.html") + poster + f'<style>{COUNTRY_PICK_CSS}</style><div class="list jeden" data-wszystkie data-sekcja="tematy">{head}<h1>{esc(t["nazwa"])}</h1><p class="s">{len(t["kraje"])} krajów '
            f'pisało o tym temacie ({DAY}). Opis przekazu analizowanych źródeł, nie faktów.</p>'
            + (f'<div class="pods" data-czytaj="temat"><div class="pods-l">Podsumowanie wszystkich krajów</div>'
               f'<p>{with_logos(pods["_opis"], list(SOURCES))}</p></div>' if pods.get("_opis") else "")
            + nav + '<p class="s">Nagłówki w tłumaczeniu roboczym; dłuższe skrócone do 15 słów.</p>' + "".join(blocks) + "</div>"
            + COUNTRY_PICK_JS)
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


def art_card(url: str, aid: int, title: str, meta: str) -> str:
    """One headline card; data-a = article id for the summary that unfolds inside it (streszczenia.py, v2/pasek.js)."""
    return (f'<li class="art"><a href="{esc(url)}" data-a="{aid}"><span class="art-t">{esc(title)}</span>'
            f'<span class="art-m">{meta}</span></a></li>')


def art_list(cards: list[str]) -> str:
    """Shared headline list of all 2.0 pages: label „Artykuły (N)” and the cards (styles in v2/pasek.js)."""
    return (f'<div class="arts"><div class="arts-l">Artykuły ({len(cards)})</div><ul class="arts-u">{"".join(cards)}</ul></div>'
            if cards else "")



def article_list(ids: list[int], pl: dict) -> str:
    info = article_info(set(ids))
    return art_list([art_card(info[a]["url"], a, headline_excerpt(pl.get(a) or info[a]["title"]), src_html(info[a]["src"]))
                     for a in dict.fromkeys(ids) if a in info])


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
    regions = card_regions(cards) if (OUT / "powitanie.png").exists() else {}
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
            blocks.append(f'<section id="kraj-{country}"><h2>{country_pill(country, big=True)}{label}'
                          f'{"".join(src_html(sid) for sid in sids)}</h2>{description}{article_list(ids, pl)}</section>')
        confidence = ""
        if card.get("pewnosc"):
            c = card["pewnosc"]
            level = c.get("poziom", "") if isinstance(c, dict) else c
            reason = c.get("uzasadnienie", "") if isinstance(c, dict) else ""
            confidence = f'<p class="s">Pewność porównania: {esc(level)}. {esc(reason)}</p>'
        title = summary.get("tytul") or card["tytul"]
        strip = OUT / f"okl-{key}.webp"                              # okładka z pasów (okladka.py), inaczej wycinek plakatu
        image = (f'<img class="pas-tematu" src="{strip.name}" alt="{esc(title)}">' if strip.exists()
                 else card_image(title, regions[key]))
        body = (bar("index.html") + image + f'<div class="list"><h1>{esc(title)}</h1>'
                + (continued_note(cont[key]) if key in cont else "") +
                f'<p>{esc(summary["opis"])}</p><p>{len(summary["kraje"])} krajów w tym zestawieniu.</p>'
                + note + confidence + "".join(blocks) + '</div>')
        (OUT / f"{key}.html").write_text(shell(title, body), encoding="utf-8")


def countries_data() -> dict:
    """Topics present only in one country's press (scripts/v2/kraje.py), Poland first."""
    path = Path("data/widok/kraje") / f"{DAY}.json"
    return json.loads(path.read_text(encoding="utf-8"))["kraje"] if path.exists() else {}


def country_strips(country: str, topics: list[dict]) -> list[str]:
    """Scene strips over the topics (scripts/v2/kraje.py obrazki), copied next to kraje.html; only when the stored
    topic titles match the current ones, otherwise none."""
    from kraje import strip_names
    names = strip_names(DAY, country, topics)
    for name in names:
        shutil.copy2(Path("data/widok/kraje") / DAY / name, OUT / f"kraje-{name}")
    return [f'<img class="pas" src="kraje-{name}" alt="" loading="lazy">' for name in names] or [""] * len(topics)


# „Czym żyje kraj”: nazwa kraju w mianowniku z orzeczeniem w liczbie pojedynczej albo mnogiej
LIVES = {"PL": "żyje Polska", "UA": "żyje Ukraina", "DE": "żyją Niemcy", "UK": "żyje Wielka Brytania",
         "US": "żyją Stany Zjednoczone", "CN": "żyją Chiny", "HK": "żyje Hongkong", "IL": "żyje Izrael",
         "PS": "żyje Palestyna", "TR": "żyje Turcja", "IN": "żyją Indie", "BR": "żyje Brazylia", "QA": "żyje Katar",
         "RU": "żyje Rosja"}


def lives_title(c: str) -> str:
    return "Czym " + LIVES.get(c, "żyje " + NAMES.get(c, c))


# Jeden kraj naraz: wybór w #KRAJ (np. #PL, działa też dawne #kraj-PL); bez JS widać wszystkie sekcje
COUNTRY_PICK_JS = """<script>(()=>{const box=document.querySelector('.jeden'),nav=box.querySelector('.kraje-nav'),
all=box.hasAttribute('data-wszystkie'),ss=[...box.querySelectorAll('section[id^=kraj-]')];box.classList.add('js');
if(all){const w=document.createElement('a');w.href='#';w.className='kraj-pig';w.dataset.k='';w.textContent='Wszystkie kraje';nav.prepend(w)}
const bs=[...nav.querySelectorAll('a')];window.plxKolko&&plxKolko(nav);
function pick(c,push){if(c&&!ss.some(s=>s.id==='kraj-'+c))c='';if(!c&&!all)c=ss[0]&&ss[0].id.slice(5);
 ss.forEach(s=>s.classList.toggle('on',!c||s.id==='kraj-'+c));bs.forEach(b=>{const on=b.dataset.k===c;b.classList.toggle('on',on);
 if(on)nav.scrollLeft+=b.getBoundingClientRect().left-nav.getBoundingClientRect().left-8});
 if(push)history.replaceState(null,'',c?'#'+c:location.pathname+location.search)}
bs.forEach(b=>b.onclick=e=>{e.preventDefault();pick(b.dataset.k,true)});
const h=()=>pick(location.hash.slice(1).replace(/^kraj-/,'')||(all?'':'PL'),false);addEventListener('hashchange',h);h()})()</script>"""
COUNTRY_PICK_CSS = (".jeden .kraje-nav{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:thin;padding-bottom:4px}"
                    ".jeden .kraje-nav a.on{background:var(--cegla);border-color:var(--cegla);color:var(--papier)}"
                    ".jeden.js section[id^=kraj-]{display:none}.jeden.js section[id^=kraj-].on{display:block}"
                    ".kraje-baner{display:block;width:100%;height:auto;border-radius:10px;margin:12px 0 0}.jeden h1{margin-top:10px}.przypis{margin:-4px 0 10px;font-size:.8em}")


def countries_page(pl: dict) -> str:
    """„Czym żyje kraj”: per country, national topics outside the multi-country events of the day; one country at a time."""
    data = countries_data()
    info = article_info({i for ts in data.values() for t in ts for i in t["ids"]})
    order = [c for c in sorted(data, key=lambda c: (c != "PL", NAMES.get(c, c))) if data[c]]
    blocks = []
    for country in order:
        sids = list(dict.fromkeys(info[i]["src"] for t in data[country] for i in t["ids"] if i in info))
        strips = country_strips(country, data[country])
        topics = "".join(f'{strips[k]}<h3>{esc(t["tytul"])}</h3><p>{esc(t["opis"])}</p>{article_list(t["ids"], pl)}'
                         for k, t in enumerate(data[country]))
        blocks.append(f'<section id="kraj-{country}"><h2>{country_pill(country, big=True)}'
                      f'{"".join(src_html(sid) for sid in sids)}<a class="osk" href="../kraje/{country}.html">Cała oś kraju →</a>'
                      f'</h2>{topics}</section>')
    nav = ('<nav class="kraje-nav">' + "".join(country_pill(c, "a", f'href="#{c}" data-k="{c}"')
                                              for c in order) + '</nav>')
    title = f"Czym żyją kraje · {DAY[8:10]}.{DAY[5:7]}"
    body = (bar("index.html") + f'<style>{COUNTRY_PICK_CSS}</style><div class="list jeden" data-sekcja="kraje">'
            + ('<img class="kraje-baner" src="../kraje/baner.webp" alt="">' if BANNER.exists() else "")
            + f'<h1>{esc(title)}</h1>'
            '<p>Sprawy, które zajmowały prasę jednego kraju, a nie trafiły do Wydarzeń dnia, bo inne kraje o nich nie pisały.</p>'
            + nav + '<p class="s przypis">Tematy i opisy wybrane przez AI z nagłówków prasy; nagłówki w tłumaczeniu roboczym, '
            'dłuższe skrócone do 15 słów.</p>' + "".join(blocks) + '</div>' + COUNTRY_PICK_JS)
    return shell(title, body)


def countries_link() -> str:
    """Tile under the cover leading to kraje.html (only when the day has national topics): the shared banner with the
    title over it, like the theme strips of the cover; without the banner the same tile on a dark background."""
    if not any(countries_data().values()):
        return ""
    img = '<img src="../kraje/baner.webp" alt="" loading="lazy">' if BANNER.exists() else ""
    return (f'<div class="okl"><a class="okl-pas kraje-pas{"" if img else " bez"}" href="kraje.html" data-sekcja="kraje">{img}'
            '<span class="okl-t"><b>Czym żyją kraje <span class="strz">›</span></b>'
            '<span class="okl-n">Tylko u nas: o tym, co nie wychodzi za granicę</span></span></a></div>')


# Baner „Czym żyje kraj”: stały zasób wspólny dla wszystkich dni (data/widok/kraje/baner.webp, plx site kopiuje go do
# v2/kraje/), generowany raz (`widok_obrazkowy.py baner`; istniejącego nie nadpisuje)
BANNER = Path("data/widok/kraje/baner.webp")
BANNER_SCENE = ("A row of small cartoon figures whose bodies are folded newspapers (newspaper people), standing side by "
                "side, each wearing a scarf in the colors of a different country (Poland white-and-red, clearly in the "
                "middle and slightly bigger; others e.g. Ukraine, Germany, United Kingdom, USA, China, Turkey, India, "
                "Brazil). Each one reads its own open newspaper and looks in a different direction. Background: faint "
                "outlines of several city skylines blending into one another. Newspaper pages show only abstract grey "
                "lines, never letters.")


def banner_prompt() -> str:
    """Codex instruction: landscape image with two strips of about 3:1 (two takes of the same scene, the better one kept)."""
    import paski
    return ("Use your built-in image generation tool to create ONE image from the prompt below, then copy it into the "
            "current directory as pasy.png. Do not write code or other files. Reply only with the file name.\n\nPROMPT:\n"
            "Landscape image 1536×1024 (3:2), clean flat editorial illustration, warm paper tones (#f4f0e8), dark ink, muted "
            "palette with brick red accents (#8a3b2a). The WHOLE image is a stack of EXACTLY 2 full-width horizontal strips "
            "of equal height (each about 3:1), one under another. Strips are separated by a thick solid uniform dark bar "
            "(#1d1b18, about 14 px), and the same thick dark border runs around the whole image. No gutters, nothing drawn "
            "across the bars, no title, no header, no footer. Both strips show the same scene in two different "
            "compositions.\nScene: " + BANNER_SCENE + "\n" + paski.NO_TEXT)


# --- 2.0 pasami (od 01.10): okładka = pasy tematów, strona tematu = pas tematu + paski krajów (scripts/v2/paski.py) ---
PASKI = OUT / "_paski"                 # oryginały przed cięciem + listy wyników (paski.py pokroj)


def _star(cx: float, cy: float, r: float, fill: str) -> str:
    import math
    pts = " ".join(f"{cx + (r if i % 2 == 0 else r * .4) * math.sin(i * math.pi / 5):.2f},"
                   f"{cy - (r if i % 2 == 0 else r * .4) * math.cos(i * math.pi / 5):.2f}" for i in range(10))
    return f'<polygon points="{pts}" fill="{fill}"/>'


def _bands(*colors: str) -> str:
    h = 20 / len(colors)
    return "".join(f'<rect y="{i * h:.3f}" width="30" height="{h + .05:.3f}" fill="{c}"/>' for i, c in enumerate(colors))


# Uproszczone flagi jako kółka przy tytule tematu (kolory flag to dane, nie kolory strony)
FLAG_SVG = {
    "PL": _bands("#fff", "#dc143c"),
    "UA": _bands("#0057b7", "#ffd700"),
    "DE": _bands("#000", "#dd0000", "#ffce00"),
    "RU": _bands("#fff", "#0039a6", "#d52b1e"),
    "IN": _bands("#ff9933", "#fff", "#138808") + '<circle cx="15" cy="10" r="2.6" fill="none" stroke="#000080" stroke-width=".8"/>',
    "UK": ('<rect width="30" height="20" fill="#012169"/><path d="M0 0L30 20M30 0L0 20" stroke="#fff" stroke-width="4"/>'
           '<path d="M0 0L30 20M30 0L0 20" stroke="#c8102e" stroke-width="1.5"/><path d="M15 0V20M0 10H30" stroke="#fff" '
           'stroke-width="6"/><path d="M15 0V20M0 10H30" stroke="#c8102e" stroke-width="3.5"/>'),
    "US": ('<rect width="30" height="20" fill="#fff"/>' + "".join(f'<rect y="{i * 20 / 13:.2f}" width="30" '
           f'height="{20 / 13:.2f}" fill="#b22234"/>' for i in range(0, 13, 2)) + '<rect width="13" height="10.8" fill="#3c3b6e"/>'),
    "CN": '<rect width="30" height="20" fill="#de2910"/>' + _star(6, 6, 3.6, "#ffde00"),
    "HK": '<rect width="30" height="20" fill="#de2910"/>' + _star(15, 10, 6, "#fff"),
    "IL": ('<rect width="30" height="20" fill="#fff"/><rect y="2" width="30" height="3" fill="#0038b8"/><rect y="15" '
           'width="30" height="3" fill="#0038b8"/><path d="M15 6.2L18.3 12H11.7ZM15 13.8L11.7 8H18.3Z" fill="none" '
           'stroke="#0038b8" stroke-width=".9"/>'),
    "PS": _bands("#000", "#fff", "#149954") + '<path d="M0 0L11 10L0 20Z" fill="#e4312b"/>',
    "TR": ('<rect width="30" height="20" fill="#e30a17"/><circle cx="11" cy="10" r="5" fill="#fff"/><circle cx="12.3" '
           'cy="10" r="4" fill="#e30a17"/>' + _star(17.5, 10, 2.4, "#fff")),
    "BR": ('<rect width="30" height="20" fill="#009c3b"/><path d="M15 2L28 10L15 18L2 10Z" fill="#ffdf00"/><circle '
           'cx="15" cy="10" r="4.6" fill="#002776"/>'),
    "QA": ('<rect width="30" height="20" fill="#8a1538"/><path d="M0 0H9' + "".join(
           f'L{12 if i % 2 else 9} {i * 20 / 18:.2f}' for i in range(1, 19)) + 'H0Z" fill="#fff"/>'),
}


def flag_html(c: str) -> str:
    return (f'<svg class="flaga" viewBox="0 0 30 20" preserveAspectRatio="xMidYMid slice" role="img" '
            f'aria-label="{esc(NAMES.get(c, c))}">{FLAG_SVG.get(c, "")}</svg>')


def country_pill(c: str, tag: str = "span", attrs: str = "", big: bool = False) -> str:
    """The one country label of the 2.0 pages: pill with the flag and the name (buttons, card headers); `big` for headers."""
    return (f'<{tag} class="kraj-pig{" duza" if big else ""}"{" " + attrs if attrs else ""}>'
            f'{flag_html(c)}{esc(NAMES.get(c, c))}</{tag}>')


def strips_mode() -> bool:
    """The day uses the strip layout once its strip originals exist; older days keep start.png and posters."""
    return PASKI.exists()


def theme_strip(t: dict) -> Path:
    return OUT / f"pas-{t['temat']}.webp"


def country_strip(t: dict, c: str) -> Path:
    return OUT / f"pas-{t['temat']}-{c}.webp"


def page_countries(t: dict, cs: list[dict]) -> list[str]:
    """Order of the country cards on the theme page: countries with a poster headline first."""
    poster = [x["kraj"] for x in cs]
    return poster + [c for c in t["kraje"] if c not in poster]


# kafelki tematów (od 02.10): panorama ok. 3:1 ze sceną z dzisiejszych opisów krajów, gazetki ukryte w scenie „jak Wally”
WALLY = ("Hidden in different places of the scene, like in \"Where's Wally\": {mascots}, small (about a fifth of the "
         "strip height), each in a funny side situation (peeking from behind a building, holding a fire hose, taking a "
         "photo, sitting on a roof, carrying a ladder); never the main actors of the events. Mascot = a folded newspaper "
         "with a simple face wearing a scarf in the flag colours; no ethnic features.")
MASCOT = ("A SMALL mascot in the lower right corner of the strip, about one quarter of the strip height: a folded "
          "newspaper with a simple face wearing a scarf in the colours of the {flag} flag, expression matching the tone; "
          "no ethnic features.")


def cover_scene(t: dict, opisy: dict, cs: list[dict]) -> str:
    """Theme tile: a wide panorama of what the press wrote on the theme that day (country descriptions), not a fixed
    symbol, so every day gets a new picture; easter eggs from the theme page headlines (cs, plakat-THEME.json) and
    newspaper mascots of up to 4 countries hidden in it."""
    said = [w["zdanie"] for c in t["kraje"] for w in opisy["opisy"].get(c, {}).get("watki", [])
            if w["temat"] == t["temat"]][:3]
    what = " ".join(said) or SCENES.get(t["temat"], t["nazwa"])
    return (f"a wide panorama for the press topic \"{t['nazwa']}\" showing concretely what the press wrote about today "
            f"(places, people, objects, actions; as they are, without softening): {what} "
            + (" Hide small easter eggs in the scene, each a recognisable detail of one of these stories from the topic "
               "page: " + "; ".join(x["naglowek"] for x in cs if x.get("naglowek")) + ". " if cs else "")
            + WALLY.format(mascots=", ".join(f"the {NAMES[c]} mascot (scarf {FLAGS[c]})" for c in list(t["kraje"])[:4]))
            + " The scene fills the strip edge to edge down to the bottom bar, NO empty band; only its lowest fifth is "
            "simpler (ground, road or water) because a caption is overlaid there later.")


def country_scene(t: dict, c: str, pods: dict, opisy: dict) -> str:
    opis = pods.get(c) or " ".join(w["zdanie"] for w in opisy["opisy"].get(c, {}).get("watki", [])
                                   if w["temat"] == t["temat"])
    return (f"how the press of {NAMES[c]} frames the topic \"{t['nazwa']}\" ({opis}). Show places, objects and a "
            "symbolic action. " + MASCOT.format(flag=FLAGS[c]))


def poster_data(t: dict, opisy: dict, pl: dict) -> list[dict]:
    """Countries and headlines exactly as on the drawn poster (plakat-THEME.json), else picked anew."""
    saved = OUT / f"plakat-{t['temat']}.json"
    return json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else poster_countries(t, opisy, pl)


def strip_jobs(ts: list[dict], opisy: dict, pl: dict) -> list[tuple[str, object]]:
    """Codex jobs of the day: cover strips (one per theme) and country strips per theme (one per country on the page)."""
    import paski
    jobs = []
    css = {t["temat"]: poster_data(t, opisy, pl) for t in ts}
    for k, part in enumerate(ts[i:i + 2] for i in range(0, len(ts), 2)):   # panorama ok. 3:1: 2 na obrazek poziomy
        name = f"okladka-{'ABCD'[k]}"
        if all(theme_strip(t).exists() for t in part):            # ponowne uruchomienie: tylko brakujące
            continue
        jobs.append((name, lambda part=part, name=name: paski.make(
            OUT / f"_gen-{name}", paski.prompt([cover_scene(t, opisy, css[t["temat"]]) for t in part], landscape=True), [theme_strip(t) for t in part],
            PASKI / f"{name}.png")))
    for t in ts:
        cs = css[t["temat"]]
        saved = OUT / f"plakat-{t['temat']}.json"         # te same kraje i dymki na stronie co przy rysowaniu
        if not saved.exists():
            saved.write_text(json.dumps(cs, ensure_ascii=False, indent=1), encoding="utf-8")
        pods = summaries(t, pl, cs)
        for k, part in enumerate(paski.split(page_countries(t, cs))):
            name = f"{t['temat']}-{'AB'[k]}"
            if all(country_strip(t, c).exists() for c in part):
                continue
            jobs.append((name, lambda t=t, part=part, name=name, pods=pods: paski.make(
                OUT / f"_gen-paski-{name}", paski.prompt([country_scene(t, c, pods, opisy) for c in part], PEOPLE_STYLE),
                [country_strip(t, c) for c in part], PASKI / f"{name}.png")))
    return jobs


def cover_html(ts: list[dict], n_countries: int) -> str:
    """Cover in HTML over the theme strips: header, then one clickable strip per theme with title, count and flags."""
    rows = []
    for t in ts:
        img = f'<img src="{theme_strip(t).name}" alt="">' if theme_strip(t).exists() else ""
        rows.append(f'<a class="okl-pas{"" if img else " bez"}" href="temat-{t["temat"]}.html">{img}<span class="okl-t">'
                    f'<b>{esc(t["nazwa"])}</b><span class="okl-n">{n_kraje(len(t["kraje"]))}</span><span class="flagi">'
                    + "".join(flag_html(c) for c in t["kraje"]) + "</span></span></a>")
    return (f'<div class="okl" data-sekcja="tematy"><header class="okl-h"><h1>Czym żyła prasa {DAY[8:10]}.{DAY[5:7]}'
            f'</h1><p>{n_countries} krajów · {len(ts)} tematów dnia</p></header>' + "".join(rows)
            + '<p class="okl-s">Kliknij temat · Opis przekazu analizowanych źródeł, nie faktów</p></div>')


STRIPS_CSS = (
    ":root{--papier:#f4f0e8;--tusz:#1d1b18;--cegla:#8a3b2a;--szary:#7a746a;--cien:rgba(29,27,24,.82);--dymek:#fffdf8;--karta:#fbf8f2;--linia:#ddd5c7}"
    # strona tematu: blok podsumowania wszystkich krajów i pigułki-kotwice do kart krajów (pasek u góry nie jest przyklejony)
    "html{scroll-behavior:smooth}section[id^=kraj-]{scroll-margin-top:12px}"
    ".pods{background:var(--karta);border:1px solid var(--linia);border-left:5px solid var(--cegla);border-radius:12px;"
    "padding:10px 14px;margin:10px 0 12px}.pods-l{color:var(--cegla);font-size:.75em;font-weight:700;letter-spacing:.06em;"
    "text-transform:uppercase}.list .pods p{margin:4px 0 0;font-size:1.06em;font-weight:500;line-height:1.55}"
    ".kraje-nav{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}"
    # jedna pigułka kraju (country_pill): przyciski krajów i nagłówki kart; .duza w nagłówkach h2
    ".kraj-pig{display:inline-flex;align-items:center;gap:6px;padding:4px 11px 4px 5px;border:1px solid var(--linia);"
    "border-radius:999px;background:var(--karta);color:var(--tusz);text-decoration:none;font-size:.9em;font-weight:400;"
    "white-space:nowrap;vertical-align:middle}"
    ".kraj-pig.duza{font-size:.75em;font-weight:700;gap:9px;padding:6px 16px 6px 7px}.kraj-pig.duza .flaga{width:28px;height:28px}"
    ".kraje-nav a:hover,.kraje-nav a:focus-visible{border-color:var(--cegla);color:var(--cegla)}"
    ".okl{max-width:720px;margin:auto;padding:0 6px 10px;box-sizing:border-box}.okl-h{text-align:center;padding:10px 0 4px}"
    ".okl-h h1{margin:0;color:var(--cegla);font:700 1.7em Georgia,serif}.okl-h p{margin:4px 0 0;color:var(--szary)}"
    ".okl-pas{position:relative;display:block;margin:8px 0;border:3px solid var(--tusz);border-radius:8px;overflow:hidden;"
    "color:var(--papier);text-decoration:none;background:var(--tusz)}.okl-pas img{display:block;width:100%;height:auto}"
    ".okl-pas.bez{min-height:120px}.okl-t{position:absolute;left:0;right:0;bottom:0;padding:22px 12px 8px;"
    "background:linear-gradient(transparent,var(--cien) 45%);display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px}"
    ".okl-t b{font:700 1.25em Georgia,serif;flex-basis:100%}.okl-n{font-size:.9em}.flagi{display:flex;flex-wrap:wrap;gap:3px}"
    ".flaga{width:18px;height:18px;border-radius:50%;border:1.5px solid var(--papier);box-sizing:border-box}"
    ".okl-pas:hover,.okl-pas:focus-visible{outline:3px solid var(--cegla);outline-offset:2px}"
    ".okl-s{text-align:center;color:var(--szary);font-size:.8em}"
    ".kraje-pas .okl-t{padding-top:30px}.kraje-pas .strz{float:right;font-size:1.3em;line-height:.8}.kraje-pas.bez{min-height:90px}"
    ".pas-tematu{display:block;width:100%;height:auto;border-radius:10px;margin:12px 0 0}"
    ".pas-kraju{display:block;width:100%;height:auto;border-radius:10px;margin:2px 0 0}"
    ".dymek{position:relative;width:fit-content;max-width:80%;margin:-18px 10px 8px auto;padding:7px 11px;"
    "background:var(--dymek);color:var(--tusz);border:2px solid var(--tusz);border-radius:14px;"
    "font:600 .95em/1.35 Georgia,serif}.dymek:before{content:'';position:absolute;right:28px;top:-11px;"
    "border:7px solid transparent;border-bottom:10px solid var(--tusz);border-top:0}"
    "@media(max-width:480px){.okl-t b{font-size:1.05em}.okl-t{padding:16px 9px 6px}.dymek{max-width:88%}}"
    # okładka z pasów (scripts/v2/okladka.py): tytuł i flagi jak na pasach tematów (.okl-t), kolumny krajów pod pasem
    # nagłówek jak winieta gazety (podwójna linia, data w ceglanym polu), sekcje jako ceglane belki jak na dawnym plakacie
    ".pp .okl-h{border-top:4px double var(--tusz);border-bottom:4px double var(--tusz);margin:6px 0 4px;padding:10px 4px 8px}"
    ".pp .okl-h h1{color:var(--tusz);font:900 2.1em/1.1 Georgia,serif;letter-spacing:-.01em}"
    ".okl-d{display:inline-block;margin-left:10px;padding:2px 9px;background:var(--cegla);color:var(--papier);"
    "font-size:.7em;vertical-align:middle;border-radius:3px}.pp .okl-h p{font-style:italic;color:var(--tusz)}"
    ".pp-sek{margin:18px 0 6px;padding:5px 12px;background:var(--cegla);color:var(--papier);font:700 1.2em Georgia,serif;"
    "border-radius:4px 4px 0 0}"
    "@media(max-width:480px){.pp .okl-h h1{font-size:1.65em}}"
    ".pp-k{margin:8px 0 12px;border:3px solid var(--tusz);border-radius:8px;overflow:hidden;background:var(--karta);"
    "color:var(--tusz)}.pp-obr{position:relative;display:block;background:var(--tusz);color:var(--papier);text-decoration:none}"
    ".pp-obr:hover,.pp-obr:focus-visible{outline:3px solid var(--cegla);outline-offset:-3px}"
    ".pp-obr img{display:block;width:100%;height:auto}"
    ".pp-ciag{flex-basis:100%;width:fit-content;max-width:fit-content;padding:2px 8px;border-radius:4px;"
    "background:var(--cegla);color:var(--papier);font-size:.72em;font-weight:700;letter-spacing:.04em;text-transform:uppercase}"
    ".pp-kols{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--linia)}"
    ".pp-kol{display:flex;flex-direction:column;gap:3px;padding:8px 10px 10px;background:var(--karta);font-size:.86em;"
    "line-height:1.4}.pp-kol b{font:700 .95em Georgia,serif;color:var(--cegla)}"
    ".pp-kol .flaga{border-color:var(--linia)}.pp-kol p{margin:0}"
    # zwijany tekst (v2/pasek.js data-zwin): 4 linie, przycisk „więcej ›” tylko gdy tekst dłuższy
    "[data-zwin]{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:4;line-clamp:4;overflow:hidden}"
    "[data-zwin].rozwin{display:block;-webkit-line-clamp:unset;line-clamp:unset}"
    ".zwin-b{align-self:flex-start;padding:0;border:0;background:none;color:var(--cegla);font:600 .95em 'Segoe UI',sans-serif;"
    "cursor:pointer}"
    "@media(max-width:480px){.pp-kol{font-size:.8em;padding:7px 8px 9px}}")


def strip_cover() -> str:
    """Welcome block in HTML over the cover strips (scripts/v2/okladka.py) once all of them exist, else ""."""
    if not (OUT / "okl-sprawa-1.webp").exists():
        return ""
    import okladka
    from widok_powitanie import poster_data
    data = poster_data()
    return okladka.cover_html(data) if okladka.ready(data) else ""


def index_page(ts: list[dict], rects, debug: bool = False) -> str:
    welcome = strip_cover()
    if not welcome and (OUT / "powitanie.png").exists():
        pl = {**polish_titles(), **titles.cached(Path("data/tytuly"), DAY)}
        inputs = welcome_cards(pl)
        cards = inputs["karty"]
        summaries = welcome_summaries(inputs)
        reg = card_regions(cards)
        welcome = overlay("powitanie.png", f"Przegląd prasy {DAY}: {EVENTS_HEADER.lower()} i różnice",
                          [(f"{k}.html", summaries[k].get("tytul") or cards[k]["tytul"]) for k in WELCOME_KEYS if k in reg],
                          [reg[k] for k in WELCOME_KEYS if k in reg], "okladka")
    if strips_mode():
        n = len(json.loads(OPISY.read_text(encoding="utf-8"))["dane"])
        return shell(f"Paralaksa · {DAY}", bar(None) + welcome + countries_link() + cover_html(ts, n), debug)
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
    if sys.argv[1:2] == ["baner"]:          # baner „Czym żyje kraj”, raz; potem wybór: baner wybierz 1|2
        import paski
        work, pick = BANNER.parent / "_baner", sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "wybierz" else None
        if pick:
            shutil.copy2(work / f"wersja-{pick}.webp", BANNER)
            print(BANNER)
        elif BANNER.exists():
            print(f"{BANNER} już jest, nie generuję ponownie")
        else:
            print(paski.make(work / "_gen", banner_prompt(), [work / "wersja-1.webp", work / "wersja-2.webp"],
                             work / "oryginal.png"))
        return
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
    if cmd == "paski":                       # okładka pasami + paski krajów tematów (Codex, 8/4 procesy)
        import paski
        PASKI.mkdir(parents=True, exist_ok=True)
        paski.run_all(strip_jobs(ts, opisy, pl))
        return
    rects = None if strips_mode() else detect_panels(OUT / "start.png")
    if cmd == "indeks":                      # tylko strona dnia (np. nowy układ okładki), bez stron tematów i spraw
        (OUT / "index.html").write_text(index_page(ts, rects), encoding="utf-8")
        if countries_data():
            (OUT / "kraje.html").write_text(countries_page(pl), encoding="utf-8")
        print("index.html")
        return
    for t in ts:
        cs = poster_data(t, opisy, pl)
        (OUT / f"temat-{t['temat']}.html").write_text(theme_page(t, opisy, pl, cs), encoding="utf-8")
        (OUT / f"_podglad-temat-{t['temat']}.html").write_text(theme_page(t, opisy, pl, cs, debug=True), encoding="utf-8")
    if (OUT / "powitanie.png").exists() or strip_cover():
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
