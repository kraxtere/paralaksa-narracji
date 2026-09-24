"""Verification hints for event cards: Wayback captures, page metadata, headline changes.

The check never edits a card and never sets `sprawdzil`. A capture time proves only what the page
showed at that moment; `datePublished` in page metadata may be a republication time.
"""

from __future__ import annotations

import html
import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx
import yaml

from paralaksa.ingest.dedup import url_hash
from paralaksa.ingest.http import PoliteClient, RobotsDisallowed

log = logging.getLogger(__name__)

WAYBACK = "https://web.archive.org"
CDX_LIMIT = 500
DEFAULT_MAX_FETCH = 12
REPUBLISH_TOLERANCE = timedelta(minutes=5)
SKIP_NAMES = {"README.md"}


class CardError(Exception):
    """Card file cannot be read as front matter + YAML."""


# --- card -------------------------------------------------------------------------------------------------------------

def load_card(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A---\s*\n(.*?)\n---\s*(\n|\Z)", text, re.S)
    if not m:
        raise CardError(f"{path}: brak nagłówka YAML między liniami ---")
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        raise CardError(f"{path}: błąd YAML: {e}") from e
    if not isinstance(data, dict) or not data.get("id"):
        raise CardError(f"{path}: nagłówek YAML bez pola id")
    return data


def card_paths(paths: list[Path]) -> list[Path]:
    """Expand directories to card files; skip the template, README and board specs (*.yaml)."""
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(x for x in p.glob("*.md") if not x.name.startswith("_") and x.name not in SKIP_NAMES))
        else:
            out.append(p)
    return out


def parse_time(value: Any) -> datetime | None:
    """Card time (ISO 8601, ideally with zone) → datetime; naive values are treated as UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        return None  # sama data bez godziny
    else:
        try:
            dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def relation_day(card: dict, rel: dict) -> date:
    """Day the relation belongs to: its publication (in its own zone), else the fact time, else the card id."""
    for value in (rel.get("publikacja"), (card.get("fakt") or {}).get("czas")):
        dt = parse_time(value)
        if dt:
            return dt.date()
    try:
        return date.fromisoformat(str(card["id"])[:10])
    except ValueError as e:
        raise CardError(f"{card['id']}: nie da się ustalić dnia relacji {rel.get('id')}") from e


# --- Wayback ----------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Snapshot:
    timestamp: str  # 14 cyfr, UTC
    original: str

    @property
    def when(self) -> datetime:
        return datetime.strptime(self.timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)

    @property
    def link(self) -> str:
        return f"{WAYBACK}/web/{self.timestamp}/{self.original}"

    @property
    def raw_link(self) -> str:  # oryginalny HTML bez paska Wayback
        return f"{WAYBACK}/web/{self.timestamp}id_/{self.original}"


def list_snapshots(client: PoliteClient, url: str, start: date, end: date) -> tuple[list[Snapshot], str | None]:
    """Captures with HTTP 200 between start and end (inclusive, UTC days), one per distinct content.

    Returns (snapshots, note). The CDX index refuses some domains (403); then we fall back to the
    captures nearest to the start and end of the window, which is less complete and says so in the note.
    """
    try:
        resp = client.get(f"{WAYBACK}/cdx/search/cdx?" + str(httpx.QueryParams({
            "url": url, "from": start.strftime("%Y%m%d"), "to": end.strftime("%Y%m%d"),
            "output": "json", "fl": "timestamp,original", "filter": "statuscode:200",
            "collapse": "digest", "limit": str(CDX_LIMIT),
        })))
        rows = json.loads(resp.text) if resp.text.strip() else []
        snaps = [Snapshot(ts, orig) for ts, orig in rows[1:]]
        note = f"indeks CDX zwrócił limit {CDX_LIMIT} kopii, mogą być dalsze" if len(snaps) >= CDX_LIMIT else None
        return snaps, note
    except (httpx.HTTPError, RobotsDisallowed, ValueError) as e:
        reason = f"HTTP {e.response.status_code}" if isinstance(e, httpx.HTTPStatusError) else e.__class__.__name__
        log.info("CDX niedostępny dla %s (%s), próbuję najbliższych kopii", url, reason)
    snaps: list[Snapshot] = []
    for probe in (start.strftime("%Y%m%d") + "000000", end.strftime("%Y%m%d") + "235959"):
        try:
            resp = client.get(f"{WAYBACK}/web/{probe}id_/{url}")
        except (httpx.HTTPError, RobotsDisallowed):
            continue
        m = re.search(r"/web/(\d{14})", str(resp.url))
        if m and start <= datetime.strptime(m.group(1)[:8], "%Y%m%d").date() <= end:
            snap = Snapshot(m.group(1), url)
            if snap not in snaps:
                snaps.append(snap)
    snaps.sort(key=lambda s: s.timestamp)
    return snaps, f"indeks CDX odmówił ({reason}); tylko kopie najbliższe początkowi i końcowi okna, lista niepełna"


# --- page metadata ----------------------------------------------------------------------------------------------------

@dataclass
class PageMeta:
    h1: str | None = None
    og_title: str | None = None
    published: str | None = None
    modified: str | None = None

    @property
    def headline(self) -> str | None:
        """h1, unless it has nothing in common with og:title (e.g. gov.pl puts the site logo in the first h1)."""
        if self.h1 and self.og_title and _overlap(self.h1, self.og_title) < 0.5:
            return title_variants(self.og_title)[-1]
        return self.h1 or self.og_title


def _overlap(a: str, b: str) -> float:
    wa, wb = set(re.findall(r"\w+", a.casefold())), set(re.findall(r"\w+", b.casefold()))
    return len(wa & wb) / len(wa) if wa else 0.0


_SITE_SEPARATOR = re.compile(r"\s+[-–—|]\s+")


def title_variants(title: str) -> list[str]:
    """og:title often ends with the site name ("… - Ministerstwo … - Portal Gov.pl"): the title and its
    prefixes cut at separators, longest first. Headlines themselves may contain dashes, so all are tried."""
    cuts = [m.start() for m in _SITE_SEPARATOR.finditer(title)]
    return [title] + [title[:c] for c in reversed(cuts)]


class _MetaParser(HTMLParser):
    META_PUBLISHED = {"article:published_time", "datepublished", "og:published_time"}
    META_MODIFIED = {"article:modified_time", "datemodified", "og:updated_time"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta = PageMeta()
        self._in_h1 = False
        self._h1_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            content = a.get("content", "").strip()
            if not content:
                return
            if key == "og:title" and not self.meta.og_title:
                self.meta.og_title = content
            elif key in self.META_PUBLISHED and not self.meta.published:
                self.meta.published = content
            elif key in self.META_MODIFIED and not self.meta.modified:
                self.meta.modified = content
        elif tag == "h1" and self.meta.h1 is None and not self._in_h1:
            self._in_h1 = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._in_h1:
            self._in_h1 = False
            self.meta.h1 = _clean(" ".join(self._h1_parts)) or None  # puste h1 (np. logo): czekamy na następne
            self._h1_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self._h1_parts.append(data)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_meta(page: str) -> PageMeta:
    parser = _MetaParser()
    try:
        parser.feed(page)
    except Exception:  # uszkodzony HTML: bierzemy to, co zdążyliśmy odczytać
        log.debug("HTMLParser przerwał analizę strony", exc_info=True)
    meta = parser.meta
    # JSON-LD ma pierwszeństwo przed meta: tam redakcje trzymają datePublished/dateModified artykułu
    for key, attr in (("datePublished", "published"), ("dateModified", "modified")):
        m = re.search(rf'"{key}"\s*:\s*"([^"]+)"', page)
        if m:
            setattr(meta, attr, m.group(1))
    if meta.og_title:
        meta.og_title = _clean(meta.og_title)
    return meta


@dataclass
class Capture:
    snapshot: Snapshot
    meta: PageMeta | None = None
    error: str | None = None


def fetch_capture(client: PoliteClient, snap: Snapshot) -> Capture:
    try:
        resp = client.get(snap.raw_link)
    except (httpx.HTTPError, RobotsDisallowed) as e:
        return Capture(snap, error=e.__class__.__name__)
    return Capture(snap, meta=parse_meta(resp.text))


def pick(snaps: list[Snapshot], n: int) -> list[Snapshot]:
    """Up to n captures spread evenly over the list, always including the first and the last."""
    if len(snaps) <= n:
        return list(snaps)
    if n <= 1:
        return [snaps[0]]
    step = (len(snaps) - 1) / (n - 1)
    return [snaps[round(i * step)] for i in range(n)]


# --- comparison -------------------------------------------------------------------------------------------------------

_QUOTES = str.maketrans({c: "'" for c in "’‘‚`´"} | {c: '"' for c in "“”„«»"})


def norm_headline(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_QUOTES).casefold()).strip()


def headline_matches(card_headline: str, page_headline: str | None) -> bool:
    """Card headline equals the page headline; a card headline ending with … may be a shortened prefix."""
    if not page_headline:
        return False
    card = norm_headline(card_headline)
    page = norm_headline(page_headline)
    truncated = card.endswith("…") or card.endswith("...")
    card = card.rstrip(".…").strip()
    return page.startswith(card) if truncated else page == card


@dataclass
class DbHit:
    source_id: str
    title: str
    published_at: str | None
    fetched_at: str


def db_lookup(conn: sqlite3.Connection | None, url: str) -> DbHit | None:
    if conn is None:
        return None
    row = conn.execute(
        "SELECT source_id, title, published_at, fetched_at FROM articles WHERE url_hash = ?", (url_hash(url),)
    ).fetchone()
    return DbHit(*row) if row else None


def open_db_readonly(path: Path) -> sqlite3.Connection | None:
    """Our database, read-only; None if it does not exist (the check must not create an empty one)."""
    if not path.exists():
        return None
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


@dataclass
class RelationCheck:
    rid: str
    kto: str
    link: str | None
    zone: timezone
    window: tuple[date, date] | None = None
    snapshots: list[Snapshot] = field(default_factory=list)
    note: str | None = None
    captures: list[Capture] = field(default_factory=list)
    db_hit: DbHit | None = None
    hints: list[str] = field(default_factory=list)

    def local(self, dt: datetime) -> str:
        return dt.astimezone(self.zone).strftime("%Y-%m-%d %H:%M") + f" ({_zone_label(self.zone)})"


def _zone_label(tz: timezone) -> str:
    off = tz.utcoffset(None)
    if not off:
        return "UTC"
    total = int(off.total_seconds() // 60)
    sign = "+" if total >= 0 else "-"
    return f"{sign}{abs(total) // 60:02d}:{abs(total) % 60:02d}"


def check_relation(
    client: PoliteClient, card: dict, rel: dict, conn: sqlite3.Connection | None,
    days: int = 2, max_fetch: int = DEFAULT_MAX_FETCH,
) -> RelationCheck:
    pub = parse_time(rel.get("publikacja"))
    upd = parse_time(rel.get("aktualizacja"))
    zone = pub.tzinfo if pub and isinstance(pub.tzinfo, timezone) else timezone.utc
    rc = RelationCheck(rid=str(rel.get("id")), kto=str(rel.get("kto")), link=rel.get("link"), zone=zone)
    if not rc.link:
        rc.hints.append("brak linku: relacji nie da się sprawdzić (zasada 1)")
        return rc
    if not rel.get("gatunek"):
        rc.hints.append("brak pola `gatunek`")

    start = relation_day(card, rel)
    rc.window = (start, start + timedelta(days=max(days, 1) - 1))
    rc.snapshots, rc.note = list_snapshots(client, rc.link, *rc.window)
    rc.captures = [fetch_capture(client, s) for s in pick(rc.snapshots, max_fetch)]
    rc.db_hit = db_lookup(conn, rc.link)

    _hint_archive(rc, rel, pub)
    _hint_headline(rc, rel)
    _hint_metadata(rc, pub, upd)
    return rc


def _hint_archive(rc: RelationCheck, rel: dict, pub: datetime | None) -> None:
    arch = rel.get("archiwum") or {}
    made = parse_time(arch.get("wykonano"))
    if arch.get("link"):
        if made and pub and made < pub:
            rc.hints.append("kopia w karcie jest starsza niż podana publikacja: sprawdzić, której wersji dotyczy")
        earlier = [s for s in rc.snapshots if made and s.when < made and (not pub or s.when >= pub)]
        if earlier:
            rc.hints.append(
                f"jest kopia bliższa publikacji niż ta w karcie: {earlier[0].link} "
                f"({rc.local(earlier[0].when)}, w karcie {rc.local(made)})"
            )
        return
    if not rc.snapshots:
        rc.hints.append("brak kopii w oknie i brak archiwum w karcie: zrobić własną kopię, póki strona żyje")
        return
    after = [s for s in rc.snapshots if not pub or s.when >= pub]
    first = (after or rc.snapshots)[0]
    rc.hints.append(f"propozycja archiwum: {first.link} (wykonano {first.when:%Y-%m-%dT%H:%MZ})")


def headline_runs(captures: list[Capture]) -> list[Capture]:
    """First capture of each run of the same headline, in time order."""
    runs: list[Capture] = []
    for c in captures:
        if not runs or norm_headline(c.meta.headline) != norm_headline(runs[-1].meta.headline):
            runs.append(c)
    return runs


def _hint_headline(rc: RelationCheck, rel: dict) -> None:
    card_headline = rel.get("naglowek")
    seen = [c for c in rc.captures if c.meta and c.meta.headline]
    if not seen:
        return
    runs = headline_runs(seen)
    variants = {norm_headline(c.meta.headline) for c in runs}
    if len(variants) > 1 and len(runs) > len(variants):
        rc.hints.append(
            f"{len(variants)} różne nagłówki występują NA PRZEMIAN ({len(runs)} odcinków): możliwy test A/B "
            "albo cache, nie jedna zmiana; nie opisywać jako „redakcja zmieniła nagłówek”"
        )
    elif len(variants) > 1:
        changes = ", ".join(rc.local(c.snapshot.when) for c in runs[1:])
        rc.hints.append(
            f"nagłówek zmieniał się w oknie ({len(variants)} wersje, zmiana widoczna w kopii: {changes}); "
            "przy porównaniu wskazać wersję i godzinę; rozważyć formę os_czasu"
            + (f" (pobrano {len(rc.captures)} z {len(rc.snapshots)} kopii: moment zmiany przybliżony, "
               "więcej wersji przy większym --max-fetch)" if len(rc.captures) < len(rc.snapshots) else "")
        )
    if card_headline:
        def candidates(m: PageMeta) -> list[str]:
            return [x for x in [m.h1, *(title_variants(m.og_title) if m.og_title else [])] if x]

        if not any(headline_matches(card_headline, x) for c in seen for x in candidates(c.meta)):
            rc.hints.append("nagłówek z karty nie występuje w żadnej sprawdzonej kopii z okna (może pochodzi z dzisiejszej wersji)")


def _hint_metadata(rc: RelationCheck, pub: datetime | None, upd: datetime | None) -> None:
    published = {p for c in rc.captures if c.meta for p in [parse_time(c.meta.published)] if p}
    if pub and published and all(abs(p - pub) > REPUBLISH_TOLERANCE for p in published):
        values = ", ".join(rc.local(p) for p in sorted(published))
        if all(_whole_hours(p - pub) for p in published):
            rc.hints.append(
                f"metadane kopii ({values}) różnią się od karty ({rc.local(pub)}) o pełne godziny: najpewniej strona "
                "podaje czas lokalny ze złą strefą (np. „Z”); ufać godzinie widocznej na stronie"
            )
        else:
            rc.hints.append(
                f"publikacja w karcie ({rc.local(pub)}) różni się od metadanych kopii ({values}); "
                "to może być ponowna publikacja albo inna strefa"
            )
    if pub is None and published:
        rc.hints.append(f"metadane kopii podają publikację {rc.local(min(published))}: do potwierdzenia na stronie")
    if rc.snapshots and pub and rc.snapshots[0].when < pub - REPUBLISH_TOLERANCE:
        rc.hints.append(
            f"pierwsza kopia ({rc.local(rc.snapshots[0].when)}) jest wcześniejsza niż publikacja w karcie: "
            "artykuł istniał wcześniej albo godzina w karcie to ponowna publikacja"
        )


def _whole_hours(delta: timedelta) -> bool:
    minutes = abs(delta.total_seconds()) / 60
    return 60 <= minutes <= 14 * 60 and min(minutes % 60, 60 - minutes % 60) <= 1


@dataclass
class CardCheck:
    path: Path
    card: dict
    relations: list[RelationCheck]


def check_card(
    path: Path, client: PoliteClient, conn: sqlite3.Connection | None,
    days: int = 2, max_fetch: int = DEFAULT_MAX_FETCH,
) -> CardCheck:
    card = load_card(path)
    rels = [check_relation(client, card, r, conn, days, max_fetch) for r in card.get("relacje") or []]
    return CardCheck(path, card, rels)


# --- report -----------------------------------------------------------------------------------------------------------

def render_check(cc: CardCheck, checked_at: datetime | None = None) -> str:
    checked_at = checked_at or datetime.now(timezone.utc)
    card = cc.card
    lines = [
        f"# Sprawdzenie karty {card['id']}",
        "",
        f"Karta: `{cc.path.as_posix()}` · forma: {card.get('forma')} · status: {card.get('status')} · "
        f"sprawdzono {checked_at:%Y-%m-%d %H:%M} UTC",
        "",
        "To są podpowiedzi, nie weryfikacja. Karta nie została zmieniona. Godzina kopii pokazuje, co było na stronie "
        "w chwili zapisu; `datePublished` w metadanych może oznaczać ponowną publikację. Pole `sprawdzil` wypełnia człowiek.",
    ]
    if not cc.relations:
        lines += ["", "Karta nie ma relacji."]
    for rc in cc.relations:
        lines += ["", f"## {rc.rid}: {rc.kto}", ""]
        if rc.link:
            lines.append(f"- link: {rc.link}")
        if rc.window:
            lines.append(f"- okno kopii (UTC): {rc.window[0]} – {rc.window[1]}; kopii o różnej treści: {len(rc.snapshots)}")
        if rc.note:
            lines.append(f"- uwaga: {rc.note}")
        if rc.db_hit:
            h = rc.db_hit
            lines.append(
                f"- nasza baza: `{h.source_id}`, pobrano {h.fetched_at}, publikacja {h.published_at or '—'}; "
                f"tytuł wtedy: „{h.title}”"
            )
        if rc.captures:
            lines += ["", "| kopia | czas lokalny | nagłówek (h1) | og:title | datePublished | dateModified |",
                      "|---|---|---|---|---|---|"]
            for c in rc.captures:
                ts = f"[{c.snapshot.timestamp}]({c.snapshot.link})"
                if c.error:
                    lines.append(f"| {ts} | {rc.local(c.snapshot.when)} | błąd: {c.error} | | | |")
                    continue
                m = c.meta
                lines.append(
                    f"| {ts} | {rc.local(c.snapshot.when)} | {_cell(m.h1)} | {_cell(m.og_title if m.og_title != m.h1 else '=')} "
                    f"| {_cell(m.published)} | {_cell(m.modified)} |"
                )
            if len(rc.captures) < len(rc.snapshots):
                lines.append(f"\nPobrano {len(rc.captures)} z {len(rc.snapshots)} kopii (`--max-fetch`).")
        if rc.hints:
            lines += ["", "Podpowiedzi:"] + [f"- {h}" for h in rc.hints]
    return "\n".join(lines) + "\n"


def _cell(value: str | None) -> str:
    return (value or "—").replace("|", "\\|")
