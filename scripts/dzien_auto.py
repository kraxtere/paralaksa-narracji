"""Automat dnia: od zakończonego daily w Actions do dnia opublikowanego na Cloudflare Pages, bez pilnowania.

  python scripts/dzien_auto.py [RRRR-MM-DD] [--sucho]

Kroki (stan w data/auto/D.json, każdy uruchomiony ponownie pomija to, co zrobione):
1. daily w Actions dla dnia D zakończony (inaczej kod 10 = czekaj, 11 = daily jeszcze nie ruszył; harmonogram ponawia),
2. baza z Release -> data/prod.db (suma SHA-256, odszyfrowanie),
3. ekstrakcja Codex dni D i D-1 do skutku (max 3 próby); artykuły, które nadal nie przechodzą, dostają extracted=3
   i są wypisane w stanie (`pominiete`), żeby kilka złych artykułów nie wstrzymywało całego dnia,
4. baza z sygnałami z powrotem do Release (nie w trakcie przebiegu Actions),
5. scripts/v2/dzien.py D --publikuj-cf (max 3 próby, wznawia od miejsca przerwania),
6. sprawdzenie, że paralaksa.pages.dev pokazuje dzień D.
Kod wyjścia: 0 = dzień na stronie, 1 = nie udało się (powód w logu i w stanie), 10/11 = jeszcze nie czas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
DB = ROOT / "data" / "prod.db"
CACHE = ROOT / "state-cache" / "auto"
SITE = "https://paralaksa.pages.dev/"
GIT_BIN = Path(r"C:\Program Files\Git\usr\bin")


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    os.environ["PATH"] = str(GIT_BIN) + os.pathsep + os.environ.get("PATH", "")
    os.environ["PYTHONIOENCODING"] = "utf-8"


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, **kw)


def gh_runs() -> list[dict]:
    p = run(["gh", "run", "list", "--workflow", "daily.yml", "--limit", "6",
             "--json", "status,conclusion,createdAt,databaseId"], capture_output=True, text=True, encoding="utf-8")
    if p.returncode:
        raise RuntimeError(f"gh run list: {p.stderr.strip()[:200]}")
    return json.loads(p.stdout)


def run_day(runs: list[dict]) -> str | None:
    """Dzień UTC najnowszego przebiegu daily (to dzień, który ten przebieg pobrał)."""
    return runs[0]["createdAt"][:10] if runs else None


class State:
    def __init__(self, day: str) -> None:
        self.path = ROOT / "data" / "auto" / f"{day}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.d = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def done(self, k: str) -> bool:
        return bool(self.d.get(k))

    def set(self, k: str, v=True) -> None:
        self.d[k] = v
        self.path.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), encoding="utf-8")


def download_db() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    for f in CACHE.glob("latest.db.enc*"):
        f.unlink()
    p = run(["gh", "release", "download", "database-backup", "-p", "latest.db.enc*", "-D", str(CACHE), "--clobber"])
    if p.returncode:
        raise RuntimeError("pobranie bazy z Release nie udało się")
    want = (CACHE / "latest.db.enc.sha256").read_text().split()[0]
    h = hashlib.sha256()
    with open(CACHE / "latest.db.enc", "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != want:
        raise RuntimeError("suma SHA-256 bazy się nie zgadza")
    if DB.exists():
        shutil.copy2(DB, ROOT / "data" / "prod_przed_auto.db")
    p = run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-in", str(CACHE / "latest.db.enc"),
             "-out", str(DB), "-pass", "env:DB_BACKUP_KEY"])
    if p.returncode:
        raise RuntimeError("odszyfrowanie bazy nie udało się (DB_BACKUP_KEY?)")


def pending(days: list[str]) -> list[int]:
    con = sqlite3.connect(DB)
    try:
        ids: list[int] = []
        for d in days:
            ids += [r[0] for r in con.execute(
                "SELECT id FROM articles WHERE extracted IN (0, 2) AND substr(fetched_at,1,10)=?", (d,))]
        return ids
    finally:
        con.close()


def extract(days: list[str], st: State) -> None:
    for attempt in range(1, 4):
        left = pending(days)
        if not left:
            return
        log(f"ekstrakcja, próba {attempt}: do zrobienia {len(left)}")
        run([PY, "scripts/ekstrakcja_codex_dnia.py", "--db", str(DB), "--dni", *days, "--zapisz"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    left = pending(days)
    if left:
        con = sqlite3.connect(DB)
        con.executemany("UPDATE articles SET extracted=3 WHERE id=?", [(i,) for i in left])
        con.commit()
        con.close()
        st.set("pominiete", left)
        log(f"UWAGA: {len(left)} artykułów nie przeszło ekstrakcji po 3 próbach, pominięte (extracted=3): {left}")


def upload_db() -> None:
    if any(r["status"] != "completed" for r in gh_runs()):
        raise RuntimeError("Actions w toku, nie nadpisuję bazy w Release")
    snap = ROOT / "data" / "snap.db"
    p = run([PY, "scripts/db_state.py", str(DB), "--snapshot", str(snap)], capture_output=True)
    if p.returncode:
        raise RuntimeError("snapshot bazy nie udał się")
    out = CACHE / "up"
    out.mkdir(parents=True, exist_ok=True)
    enc = out / "latest.db.enc"
    p = run(["openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2", "-iter", "200000", "-in", str(snap), "-out", str(enc),
             "-pass", "env:DB_BACKUP_KEY"])
    if p.returncode:
        raise RuntimeError("szyfrowanie bazy nie udało się")
    h = hashlib.sha256(enc.read_bytes()).hexdigest()
    (out / "latest.db.enc.sha256").write_text(f"{h} *latest.db.enc\n")
    p = run(["gh", "release", "upload", "database-backup", str(enc), str(out / "latest.db.enc.sha256"), "--clobber"])
    snap.unlink(missing_ok=True)
    if p.returncode:
        raise RuntimeError("wysyłka bazy do Release nie udała się")


def site_shows(day: str) -> bool:
    try:
        req = urllib.request.Request(SITE + f"?t={int(time.time())}", headers={"Cache-Control": "no-cache", "User-Agent": "Mozilla/5.0 (paralaksa-auto)"})
        return day in urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        log(f"sprawdzenie strony: {e}")
        return False


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dzien", nargs="?", help="RRRR-MM-DD (domyślnie dzień ostatniego przebiegu daily)")
    ap.add_argument("--sucho", action="store_true", help="tylko pokaż, co byłoby zrobione")
    a = ap.parse_args(argv)
    load_env()
    os.chdir(ROOT)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not a.dzien and State(today).done("opublikowany"):
        log(f"{today}: już na stronie, nic do zrobienia")
        return 0
    runs = gh_runs()
    day = a.dzien or run_day(runs)
    if not day or (not a.dzien and day != today):
        log(f"daily dla {today} jeszcze nie ruszył (ostatni: {day})")
        return 11
    st = State(day)
    if st.done("opublikowany"):
        log(f"{day}: już na stronie, nic do zrobienia")
        return 0
    if any(r["status"] != "completed" for r in runs):
        log("daily w toku, czekam")
        return 10
    if runs[0]["conclusion"] != "success":
        log(f"ostatni daily zakończył się: {runs[0]['conclusion']}, nie ruszam")
        return 1
    prev = (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    log(f"dzień {day}" + (" (sucho)" if a.sucho else ""))
    if a.sucho:
        return 0

    free_gb = shutil.disk_usage(ROOT).free / 2**30
    if free_gb < 1.5:
        st.set("blad", f"dysk pełny: wolne {free_gb:.1f} GB")
        log(f"BŁĄD: za mało miejsca na dysku ({free_gb:.1f} GB wolnego), nie ruszam; zwolnij miejsce")
        return 1
    lock = ROOT / "data" / "auto" / ".lock"
    if lock.exists() and time.time() - lock.stat().st_mtime < 6 * 3600:
        log("inny przebieg automatu trwa (blokada), wychodzę")
        return 10
    lock.write_text(str(os.getpid()))
    try:
        if not st.done("baza_pobrana"):
            download_db()
            st.set("baza_pobrana")
        if not st.done("ekstrakcja"):
            extract([prev, day], st)
            st.set("ekstrakcja")
            st.set("baza_wyslana", False)
        if not st.done("baza_wyslana"):
            upload_db()
            st.set("baza_wyslana")
        for attempt in range(1, 4):
            log(f"dzien.py {day} --publikuj-cf, próba {attempt}")
            p = run([PY, "scripts/v2/dzien.py", day, "--publikuj-cf"],
                    stdout=open(ROOT / "data" / "auto" / f"{day}_dzien.log", "a", encoding="utf-8"), stderr=subprocess.STDOUT)
            if p.returncode == 0:
                break
            log(f"dzien.py: kod {p.returncode}")
        else:
            st.set("blad", "dzien.py nie przeszedł po 3 próbach")
            return 1
        for _ in range(6):
            if site_shows(day):
                st.d.pop("blad", None)
                st.set("opublikowany", datetime.now().isoformat(timespec="seconds"))
                log(f"{day}: na stronie ({SITE})")
                return 0
            time.sleep(20)
        st.set("blad", "strona nie pokazuje dnia po publikacji")
        log("UWAGA: publikacja przeszła, ale strona nie pokazuje dnia")
        return 1
    except Exception as e:  # noqa: BLE001
        st.set("blad", str(e))
        log(f"BŁĄD: {e}")
        return 1
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
