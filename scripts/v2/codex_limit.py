"""Stan limitu konta Codex (tylko odczyt: account/rateLimits/read przez `codex app-server` na stdio). Nic nie zużywa.
  python scripts/v2/codex_limit.py          -> wypisuje procent zużycia okien limitu
Użycie w skryptach: `usage()` przed i po zadaniu, różnica = koszt zadania w punktach procentowych.
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from komiks_codex import codex_exe  # noqa: E402


def _rpc(proc, msg_id: int, method: str, params) -> dict:
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}) + "\n")
    proc.stdin.flush()
    while True:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError(f"app-server zakończył się przed odpowiedzią na {method}")
        msg = json.loads(line)
        if msg.get("id") == msg_id:
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error']}")
            return msg["result"]


def raw_limits() -> dict:
    proc = subprocess.Popen([codex_exe(), "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    try:
        _rpc(proc, 1, "initialize", {"clientInfo": {"name": "paralaksa-limit", "version": "0.1"}})
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "initialized"}) + "\n")
        return _rpc(proc, 2, "account/rateLimits/read", None)
    finally:
        proc.kill()


def usage() -> dict[str, float]:
    """{window name: used percent} of the account's main limit windows."""
    rl = raw_limits().get("rateLimits") or {}
    out = {}
    for key in ("primary", "secondary"):
        w = rl.get(key)
        if w:
            name = f"{key} ({w.get('windowDurationMins', '?')} min)"
            out[name] = w.get("usedPercent")
            if w.get("resetsAt"):
                out[name + " reset"] = datetime.fromtimestamp(w["resetsAt"]).strftime("%Y-%m-%d %H:%M")
    return out


if __name__ == "__main__":
    if "--raw" in sys.argv:
        print(json.dumps(raw_limits(), indent=1, ensure_ascii=False))
    else:
        for k, v in usage().items():
            print(f"{k}: {v}")
