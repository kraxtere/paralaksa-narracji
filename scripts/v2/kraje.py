"""Zakładka „Kraje” (plan 2026-10-02, docs/zadania/kraje.md): dla każdego kraju dnia 3–5 tematów krajowych z artykułów,
które nie weszły do żadnego wydarzenia wielokrajowego („tylko tutaj”). Codex (model tekstowy, limit konta) grupuje
artykuły kraju w tematy i odrzuca poradniki, lifestyle, sport i pogodę; walidacja w kodzie, jedna próba ponowienia.
  python scripts/v2/kraje.py 2026-10-01
Wejście: okno dnia jak w data/stories/D.json (publication_meta + story_items), bez artykułów przypisanych do historii
(kraje, pozostale, odrzucone) w data/stories/D.json i data/widok/os/dodatkowe/D.json; polskie tytuły z data/tytuly/D.json.
Wynik: data/widok/kraje/D.json {"day", "model", "kraje": {"PL": [{"tytul", "opis", "ids", "redakcje"}]}}, Polska pierwsza.
  python scripts/v2/kraje.py obrazki 2026-10-01 [PL UA ...]   # domyślnie tylko PL; 1 obrazek Codex na kraj
Obrazki: jeden pionowy obrazek 1024×1536 na kraj, N poziomych pasków (N = liczba tematów) rozdzielonych grubą ciemną
ramką; paski wycinane po wykrytych ramkach (inna liczba niż N = błąd, nic nie zapisane) do data/widok/kraje/D/KRAJ-n.webp,
tytuły tematów w data/widok/kraje/D/KRAJ.json (strona pokazuje paski tylko przy zgodnych tytułach).
"""
import json
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

OUT = Path("data/widok/kraje")
MAX_TOPICS, MAX_IDS, MAX_TITLE_WORDS, MIN_DESC_WORDS, MAX_DESC_WORDS = 5, 4, 6, 25, 70


def assigned(day: str) -> set[int]:
    """Article ids already used by multi-country stories (main and further events of the day)."""
    out: set[int] = set()
    for path in (Path(f"data/stories/{day}.json"), Path(f"data/widok/os/dodatkowe/{day}.json")):
        if not path.exists():
            continue
        for h in json.loads(path.read_text(encoding="utf-8")).get("historie", []):
            out |= {k["article_id"] for k in h.get("kraje", [])}
            out |= {int(i) for i in h.get("pozostale", []) + h.get("odrzucone", [])}
    return out


