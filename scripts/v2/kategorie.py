"""Kategoria ogólna dla artykułów bez sygnałów (model zwrócił pustą listę), po samym tytule, przez Codex lokalnie.
  python scripts/v2/kategorie.py [--db data/prod.db] [--od 2026-09-24] [--wsady N] [--rozmiar 100] [--model codex:gpt-6.1-sol:low]
Wynik: data/widok/kategorie.json {id_artykułu: kategoria}; ponowne uruchomienie dokańcza brakujące.
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
PROMPT = ("Przypisz każdemu tytułowi artykułu prasowego (różne języki) dokładnie jedną kategorię z listy: {kat}.\n"
          "Oceniaj tylko po tytule; gdy niejasne, wybierz „inne”. Odpowiedz wyłącznie wierszami „numer|kategoria”, "
          "po jednym na tytuł, bez komentarzy, kategorie dokładnie jak na liście.\n\n{tytuly}")


def wczytaj() -> dict:
    return json.loads(PLIK.read_text(encoding="utf-8")) if PLIK.exists() else {}


def brakujace(db: str, od: str, gotowe: dict) -> list[tuple[int, str]]:
    c = sqlite3.connect(db)
    rows = c.execute("select id, title from articles a where published_at>=? and title<>'' and not exists "
                     "(select 1 from signals g where g.article_id=a.id) order by id", (od,)).fetchall()
    return [(i, t) for i, t in rows if str(i) not in gotowe]


def parsuj(tekst: str, ids: list[int]) -> dict[str, str]:
    """Wiersze „n|kategoria” -> {id: kategoria}; nieznane kategorie i numery pomijamy (zostaną do ponowienia)."""
    out = {}
    for m in re.finditer(r"^\s*(\d+)\s*[|:.\-]\s*(.+?)\s*$", tekst, re.M):
        n, kat = int(m.group(1)), m.group(2).strip().strip("„”\"'").lower()
        if 1 <= n <= len(ids) and kat in LOWER:
            out[str(ids[n - 1])] = LOWER[kat]
    return out


def klasyfikuj(wsad: list[tuple[int, str]], model: str, klient: CodexClient) -> dict[str, str]:
    tytuly = "\n".join(f"{n}. {t[:200]}" for n, (_, t) in enumerate(wsad, 1))
    msg = PROMPT.format(kat=", ".join(KATEGORIE), tytuly=tytuly)
    r = klient.complete(LLMRequest("kat", model, 4000, [{"role": "user", "content": msg}]))
    if r.error:
        print("błąd:", r.error[:200])
        return {}
    return parsuj(r.text, [i for i, _ in wsad])


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(ROOT / "data" / "prod.db"))
    p.add_argument("--od", default="2026-09-24")
    p.add_argument("--wsady", type=int, default=0, help="maks. liczba wsadów (0 = wszystkie)")
    p.add_argument("--rozmiar", type=int, default=100)
    p.add_argument("--model", default="codex:gpt-6.1-sol:low")
    a = p.parse_args()
    gotowe = wczytaj()
    todo = brakujace(a.db, a.od, gotowe)
    print(f"do klasyfikacji: {len(todo)}")
    klient = CodexClient(timeout_s=600)
    for k in range(0, len(todo), a.rozmiar):
        if a.wsady and k // a.rozmiar >= a.wsady:
            break
        wsad = todo[k:k + a.rozmiar]
        wyn = klasyfikuj(wsad, a.model, klient)
        gotowe.update(wyn)
        PLIK.parent.mkdir(parents=True, exist_ok=True)
        PLIK.write_text(json.dumps(gotowe, ensure_ascii=False), encoding="utf-8")
        print(f"wsad {k // a.rozmiar + 1}: {len(wyn)}/{len(wsad)}")


if __name__ == "__main__":
    main()
