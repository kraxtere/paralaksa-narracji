"""Zakładka „Kraje” (plan 2026-10-02, docs/zadania/kraje.md): dla każdego kraju dnia 3–5 tematów krajowych z artykułów,
które nie weszły do żadnego wydarzenia wielokrajowego („tylko tutaj”). Codex (model tekstowy, limit konta) grupuje
artykuły kraju w tematy i odrzuca poradniki, lifestyle, sport i pogodę; walidacja w kodzie, jedna próba ponowienia.
  python scripts/v2/kraje.py 2026-10-01
Wejście: okno dnia jak w data/stories/D.json (publication_meta + story_items), bez artykułów przypisanych do historii
(kraje, pozostale, odrzucone) w data/stories/D.json i data/widok/os/dodatkowe/D.json; polskie tytuły z data/tytuly/D.json.
Wynik: data/widok/kraje/D.json {"day", "model", "kraje": {"PL": [{"tytul", "opis", "ids", "redakcje"}]}}, Polska pierwsza.
  python scripts/v2/kraje.py obrazki 2026-10-01 [PL UA ...]   # domyślnie tylko PL; 1 obrazek Codex na kraj
Obrazki: jeden pionowy obrazek 1024×1536 na kraj, N poziomych pasków (N = liczba tematów) rozdzielonych grubą ciemną
ramką; N−1 ramek szukane w oknach ±15% wysokości paska wokół k·H/N (brak ramki w oknie = błąd, nic nie zapisane) do data/widok/kraje/D/KRAJ-n.webp,
tytuły tematów w data/widok/kraje/D/KRAJ.json (strona pokazuje paski tylko przy zgodnych tytułach).
  python scripts/v2/kraje.py pokroj 2026-10-01 IL ...         # ponowne cięcie zapisanego oryginału, bez Codex
  python scripts/v2/kraje.py ciag 2026-10-01      # Codex: które tematy to ciąg dalszy spraw z 7 dni wstecz (ciag_od)
  python scripts/v2/kraje.py strona               # oś kraju data/widok/kraje/KRAJ.html, wszystkie dni, najnowszy u góry
"""
import json
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
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


def runs_strips(png: Path) -> list[tuple[int, int, int, int]]:
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


def chosen_strips(png: Path, n: int) -> list[tuple[int, int, int, int]]:
    """Pixel boxes (x0, y0, x1, y1) of exactly n strips, or [] when no set of n-1 inner bars fits.

    A bar is a horizontal band 6 px to 3% of the height thick whose rows are >= 95% dark pixels of one uniform tone
    (thicker dark bands are scenery). Of all choices of n-1 bars leaving every strip >= 40% of the mean strip height,
    the one with the thickest bars (then the most even strips) wins, so dark lines inside the scenes do not change the count."""
    from itertools import combinations
    from PIL import Image, ImageStat
    im = Image.open(png).convert("L")
    w, h = im.size
    px = im.load()
    mask = im.point(lambda v: 255 if v < 90 else 0)

    def is_bar_row(y):
        if ImageStat.Stat(mask.crop((0, y, w, y + 1))).mean[0] < 0.95 * 255:
            return False
        dark = [px[x, y] for x in range(0, w, 2) if px[x, y] < 90]
        mean = sum(dark) / len(dark)
        return (sum((v - mean) ** 2 for v in dark) / len(dark)) ** 0.5 <= 20

    flags = [is_bar_row(y) for y in range(h)]
    bands, start = [], None
    for y, f in enumerate(flags + [False]):
        if f and start is None:
            start = y
        elif not f and start is not None:
            bands.append((start, y - 1))
            start = None
    thin = [(a, b) for a, b in bands if b - a + 1 <= 0.03 * h]
    top = next((b for a, b in thin if a == 0), -1)                    # ramka zewnętrzna (gdy jest)
    bottom = next((a for a, b in thin if b == h - 1), h)
    inner = [(a, b) for a, b in thin if b - a >= 5 and a > top and b < bottom]
    least, best = 0.4 * (bottom - top) / n, None
    for pick in combinations(inner, n - 1):
        edges = [(top, top), *pick, (bottom, bottom)]
        heights = [nxt[0] - prev[1] - 1 for prev, nxt in zip(edges, edges[1:])]
        if min(heights) >= least:
            weight = (sum(b - a for a, b in pick), -(max(heights) - min(heights)))   # remis: równiejsze paski
            if best is None or weight > best[0]:
                best = (weight, edges)
    if best is None:
        return []
    bars = best[1]
    boxes = []
    for (_, t), (bt, _) in zip(bars, bars[1:]):
        y0, y1 = t + 1, bt - 1
        ys = range(y0, y1 + 1, 4)
        cols = [sum(px[x, y] < 90 for y in ys) >= 0.9 * len(ys) for x in range(w)]
        left = next((x for x in range(int(0.1 * w)) if cols[x] and not cols[x + 1]), -1)
        right = next((x for x in range(w - 1, int(0.9 * w), -1) if cols[x] and not cols[x - 1]), w)
        boxes.append((left + 1, y0, right - 1, y1))
    return boxes


