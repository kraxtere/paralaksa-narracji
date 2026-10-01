"""Ad hoc prototyp: plakaty komiksowe z opisów dnia (scripts/v2/dzien_prasy.py) przez Codex (image_gen z konta) + kontrola obrazu Claude.

  python scripts/v2/komiks_codex.py gen JOB [JOB ...]     # JOB: przeglad | kraj:US | kraj:UK ...; generuje i sprawdza
  python scripts/v2/komiks_codex.py check OBRAZ SPEC.json # sama kontrola istniejącego obrazu

Wynik: data/comic/codex/<job>/{polecenie.txt, spec.json, obraz.png, kontrola.json, codex.log}
Codex pracuje tylko w folderze joba (workspace-write), bez kodu; Claude nie ufa obrazowi: przepisuje tekst, kod porównuje.
"""

import base64
import glob
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

from paralaksa.config import load_settings
from paralaksa.extract.llm_client import LLMRequest, build_client
from paralaksa.gdelt.tv_stories import _json

DAY = "2026-09-29"
ROOT = Path("data/comic/codex")
OPISY = Path("data/dzien_prasy") / DAY / "opisy.json"
CHECK_MODEL = "claude-sonnet-5"
NAMES = {"PL": "Polska", "UA": "Ukraina", "DE": "Niemcy", "UK": "Wielka Brytania", "US": "USA", "CN": "Chiny",
         "IL": "Izrael", "TR": "Turcja", "IN": "Indie", "HK": "Hongkong", "PS": "Palestyna", "BR": "Brazylia", "QA": "Katar"}
SCARF = {"PL": "white-red", "UA": "blue-yellow", "DE": "black-red-gold", "UK": "union flag", "US": "stars and stripes",
         "CN": "red with yellow stars", "IL": "white with blue star of David", "TR": "red with white crescent",
         "IN": "saffron-white-green", "HK": "red with white bauhinia flower", "PS": "black-white-green with red triangle",
         "BR": "green-yellow", "QA": "maroon-white"}
FOOTER = "Opis przekazu analizowanych źródeł, nie faktów · Paralaksa"
STYLE = ("clean flat editorial comic illustration, warm paper background (#f4f0e8), dark ink outlines, muted palette with "
         "brick red accents (#8a3b2a). No realistic people, no politicians' faces, no ethnic features; countries appear only "
         "as friendly cartoon mascots: a folded newspaper with a simple face wearing a scarf in the country's flag colours.")
# Lżejsza wskazówka (decyzja właściciela 2026-09-30: nie przesadzać z cenzurą rysunku; rygor tylko dla tekstu).
SAFE = ("Illustrate the caption symbolically; where the caption reports a claim or suspicion, keep it visibly a claim "
        "(e.g. a newspaper page or screen showing it) rather than a proven event. No photorealistic real people.")


