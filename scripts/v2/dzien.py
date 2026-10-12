"""Procedura dnia strony 2.0 w trzech fazach, wznawialna (gotowe kroki pomija).

  python scripts/v2/dzien.py 2026-10-05 [--publikuj] [--faza 1|2|3] [--sucho]

Faza 1: teksty (Sprawy, raport, dane krajów, oś: dzien/ciag/opisy, kraje D i ciąg), niezależne kroki równolegle (`after`).
Faza 2: WSZYSTKIE obrazki dnia w jednej kolejce (paski tematów i krajów w tematach, okładka, oś, kraje):
        jeden proces na obrazek, starty co 10 s (`PASKI_ODSTEP`), po 429 hamowanie i ponowienie (paski.run_all).
         Streszczenia (potrzebują tylko linków ze stron) idą równolegle z obrazkami, po stronach „wstępnych”.
Faza 3: strony końcowe, z `--publikuj` także plx site --publikuj (samodzielnie: strony, streszczenia, strony, publikacja).
Czasy kroków i faz: data/widok/D/_czasy.json (fazy, kroki, przebiegi ze startem i końcem; kolejne fazy dopisują, nie nadpisują),
czasy wywołań modelu: data/widok/D/_wywolania.jsonl (paralaksa.extract.call_log); podsumowanie na końcu.
Stan kroków: data/widok/DZIEN/_dzien.json; krok z gotowym wynikiem (plik) albo zapisany w stanie jest pomijany.
Baza data/prod.db tylko do odczytu (jak w README).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
PY = sys.executable
PLX = str(Path(PY).with_name("plx.exe" if os.name == "nt" else "plx"))
DB = "data/prod.db"
POLL_S = 2          # co ile sekund run_parallel sprawdza markery gotowości (wait_files)


@dataclass
class Step:
    name: str
    cmd: list[str]
    result: Path | None = None        # istniejący plik = krok już zrobiony (bez wpisu w stanie)
    always: bool = False              # budowa stron i publikacja: za każdym razem (tanie, po poprawce obrazka trzeba je złożyć)
    after: tuple[str, ...] = ()       # kroki, które muszą się skończyć wcześniej (faza 1 idzie równolegle, reszta bez zależności rusza od razu)
    wait_files: tuple[Path, ...] = () # markery gotowości: krok rusza, gdy te pliki istnieją (i są kompletnym JSON-em), choć krok który je pisze jeszcze trwa


def ready(path: Path) -> bool:
    """Marker file is there and complete (JSON parses): another step may still be running that wrote it."""
    try:
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        return path.is_file()
    except (OSError, ValueError):
        return False


def script(name: str, *args: str) -> list[str]:
    return [PY, str(HERE / name), *args]


def phase1(day: str) -> list[Step]:
    """Kolejność listy jest poprawna także szeregowo; `after` pozwala `run_parallel` ruszyć niezależne kroki od razu.
    Zależności: os-dzien czyta tylko data/stories/D.json, więc rusza, gdy ten plik jest gotowy (marker `wait_files`), nie po całym
    `plx site` (tłumaczenia nagłówków i budowa stron trwają dalej obok); kraje-D czyta też data/tytuly/D.json, więc czeka na
    cały site, a wyklucza też wynik os-dzien (assigned); os-ciag/os-opisy zapisują ten sam magazyn osi po os-dzien;
    kraje-ciag po kraje-D. kategorie, report i dzien_prasy czytają tylko bazę (do odczytu) i nie zależą od reszty."""
    return [
        Step("kategorie", script("kategorie.py")),        # kategoria ogólna artykułów bez sygnałów (archiwum); dokańcza brakujące
        Step("site", [PLX, "site", "--db", DB], Path(f"data/stories/{day}.json")),
        Step("report", [PLX, "report", "--date", day, "--db", DB], Path(f"reports/{day}.json")),
        Step("dzien_prasy", script("dzien_prasy.py", day, "--bez-opisow"), Path(f"data/dzien_prasy/{day}/opisy.json")),
        Step("os-dzien", script("os_czasu.py", "dzien", day), Path(f"data/widok/os/dodatkowe/{day}.json"),
             wait_files=(Path(f"data/stories/{day}.json"),)),
        Step("os-ciag", script("os_czasu.py", "ciag", day), Path(f"data/widok/os/ciag/{day}.json"), after=("os-dzien",)),
        Step("os-opisy", script("os_czasu.py", "opisy"), after=("os-ciag",)),
        Step("kraje-D", script("kraje.py", day), Path(f"data/widok/kraje/{day}.json"), after=("site", "os-dzien")),
        Step("kraje-ciag", script("kraje.py", "ciag", day), after=("kraje-D",)),
    ]


def pages(day: str, suffix: str = "") -> list[Step]:
    return [Step(f"strona-dnia{suffix}", script("widok_obrazkowy.py", "strona"), always=True),
            Step(f"strona-osi{suffix}", script("os_czasu.py", "strona"), always=True),
            Step(f"strona-krajow{suffix}", script("kraje.py", "strona"), always=True)]


def summaries_step(day: str) -> Step:
    return Step("streszczenia", script("streszczenia.py", day), always=True)


def final_steps(day: str, publish: bool) -> list[Step]:
    return [Step("publikacja", [PLX, "site", "--db", DB, "--publikuj"], always=True)] if publish else []


def phase3(day: str, publish: bool) -> list[Step]:
    """Samodzielna faza 3 (--faza 3): strony, streszczenia, strony ponownie, publikacja."""
    return [*pages(day), summaries_step(day), *pages(day, "-2"), *final_steps(day, publish)]


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


class Timings:
    """Czasy kroków i faz (sekundy) w data/widok/D/_czasy.json; podsumowanie na końcu."""

    def __init__(self, day: str) -> None:
        self.path = Path("data/widok") / day / "_czasy.json"
        self.steps: dict[str, float] = {}
        self.phases: dict[str, float] = {}
        self.runs: list[dict] = []        # start/koniec każdego przebiegu kroku (UTC, HH:MM:SS) w tym procesie
        self.lock = threading.Lock()
        try:                              # wcześniejsze fazy tego dnia zostają (dawniej każdy proces nadpisywał plik)
            self.prev = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.prev = {}

    def step(self, name: str, secs: float, started: datetime | None = None) -> None:
        end = datetime.now(timezone.utc)
        with self.lock:
            self.steps[name] = round(self.steps.get(name, 0) + secs, 1)
            self.runs.append({"krok": name, "start": (started or end).strftime("%H:%M:%S"), "koniec": end.strftime("%H:%M:%S"),
                              "s": round(secs, 1)})

    def phase(self, name: str, secs: float) -> None:
        with self.lock:
            self.phases[name] = round(self.phases.get(name, 0) + secs, 1)

    def save(self) -> None:
        def merged(key: str, now: dict) -> dict:
            out = dict(self.prev.get(key, {}))
            for k, v in now.items():
                out[k] = round(out.get(k, 0) + v, 1)
            return out
        data = {"fazy": merged("fazy", self.phases), "kroki": merged("kroki", self.steps),
                "przebiegi": [*self.prev.get("przebiegi", []), *self.runs]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def summary(self) -> str:
        slow = sorted(self.steps.items(), key=lambda kv: -kv[1])[:6]
        return ("Czasy: " + ", ".join(f"{k} {v:.0f} s" for k, v in self.phases.items())
                + (" | najdłuższe kroki: " + ", ".join(f"{k} {v:.0f} s" for k, v in slow) if slow else ""))


def timed(run: Callable[[list[str], dict], int], timings: Timings | None, name: str) -> Callable[[list[str], dict], int]:
    def inner(cmd: list[str], env: dict) -> int:
        t0, started = time.monotonic(), datetime.now(timezone.utc)
        try:
            return run(cmd, env)
        finally:
            if timings:
                timings.step(name, time.monotonic() - t0, started)
    return inner


def run_parallel(steps: list[Step], day: str, state: State, run: Callable[[list[str], dict], int], dry: bool = False,
                 timings: Timings | None = None, workers: int = 9) -> bool:
    """Like run_steps, but steps start as soon as their `after` are finished; first failure stops new starts
    (running ones are awaited), rerun continues from there."""
    env = {**os.environ, "DZIEN": day, "PYTHONIOENCODING": "utf-8"}
    if dry:
        return run_steps(steps, day, state, run, dry=True)
    finished: set[str] = set()
    pending = list(steps)
    running: dict = {}
    lock = threading.Lock()
    failed = False

    def work(s: Step) -> int:
        print(f"> {s.name}", flush=True)
        code = timed(run, timings, s.name)(s.cmd, env)
        if code == 0:
            with lock:
                state.add(s.name)
        else:
            print(f"! {s.name}: kod {code}, przerwano (ponowne uruchomienie wznawia)", flush=True)
        return code

    with ThreadPoolExecutor(max_workers=workers) as pool:
        while pending or running:
            for s in list(pending):
                if failed:
                    break
                if not s.always and (state.has(s.name) or (s.result is not None and s.result.exists())):
                    print(f"= {s.name}: gotowe, pomijam", flush=True)
                    finished.add(s.name)
                    pending.remove(s)
                elif all(a in finished for a in s.after) and all(ready(w) for w in s.wait_files):
                    pending.remove(s)
                    running[pool.submit(work, s)] = s
            if not running:
                break
            done, _ = wait(list(running), timeout=POLL_S, return_when=FIRST_COMPLETED)     # co POLL_S także sprawdza markery gotowości
            for f in done:
                s = running.pop(f)
                if f.result() == 0:
                    finished.add(s.name)
                else:
                    failed = True
    return not failed and not pending


def run_steps(steps: list[Step], day: str, state: State, run: Callable[[list[str], dict], int], dry: bool = False,
              timings: Timings | None = None) -> bool:
    """Runs the steps that are not done yet; False and stop at the first failure (rerun continues from there)."""
    env = {**os.environ, "DZIEN": day, "PYTHONIOENCODING": "utf-8"}
    for s in steps:
        if not s.always and (state.has(s.name) or (s.result is not None and s.result.exists())):
            print(f"= {s.name}: gotowe, pomijam", flush=True)
            continue
        print(f"> {s.name}", flush=True)
        if dry:
            continue
        code = timed(run, timings, s.name)(s.cmd, env)
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


def timed_job(fn: Callable[[], object], timings: Timings, name: str) -> Callable[[], object]:
    def inner():
        t0, started = time.monotonic(), datetime.now(timezone.utc)
        try:
            return fn()
        finally:
            timings.step(name, time.monotonic() - t0, started)
    return inner


def phase2(day: str, build: Callable[[str], list[tuple[str, object]]] = image_jobs, timings: Timings | None = None) -> bool:
    import paski
    os.environ.setdefault("PASKI_PROCESY", "100")          # jeden proces na obrazek; tempo wyznacza odstęp 10 s
    jobs = build(day)
    if not jobs:
        print("= obrazki: wszystkie gotowe", flush=True)
        return True
    if timings:                                             # start/koniec każdego obrazka do _czasy.json (przebiegi)
        jobs = [(label, timed_job(fn, timings, f"obraz:{label}")) for label, fn in jobs]
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
    state, tm = State(day), Timings(day)
    t_all = time.monotonic()

    def phase(name: str, fn: Callable[[], bool]) -> bool:
        t0 = time.monotonic()
        ok = fn()
        tm.phase(name, time.monotonic() - t0)
        return ok

    ok, code = True, 1
    if only in (None, "1"):
        ok = phase("faza1", lambda: run_parallel(phase1(day), day, state, shell, dry, tm))
    if ok and only is None and not dry:
        # streszczenia czytają linki ze stron, nie obrazki: strony „wstępne”, potem streszczenia równolegle z obrazkami
        (Path("data/widok") / day / "_paski").mkdir(parents=True, exist_ok=True)   # świeży dzień bez tego szuka start.png (układ pasami)
        ok = phase("strony-wstepne", lambda: run_steps(pages(day), day, state, shell, timings=tm))
        if ok:
            box: dict = {}
            th = threading.Thread(target=lambda: box.update(
                ok=phase("streszczenia", lambda: run_steps([summaries_step(day)], day, state, shell, timings=tm))))
            th.start()
            img_ok = phase("faza2", lambda: phase2(day, timings=tm))
            th.join()
            if not img_ok:
                print("! obrazki: część odrzucona lub przerwana (429); ponowne uruchomienie robi tylko brakujące", flush=True)
            ok = img_ok and box.get("ok", False)
            code = 2 if not img_ok else 1
        if ok:
            ok = phase("strony-koncowe", lambda: run_steps(pages(day, "-2") + final_steps(day, a.publikuj), day, state, shell, timings=tm))
            code = 1
    else:
        code = 1
        if ok and only == "2" and not dry:
            ok = phase("faza2", lambda: phase2(day, timings=tm))
            code = 2
            if not ok:
                print("! obrazki: część odrzucona lub przerwana (429); ponowne uruchomienie robi tylko brakujące", flush=True)
        if ok and only == "3":
            ok = phase("faza3", lambda: run_steps(phase3(day, a.publikuj), day, state, shell, dry, tm))
            code = 1
    if not dry:
        tm.phase("razem", time.monotonic() - t_all)
        tm.save()
        print(tm.summary(), flush=True)
    return 0 if ok else code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
