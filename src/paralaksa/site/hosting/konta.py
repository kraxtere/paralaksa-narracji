"""Accounts and reading time for the internal site (standard library only).

Render's free disk is wiped on every sleep and deploy, so everything lives in a private GitHub repo (ACTIVITY_REPO)
written through the contents API with a fine-grained token (ACTIVITY_TOKEN, access to that one repo only):
  osoby.json                 people (PBKDF2 password hashes, never passwords) and pending invites (token hashes)
  aktywnosc/<YYYY-MM-DD>.jsonl   one line per page view ("v"), heartbeat ("p", every minute while the tab is visible,
                             path with the #tab) or hidden tab ("h": the app went to the background or was closed)
Logins live in a signed cookie (sign_session/read_session): stateless, so it survives Render's restarts; it stops
working when the person's password changes or the account is blocked or deleted.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Callable

ITERATIONS = 120_000          # PBKDF2; udane logowania są cache'owane, więc koszt płaci się raz na proces
INVITE_DAYS = 7
SESSION_GAP_S = 600           # przerwa dłuższa niż 10 min zaczyna nową sesję
PING_S = 60
MAX_PENDING = 50_000
DEFAULT_REPO = "kraxtere/paralaksa-aktywnosc"
LOGIN_RE = re.compile(r"^[a-z0-9-]{1,32}$")


class Conflict(Exception):
    """The file changed since it was read (stale sha)."""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def hash_password(password: str, salt: str | None = None, iterations: int = ITERATIONS) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def check_password(password: str, stored: str | None) -> bool:
    try:
        algo, iterations, salt, digest = (stored or "").split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
    return hmac.compare_digest(dk.hex(), digest)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def sign_session(secret: bytes, login: str, exp: int, fingerprint: str) -> str:
    """Cookie value `login.exp.mac`; the mac covers the password fingerprint, so a new password ends old logins."""
    raw = base64.urlsafe_b64encode(login.encode()).decode().rstrip("=")
    mac = hmac.new(secret, f"{raw}.{exp}.{fingerprint}".encode(), "sha256").hexdigest()[:40]
    return f"{raw}.{exp}.{mac}"


def read_session(secret: bytes, value: str, fingerprint_of: Callable[[str], str | None],
                 now_s: float) -> tuple[str, int] | None:
    """(login, expiry) from a valid cookie value, else None (garbage, expired, account changed or gone)."""
    try:
        raw, exp_s, mac = value.split(".")
        login, exp = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode(), int(exp_s)
    except Exception:
        return None
    fingerprint = fingerprint_of(login)
    if fingerprint is None or exp < now_s:
        return None
    good = hmac.new(secret, f"{raw}.{exp}.{fingerprint}".encode(), "sha256").hexdigest()[:40]
    return (login, exp) if hmac.compare_digest(mac, good) else None


def make_login(name: str, taken) -> str:
    """ASCII login from a display name ("Ala Nowak" -> "ala-nowak"), unique among `taken`."""
    base = unicodedata.normalize("NFKD", name.replace("ł", "l").replace("Ł", "L")).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:24] or "osoba"
    login, n = base, 2
    while login in taken:
        login, n = f"{base}-{n}", n + 1
    return login


class GitHubFiles:
    """Text files in a GitHub repo through the contents API (no git binary needed)."""

    def __init__(self, repo: str, token: str, urlopen: Callable = urllib.request.urlopen, branch: str = "main"):
        self.repo, self.token, self.urlopen, self.branch = repo, token, urlopen, branch

    def _call(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(f"https://api.github.com/repos/{self.repo}/contents/{path}"
                                     + (f"?ref={self.branch}" if method == "GET" else ""),
                                     data=json.dumps(body).encode() if body is not None else None, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "paralaksa-strona")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        with self.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())

    def get(self, path: str) -> tuple[str | None, str | None]:
        try:
            data = self._call("GET", path)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, None
            raise
        return base64.b64decode(data["content"]).decode("utf-8"), data["sha"]

    def put(self, path: str, text: str, sha: str | None, message: str) -> str:
        body = {"message": message, "content": base64.b64encode(text.encode("utf-8")).decode(), "branch": self.branch}
        if sha:
            body["sha"] = sha
        try:
            return self._call("PUT", path, body)["content"]["sha"]
        except urllib.error.HTTPError as e:
            if e.code in (409, 422):
                raise Conflict(path) from e
            raise

    def list(self, folder: str) -> list[str]:
        try:
            return [x["name"] for x in self._call("GET", folder) if x.get("type") == "file"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            raise


class MemoryFiles:
    """Same interface in memory (tests, local runs without a token)."""

    def __init__(self):
        self.files: dict[str, tuple[str, str]] = {}
        self.conflicts = 0          # ile następnych zapisów ma zgłosić konflikt (testy)

    def get(self, path):
        return self.files.get(path, (None, None))

    def put(self, path, text, sha, message):
        if self.conflicts:
            self.conflicts -= 1
            raise Conflict(path)
        if self.files.get(path, (None, None))[1] != sha:
            raise Conflict(path)
        new = hashlib.sha1(text.encode()).hexdigest()
        self.files[path] = (text, new)
        return new

    def list(self, folder):
        return sorted(p.split("/", 1)[1] for p in self.files if p.startswith(folder + "/"))


class Store:
    def __init__(self, files, clock: Callable[[], datetime] = now_utc):
        self.files, self.clock = files, clock
        self.reserved: set[str] = set()          # loginy zajęte poza osoby.json (właściciel z SITE_USER)
        self.lock = threading.RLock()
        self.pending: list[dict] = []
        self.error = ""
        self.data: dict = {"osoby": {}, "zaproszenia": {}}
        self.sha: str | None = None
        self._auth_cache: dict[str, str] = {}
        self._day_cache: dict[str, tuple[str, list[dict]]] = {}
        self.load()

    # --- osoby -------------------------------------------------------------------------------------------------------
    def load(self) -> None:
        with self.lock:
            text, sha = self.files.get("osoby.json")
            data = json.loads(text) if text else {}
            self.data = {"osoby": data.get("osoby", {}), "zaproszenia": data.get("zaproszenia", {})}
            self.sha = sha
            self._auth_cache.clear()

    def _change(self, change: Callable[[dict], object], message: str):
        """Apply `change` to the freshest osoby.json and write it at once (a lost write would lose an account)."""
        with self.lock:
            for _ in range(3):
                self.load()
                result = change(self.data)
                try:
                    self.sha = self.files.put("osoby.json", json.dumps(self.data, ensure_ascii=False, indent=1) + "\n",
                                              self.sha, message)
                    self._auth_cache.clear()
                    return result
                except Conflict:
                    continue
            raise RuntimeError("osoby.json: zapis się nie udał (konflikt)")

    def people(self) -> dict:
        with self.lock:
            return json.loads(json.dumps(self.data["osoby"]))

    def invite(self, name: str = "", login: str | None = None) -> tuple[str, str]:
        """New person (from `name`) or a fresh link for an existing `login` (also a password reset). Returns (login, token)."""
        token = secrets.token_urlsafe(24)

        def change(d):                       # przy konflikcie wołane ponownie na świeżych danych: bez stanu z zewnątrz
            who = login
            if who is None:
                who = make_login(name, set(d["osoby"]) | self.reserved)
                d["osoby"][who] = {"imie": name.strip()[:60] or who, "hash": None, "utworzono": iso(self.clock()),
                                   "zablokowana": False}
            elif who not in d["osoby"] or d["osoby"][who].get("usunieta"):
                raise KeyError(who)
            d["zaproszenia"] = {k: v for k, v in d["zaproszenia"].items()
                                if v["login"] != who and parse_iso(v["wygasa"]) > self.clock()}
            d["zaproszenia"][token_hash(token)] = {"login": who,
                                                   "wygasa": iso(self.clock() + timedelta(days=INVITE_DAYS))}
            return who

        return self._change(change, f"osoby: zaproszenie {login or make_login(name, ())}"), token

    def invite_info(self, token: str) -> dict | None:
        with self.lock:
            inv = self.data["zaproszenia"].get(token_hash(token))
            if not inv or parse_iso(inv["wygasa"]) <= self.clock():
                return None
            person = self.data["osoby"].get(inv["login"])
            if not person or person.get("zablokowana"):
                return None
            return {"login": inv["login"], "imie": person["imie"], "wygasa": inv["wygasa"]}

    def accept(self, token: str, password: str) -> str:
        if len(password) < 10:
            raise ValueError("Hasło musi mieć co najmniej 10 znaków.")
        hashed = hash_password(password)

        def change(d):
            inv = d["zaproszenia"].pop(token_hash(token), None)
            if not inv or parse_iso(inv["wygasa"]) <= self.clock() or inv["login"] not in d["osoby"]:
                raise LookupError("Link nie działa albo wygasł.")
            d["osoby"][inv["login"]]["hash"] = hashed
            return inv["login"]

        return self._change(change, "osoby: ustawione hasło")

    def set_blocked(self, login: str, blocked: bool) -> None:
        def change(d):
            if d["osoby"][login].get("usunieta"):
                return
            d["osoby"][login]["zablokowana"] = blocked
            if blocked:
                d["zaproszenia"] = {k: v for k, v in d["zaproszenia"].items() if v["login"] != login}
        self._change(change, f"osoby: {'blokada' if blocked else 'odblokowanie'} {login}")

    def delete(self, login: str) -> None:
        """Remove the account (password hash, invites). The name stays, so past sessions keep it and the login is not
        given to someone else."""
        def change(d):
            person = d["osoby"][login]
            d["osoby"][login] = {"imie": person["imie"], "hash": None, "utworzono": person.get("utworzono"),
                                 "zablokowana": True, "usunieta": iso(self.clock())}
            d["zaproszenia"] = {k: v for k, v in d["zaproszenia"].items() if v["login"] != login}
        self._change(change, f"osoby: usunięta {login}")

    def fingerprint(self, login: str) -> str | None:
        """Changes whenever the password does; None when the person cannot log in (cookie check)."""
        with self.lock:
            person = self.data["osoby"].get(login)
            if not person or person.get("zablokowana") or person.get("usunieta") or not person.get("hash"):
                return None
            return person["hash"]

    def authenticate(self, login: str, password: str) -> bool:
        with self.lock:
            person = self.data["osoby"].get(login)
            if not person or person.get("zablokowana") or person.get("usunieta") or not person.get("hash"):
                return False
            key = hashlib.sha256(f"{login}\0{password}\0{person['hash']}".encode()).hexdigest()
            if self._auth_cache.get(key) == login:
                return True
        if check_password(password, person["hash"]):
            with self.lock:
                if len(self._auth_cache) > 1000:
                    self._auth_cache.clear()
                self._auth_cache[key] = login
            return True
        return False

    # --- aktywność ---------------------------------------------------------------------------------------------------
    def record(self, login: str, path: str, kind: str) -> None:
        with self.lock:
            if len(self.pending) < MAX_PENDING:
                self.pending.append({"t": iso(self.clock()), "u": login, "p": path[:200], "k": kind})

    def flush(self) -> None:
        """Append pending events to their day files; on failure they stay pending for the next try."""
        with self.lock:
            batch, self.pending = self.pending, []
        by_day: dict[str, list[dict]] = {}
        for e in batch:
            by_day.setdefault(e["t"][:10], []).append(e)
        failed = []
        for day, events in sorted(by_day.items()):
            path = f"aktywnosc/{day}.jsonl"
            lines = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events)
            try:
                for _ in range(3):
                    text, sha = self.files.get(path)
                    try:
                        self.files.put(path, (text or "") + lines, sha, f"aktywnosc {day}")
                        break
                    except Conflict:
                        continue
                else:
                    raise RuntimeError(f"{path}: konflikt")
                self.error = ""
            except Exception as e:                          # sieć, token, limit API: spróbujemy przy następnym zapisie
                self.error = f"zapis aktywności: {e}"
                failed.extend(events)
        if failed:
            with self.lock:
                self.pending = (failed + self.pending)[:MAX_PENDING]

    def events(self, days: int = 30) -> list[dict]:
        since = (self.clock() - timedelta(days=days)).strftime("%Y-%m-%d")
        out = []
        for name in sorted(self.files.list("aktywnosc")):
            day = name.removesuffix(".jsonl")
            if not name.endswith(".jsonl") or day < since:
                continue
            path = f"aktywnosc/{name}"
            cached = self._day_cache.get(path)
            if cached and day < self.clock().strftime("%Y-%m-%d"):     # dni zamknięte się nie zmieniają
                out.extend(cached[1])
                continue
            text, sha = self.files.get(path)
            if cached and cached[0] == sha:
                out.extend(cached[1])
                continue
            parsed = [json.loads(line) for line in (text or "").splitlines() if line.strip()]
            self._day_cache[path] = (sha, parsed)
            out.extend(parsed)
        with self.lock:
            out.extend(self.pending)
        return out


def _page(place: str | None) -> str:
    return (place or "/").partition("#")[0].partition("@")[0]


def _live(evs: list[dict]) -> list[dict]:
    """Drop "h" signals of a page that is no longer open: leaving a page sends its "h" while the next page loads, and it
    often arrives after the next page's view; it must not stop the clock of the new page."""
    out, current = [], None
    for e in evs:
        if e["k"] == "h" and current is not None and _page(e.get("p")) != current:
            continue
        if e["k"] != "h":
            current = _page(e.get("p"))
        out.append(e)
    return out


