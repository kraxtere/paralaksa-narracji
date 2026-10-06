"""Kategoria ogólna i krótki opis dla artykułów bez sygnałów (model zwrócił pustą listę), przez Codex lokalnie.
  python scripts/v2/kategorie.py [--db data/prod.db] [--od 2026-09-24] [--wsady N] [--rozmiar 100] [--model codex:gpt-6.1-sol:low]
Nowe artykuły: kategoria po tytule i, gdy jest zajawka RSS (lead), jedno zdanie opisu po polsku (tytuł + zajawka, nie
pełny tekst). Potem `--opisy` dopisuje opisy do już sklasyfikowanych, które mają zajawkę. Wynik: data/widok/kategorie.json
{id: {"k": kategoria, "o": opis}} (stary format {id: kategoria} też się wczytuje); ponowne uruchomienie dokańcza braki.
Codex działa tylko lokalnie; model nigdy ultra (parse_model odrzuca). Użycie: dzien.py faza 1."""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from paralaksa.extract.codex_client import CodexClient  # noqa: E402
from paralaksa.extract.llm_client import LLMRequest  # noqa: E402

PLIK = ROOT / "data" / "widok" / "kategorie.json"
KATEGORIE = ["polityka", "gospodarka", "sport", "kultura i rozrywka", "technologia i AI", "nauka", "zdrowie",
             "społeczeństwo", "wypadki i kryminalne", "pogoda i środowisko", "inne"]
LOWER = {k.lower(): k for k in KATEGORIE}      # model bywa niedokładny w wielkości liter (AI/ai)
MIN_LEAD = 40                                  # krótsza zajawka nie wystarcza na opis
LEAD_MAX = 400
OPIS_ZASADY = ("Opis: jedno zdanie po polsku (do 25 słów) o tym, czego dotyczy artykuł, wyłącznie na podstawie tytułu "
               "i zajawki; bez dodawania faktów spoza nich, bez ocen, cytat najwyżej 15 słów. Gdy zajawki brak (oznaczone "
               "„brak”), opis zostaw pusty.")
PROMPT_KAT = ("Przypisz każdemu artykułowi prasowemu (różne języki) dokładnie jedną kategorię z listy: {kat}.\n"
              "Gdy niejasne, wybierz „inne”. " + OPIS_ZASADY + "\nOdpowiedz wyłącznie wierszami „numer|kategoria|opis”, po "
              "jednym na artykuł, bez komentarzy, kategorie dokładnie jak na liście.\n\n{tekst}")
PROMPT_OPIS = (OPIS_ZASADY + "\nOdpowiedz wyłącznie wierszami „numer|opis”, po jednym na artykuł, bez komentarzy.\n\n{tekst}")


def wczytaj(plik: Path = PLIK) -> dict[str, dict]:
    if not plik.exists():
        return {}
    raw = json.loads(plik.read_text(encoding="utf-8"))
    return {k: ({"k": v} if isinstance(v, str) else v) for k, v in raw.items()}


def zapisz(dane: dict, plik: Path = PLIK) -> None:
    plik.parent.mkdir(parents=True, exist_ok=True)
    plik.write_text(json.dumps(dane, ensure_ascii=False), encoding="utf-8")


def _rows(db: str, od: str) -> list[tuple[int, str, str]]:
    c = sqlite3.connect(db)
    return c.execute("select id, title, coalesce(lead, '') from articles a where published_at>=? and title<>'' and not exists "
                     "(select 1 from signals g where g.article_id=a.id) order by id", (od,)).fetchall()


def brakujace(db: str, od: str, gotowe: dict) -> list[tuple[int, str, str]]:
    return [r for r in _rows(db, od) if str(r[0]) not in gotowe]


def bez_opisu(db: str, od: str, gotowe: dict) -> list[tuple[int, str, str]]:
    """Sklasyfikowane z zajawką, którym jeszcze nie próbowano zrobić opisu (brak klucza "o")."""
    return [r for r in _rows(db, od) if str(r[0]) in gotowe and "o" not in gotowe[str(r[0])] and len(r[2]) >= MIN_LEAD]