def detect_strips(png: Path, n: int) -> list[tuple[int, int, int, int]]:
    """Strips by all wide dark bars (runs_strips); when their count is not n or a strip is under 40% of the mean
    strip height (a scene line taken for a bar), the best choice of n-1 bars (chosen_strips)."""
    boxes = runs_strips(png)
    if len(boxes) == n and min(b[3] - b[1] for b in boxes) + 1 >= 0.4 * sum(b[3] - b[1] + 1 for b in boxes) / n:
        return boxes
    return chosen_strips(png, n)


def cut(day: str, country: str, topics: list[dict], png: Path) -> None:
    """Slices png into the strips of the topics and saves them; SystemExit when the bars do not match."""
    from PIL import Image
    folder = OUT / day
    boxes = detect_strips(png, len(topics))
    if not boxes:
        raise SystemExit(f"{country}: brak ramki w oknie, tematów {len(topics)}; nic nie zapisano ({png})")
    im = Image.open(png).convert("RGB")
    for n, box in enumerate(boxes, 1):
        im.crop((box[0], box[1], box[2] + 1, box[3] + 1)).save(folder / f"{country}-{n}.webp", quality=85)
    if png != folder / f"_{country}.png":
        png.replace(folder / f"_{country}.png")
    (folder / f"{country}.json").write_text(json.dumps([t["tytul"] for t in topics], ensure_ascii=False),
                                            encoding="utf-8")
    print(f"{country}: {len(boxes)} pasków {im.size[0]}×{im.size[1]} -> {folder}")


def recut(day: str, countries: list[str]) -> None:
    """Slices again the saved originals (_gen-KRAJ/pasy.png after a rejection, else _KRAJ.png), without Codex."""
    data = json.loads((OUT / f"{day}.json").read_text(encoding="utf-8"))["kraje"]
    for country in countries:
        folder = OUT / day
        png = next((p for p in (folder / f"_gen-{country}" / "pasy.png", folder / f"_{country}.png") if p.exists()), None)
        if not png or not data.get(country):
            print(f"{country}: brak oryginału albo tematów")
            continue
        cut(day, country, data[country], png)


def images(day: str, countries: list[str]) -> None:
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
        cut(day, country, topics, png)


def strip_names(day: str, country: str, topics: list[dict]) -> list[str]:
    """Strip files of the topics (data/widok/kraje/D/KRAJ-n.webp) when the stored titles match the current ones."""
    saved = OUT / day / f"{country}.json"
    if saved.exists() and json.loads(saved.read_text(encoding="utf-8")) == [t["tytul"] for t in topics]:
        return [f"{country}-{n}.webp" for n in range(1, len(topics) + 1)]
    return []


def load_days() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text(encoding="utf-8"))["kraje"] for p in sorted(OUT.glob("*.json"))
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem)}


def ciag_prompt(country: str, day: str, topics: list[dict], previous: dict[str, list[dict]]) -> str:
    def line(key, t):
        return f"- {key}: {t['tytul']}. {t['opis']}"
    return (
        f"Niżej tematy prasy z kraju {country} z dnia {day} (numerowane) i tematy tej samej prasy z poprzednich dni "
        "(klucz DATA#n). Wskaż tematy dnia, które są CIĄGIEM DALSZYM konkretnej sprawy z poprzednich dni: ta sama sprawa, "
        "te same osoby lub instytucje, kolejny etap (np. nowe zarzuty w tym samym śledztwie). Sam ten sam obszar "
        "(np. dwie różne sprawy sądowe) to NIE ciąg dalszy. Przy kilku pasujących dniach wskaż najpóźniejszy.\n"
        "Zwróć WYŁĄCZNIE JSON: {\"ciag\":[{\"temat\":1,\"od\":\"2026-09-30#2\"}]} (pusta lista, jeśli nic).\n\n"
        f"Tematy dnia {day}:\n" + "\n".join(line(n, t) for n, t in enumerate(topics, 1)) +
        "\n\nPoprzednie dni:\n" + "\n".join(line(f"{d}#{n}", t) for d in sorted(previous)
                                            for n, t in enumerate(previous[d], 1)))


def check_ciag(pairs: list, n_today: int, previous: dict[str, list[dict]]) -> list[str]:
    """The day and the topic referenced as the earlier case must exist; each topic of the day at most once."""
    errors, seen = [], set()
    for p in pairs:
        if not isinstance(p, dict) or not isinstance(p.get("temat"), int) or not isinstance(p.get("od"), str):
            errors.append(f"zły wpis {p}")
            continue
        found = re.fullmatch(r"(\d{4}-\d{2}-\d{2})#(\d+)", p["od"])
        if not 1 <= p["temat"] <= n_today or p["temat"] in seen:
            errors.append(f"temat {p['temat']}: spoza listy albo powtórzony")
        elif not found or found.group(1) not in previous:
            errors.append(f"temat {p['temat']}: dzień {p['od']} nie istnieje")
        elif not 1 <= int(found.group(2)) <= len(previous[found.group(1)]):
            errors.append(f"temat {p['temat']}: {p['od']} nie ma takiego tematu")
        seen.add(p["temat"])
    return errors


