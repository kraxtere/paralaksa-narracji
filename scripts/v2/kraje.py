"""Zakładka „Kraje” (plan 2026-10-02, docs/zadania/kraje.md): dla każdego kraju dnia 3–5 tematów krajowych z artykułów,
które nie weszły do żadnego wydarzenia wielokrajowego („tylko tutaj”). Codex (model tekstowy, limit konta) grupuje
artykuły kraju w tematy i odrzuca poradniki, lifestyle, sport i pogodę; walidacja w kodzie, jedna próba ponowienia.
  python scripts/v2/kraje.py 2026-10-01
Wejście: okno dnia jak w data/stories/D.json (publication_meta + story_items), bez artykułów przypisanych do historii
(kraje, pozostale, odrzucone) w data/stories/D.json i data/widok/os/dodatkowe/D.json; polskie tytuły z data/tytuly/D.json.
Wynik: data/widok/kraje/D.json {"day", "model", "kraje": {"PL": [{"tytul", "opis", "ids", "redakcje"}]}}, Polska pierwsza.
"""
import json
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

OUT = Path("data/widok/kraje")
MAX_TOPICS, MAX_IDS, MAX_TITLE_WORDS, MAX_DESC_WORDS = 5, 4, 6, 25


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
        "- opis: jedno zdanie po polsku, najwyżej 25 słów, co podaje prasa, bez ocen i bez własnej wiedzy;\n"
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
        if len(t["opis"].split()) > MAX_DESC_WORDS:
            errors.append(f"temat {n}: opis ma {len(t['opis'].split())} słów, najwyżej {MAX_DESC_WORDS}")
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


if __name__ == "__main__":
    if len(sys.argv) != 2 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[1]):
        raise SystemExit(__doc__)
    main(sys.argv[1])
