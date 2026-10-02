"""Ad hoc prototyp: „Dzień w prasie” — opis dnia per kraj z naszej bazy (jak raporty TV GDELT) + grafika. Bez zmian w src/.

Uruchom: .venv\\Scripts\\python scripts/v2/dzien_prasy.py [DZIEN]
Wynik: data/dzien_prasy/DZIEN/{opisy.json, opisy.md, <KRAJ>.png, przeglad.png, *.html}
Baza tylko do odczytu; opisy zapisane — ponowne uruchomienie renderuje bez wywołań modelu (usuń opisy.json, żeby liczyć od nowa).
"""

import html
import json
import re
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from paralaksa.aggregate.package import build_data_package
from paralaksa.board.render import find_browser
from paralaksa.config import load_settings, load_themes
from paralaksa.extract.llm_client import build_client
from paralaksa.gdelt.tv_stories import _call, _json
from paralaksa.report.validate import long_quotes
from paralaksa.site import titles

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
DAY = ARGS[0] if ARGS else "2026-09-29"
NO_DESC = "--bez-opisow" in sys.argv     # tylko dane (widok 2.0), bez modelu i bez PNG
MODEL = "deepseek-v4-pro"
OUT = Path("data/dzien_prasy") / DAY
TOP_THEMES = 4
SIGNALS_PER_THEME = 5
MIN_ARTICLES = 8        # kraj z mniejszą próbą dnia: karta bez opisu modelu

NAMES = {"PL": "Polska", "UA": "Ukraina", "DE": "Niemcy", "UK": "Wielka Brytania", "US": "Stany Zjednoczone",
         "CN": "Chiny", "HK": "Hongkong", "IL": "Izrael", "PS": "Palestyna", "TR": "Turcja", "IN": "Indie",
         "BR": "Brazylia", "QA": "Katar", "RU": "Rosja", "FR": "Francja", "HU": "Węgry", "IR": "Iran"}
ACTORS = {**NAMES, "IR": "Iran", "UE": "UE", "NATO": "NATO", "ONZ": "ONZ", "FR": "Francja",
          "JP": "Japonia", "SA": "Arabia Saudyjska", "ES": "Hiszpania", "AU": "Australia", "KR": "Korea Płd."}
STANCE_COLORS = {"alarm": "#c8412f", "krytyka": "#e0873a", "neutralny": "#b9b4aa", "uspokojenie": "#4f9d8f",
                 "poparcie": "#3b6fb6"}
TREND = re.compile(r"rośnie od|maleje od|coraz |narasta|trend|nowy temat|znowu|jak zwykle|codziennie|od tygodnia", re.I)
MEDIA = re.compile(r"\bmedi(?:a|ów|ach|ami)\b", re.I)

PROMPT = """Napisz krótki opis dnia {day} w analizowanych źródłach z kraju {kraj} ({nazwa}): {zrodla}.
To opis przekazu (o czym i jak pisały te redakcje), nie opis faktów i nie ocena. Styl: rzeczowy, jak poranny przegląd prasy.

Zasady:
- tylko to, co jest w DANYCH; nie dodawaj przyczyn, skutków ani ocen, których w danych nie ma;
- redakcje nazywaj po nazwie (np. „onet”, „Global Times”) albo „analizowane źródła”, nigdy „media {nazwa_dop}”;
- żadnych trendów ani porównań z innymi dniami („coraz”, „znowu”, „rośnie”), nie ma linii bazowej;
- cytat w „…” tylko dosłownie z DANYCH, maks. 15 słów;
- każdy wątek ma article_ids wyłącznie z DANYCH;
- twierdzenia redakcji przypisuj im („onet pisał, że…”, „według Global Times…”), nie podawaj ich jako faktów;
- hasło nazywa JEDNĄ konkretną sprawę dnia (wydarzenie, osoba, miejsce), którą redakcje opisywały najczęściej albo najmocniej;
  zakazane w haśle: wyliczanka tematów, „w centrum uwagi”, „dominuje”, „napięcia”;
- bez komentarzy o danych (np. że jakaś redakcja „nie pojawiła się”).

Zwróć JSON:
{{"haslo": "hasło dnia, maks. 60 znaków, bez clickbaitu",
  "opis": "2–3 zdania, maks. 320 znaków: czym żyły analizowane źródła i w jakim tonie",
  "watki": [{{"temat": "<id tematu z DANYCH>", "zdanie": "maks. 140 znaków, z nazwą redakcji", "article_ids": [..]}}]}}
(maks. 3 wątki, od najważniejszego)

DANE:
{dane}
"""