def tekst(wsad: list[tuple[int, str, str]]) -> str:
    return "\n".join(f"{n}. {t[:200]}\n   zajawka: {l[:LEAD_MAX].replace(chr(10), ' ') if len(l) >= MIN_LEAD else 'brak'}"
                     for n, (_, t, l) in enumerate(wsad, 1))


def _opis(s: str) -> str:
    return s.strip().strip("„”\"'").strip()


def parsuj(odpowiedz: str, ids: list[int], z_opisem: bool = True) -> dict[str, dict]:
    """Wiersze „n|kategoria|opis” -> {id: {"k","o"}}; nieznane kategorie i numery pomijamy (zostaną do ponowienia)."""
    out = {}
    for m in re.finditer(r"^[ 	]*(\d+)[ 	]*[|:][ 	]*(.+?)[ 	]*$", odpowiedz, re.M):
        n = int(m.group(1))
        if not 1 <= n <= len(ids):
            continue
        kat, _, opis = m.group(2).partition("|")
        kat = kat.strip().strip("„”\"'").lower()
        if kat in LOWER:
            out[str(ids[n - 1])] = {"k": LOWER[kat], "o": _opis(opis) if z_opisem else ""}
    return out


def parsuj_opisy(odpowiedz: str, ids: list[int]) -> dict[str, str]:
    out = {}
    for m in re.finditer(r"^[ 	]*(\d+)[ 	]*[|:][ 	]*(.*?)[ 	]*$", odpowiedz, re.M):
        n = int(m.group(1))
        if 1 <= n <= len(ids):
            out[str(ids[n - 1])] = _opis(m.group(2))
    return out


def _wywolaj(prompt: str, model: str, klient: CodexClient) -> str:
    r = klient.complete(LLMRequest("kat", model, 6000, [{"role": "user", "content": prompt}]))
    if r.error:
        print("błąd:", r.error[:200])
        return ""
    return r.text


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(ROOT / "data" / "prod.db"))
    p.add_argument("--od", default="2026-09-24")
    p.add_argument("--wsady", type=int, default=0, help="maks. liczba wsadów (0 = wszystkie)")
    p.add_argument("--rozmiar", type=int, default=100)
    p.add_argument("--opisy", action="store_true", help="dopisz opisy do już sklasyfikowanych (z zajawką)")
    p.add_argument("--model", default="codex:gpt-6.1-sol:low")
    a = p.parse_args()
    gotowe = wczytaj()
    todo = bez_opisu(a.db, a.od, gotowe) if a.opisy else brakujace(a.db, a.od, gotowe)
    print(f"do {'opisania' if a.opisy else 'klasyfikacji'}: {len(todo)}")
    klient = CodexClient(timeout_s=900)
    for k in range(0, len(todo), a.rozmiar):
        if a.wsady and k // a.rozmiar >= a.wsady:
            break
        wsad, ids = todo[k:k + a.rozmiar], [i for i, _, _ in todo[k:k + a.rozmiar]]
        if a.opisy:
            odp = parsuj_opisy(_wywolaj(PROMPT_OPIS.format(tekst=tekst(wsad)), a.model, klient), ids)
            for i, o in odp.items():
                gotowe[i]["o"] = o
        else:
            odp = parsuj(_wywolaj(PROMPT_KAT.format(kat=", ".join(KATEGORIE), tekst=tekst(wsad)), a.model, klient), ids)
            for i, d in odp.items():
                if not d["o"] and len(next(l for j, _, l in wsad if str(j) == i)) < MIN_LEAD:
                    d["o"] = ""                                # bez zajawki opisu nie będzie, nie ponawiaj
            gotowe.update(odp)
        zapisz(gotowe)
        print(f"wsad {k // a.rozmiar + 1}: {len(odp)}/{len(wsad)}")


if __name__ == "__main__":
    main()