def sessions(events: list[dict], gap_s: int = SESSION_GAP_S, ping_s: int = PING_S) -> list[dict]:
    """Per person: runs of activity without a gap longer than `gap_s`.

    A view or heartbeat counts as reading until the next signal, at most `ping_s` (a visible tab pings every minute);
    "h" (tab hidden) stops the clock at once. `miejsca` is reading time per page (#tab included), in visiting order."""
    by_user: dict[str, list[dict]] = {}
    for e in events:
        by_user.setdefault(e["u"], []).append(e)
    out = []
    for user, evs in by_user.items():
        evs = _live(sorted(evs, key=lambda e: e["t"]))
        times = [parse_iso(e["t"]) for e in evs]
        cur = None
        for i, (e, t) in enumerate(zip(evs, times)):
            if cur is None or (t - cur["do"]).total_seconds() > gap_s:
                cur = {"u": user, "od": t, "do": t, "strony": 0, "sekundy": 0.0, "miejsca": {}}
                out.append(cur)
            cur["do"] = t
            if e["k"] == "v":
                cur["strony"] += 1
            if e["k"] == "h":
                continue
            seconds = min((times[i + 1] - t).total_seconds(), ping_s) if i + 1 < len(evs) else ping_s
            cur["sekundy"] += seconds
            place = e.get("p") or "/"
            cur["miejsca"][place] = cur["miejsca"].get(place, 0.0) + seconds
    for s in out:
        s["minuty"] = max(1, round(s.pop("sekundy") / 60))
    return sorted(out, key=lambda s: s["od"], reverse=True)