def ro_connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def country_data(pkg: dict, names: dict[str, str], pl_titles: dict[str, str]) -> dict[str, dict]:
    by_country = defaultdict(list)
    for s in pkg["dowody"]:
        by_country[s["kraj"]].append(s)
    out = {}
    for c, info in pkg["kraje"].items():
        sigs = by_country.get(c, [])
        themes = sorted(((t["kraje"].get(c, {}).get("udzial") or 0, t["temat"]) for t in pkg["tematy"]), reverse=True)
        themes = [(share, t) for share, t in themes if share > 0][:TOP_THEMES]
        blocks = []
        for share, t in themes:
            ts = [s for s in sigs if s["theme_id"] == t]
            frames = Counter(s["rama"] for s in ts).most_common(3)
            seen, reps = set(), []
            for s in sorted(ts, key=lambda s: -s["intensywnosc"]):
                if s["article_id"] in seen:
                    continue
                seen.add(s["article_id"])
                reps.append({"article_id": s["article_id"], "zrodlo": s["zrodlo"], "stance": s["stance"],
                             "o_kim": s["subject_actor"], "streszczenie": s["streszczenie"],
                             "tytul_pl": pl_titles.get(str(s["article_id"]), "")})
                if len(reps) == SIGNALS_PER_THEME:
                    break
            blocks.append({"temat": t, "nazwa": names.get(t, t.removeprefix("emergent:")), "udzial": share,
                           "ramy": [f"{f} ({n})" for f, n in frames], "sygnaly": reps})
        out[c] = {
            "kraj": c, "n_artykulow": info["n_artykulow"], "n_zrodel": info["n_zrodel"],
            "zrodla": sorted({s["zrodlo"] for s in sigs}), "tylko_lead": info["udzial_sygnalow_tylko_lead"],
            "stance": dict(Counter(s["stance"] for s in sigs)),
            "o_kim": Counter(s["subject_actor"] for s in sigs).most_common(5),
            "tematy": blocks,
            "ids": sorted({s["article_id"] for s in sigs}),
        }
    return out


def check(desc: dict, data: dict) -> list[str]:
    errs = []
    allowed = set(data["ids"])
    texts = [desc.get("haslo", ""), desc.get("opis", "")] + [w.get("zdanie", "") for w in desc.get("watki", [])]
    for w in desc.get("watki", []):
        bad = set(w.get("article_ids", [])) - allowed
        if bad or not w.get("article_ids"):
            errs.append(f"wątek {w.get('temat')}: odnośniki spoza danych {sorted(bad)}" if bad else "wątek bez odnośników")
    blob = json.dumps(data, ensure_ascii=False).lower()
    for t in texts:
        errs += [f"cytat > 15 słów: {q[:40]}" for q in long_quotes(t)]
        errs += [f"cytat spoza danych: „{q}”" for q in re.findall(r"„([^”\"]+)[”\"]", t) if q.lower() not in blob]
        if TREND.search(t):
            errs.append(f"język trendu: {TREND.search(t).group(0)}")
        if MEDIA.search(t) and "analizowan" not in t.lower():
            errs.append("„media” zamiast analizowanych źródeł")
    if re.search(r"w centrum uwagi|dominuj", desc.get("haslo", ""), re.I):
        errs.append("hasło to wyliczanka, a ma nazwać jedną sprawę")
    if len(desc.get("haslo", "")) > 70 or len(desc.get("opis", "")) > 360:
        errs.append("za długie hasło/opis")
    return errs


def describe(client, data: dict) -> tuple[dict, float, list[str]]:
    c = data["kraj"]
    dane = {k: v for k, v in data.items() if k != "ids"}
    prompt = PROMPT.format(day=DAY, kraj=c, nazwa=NAMES.get(c, c), nazwa_dop=NAMES.get(c, c),
                           zrodla=", ".join(data["zrodla"]), dane=json.dumps(dane, ensure_ascii=False, indent=1))
    cost = 0.0
    for attempt in (1, 2):
        res = _call(client, MODEL, f"dzien-prasy-{DAY}-{c}-{attempt}", prompt)
        cost += res.cost_usd
        try:
            desc = _json(res.text)
        except ValueError:
            continue
        errs = check(desc, data)
        if not errs or attempt == 2:
            return desc, cost, errs
        prompt += "\n\nPOPRAW te błędy poprzedniej odpowiedzi:\n- " + "\n- ".join(errs)
    return {}, cost, ["brak poprawnego JSON"]


