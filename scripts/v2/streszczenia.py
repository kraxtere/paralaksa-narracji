"""Streszczenia artykułów pod nagłówkami stron 2.0 (decyzja właściciela 2026-10-02): klik w nagłówek pod krajem rozwija
5–7 zdań streszczenia i link „Przejdź do artykułu”. Tylko dla nagłówków, które strony pokazują (linki z data-a=<id artykułu>
na stronach dnia i na osi), nie dla całej ekstrakcji. Codex z limitu konta, pełny tekst z lokalnej bazy (0 $).
Źródła bez pełnego tekstu (paywall, np. rp, Spiegel): 1–2 zdania z leadu, oznaczone na stronie.
  python scripts/v2/streszczenia.py 2026-10-02          # strony dnia D i oś czasu; tylko brakujące
  python scripts/v2/streszczenia.py wszystko            # wszystkie dni w data/widok/ i oś
Wynik: data/widok/streszczenia/<id // 500>.json ({id: {"t": tekst, "lead": bool}}); plx site kopiuje do v2/streszczenia/,
a v2/pasek.js wczytuje plik przy kliknięciu.
"""
import json
import re
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from widok_obrazkowy import codex_text  # noqa: E402

ROOT = Path("data/widok")
OUT = ROOT / "streszczenia"
SHARD = 500                    # artykułów na plik (strona pobiera jeden plik przy kliknięciu)
CHUNK = 20                     # artykułów na wywołanie Codex (10 na próbie 02.10: ok. 1% okna 5 h, 1 min)
MIN_TEXT_WORDS = 120           # krótszy tekst traktujemy jak sam lead
LINK = re.compile(r'data-a="(\d+)"')
QUOTE = re.compile(r'[„"«“]([^”"»„“]+)[”"»“]')


def shown_ids(day: str | None) -> list[int]:
    """Article ids linked from the pages: one day (and the axis) or all days."""
    files = list((ROOT / "os").glob("index.html")) + list((ROOT / "kraje").glob("*.html"))   # oś czasu, osie krajów
    days = [ROOT / day] if day else [d for d in ROOT.iterdir() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name)]
    for d in days:
        files += [f for f in d.glob("*.html") if not f.name.startswith("_")]
    return sorted({int(i) for f in files for i in LINK.findall(f.read_text(encoding="utf-8"))})


def load_all() -> dict[int, dict]:
    out = {}
    for f in OUT.glob("*.json"):
        out.update({int(k): v for k, v in json.loads(f.read_text(encoding="utf-8")).items()})
    return out


def save(done: dict[int, dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shards: dict[int, dict] = {}
    for i, v in done.items():
        shards.setdefault(i // SHARD, {})[str(i)] = v
    for n, items in shards.items():
        (OUT / f"{n}.json").write_text(json.dumps(dict(sorted(items.items(), key=lambda kv: int(kv[0]))),
                                                  ensure_ascii=False, indent=0), encoding="utf-8")


def articles(ids: list[int]) -> list[dict]:
    conn = sqlite3.connect("file:data/prod.db?mode=ro", uri=True)
    q = (f"SELECT a.id, s.name, a.title, a.lead, a.fulltext FROM articles a JOIN sources s ON s.id = a.source_id "
         f"WHERE a.id IN ({','.join(map(str, ids))})")
    out = []
    for i, src, title, lead, text in conn.execute(q):
        text = " ".join((text or "").split())
        only_lead = len(text.split()) < MIN_TEXT_WORDS
        out.append({"id": i, "zrodlo": src, "tytul": " ".join((title or "").split()), "lead": only_lead,
                    "tekst": " ".join((lead or "").split()) if only_lead else text})
    return [a for a in out if a["tekst"] or a["tytul"]]


def prompt(batch: list[dict]) -> str:
    parts = "\n\n".join(f"### #{a['id']} | {a['zrodlo']} | {'TYLKO LEAD' if a['lead'] else 'PEŁNY TEKST'}\n"
                        f"Tytuł: {a['tytul']}\n{a['tekst']}" for a in batch)
    return (
        "Streszczasz artykuły prasowe dla polskiego czytelnika serwisu, który porównuje przekaz prasy z różnych krajów. "
        "Dla KAŻDEGO artykułu niżej napisz po polsku streszczenie tego, co podaje sam artykuł:\n"
        "- PEŁNY TEKST: 5–7 zdań (razem 70–150 słów): co się stało albo o czym jest tekst, najważniejsze ustalenia i liczby, "
        "na kogo powołuje się redakcja, czyje stanowiska przytacza i jakie ma ujęcie (np. podkreśla skutki dla…, oddaje głos…).\n"
        "- TYLKO LEAD: 1–2 zdania z tego, co jest w tytule i leadzie; nie dopowiadaj reszty.\n"
        "Zasady: wyłącznie na podstawie podanego tekstu, bez własnej wiedzy, bez ocen prawdziwości i bez prognoz. Twierdzenia "
        "sporne przypisz („według ministerstwa…”, „gazeta pisze…”, „autor ocenia…”). Pisz własnymi słowami; cytat najwyżej "
        "jeden na streszczenie i najwyżej 10 słów. Nie zaczynaj od „Artykuł…” w każdym streszczeniu, nie powtarzaj tytułu "
        "słowo w słowo, nie używaj myślników jako przecinków. Nazwy własne w polskiej pisowni.\n"
        "Zwróć WYŁĄCZNIE JSON: {\"streszczenia\":[{\"id\":123,\"tekst\":\"...\"}]} z wszystkimi id.\n\n" + parts)


def sentences(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?…])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ„\"])", text.strip()) if s])