def codex_exe() -> str:
    found = sorted(glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe")), key=os.path.getmtime)
    if not found:
        raise SystemExit("nie znaleziono codex.exe")
    return found[-1]


def spec_country(code: str, opisy: dict) -> dict:
    d, data = opisy["opisy"][code], opisy["dane"][code]
    sources = ", ".join(data["zrodla"])
    panels = [{"tekst": w["zdanie"], "article_ids": w["article_ids"]} for w in d["watki"][:3]]
    texts = [f"{NAMES[code]} · {DAY[8:10]}.{DAY[5:7]} · wg: {sources}", d["haslo"], *[p["tekst"] for p in panels], FOOTER]
    prompt = (f"Portrait 4:5 editorial infographic poster, {STYLE}\n"
              f"Header line, exactly: \"{texts[0]}\".\nBig title, exactly: \"{d['haslo']}\".\n"
              f"Below: {len(panels)} stacked comic panels. In every panel the {NAMES[code]} mascot (scarf {SCARF[code]}) "
              f"reports the story. {SAFE} No added facts, numbers or slogans. "
              "Each panel has one caption box with EXACTLY this Polish text:\n"
              + "\n".join(f"Panel {i}: \"{p['tekst']}\"" for i, p in enumerate(panels, 1))
              + f"\nSmall footer, exactly: \"{FOOTER}\".\nUse correct Polish diacritics. No other text anywhere.")
    return {"job": f"kraj-{code}", "prompt": prompt, "texts": texts,
            "mascots": [{"panel": "wszystkie", "kraj": code, "szalik": SCARF[code]}], "panels": panels}


def spec_overview(codes: list[str], opisy: dict) -> dict:
    items = []
    for i, c in enumerate(codes, 1):
        d, data = opisy["opisy"][c], opisy["dane"][c]
        items.append({"nr": i, "kraj": c, "dymek": d["haslo"], "podpis": f"{NAMES[c]} · wg: {', '.join(data['zrodla'])}"})
    title = f"Czym żyła prasa {DAY[8:10]}.{DAY[5:7]}"
    rows = (len(items) + 1) // 2
    prompt = (f"Vertical 9:16 comic poster, {STYLE}\nTitle at top, exactly: \"{title}\". {len(items)} panels in a 2x{rows} grid. "
              "In each panel one country mascot with one speech bubble (EXACT Polish text) and a caption under the panel. "
              f"Add a small background landmark of the country. Props must not be shared between panels. {SAFE}\n"
              + "\n".join(f"{it['nr']}) {NAMES[it['kraj']]}, scarf {SCARF[it['kraj']]}. Bubble: \"{it['dymek']}\". "
                          f"Caption: \"{it['podpis']}\"" for it in items)
              + f"\nFooter small text, exactly: \"{FOOTER}\". Use correct Polish diacritics. No other text anywhere.")
    return {"job": "przeglad", "prompt": prompt, "texts": [title, *[t for it in items for t in (it["dymek"], it["podpis"])], FOOTER],
            "mascots": [{"panel": it["nr"], "kraj": it["kraj"], "szalik": SCARF[it["kraj"]], "dymek": it["dymek"]} for it in items]}


def generate(spec: dict) -> Path:
    job = ROOT / spec["job"]
    job.mkdir(parents=True, exist_ok=True)
    out = job / "obraz.png"
    (job / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    (job / "polecenie.txt").write_text(
        "Use your built-in image generation tool to create ONE image from the prompt below, then copy it into the current "
        "directory as obraz.png. Do not write code or other files. Reply only with the file name.\n\nPROMPT:\n"
        + spec["prompt"], encoding="utf-8")
    if out.exists():
        out.rename(job / f"obraz-{int(out.stat().st_mtime)}.png")
    with open(job / "codex.log", "w", encoding="utf-8") as log:
        subprocess.run([codex_exe(), "exec", "--skip-git-repo-check", "-C", str(job.resolve()), "--sandbox", "workspace-write",
                        "-c", 'model_reasoning_effort="medium"',
                        "Read the file polecenie.txt in the current directory (UTF-8) and follow its instructions exactly."],
                       stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=900)
    if not out.exists():
        raise RuntimeError(f"{spec['job']}: Codex nie zapisał obrazu (log: {job / 'codex.log'})")
    return out


CHECK_PROMPT = """Jesteś korektorem grafiki. Przepisz DOSŁOWNIE cały tekst widoczny na obrazku (zachowaj litery, polskie znaki,
interpunkcję; łamanie wierszy zamień na spacje), fragment po fragmencie, w kolejności od góry. Nie poprawiaj błędów.
Potem dla każdej postaci-maskotki opisz: w którym panelu jest (numer od lewej-góry), kolory szalika, trzymany rekwizyt,
i jaki tekst dymka/podpisu jest przy niej.
Wypisz też osobno wszystkie liczby, nazwy i hasła na obrazku, które nie są częścią dymków/podpisów/tytułów (np. na tablicach, ekranach).
Zwróć JSON: {"teksty": ["…"], "postacie": [{"panel": 1, "szalik": "…", "rekwizyt": "…", "tekst_przy_postaci": "…"}],
"inne_napisy": ["…"]}"""

JUDGE_PROMPT = """Porównaj opis postaci z obrazka z zamówieniem. Dla każdej zamówionej postaci odpowiedz, czy na obrazku
postać z tym tekstem ma szalik w zamówionych barwach (true/false) i czy jakaś inna postać nosi te barwy albo ten sam rekwizyt.
ZAMÓWIENIE: {order}
OPIS Z OBRAZKA: {seen}
Zwróć JSON: {{"postacie": [{{"kraj": "PL", "szalik_zgodny": true, "uwaga": ""}}]}}"""


VISUAL_PROMPT = """Jesteś redaktorem odpowiedzialnym za grafikę publikowaną publicznie. Obrazek ilustruje podpisy:
{captions}
Dla KAŻDEGO panelu oceń sam rysunek (nie tekst). Odpowiedz true/false:
- "dodaje_fakty": rysunek pokazuje coś jako fakt, czego podpis nie twierdzi (np. sprawcę, wybuch, winnego, skutek),
  albo zamienia „X twierdzi/uznał” w „tak było”;
- "szkodliwy_motyw": motywy, które mogą być odczytane jako nienawistne albo stereotypowe (np. lalkarz/sterujące ręce,
  symbole religijne przy spisku, karykatura grup etnicznych lub religijnych, dehumanizacja);
- "prawdziwa_osoba": rozpoznawalna lub opisana w podpisie prawdziwa osoba (także sylwetka);
- "flaga_jako_sprawca": flaga lub symbol państwa na postaci sprawcy/zagrożenia.
Zwróć JSON: {{"panele": [{{"panel": 1, "dodaje_fakty": false, "szkodliwy_motyw": false, "prawdziwa_osoba": false,
"flaga_jako_sprawca": false, "opis": "co widać, 1 zdanie"}}]}}"""


def visual_check(client, image: Path, spec: dict) -> tuple[list[dict], float]:
    captions = "\n".join(f"- {t}" for t in spec["texts"])
    res = client.complete(LLMRequest(custom_id=f"rysunek-{spec['job']}", model=CHECK_MODEL, max_tokens=3000,
                                     messages=[{"role": "user", "content": [image_block(image), {"type": "text",
                                                "text": VISUAL_PROMPT.format(captions=captions)}]}]))
    if not res.ok:
        raise RuntimeError(res.error)
    panels = _json(res.text).get("panele", [])
    flags = ("dodaje_fakty", "szkodliwy_motyw", "prawdziwa_osoba", "flaga_jako_sprawca")
    return [p for p in panels if any(p.get(f) for f in flags)], res.cost_usd


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).replace(" ", " ")
    s = re.sub(r"[„”\"“]", '"', s)
    s = re.sub(r"[•∙⋅]", "·", s)            # odczyt kropki środkowej jako punktora to nie błąd grafiki
    return re.sub(r"\s+", " ", s).strip().rstrip(".").strip().lower()


def _block(im) -> dict:
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                        "data": base64.b64encode(buf.getvalue()).decode()}}