def inputs(day: str) -> dict[str, list[dict]]:
    """Unassigned articles of the day's window, grouped by country, with Polish titles where available."""
    sys.path.insert(0, "src")
    from paralaksa.aggregate.sample import publication_meta
    from paralaksa.site import stories as S
    conn = sqlite3.connect("file:data/prod.db?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    items = S.story_items(conn, day, set(publication_meta(conn, day)["eligible_ids"]))
    conn.close()
    tpath = Path(f"data/tytuly/{day}.json")
    pl = json.loads(tpath.read_text(encoding="utf-8"))["tytuly"] if tpath.exists() else {}
    taken = assigned(day)
    out: dict[str, list[dict]] = {}
    for i in items:
        if i["id"] not in taken:
            out.setdefault(i["kraj"], []).append({**i, "tytul": " ".join((pl.get(str(i["id"])) or i["tytul"]).split())})
    return out


def prompt(country: str, items: list[dict]) -> str:
    lines = "\n".join(f"#{i['id']} | {i['zrodlo']} | {i['tytul']} | {' '.join(i['streszczenie'].split())}" for i in items)
    return (
        f"Niżej artykuły prasy z kraju {country} z jednego dnia, które NIE weszły do wydarzeń opisywanych przez prasę wielu "
        "krajów. Wybierz 3–5 tematów krajowych, o których pisała ta prasa (najpierw te, o których pisało kilka redakcji).\n"
        "- tytul: po polsku, najwyżej 6 słów, rzeczowo, bez ocen;\n"
        "- opis: 2–3 zdania po polsku, 40–60 słów: co się dzieje, kto jest stroną i jak ujmują to redakcje; bez ocen i bez "
        "własnej wiedzy, twierdzenia przypisane źródłom („według X…”, „Y pisze, że…”);\n"
        "- ids: 1–4 numery artykułów o tym temacie (tylko z listy, każdy numer w jednym temacie).\n"
        "Pomijaj poradniki, lifestyle, rozrywkę, sport i pogodę. Jeśli sensownych tematów jest mniej niż 3, podaj tyle, ile jest. "
        "Nie używaj myślników jako przecinków.\n"
        "Zwróć WYŁĄCZNIE JSON: {\"tematy\":[{\"tytul\":\"...\",\"opis\":\"...\",\"ids\":[123]}]}\n\n"
        "Artykuły (numer | redakcja | tytuł | streszczenie):\n" + lines)


def check(topics: list, items: list[dict]) -> list[str]:
    """Validation errors of one country's topics (empty list: valid)."""
    known, seen, errors = {i["id"] for i in items}, set(), []
    if not isinstance(topics, list) or len(topics) > MAX_TOPICS:
        return [f"ma być lista najwyżej {MAX_TOPICS} tematów"]
    for n, t in enumerate(topics, 1):
        if not isinstance(t, dict) or not t.get("tytul") or not t.get("opis") or not isinstance(t.get("ids"), list):
            errors.append(f"temat {n}: brak tytul/opis/ids")
            continue
        if len(t["tytul"].split()) > MAX_TITLE_WORDS:
            errors.append(f"temat {n}: tytuł ma {len(t['tytul'].split())} słów, najwyżej {MAX_TITLE_WORDS}")
        if not MIN_DESC_WORDS <= len(t["opis"].split()) <= MAX_DESC_WORDS:
            errors.append(f"temat {n}: opis ma {len(t['opis'].split())} słów, ma mieć {MIN_DESC_WORDS}–{MAX_DESC_WORDS}")
        if not 1 <= len(t["ids"]) <= MAX_IDS:
            errors.append(f"temat {n}: {len(t['ids'])} artykułów, ma być 1–{MAX_IDS}")
        for i in t["ids"]:
            if i not in known:
                errors.append(f"temat {n}: #{i} spoza wejścia")
            elif i in seen:
                errors.append(f"temat {n}: #{i} powtórzony")
            seen.add(i)
    return errors


def run(country: str, items: list[dict]) -> list[dict]:
    from widok_obrazkowy import codex_text
    text, topics = prompt(country, items), []
    for attempt in range(2):
        raw = codex_text(OUT / f"_codex-{country}", text)
        try:
            topics = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])["tematy"]
            for t in topics:
                t["ids"] = [int(i) for i in t["ids"]]
                t["tytul"], t["opis"] = " ".join(t["tytul"].split()), " ".join(t["opis"].split())
            errors = check(topics, items)
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            errors = [f"niepoprawny JSON ({e})"]
        if not errors:
            break
        print(f"{country}: {'ponawiam' if attempt == 0 else 'pomijam kraj'}: {'; '.join(errors)[:300]}", flush=True)
        text = prompt(country, items) + "\n\nPoprzednio błędy:\n" + "\n".join(errors)
        topics = []
    src = {i["id"]: i["zrodlo"] for i in items}
    for t in topics:
        t["redakcje"] = len({src[i] for i in t["ids"]})
    return sorted(topics, key=lambda t: -t["redakcje"])        # temat z >= 2 redakcji wyżej (sort stabilny)


def main(day: str) -> None:
    from codex_limit import usage
    from widok_obrazkowy import TEXT_MODEL
    data = inputs(day)
    order = sorted(data, key=lambda c: (c != "PL", c))
    before = usage()
    with ThreadPoolExecutor(4) as ex:
        results = dict(zip(order, ex.map(lambda c: run(c, data[c]), order)))
    after = usage()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{day}.json").write_text(json.dumps({"day": day, "model": " ".join(TEXT_MODEL), "kraje": results},
                                                ensure_ascii=False, indent=1), encoding="utf-8")
    used = ", ".join(f"{k} +{(after[k] or 0) - (before[k] or 0)} pp" for k in after
                     if not k.endswith("reset") and k in before)
    print(f"wejście: {sum(map(len, data.values()))} artykułów, {len(data)} krajów, "
          f"{sum(len(prompt(c, data[c])) for c in data)} znaków; tematów: {sum(map(len, results.values()))}; "
          f"limit Codex: {used}")