def check(batch: list[dict], got: dict[int, str]) -> list[str]:
    errors = []
    for a in batch:
        t = got.get(a["id"])
        if not t:
            errors.append(f"#{a['id']}: brak streszczenia")
            continue
        n = sentences(t)
        if a["lead"] and n > 3:
            errors.append(f"#{a['id']}: {n} zdań, przy samym leadzie najwyżej 2")
        if not a["lead"] and not 4 <= n <= 8:
            errors.append(f"#{a['id']}: {n} zdań, ma być 5–7")
        # w prompcie 10 słów, twardy próg to zasada projektu (cytaty maks. 15 słów)
        errors += [f"#{a['id']}: cytat ma {len(q.split())} słów, najwyżej 10" for q in QUOTE.findall(t) if len(q.split()) > 15]
    return errors


def run(batch: list[dict], n: int) -> dict[int, str]:
    work = OUT / f"_codex-{n}"
    text = prompt(batch)
    got: dict[int, str] = {}
    for attempt in range(2):
        raw = codex_text(work, text)
        try:
            new = {int(d["id"]): " ".join(d["tekst"].split())
                   for d in json.loads(raw[raw.index("{"):raw.rindex("}") + 1])["streszczenia"]}
            got.update({i: t for i, t in new.items() if i in {a["id"] for a in batch}})
        except (ValueError, KeyError, TypeError) as e:
            print(f"porcja {n}: niepoprawny JSON ({e})", flush=True)
        errors = check(batch, got)
        if not errors:
            break
        bad = {int(e[1:e.index(":")]) for e in errors}
        if attempt == 0:
            for i in bad:
                got.pop(i, None)
            text = prompt([a for a in batch if a["id"] in bad]) + "\n\nPoprzednio błędy:\n" + "\n".join(errors)
            print(f"porcja {n}: ponawiam {len(bad)}: {'; '.join(errors)[:300]}", flush=True)
        else:                                          # po ponowieniu: zostają tylko poprawne
            print(f"porcja {n}: pomijam {sorted(bad)}", flush=True)
            for i in bad:
                got.pop(i, None)
    return got


def main(arg: str) -> None:
    ids = shown_ids(None if arg == "wszystko" else arg)
    done = load_all()
    todo = articles([i for i in ids if i not in done]) if any(i not in done for i in ids) else []
    print(f"nagłówków na stronach: {len(ids)}, do streszczenia: {len(todo)}", flush=True)
    batches = [todo[k:k + CHUNK] for k in range(0, len(todo), CHUNK)]
    meta = {a["id"]: a["lead"] for a in todo}
    with ThreadPoolExecutor(4) as ex:
        for got in ex.map(run, batches, range(len(batches))):
            done.update({i: {"t": t, "lead": meta[i]} for i, t in got.items()})
            save(done)                                  # po każdej porcji: przerwany przebieg nie traci wyników
    print(f"streszczeń razem: {len(done)}; brakuje dla stron: {len([i for i in ids if i not in done])}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not (sys.argv[1] == "wszystko" or re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[1])):
        raise SystemExit(__doc__)
    main(sys.argv[1])