def image_block(path: Path) -> dict:
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((1568, 1568))
    return _block(im)


def strips(path: Path, n: int = 4, overlap: float = 0.06) -> list[dict]:
    """Horizontal strips, upscaled: at full-poster scale the reader silently fixes typos (e.g. „ałtaki” read as „ataki”)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    step = h / n
    out = []
    for i in range(n):
        top, bottom = max(0, int(i * step - overlap * h)), min(h, int((i + 1) * step + overlap * h))
        s = im.crop((0, top, w, bottom))
        scale = min(1568 / s.width, 1568 / s.height, 2.0)
        out.append(_block(s.resize((int(s.width * scale), int(s.height * scale)), Image.LANCZOS)))
    return out


SPELL_PROMPT = """To jest kontrola literówek na grafice pociętej na {n} zachodzące na siebie pasy (od góry).
Przepisz ZNAK PO ZNAKU cały widoczny tekst, dokładnie tak, jak jest narysowany: jeśli słowo ma dodatkową, brakującą
albo zmienioną literę (np. „ałtaki” zamiast „ataki”), przepisz je Z BŁĘDEM. Niczego nie poprawiaj ani nie uzupełniaj
domysłem; nieczytelny znak oznacz jako [?]. Tekst ucięty na krawędzi pasa pomiń (jest w sąsiednim pasie).
Zwróć JSON: {{"teksty": ["…"], "podejrzane": ["słowa, które wyglądają na błędnie narysowane"]}}"""


def check(image: Path, spec: dict) -> dict:
    settings = load_settings()
    client = build_client(CHECK_MODEL, settings.pricing, 30, 1)
    res = client.complete(LLMRequest(custom_id=f"kontrola-{spec['job']}", model=CHECK_MODEL, max_tokens=4000,
                                     messages=[{"role": "user", "content": [image_block(image), {"type": "text", "text": CHECK_PROMPT}]}]))
    if not res.ok:
        raise RuntimeError(res.error)
    seen, cost = _json(res.text), res.cost_usd
    parts = strips(image)
    res3 = client.complete(LLMRequest(custom_id=f"literowki-{spec['job']}", model=CHECK_MODEL, max_tokens=4000,
                                      messages=[{"role": "user", "content": [*parts, {"type": "text",
                                                                                       "text": SPELL_PROMPT.format(n=len(parts))}]}]))
    if not res3.ok:
        raise RuntimeError(res3.error)
    spell, cost = _json(res3.text), cost + res3.cost_usd
    seen["teksty_z_pasow"], seen["podejrzane"] = spell.get("teksty", []), spell.get("podejrzane", [])
    # tekst liczy się jako obecny, gdy jest i w odczycie całości, i w odczycie z pasów (pasy łapią literówki)
    blob = " | ".join(norm(t) for t in seen.get("teksty", []))
    strip_blob = norm(" ".join(spell.get("teksty", [])))
    missing = [t for t in spec["texts"] if norm(t) not in blob or norm(t) not in strip_blob]
    expected = {norm(t) for t in spec["texts"]}
    extra = [t for t in seen.get("teksty", []) if not any(norm(t) in e or e in norm(t) for e in expected)]
    swaps = []
    if len(spec["mascots"]) > 1:
        res2 = client.complete(LLMRequest(custom_id=f"sedzia-{spec['job']}", model=CHECK_MODEL, max_tokens=2000,
                                          messages=[{"role": "user", "content": JUDGE_PROMPT.format(
                                              order=json.dumps(spec["mascots"], ensure_ascii=False),
                                              seen=json.dumps(seen.get("postacie", []), ensure_ascii=False))}]))
        cost += res2.cost_usd
        swaps = [p for p in _json(res2.text).get("postacie", []) if not p.get("szalik_zgodny")]
    visual, vcost = visual_check(client, image, spec)
    cost += vcost
    verdict = {"ok": not missing and not swaps, "brakujace_lub_znieksztalcone": missing,
               "rysunek_ostrzezenia": visual,   # tylko do wglądu, nie odrzuca obrazu
               "podejrzane_slowa": seen["podejrzane"], "dodatkowe_napisy": extra,
               "inne_napisy": seen.get("inne_napisy", []), "zamiany_postaci": swaps, "koszt_usd": round(cost, 4),
               "odczyt": seen}
    return verdict


def main():
    load_dotenv()
    if sys.argv[1] == "check":
        spec = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        v = check(Path(sys.argv[2]), spec)
        print(json.dumps({k: v[k] for k in v if k != "odczyt"}, ensure_ascii=False, indent=1))
        return
    opisy = json.loads(OPISY.read_text(encoding="utf-8"))
    for job in sys.argv[2:]:
        if job == "przeglad":
            spec = spec_overview(["PL", "UA", "DE", "UK", "US", "CN", "IL", "TR"], opisy)
        else:
            spec = spec_country(job.split(":")[1], opisy)
        print(f"{spec['job']}: generuję…", flush=True)
        try:
            img = generate(spec)
        except Exception as e:
            print(f"{spec['job']}: BŁĄD {e}", flush=True)
            continue
        v = check(img, spec)
        (ROOT / spec["job"] / "kontrola.json").write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{spec['job']}: {'OK' if v['ok'] else 'DO POPRAWY'}; braki {len(v['brakujace_lub_znieksztalcone'])}, "
              f"zamiany {len(v['zamiany_postaci'])}, dodatkowe {len(v['dodatkowe_napisy'])}, kontrola {v['koszt_usd']} $",
              flush=True)


if __name__ == "__main__":
    main()