# ------------------------------------------------------------------ grafika

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:%(w)dpx;height:%(h)dpx;background:#f4f0e8;color:#1d1b18;font-family:'Segoe UI','Noto Sans','DejaVu Sans',sans-serif;overflow:hidden}
.wrap{padding:56px 64px 40px;height:100%%;display:flex;flex-direction:column;gap:26px}
.brand{font-size:24px;letter-spacing:.18em;font-weight:700;color:#8a3b2a}
.date{font-size:24px;color:#6b655c}
h1{font-size:76px;line-height:1.02;font-weight:800}
.src{font-size:24px;color:#6b655c;margin-top:8px}
.haslo{font-size:46px;line-height:1.15;font-weight:700;border-left:10px solid #8a3b2a;padding-left:24px}
.opis{font-size:28px;line-height:1.36}
.bars{display:flex;flex-direction:column;gap:14px}
.bar{display:grid;grid-template-columns:330px 1fr 90px;align-items:center;gap:16px;font-size:26px}
.track{height:26px;background:#e3ddd2;border-radius:13px;overflow:hidden}
.fill{height:100%%;background:#8a3b2a;border-radius:13px}
.pct{text-align:right;font-weight:700}
.lbl{font-size:22px;letter-spacing:.12em;text-transform:uppercase;color:#6b655c;margin-bottom:10px}
.strip{display:flex;height:30px;border-radius:15px;overflow:hidden}
.legend{display:flex;gap:22px;font-size:21px;color:#6b655c;margin-top:10px;flex-wrap:wrap}
.legend i{display:inline-block;width:16px;height:16px;border-radius:8px;margin-right:7px;vertical-align:-2px}
.w{font-size:27px;line-height:1.32;padding:14px 0;border-top:1px solid #d8d1c4}
.w b{color:#8a3b2a}
.foot{margin-top:auto;font-size:19px;line-height:1.4;color:#7a746a}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.cell{background:#fbf8f2;border:1px solid #ddd5c7;border-radius:16px;padding:16px 22px;display:flex;flex-direction:column;gap:5px}
.cell h3{font-size:28px;font-weight:800}
.cell .t{font-size:19px;color:#8a3b2a;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
.cell .h{font-size:23px;line-height:1.22}
.cell .s{font-size:16px;color:#7a746a}
"""


def esc(s) -> str:
    return html.escape(str(s))


def strip_html(stance: dict) -> str:
    total = sum(stance.values()) or 1
    parts = "".join(f'<div style="width:{100 * stance.get(k, 0) / total:.1f}%;background:{col}"></div>'
                    for k, col in STANCE_COLORS.items() if stance.get(k))
    legend = "".join(f'<span><i style="background:{col}"></i>{k} {round(100 * stance.get(k, 0) / total)}%</span>'
                     for k, col in STANCE_COLORS.items() if stance.get(k))
    return f'<div class="strip">{parts}</div><div class="legend">{legend}</div>'


def card_html(data: dict, desc: dict) -> str:
    c = data["kraj"]
    top = max((b["udzial"] for b in data["tematy"]), default=1) or 1
    bars = "".join(f'<div class="bar"><span>{esc(b["nazwa"])}</span><div class="track"><div class="fill" '
                   f'style="width:{100 * b["udzial"] / top:.0f}%"></div></div><span class="pct">{round(100 * b["udzial"])}%</span></div>'
                   for b in data["tematy"])
    names = {b["temat"]: b["nazwa"] for b in data["tematy"]}
    watki = "".join(f'<div class="w"><b>{esc(names.get(w["temat"], w["temat"]))}:</b> {esc(w["zdanie"])}</div>'
                    for w in desc.get("watki", [])[:2])
    lead = f' · {round(100 * data["tylko_lead"])}% sygnałów tylko z tytułu i leadu' if data["tylko_lead"] else ""
    body = f"""<div class="wrap">
<div><div class="brand">PARALAKSA · DZIEŃ W PRASIE</div><div class="date">{DAY}</div></div>
<div><h1>{esc(NAMES.get(c, c))}</h1><div class="src">wg: {esc(", ".join(data["zrodla"]))}</div></div>
{f'<div class="haslo">{esc(desc["haslo"])}</div>' if desc.get("haslo") else ""}
{f'<div class="opis">{esc(desc["opis"])}</div>' if desc.get("opis") else ""}
<div><div class="lbl">O czym pisano (udział artykułów)</div><div class="bars">{bars}</div></div>
<div><div class="lbl">Ton sygnałów</div>{strip_html(data["stance"])}</div>
<div>{watki}</div>
<div class="foot">Opis przekazu analizowanych źródeł, nie faktów. Próba: {data["n_artykulow"]} artykułów,
{data["n_zrodel"]} niezależnych redakcji{lead}. Streszczenie maszynowe z odnośnikami do artykułów.</div>
</div>"""
    return f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><style>{CSS % {"w": 1080, "h": 1350}}</style></head><body>{body}</body></html>'


def overview_html(all_data: dict, descs: dict, order: list[str]) -> str:
    cells = []
    for c in order:
        d, desc = all_data[c], descs.get(c, {})
        top = d["tematy"][0]["nazwa"] if d["tematy"] else ""
        cells.append(f'<div class="cell"><h3>{esc(NAMES.get(c, c))}</h3><div class="t">{esc(top)}</div>'
                     f'<div class="h">{esc(desc.get("haslo", ""))}</div><div class="s">wg: {esc(", ".join(d["zrodla"]))}</div></div>')
    body = f"""<div class="wrap" style="gap:26px">
<div><div class="brand">PARALAKSA · DZIEŃ W PRASIE</div><div class="date">{DAY}</div></div>
<h1 style="font-size:58px">Czym żyła prasa {len(order)} krajów</h1>
<div class="grid">{''.join(cells)}</div>
<div class="foot">Temat z największym udziałem artykułów w analizowanych źródłach kraju i hasło dnia z ich przekazu.
Opis przekazu, nie faktów. Paralaksa narracji.</div></div>"""
    return f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><style>{CSS % {"w": 1080, "h": 1920}}</style></head><body>{body}</body></html>'


def shoot(html_text: str, name: str, size: tuple[int, int], browser: str) -> Path:
    page, png = OUT / f"{name}.html", OUT / f"{name}.png"
    page.write_text(html_text, encoding="utf-8")
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--window-size={size[0]},{size[1]}", f"--screenshot={png.resolve()}", page.resolve().as_uri()],
                   check=True, capture_output=True, timeout=60)
    return png


def main():
    load_dotenv()
    settings, themes = load_settings(), load_themes()
    names = {t.id: t.name_pl for t in themes}
    conn = ro_connect(Path("data/prod.db"))
    pkg = build_data_package(conn, DAY, settings, themes)
    data = country_data(pkg, names, titles.cached(Path("data/tytuly"), DAY))
    OUT.mkdir(parents=True, exist_ok=True)
    order = sorted(data, key=lambda c: -data[c]["n_artykulow"])
    saved = OUT / "opisy.json"
    if saved.exists():
        descs = json.loads(saved.read_text(encoding="utf-8"))["opisy"]
        cost, errors = 0.0, {}
    elif NO_DESC:
        saved.write_text(json.dumps({"dzien": DAY, "model": None, "koszt_usd": 0, "opisy": {}, "bledy": {}, "dane": data},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"dane bez opisów: {saved}")
        return
    else:
        client = build_client(MODEL, settings.pricing, 30, 1)
        todo = [c for c in order if data[c]["n_artykulow"] >= MIN_ARTICLES]
        with ThreadPoolExecutor(6) as ex:
            results = dict(zip(todo, ex.map(lambda c: describe(client, data[c]), todo)))
        descs = {c: r[0] for c, r in results.items()}
        errors = {c: r[2] for c, r in results.items() if r[2]}
        cost = sum(r[1] for r in results.values())
        saved.write_text(json.dumps({"dzien": DAY, "model": MODEL, "koszt_usd": round(cost, 4), "opisy": descs,
                                     "bledy": errors, "dane": data}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# Dzień w prasie {DAY}", ""]
    for c in order:
        d = descs.get(c, {})
        md += [f"## {NAMES.get(c, c)} (wg: {', '.join(data[c]['zrodla'])}; {data[c]['n_artykulow']} art.)",
               f"**{d.get('haslo', '—')}**", "", d.get("opis", "(za mała próba, bez opisu)"), ""]
        md += [f"- {w['temat']}: {w['zdanie']} [{', '.join(map(str, w['article_ids']))}]" for w in d.get("watki", [])]
        md.append("")
    (OUT / "opisy.md").write_text("\n".join(md), encoding="utf-8")
    browser = find_browser()
    if not browser:
        raise SystemExit("brak Chrome/Edge do renderu")
    for c in order:
        shoot(card_html(data[c], descs.get(c, {})), c, (1080, 1350), browser)
    shoot(overview_html(data, descs, order), "przeglad", (1080, 1920), browser)
    print(f"koszt {cost:.4f} $, kraje {len(order)}, błędy walidacji: {errors or 'brak'}")


if __name__ == "__main__":
    main()
