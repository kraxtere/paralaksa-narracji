"""Timing log of model calls for the day procedure (scripts/v2/dzien.py sets DZIEN): one JSON line per call in
data/widok/DZIEN/_wywolania.jsonl. Append-only, so several processes (site, os-dzien, kraje, report) can write at once.
Without DZIEN nothing is written; a log failure never breaks a call."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_attempts: dict[str, int] = {}
_lock = threading.Lock()


def log_call(custom_id: str, prompt_chars: int, secs: float, ok: bool, model: str = "", started: datetime | None = None) -> None:
    day = os.environ.get("DZIEN")
    if not day:
        return
    with _lock:
        _attempts[custom_id] = attempt = _attempts.get(custom_id, 0) + 1     # attempt > 1: repeated call of the same id
    start = started or datetime.now(timezone.utc)
    row = {"id": custom_id, "start": start.strftime("%H:%M:%S"), "s": round(secs, 1), "znaki": prompt_chars, "ok": ok,
           "proba": attempt, "model": model, "pid": os.getpid()}
    try:
        path = Path("data/widok") / day / "_wywolania.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass
