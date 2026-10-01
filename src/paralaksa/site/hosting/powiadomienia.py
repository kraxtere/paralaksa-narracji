"""Web Push about a new edition (the only part of the server outside the standard library: pywebpush).

People turn notifications on in the page menu (pasek.js); the browser's push subscription is kept in the activity repo
next to the accounts (powiadomienia.json, written through konta.GitHubFiles), because Render's disk is wiped on sleep.
The server sends on startup after a deploy: when v2/powiadomienie.json (written by `plx site` for the newest day) names
a day newer than the last one announced, every subscription gets one message. The day is marked as announced before
sending, so a restart never repeats it (a crash mid-way loses the rest, never doubles). Subscriptions the push service
reports as gone (404/410) are removed.

VAPID_PRIVATE_KEY (Render, raw P-256 key in base64url) signs the messages; the page gets the public key derived from it.
Without the key or pywebpush the menu simply has no notification switch."""
from __future__ import annotations

import base64
import hashlib
import json
import threading
from datetime import datetime
from typing import Callable

import konta

PATH = "powiadomienia.json"
MAX_SUBS = 500
GONE = (404, 410)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def public_key(private_key: str) -> str:
    """Application server key for pushManager.subscribe (uncompressed P-256 point) from the raw private key."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    raw = base64.urlsafe_b64decode(private_key + "=" * (-len(private_key) % 4))
    key = ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())
    return b64url(key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))


def new_private_key() -> str:
    from cryptography.hazmat.primitives.asymmetric import ec
    return b64url(ec.generate_private_key(ec.SECP256R1()).private_numbers().private_value.to_bytes(32, "big"))


def valid(sub) -> dict | None:
    """Only what the browser's PushSubscription.toJSON() gives: an https endpoint and the two keys."""
    if not isinstance(sub, dict):
        return None
    endpoint, keys = sub.get("endpoint"), sub.get("keys")
    if not (isinstance(endpoint, str) and endpoint.startswith("https://") and len(endpoint) < 1000 and isinstance(keys, dict)):
        return None
    p256dh, auth = keys.get("p256dh"), keys.get("auth")
    if not (isinstance(p256dh, str) and isinstance(auth, str) and 0 < len(p256dh) < 200 and 0 < len(auth) < 100):
        return None
    return {"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}


def key_of(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode()).hexdigest()[:24]


class Subscriptions:
    def __init__(self, files, clock: Callable[[], datetime] = konta.now_utc):
        self.files, self.clock = files, clock
        self.lock = threading.RLock()
        self.data: dict = {"subskrypcje": {}, "ostatni_dzien": ""}
        self.sha: str | None = None

    def load(self) -> None:
        with self.lock:
            text, self.sha = self.files.get(PATH)
            data = json.loads(text) if text else {}
            self.data = {"subskrypcje": data.get("subskrypcje", {}), "ostatni_dzien": data.get("ostatni_dzien", "")}

    def _change(self, change: Callable[[dict], bool], message: str) -> None:
        """Apply `change` to the freshest file; `change` returns False when there is nothing to write."""
        with self.lock:
            for _ in range(3):
                self.load()
                if not change(self.data):
                    return
                try:
                    self.sha = self.files.put(PATH, json.dumps(self.data, ensure_ascii=False, indent=1) + "\n", self.sha, message)
                    return
                except konta.Conflict:
                    continue
            raise RuntimeError(f"{PATH}: zapis się nie udał (konflikt)")

    def add(self, login: str, sub: dict) -> None:
        sub = valid(sub)
        if sub is None:
            raise ValueError("zła subskrypcja")
        key = key_of(sub["endpoint"])

        def change(d):
            old = d["subskrypcje"].get(key)
            if old and old.get("login") == login and old.get("sub") == sub:
                return False
            if not old and len(d["subskrypcje"]) >= MAX_SUBS:
                raise ValueError("za dużo subskrypcji")
            d["subskrypcje"][key] = {"login": login, "sub": sub, "dodano": konta.iso(self.clock())}
            return True

        self._change(change, f"powiadomienia: {login} włącza")

    def remove(self, endpoint: str, login: str | None = None) -> None:
        key = key_of(endpoint)

        def change(d):
            old = d["subskrypcje"].get(key)
            if not old or (login is not None and old.get("login") != login):
                return False
            del d["subskrypcje"][key]
            return True

        self._change(change, "powiadomienia: wyłączenie")

    def announce(self, day: str, payload: dict, send: Callable[[dict, str], int],
                 active: Callable[[str], bool] = lambda login: True) -> tuple[int, int]:
        """Send `payload` about `day` to everyone once (newer day than the last announced). Returns (sent, removed).
        `active(login)` skips blocked or deleted accounts."""
        claimed = []

        def change(d):
            if d["ostatni_dzien"] >= day:
                return False
            d["ostatni_dzien"] = day
            claimed.append(True)
            return True

        self._change(change, f"powiadomienia: wydanie {day}")
        if not claimed:
            return 0, 0
        data = json.dumps(payload, ensure_ascii=False)
        sent, gone = 0, []
        for key, entry in list(self.data["subskrypcje"].items()):
            if not active(entry.get("login", "")):
                continue
            try:
                status = send(entry["sub"], data)
            except Exception:
                status = 0
            if 200 <= status < 300:
                sent += 1
            elif status in GONE:
                gone.append(entry["sub"]["endpoint"])
        for endpoint in gone:
            self.remove(endpoint)
        return sent, len(gone)


def sender(private_key: str, contact: str) -> Callable[[dict, str], int]:
    """pywebpush with a fresh claims dict per message (pywebpush writes aud/exp into it)."""
    from pywebpush import WebPushException, webpush

    def send(sub: dict, data: str) -> int:
        try:
            r = webpush(subscription_info=sub, data=data, vapid_private_key=private_key,
                        vapid_claims={"sub": contact}, ttl=24 * 3600, timeout=15)
            return r.status_code
        except WebPushException as e:
            return e.response.status_code if e.response is not None else 0

    return send
