"""Procedura dnia strony 2.0 w trzech fazach, wznawialna (gotowe kroki pomija).

  python scripts/v2/dzien.py 2026-10-05 [--publikuj] [--faza 1|2|3] [--sucho]

Faza 1: wszystkie teksty po kolei (Sprawy, raport, dane krajów, oś: dzien/ciag/opisy, kraje D i ciąg).
Faza 2: WSZYSTKIE obrazki dnia w jednej kolejce (paski tematów i krajów w tematach, okładka, oś, kraje):
        jeden proces na obrazek, starty co 10 s (`PASKI_ODSTEP`), po 429 hamowanie i ponowienie (paski.run_all).
Faza 3: strony (dzień, oś, kraje), streszczenia, strony ponownie ze streszczeniami, z `--publikuj` także plx site --publikuj.
Stan kroków: data/widok/DZIEN/_dzien.json; krok z gotowym wynikiem (plik) albo zapisany w stanie jest pomijany.
Baza data/prod.db tylko do odczytu (jak w README).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
PY = sys.executable
PLX = str(Path(PY).with_name("plx.exe" if os.name == "nt" else "plx"))
DB = "data/prod.db"


@dataclass
class Step:
    name: str
    cmd: list[str]
    result: Path | None = None        # istniejący plik = krok już zrobiony (bez wpisu w stanie)
    always: bool = False              # budowa stron i publikacja: za każdym razem (tanie, po poprawce obrazka trzeba je złożyć)


def script(name: str, *args: str) -> list[str]:
    return [PY, str(HERE / name), *args]


def phase1(day: str) -> list[Step]:
    return [
        Step("kategorie", script("kategorie.py")),        # kategoria ogólna artykułów bez sygnałów (archiwum); dokańcza brakujące
        Step("site", [PLX, "site", "--db", DB], Path(f"data/stories/{day}.json")),
        Step("report", [PLX, "report", "--date", day, "--db", DB], Path(f"reports/{day}.json")),
        Step("dzien_prasy", script("dzien_prasy.py", day, "--bez-opisow"), Path(f"data/dzien_prasy/{day}/opisy.json")),
        Step("os-dzien", script("os_czasu.py", "dzien", day), Path(f"data/widok/os/dodatkowe/{day}.json")),
        Step("os-ciag", script("os_czasu.py", "ciag", day), Path(f"data/widok/os/ciag/{day}.json")),
        Step("os-opisy", script("os_czasu.py", "opisy")),
        Step("kraje-D", script("kraje.py", day), Path(f"data/widok/kraje/{day}.json")),
        Step("kraje-ciag", script("kraje.py", "ciag", day)),
    ]


def phase3(day: str, publish: bool) -> list[Step]:
    pages = [Step("strona-dnia", script("widok_obrazkowy.py", "strona"), always=True),
             Step("strona-osi", script("os_czasu.py", "strona"), always=True),
             Step("strona-krajow", script("kraje.py", "strona"), always=True)]
    again = [Step(f"{s.name}-2", s.cmd, always=True) for s in pages]
    steps = [*pages, Step("streszczenia", script("streszczenia.py", day), always=True), *again]
    if publish:
        steps.append(Step("publikacja", [PLX, "site", "--db", DB, "--publikuj"], always=True))
    return steps


class State:
    def __init__(self, day: str) -> None:
        self.path = Path("data/widok") / day / "_dzien.json"
        self.done: list[str] = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []

    def has(self, name: str) -> bool:
        return name in self.done

    def add(self, name: str) -> None:
        if name not in self.done:
            self.done.append(name)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.done, ensure_ascii=False), encoding="utf-8")


def run_steps(steps: list[Step], day: str, state: State, run: Callable[[list[str], dict], int], dry: bool = False) -> bool:
    """Runs the steps that are not done yet; False and stop at the first failure (rerun continues from there)."""
    env = {**os.environ, "DZIEN": day, "PYTHONIOENCODING": "utf-8"}
    for s in steps:
        if not s.always and (state.has(s.name) or (s.result is not None and s.result.exists())):
            print(f"= {s.name}: gotowe, pomijam", flush=True)
            continue
        print(f"> {s.name}", flush=True)
        if dry:
            continue
        code = run(s.cmd, env)
        if code != 0:
            print(f"! {s.name}: kod {code}, przerwano (ponowne uruchomienie wznawia)", flush=True)
            return False
        state.add(s.name)
    return True


def image_jobs(day: str) -> list[tuple[str, object]]:
    """All image jobs of the day in one list (modules read DZIEN at import, so the env is set first)."""
    os.environ["DZIEN"] = day
    sys.path.insert(0, str(HERE))
    import kraje
    import okladka
    import os_czasu
    import widok_obrazkowy
    jobs = [*widok_obrazkowy.image_jobs(), *okladka.image_jobs(), *os_czasu.image_jobs(), *kraje.image_jobs(day)]
    seen, unique = set(), []
    for label, fn in jobs:
        key = label if label not in seen else f"{label}#{len(seen)}"
        seen.add(key)
        unique.append((key, fn))
    return unique


def phase2(day: str, build: Callable[[str], list[tuple[str, object]]] = image_jobs) -> bool:
    import paski
    os.environ.setdefault("PASKI_PROCESY", "100")          # jeden proces na obrazek; tempo wyznacza odstęp 10 s
    jobs = build(day)
    if not jobs:
        print("= obrazki: wszystkie gotowe", flush=True)
        return True
    results = paski.run_all(jobs)
    return all(v == "ok" for v in results.values())


def shell(cmd: list[str], env: dict) -> int:
    return subprocess.run(cmd, env=env).returncode


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dzien", help="RRRR-MM-DD")
    ap.add_argument("--faza", choices=["1", "2", "3"], help="tylko jedna faza")
    ap.add_argument("--publikuj", action="store_true", help="na końcu plx site --publikuj")
    ap.add_argument("--sucho", action="store_true", help="pokaż kroki fazy 1 i 3, nic nie uruchamiaj")
    a = ap.parse_args(argv)
    day, only, dry = a.dzien, a.faza, a.sucho
    os.environ["DZIEN"] = day            # moduły v2 czytają DZIEN przy imporcie (domyślnie 2026-09-29!), więc przed każdym importem
    state = State(day)
    if only in (None, "1") and not run_steps(phase1(day), day, state, shell, dry):
        return 1
    if only in (None, "2") and not dry and not phase2(day):
        print("! obrazki: część odrzucona lub przerwana (429); ponowne uruchomienie robi tylko brakujące", flush=True)
        return 2
    if only in (None, "3") and not run_steps(phase3(day, a.publikuj), day, state, shell, dry):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