def strip_prompt(topics: list[dict]) -> str:
    from widok_obrazkowy import PEOPLE_STYLE
    n = len(topics)
    rows = "\n".join(f"Strip {i} (from the top): a scene for this national news topic: \"{t['tytul']}\" ({t['opis']}) "
                     "Show places, objects and a symbolic action, not a portrait." for i, t in enumerate(topics, 1))
    return ("Use your built-in image generation tool to create ONE image from the prompt below, then copy it into the "
            "current directory as pasy.png. Do not write code or other files. Reply only with the file name.\n\nPROMPT:\n"
            "Portrait image 1024×1536 (2:3), clean flat editorial illustration, warm paper tones (#f4f0e8), dark ink, muted "
            f"palette with brick red accents (#8a3b2a). The WHOLE image is a stack of EXACTLY {n} full-width horizontal "
            "strips of equal height, one under another. Strips are separated by thick solid uniform dark bars (#1d1b18, "
            "about 14 px), and the same thick dark border runs around the whole image. No gutters, nothing drawn across "
            "the bars, no title, no header, no footer. " + PEOPLE_STYLE + "\n" + rows +
            "\nABSOLUTELY NO TEXT anywhere: no letters, numbers, captions, signs, logos or flags with writing.")


def detect_strips(png: Path) -> list[tuple[int, int, int, int]]:
    """Pixel boxes (x0, y0, x1, y1) of the strips between thick dark horizontal bars spanning the image width."""
    from PIL import Image
    im = Image.open(png).convert("L")
    w, h = im.size
    px = im.load()

    def runs(flags):
        out, start = [], None
        for i, f in enumerate(flags + [False]):
            if f and start is None:
                start = i
            elif not f and start is not None:
                out.append((start, i - 1))
                start = None
        return out

    def longest(y):
        best = cur = 0
        for x in range(w):
            cur = cur + 1 if px[x, y] < 90 else 0
            best = max(best, cur)
        return best

    # ramka = poziomy ciemny pas przez >= 90% szerokości, gruby na >= 4 px (krawędzie w scenie są cieńsze)
    bars = [(a, b) for a, b in runs([longest(y) >= 0.9 * w for y in range(h)]) if b - a >= 3]
    bars = [(-1, -1)] + bars + [(h, h)]                       # brzegi obrazka, gdy brak ramki zewnętrznej
    boxes = []
    for (_, top), (bottom, _) in zip(bars, bars[1:]):
        y0, y1 = top + 1, bottom - 1
        if y1 - y0 < 0.06 * h:                              # wąska szczelina między ramkami albo margines
            continue
        cols = runs([sum(px[x, y] < 90 for y in range(y0, y1 + 1, 4)) >= 0.9 * len(range(y0, y1 + 1, 4))
                     for x in range(w)])
        left = [b for a, b in cols if a < 0.1 * w]
        right = [a for a, b in cols if b > 0.9 * w]
        boxes.append((left[0] + 1 if left else 0, y0, right[-1] - 1 if right else w - 1, y1))
    return boxes


def images(day: str, countries: list[str]) -> None:
    from PIL import Image
    from widok_obrazkowy import run_codex
    data = json.loads((OUT / f"{day}.json").read_text(encoding="utf-8"))["kraje"]
    folder = OUT / day
    for country in countries:
        topics = data.get(country) or []
        if not topics:
            print(f"{country}: brak tematów")
            continue
        work = folder / f"_gen-{country}"
        run_codex(work, strip_prompt(topics))
        png = work / "pasy.png"
        if not png.exists():
            raise SystemExit(f"{country}: Codex nie zapisał obrazka (zob. {work / 'codex.log'})")
        boxes = detect_strips(png)
        if len(boxes) != len(topics):
            raise SystemExit(f"{country}: wykryto {len(boxes)} pasków, tematów {len(topics)}; nic nie zapisano ({png})")
        im = Image.open(png).convert("RGB")
        for n, box in enumerate(boxes, 1):
            im.crop((box[0], box[1], box[2] + 1, box[3] + 1)).save(folder / f"{country}-{n}.webp", quality=85)
        png.replace(folder / f"_{country}.png")
        (folder / f"{country}.json").write_text(json.dumps([t["tytul"] for t in topics], ensure_ascii=False),
                                                encoding="utf-8")
        print(f"{country}: {len(boxes)} pasków {im.size[0]}×{im.size[1]} -> {folder}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "obrazki" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[2]):
        images(sys.argv[2], sys.argv[3:] or ["PL"])
    elif len(sys.argv) == 2 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[1]):
        main(sys.argv[1])
    else:
        raise SystemExit(__doc__)