def ciag(day: str) -> None:
    """Mark the day's topics that continue a case of the last 7 days (ciag_od: first day of the case)."""
    from widok_obrazkowy import codex_text
    days = load_days()
    data = days[day]
    window = {(date.fromisoformat(day) - timedelta(days=k)).isoformat() for k in range(1, 8)}

    def one(country: str) -> int:
        topics = data[country]
        for t in topics:
            t.pop("ciag_od", None)
        previous = {d: days[d][country] for d in sorted(window & days.keys()) if days[d].get(country)}
        if not topics or not previous:
            return 0
        text, pairs = ciag_prompt(country, day, topics, previous), []
        for attempt in range(2):
            raw = codex_text(OUT / f"_codex-ciag-{country}", text)
            try:
                pairs = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])["ciag"]
                errors = check_ciag(pairs, len(topics), previous)
            except (ValueError, KeyError, TypeError) as e:
                errors = [f"niepoprawny JSON ({e})"]
            if not errors:
                break
            print(f"{country}: {'ponawiam' if attempt == 0 else 'pomijam kraj'}: {'; '.join(errors)[:300]}", flush=True)
            text, pairs = ciag_prompt(country, day, topics, previous) + "\n\nPoprzednio błędy:\n" + "\n".join(errors), []
        for p in pairs:
            d, n = p["od"].split("#")
            earlier = previous[d][int(n) - 1]
            topics[p["temat"] - 1]["ciag_od"] = earlier.get("ciag_od") or d     # początek sprawy, nie poprzedni etap
        return len(pairs)

    with ThreadPoolExecutor(4) as ex:
        found = sum(ex.map(one, list(data)))
    doc = json.loads((OUT / f"{day}.json").read_text(encoding="utf-8"))
    doc["kraje"] = data
    (OUT / f"{day}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{day}: ciąg dalszy w {found} tematach (dni wstecz z danymi: {len(window & days.keys())})")


def country_pages() -> None:
    """data/widok/kraje/KRAJ.html: every day with national topics of the country, newest first (plx site -> v2/kraje/)."""
    import widok_obrazkowy as W
    days = load_days()
    order = sorted(days, reverse=True)
    countries = sorted({c for d in days for c, ts in days[d].items() if ts}, key=lambda c: (c != "PL", W.NAMES.get(c, c)))
    W.OUT = OUT                                   # src_html kopiuje logo obok strony
    for country in countries:
        sections = []
        for d in order:
            topics = days[d].get(country) or []
            if not topics:
                continue
            W.DAY = d
            pl = {**W.polish_titles(), **W.titles.cached(Path("data/tytuly"), d)}
            strips = strip_names(d, country, topics) or [""] * len(topics)
            body = ""
            for t, strip in zip(topics, strips):
                img = f'<img class="pas" src="{d}/{strip}" alt="" loading="lazy">' if strip else ""
                od = t.get("ciag_od")
                note = (f'<p class="ciag"><a href="#d-{od}"><b>Ciąg dalszy</b> · od {od[8:10]}.{od[5:7]}</a></p>'
                        if od else "")
                body += f'{img}<h3>{W.esc(t["tytul"])}</h3>{note}<p>{W.esc(t["opis"])}</p>{W.article_list(t["ids"], pl)}'
            sections.append(f'<section id="d-{d}"><h2>{d[8:10]}.{d[5:7]} <a class="osk" href="../{d}/kraje.html'
                            f'#kraj-{country}">cały dzień →</a></h2>{body}</section>')
        name = W.NAMES.get(country, country)
        title = f"{name} · tylko tutaj"
        page = (f'<div id="pasek" data-dzien="{order[0]}" data-wstecz></div><script src="../pasek.js"></script>'
                f'<div class="list" data-sekcja="kraje"><h1>{W.esc(title)}</h1>'
                f'<p>Sprawy obecne tylko w prasie tego kraju ({W.esc(name)}), dzień po dniu, najnowszy u góry.</p>'
                '<p class="s">Tematy i opisy wybrane przez AI z nagłówków prasy; nagłówki w tłumaczeniu roboczym, '
                'dłuższe skrócone do 15 słów.</p>' + "".join(sections) + '</div>')
        (OUT / f"{country}.html").write_text(W.shell(title, page), encoding="utf-8")
    print(f"strony osi kraju: {len(countries)} ({', '.join(countries)}), dni: {len(order)}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "obrazki" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[2]):
        images(sys.argv[2], sys.argv[3:] or ["PL"])
    elif len(sys.argv) >= 4 and sys.argv[1] == "pokroj" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[2]):
        recut(sys.argv[2], sys.argv[3:])
    elif len(sys.argv) == 3 and sys.argv[1] == "ciag" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[2]):
        ciag(sys.argv[2])
    elif sys.argv[1:] == ["strona"]:
        country_pages()
    elif len(sys.argv) == 2 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[1]):
        main(sys.argv[1])
    else:
        raise SystemExit(__doc__)
