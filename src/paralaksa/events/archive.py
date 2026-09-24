"""Archive copies for event cards: reuse an existing Wayback capture or make one with Save Page Now.

Only fills `archiwum: {link: null, wykonano: null}` of relations that have a link; never overwrites an
archive, never touches `sprawdzil`, `porownywana_wersja` or anything else. A copy made today shows the page
as it is today, not on the day of publication, and the comment written next to it says so.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import httpx

from paralaksa.events.check import (
    WAYBACK,
    CardError,
    Snapshot,
    list_snapshots,
    load_card,
    parse_time,
    relation_day,
)
from paralaksa.ingest.dedup import normalize_url
from paralaksa.ingest.http import PoliteClient, RobotsDisallowed

log = logging.getLogger(__name__)

SAVE_URL = f"{WAYBACK}/save"
KEYS_URL = "https://archive.org/account/s3.php"
POLL_INTERVAL_S = 5.0
SAVE_TIMEOUT_S = 180.0
LATE_AFTER = timedelta(hours=48)  # późniejszej istniejącej kopii nie wpisujemy automatycznie
EMPTY_ARCHIVE = re.compile(
    r"^(?P<indent>[ \t]+)archiwum:[ \t]*\{[ \t]*link:[ \t]*null[ \t]*,[ \t]*wykonano:[ \t]*null[ \t]*\}(?P<rest>[^\n]*)$", re.M
)

NOTE_EXISTING = "kopia Wayback: pierwsza po publikacji (plx events archive)"
NOTE_OWN = "własna kopia Save Page Now z {day}: strona z chwili kopii, nie z dnia publikacji"


class SaveError(Exception):
    """Save Page Now did not produce a capture."""


def ia_auth_from_env() -> str | None:
    """`LOW key:secret` from IA_ACCESS_KEY / IA_SECRET_KEY (archive.org account, S3-like keys)."""
    access, secret = os.environ.get("IA_ACCESS_KEY"), os.environ.get("IA_SECRET_KEY")
    return f"LOW {access}:{secret}" if access and secret else None


def save_page(
    client: PoliteClient, url: str, auth: str,
    sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
    poll_s: float = POLL_INTERVAL_S, timeout_s: float = SAVE_TIMEOUT_S,
) -> Snapshot:
    """Capture `url` with Save Page Now (SPN2 API) and wait for the result."""
    headers = {"Accept": "application/json", "Authorization": auth}
    try:
        resp = client.post(SAVE_URL, data={"url": url, "skip_first_archive": "1"}, headers=headers)
        job = _json(resp)
    except httpx.HTTPStatusError as e:
        raise SaveError(_http_reason(e)) from e
    except (httpx.HTTPError, RobotsDisallowed) as e:
        raise SaveError(e.__class__.__name__) from e
    if not job.get("job_id"):
        raise SaveError(job.get("message") or job.get("status_ext") or "brak job_id w odpowiedzi")

    deadline = clock() + timeout_s
    while True:
        sleep(poll_s)
        try:
            status = _json(client.get(f"{SAVE_URL}/status/{job['job_id']}", headers=headers))
        except httpx.HTTPStatusError as e:
            raise SaveError(_http_reason(e)) from e
        except httpx.HTTPError as e:
            raise SaveError(e.__class__.__name__) from e
        state = status.get("status")
        if state == "success" and status.get("timestamp"):
            return Snapshot(str(status["timestamp"]), status.get("original_url") or url)
        if state != "pending":
            raise SaveError(f"{status.get('status_ext') or state}: {status.get('message') or 'bez opisu'}")
        if clock() > deadline:
            raise SaveError(f"brak wyniku po {timeout_s:.0f} s (zadanie {job['job_id']}, można sprawdzić później)")


def _json(resp: httpx.Response) -> dict:
    try:
        data = json.loads(resp.text)
    except ValueError as e:
        raise SaveError("odpowiedź Save Page Now nie jest JSON-em") from e
    return data if isinstance(data, dict) else {}


def _http_reason(e: httpx.HTTPStatusError) -> str:
    code = e.response.status_code
    if code == 401:
        return f"HTTP 401: Wayback wymaga konta, sprawdź IA_ACCESS_KEY/IA_SECRET_KEY ({KEYS_URL})"
    if code == 429:
        return "HTTP 429: limit zapytań Save Page Now, spróbuj za kilka minut"
    return f"HTTP {code}"


# --- card --------------------------------------------------------------------------------------------------------------

@dataclass
class RelationArchive:
    rid: str
    kto: str
    action: str  # "jest" | "istniejąca" | "późna" | "własna" | "pominięta" | "błąd"
    message: str
    snapshot: Snapshot | None = None
    note: str | None = None


@dataclass
class CardArchive:
    path: Path
    card_id: str
    relations: list[RelationArchive] = field(default_factory=list)
    written: int = 0


def archive_card(
    path: Path, client: PoliteClient, auth: str | None, write: bool = True, dry_run: bool = False,
    today: date | None = None, sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> CardArchive:
    card = load_card(path)
    today = today or datetime.now(timezone.utc).date()
    result = CardArchive(path, str(card["id"]))
    for rel in card.get("relacje") or []:
        ra = _archive_relation(card, rel, client, auth, dry_run, today, sleep, clock)
        result.relations.append(ra)
    if write and not dry_run:
        for ra in result.relations:
            if ra.snapshot and ra.note:
                if write_archive(path, ra.rid, ra.snapshot, ra.note):
                    result.written += 1
                else:
                    ra.message += "; nie udało się wpisać do karty (inny zapis pola `archiwum`), wpisz ręcznie"
    return result


def _archive_relation(
    card: dict, rel: dict, client: PoliteClient, auth: str | None, dry_run: bool, today: date,
    sleep: Callable[[float], None], clock: Callable[[], float],
) -> RelationArchive:
    rid, kto, url = str(rel.get("id")), str(rel.get("kto")), rel.get("link")
    if (rel.get("archiwum") or {}).get("link"):
        return RelationArchive(rid, kto, "jest", "archiwum już jest w karcie")
    if not url:
        return RelationArchive(rid, kto, "pominięta", "brak linku")

    start = relation_day(card, rel)
    snaps, note = list_snapshots(client, url, start, max(start, today))
    if snaps:
        pub = parse_time(rel.get("publikacja"))
        after = [s for s in snaps if not pub or s.when >= pub]
        first = (after or snaps)[0]
        msg = f"istniejąca kopia {first.when:%Y-%m-%d %H:%M} UTC: {first.link}"
        if note:
            msg += f" ({note})"
        ref = pub or datetime.combine(start, datetime.min.time(), timezone.utc)
        if first.when - ref > LATE_AFTER:
            days = (first.when - ref).days
            return RelationArchive(rid, kto, "późna", f"{msg}; {days} dni po publikacji, nie wpisuję: sprawdzić ręcznie")
        return RelationArchive(rid, kto, "istniejąca", msg, first, NOTE_EXISTING)

    if dry_run:
        return RelationArchive(rid, kto, "pominięta", "brak kopii: zrobiłbym własną (Save Page Now)")
    if not auth:
        return RelationArchive(
            rid, kto, "pominięta",
            f"brak kopii; Save Page Now wymaga konta archive.org: klucze z {KEYS_URL} "
            f"do .env (IA_ACCESS_KEY, IA_SECRET_KEY) albo ręcznie {SAVE_URL}",
        )
    try:
        snap = save_page(client, url, auth, sleep=sleep, clock=clock)
    except SaveError as e:
        return RelationArchive(rid, kto, "błąd", f"Save Page Now: {e}")
    if normalize_url(snap.original) != normalize_url(url):  # przekierowanie: paywall, strona główna, inny tekst
        return RelationArchive(
            rid, kto, "błąd",
            f"Save Page Now zapisał inny adres (przekierowanie): {snap.link}; nie wpisuję, sprawdzić link w karcie",
        )
    return RelationArchive(
        rid, kto, "własna", f"własna kopia {snap.when:%Y-%m-%d %H:%M} UTC: {snap.link}",
        snap, NOTE_OWN.format(day=f"{snap.when:%Y-%m-%d}"),
    )


def write_archive(path: Path, rid: str, snap: Snapshot, note: str) -> bool:
    """Fill the empty `archiwum` of relation `rid` in place. Returns False if the card has another layout."""
    raw = path.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    fm = re.match(r"\A---\s*\n(.*?)\n---\s*(\n|\Z)", text, re.S)
    if not fm:
        return False
    head = fm.group(1)
    start = re.search(rf"^(?P<indent>[ \t]*)- id: ['\"]?{re.escape(rid)}['\"]?[ \t]*$", head, re.M)
    if not start:
        return False
    nxt = re.compile(rf"^({re.escape(start.group('indent'))}- id: |\S)", re.M).search(head, start.end())
    end = nxt.start() if nxt else len(head)
    m = EMPTY_ARCHIVE.search(head, start.end(), end)
    if not m:
        return False
    line = (f"{m.group('indent')}archiwum: {{link: '{snap.link}', wykonano: '{snap.when:%Y-%m-%dT%H:%MZ}'}}"
            f"   # {note}")
    old_comment = m.group("rest").strip().lstrip("#").strip()
    if old_comment:
        line += f"; {old_comment}"
    new_head = head[:m.start()] + line + head[m.end():]
    new_text = text[:fm.start(1)] + new_head + text[fm.end(1):]

    path.write_bytes(new_text.replace("\n", eol).encode("utf-8"))
    try:  # zapis musi dać tę samą kartę z uzupełnionym archiwum
        card = load_card(path)
        rel = next(r for r in card["relacje"] if str(r.get("id")) == rid)
        ok = rel["archiwum"]["link"] == snap.link
    except (CardError, StopIteration, KeyError, TypeError):
        ok = False
    if not ok:
        path.write_bytes(raw.encode("utf-8"))
    return ok