def intervals(events: list[dict], ping_s: int = PING_S) -> list[dict]:
    """Reading time as intervals ({"u", "od", "do", "p"}), counted like in `sessions`: a view or heartbeat lasts until the
    next signal, at most `ping_s`; "h" adds nothing. For the timeline and the time per part of the site."""
    by_user: dict[str, list[dict]] = {}
    for e in events:
        by_user.setdefault(e["u"], []).append(e)
    out = []
    for user, evs in by_user.items():
        evs = _live(sorted(evs, key=lambda e: e["t"]))
        times = [parse_iso(e["t"]) for e in evs]
        for i, (e, t) in enumerate(zip(evs, times)):
            if e["k"] == "h":
                continue
            end = t + timedelta(seconds=ping_s)
            if i + 1 < len(evs):
                end = min(end, times[i + 1])
            if end > t:
                out.append({"u": user, "od": t, "do": end, "p": e.get("p") or "/"})
    return out


def from_env(env) -> tuple[Store | None, str]:
    """Store from ACTIVITY_TOKEN / ACTIVITY_REPO; without a token (or when GitHub refuses) the site runs owner-only."""
    token = env.get("ACTIVITY_TOKEN", "")
    if not token:
        return None, "brak ACTIVITY_TOKEN: działa tylko konto właściciela, czas nie jest zapisywany"
    repo = env.get("ACTIVITY_REPO", DEFAULT_REPO)
    try:
        return Store(GitHubFiles(repo, token)), ""
    except Exception as e:
        return None, f"repo {repo} niedostępne ({e}): działa tylko konto właściciela"
