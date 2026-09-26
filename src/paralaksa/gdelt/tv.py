"""TV news reports from GDELT's Today's Media Trends: Gemini summaries of a day of broadcasts per channel (TV News Archive).

The PDFs are public at a fixed address and appear the day after. This module downloads them for a fixed channel list,
keeps the text and the links to the broadcasts, and lists names that several channels mention on a day but hardly
anyone mentioned the day before, with one sentence per channel, so differences in framing sit side by side.
No model: the reports already are a model's summaries. The transcripts behind the links are only viewable in GDELT's
Visual Explorer (signed per-broadcast cookie); they are not downloaded."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
import io
import json
from pathlib import Path
import re
from typing import Callable, Iterable
import unicodedata

URL = "https://data.gdeltproject.org/gdeltv5/iatv/todaysmediatrends/{day}.{code}.pdf"
VIEWER = "https://visualexplorer.gdeltproject.org/tvv?id={id}"

# kod GDELT → (kraj, nazwa); lista z posta „Today's Media Trends” i sprawdzonych kodów (2026-09-26)
CHANNELS: dict[str, tuple[str, str]] = {
    "TVPINFO": ("PL", "TVP Info"),
    "ESPRESO": ("UA", "Espreso"),
    "RUSSIA1": ("RU", "Rossija 1"),
    "RUSSIA24": ("RU", "Rossija 24"),
    "1TV": ("RU", "Pierwyj kanał"),
    "NTV": ("RU", "NTV"),
    "BELARUSTV": ("BY", "Belarus 24"),
    "CURRENTTIME": ("RFE/RL", "Current Time"),
    "LRT": ("LT", "LRT"),
    "DR1": ("DK", "DR1"),
    "M1": ("HU", "M1"),
    "BBCNEWS": ("UK", "BBC News"),
    "FRANCE24": ("FR", "France 24"),
    "TRTWORLD": ("TR", "TRT World"),
    "KAN11": ("IL", "Kan 11"),
    "PRESSTV": ("IR", "Press TV"),
    "CCTV13": ("CN", "CCTV-13"),
}

MIN_CHANNELS = 3      # nazwa w co najmniej tylu stacjach
MAX_BEFORE = 1        # dzień wcześniej w co najwyżej tylu stacjach, żeby była „nowa”
RISE = 3              # albo przybyło co najmniej tylu stacji i jest ich co najmniej dwa razy więcej
MAX_GROUPS = 25
SNIPPET = 320

FOOTER = re.compile(r"TODAY'?S MEDIA TRENDS BY THE GDELT PROJECT")
MONTHS = "JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER"
TITLE = re.compile(rf"\b(?:{MONTHS}) \d{{1,2}}, \d{{4}} (.+?) DAY-AT ?-A-GLANCE")
WORD = re.compile(r"[A-Za-zÀ-ɏ][A-Za-zÀ-ɏ0-9'’]*")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“(])")
CALENDAR = {m.casefold() for m in MONTHS.split("|")} | {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}


@dataclass
class Report:
    code: str
    title: str
    text: str
    shows: list[str] = field(default_factory=list)


def report_url(day: str, code: str) -> str:
    return URL.format(day=day.replace("-", ""), code=code)


def pdf_text(data: bytes) -> tuple[str, list[str]]:
    """Text of the report and the Visual Explorer broadcast ids it links to, in order of appearance."""
    from pypdf import PdfReader   # opcjonalna zależność: pip install -e ".[gdelt]"

    reader = PdfReader(io.BytesIO(data))
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    shows = []
    for page in reader.pages:
        for annot in page.get("/Annots") or []:
            uri = str((annot.get_object().get("/A") or {}).get("/URI") or "")
            if "tvv?id=" in uri:
                shows.append(uri.split("tvv?id=", 1)[1])
    return text, shows


def clean(text: str) -> str:
    """One line of prose: no bullets, page footers or the closing 'About this report'."""
    text = text.split("ABOUT THIS REPORT")[0]
    text = FOOTER.sub(" ", text)
    text = re.sub(r"\s*[•◦]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_of(text: str) -> str:
    m = TITLE.search(text)
    return m.group(1).strip() if m else ""


def body(text: str) -> str:
    """The report from 'Day at a glance' on (the cover repeats the title and the channel code)."""
    i = text.find("DAY-AT")
    return text[i:] if i >= 0 else text


def load(day: str, codes: Iterable[str], cache: Path, fetch: Callable[[str], bytes | None],
         parse: Callable[[bytes], tuple[str, list[str]]] = pdf_text) -> dict[str, Report]:
    """Reports for a day, from the cache or downloaded. `fetch` returns None when the report does not exist (404)."""
    out = {}
    folder = cache / day
    for code in codes:
        path = folder / f"{code}.json"
        if path.exists():
            d = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = fetch(report_url(day, code))
            if data is None:
                continue
            raw, shows = parse(data)
            text = clean(raw)
            d = {"code": code, "title": title_of(text), "text": body(text), "shows": shows}
            folder.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        out[code] = Report(d["code"], d["title"], d["text"], d["shows"])
    return out


def key(word: str) -> str:
    word = re.sub(r"['’]s$", "", word).replace("ł", "l").replace("Ł", "L")
    word = "".join(c for c in unicodedata.normalize("NFKD", word) if not unicodedata.combining(c))
    return word.casefold()


def _words(text: str) -> list[tuple[str, bool]]:
    """Words with a flag: a name, i.e. capitalised right after a lower-case word in the same sentence ("the Firepoint",
    "of Starlink"). Section headings in the reports are runs of capitalised words, so their words never qualify."""
    out = []
    matches = list(WORD.finditer(text))
    for i, m in enumerate(matches):
        w = m.group()
        prev = matches[i - 1] if i else None
        gap = text[prev.end():m.start()] if prev else ""
        after_lower = prev is not None and prev.group()[0].islower() and not re.search(r"[.!?:]", gap)
        name = (after_lower and w[0].isupper() and (len(w) >= 3 or (len(w) == 2 and w.isupper()))
                and w.casefold() not in CALENDAR)
        out.append((w, name))
    return out


def vocabulary(reports: Iterable[Report]) -> tuple[set[str], dict[str, Counter]]:
    """Names (words written capitalised mid-sentence at least as often as in lower case) and word counts per channel."""
    cap, low = Counter(), Counter()
    per_channel = {}
    for r in reports:
        counts = Counter()
        for w, name in _words(r.text):
            k = key(w)
            counts[k] += 1
            if name:
                cap[k] += 1
            elif w[0].islower():
                low[k] += 1
        per_channel[r.code] = counts
    return {k for k, n in cap.items() if n >= low[k]}, per_channel


def sentences(text: str) -> list[str]:
    return SENTENCE.split(text)


def _has(sentence: str, k: str) -> bool:
    return any(key(w) == k for w in WORD.findall(sentence))


def trends(today: dict[str, Report], before: dict[str, Report], min_channels: int = MIN_CHANNELS,
           max_before: int = MAX_BEFORE, rise: int = RISE, max_groups: int = MAX_GROUPS) -> list[dict]:
    """Names several channels mention today that were (almost) absent the day before, grouped when they come together."""
    names, counts = vocabulary(today.values())
    _, counts_before = vocabulary(before.values())
    rows = []
    for k in names:
        chans = [c for c in today if counts[c][k]]
        if len(chans) < min_channels:
            continue
        prev = sum(1 for c in counts_before.values() if c[k])
        if before and not (prev <= max_before or (len(chans) - prev >= rise and len(chans) >= 2 * prev)):
            continue
        rows.append({"key": k, "channels": chans, "before": prev, "mentions": sum(counts[c][k] for c in chans)})
    rows.sort(key=lambda r: (-len(r["channels"]), -r["mentions"], r["key"]))

    sents = {c: sentences(r.text) for c, r in today.items()}
    hits = {(r["key"], c): {i for i, s in enumerate(sents[c]) if _has(s, r["key"])} for r in rows for c in r["channels"]}
    groups: list[dict] = []
    for r in rows:   # nazwa idzie do grupy silniejszej, jeśli we wszystkich jej stacjach pada w tym samym zdaniu
        home = next((g for g in groups if set(r["channels"]) <= set(g["channels"])
                     and all(hits[(r["key"], c)] & hits[(g["keys"][0], c)] for c in r["channels"])), None)
        if home:
            home["keys"].append(r["key"])
        elif len(groups) < max_groups:
            groups.append({"keys": [r["key"]], "channels": r["channels"], "before": r["before"]})
    for g in groups:
        g["label"] = ", ".join(_display(k, today) for k in g["keys"])
        g["snippets"] = {c: _snippet(sents[c], g["keys"]) for c in g["channels"]}
    return [g for g in groups if g["label"][0].isupper()]   # zwykłe słowo, tylko czasem wielką literą


def phrase_snippets(today: dict[str, Report], phrase: str) -> dict[str, str]:
    """One sentence per channel containing the phrase (case and diacritics ignored)."""
    want = key(phrase)
    out = {}
    for c, r in today.items():
        hit = next((s for s in sentences(r.text) if want in key(s)), None)
        if hit:
            out[c] = _cut(hit, key(hit).find(want))
    return out


def _display(k: str, reports: dict[str, Report]) -> str:
    """The most frequent spelling of a name in the reports."""
    forms = Counter(w for r in reports.values() for w in WORD.findall(r.text) if key(w) == k)
    return forms.most_common(1)[0][0] if forms else k


def _snippet(sents: list[str], keys: list[str]) -> str:
    best = max(sents, key=lambda s: (_has(s, keys[0]), sum(_has(s, k) for k in keys)))
    pos = next((m.start() for m in WORD.finditer(best) if key(m.group()) == keys[0]), 0)
    return _cut(best, pos)


def _cut(s: str, pos: int) -> str:
    if len(s) <= SNIPPET:
        return s
    start = max(0, min(pos - SNIPPET // 3, len(s) - SNIPPET))
    return ("…" if start else "") + s[start:start + SNIPPET].strip() + ("…" if start + SNIPPET < len(s) else "")


def previous_day(day: str) -> str:
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def channel_label(code: str) -> str:
    country, name = CHANNELS.get(code, ("?", code))
    return f"{name} ({country})"


def render(day: str, today: dict[str, Report], before_day: str, before: dict[str, Report], groups: list[dict],
           phrases: dict[str, dict[str, str]], missing: list[str]) -> str:
    lines = [f"# Telewizja {day}: raporty GDELT „Today's Media Trends”", "",
             f"Kanały: {len(today)}" + (f"; brak raportu: {', '.join(missing)}" if missing else "")
             + f". Porównanie z {before_day} ({len(before)} kanałów).",
             "Raporty to streszczenia modelu (Gemini), nie przekaz stacji. Zdanie przy kanale jest z raportu; "
             "przed użyciem sprawdź w transkrypcji wydania (Visual Explorer).", ""]
    for phrase, snips in phrases.items():
        lines += [f"## Fraza: {phrase} ({len(snips)} kanałów)", ""]
        lines += [f"- **{channel_label(c)}**: {s}" for c, s in snips.items()] or ["- brak"]
        lines.append("")
    lines += ["## Nowe albo rosnące w kilku stacjach", ""]
    if not groups:
        lines += ["Brak.", ""]
    for n, g in enumerate(groups, 1):
        lines += [f"### {n}. {g['label']} ({len(g['channels'])} kanałów, dzień wcześniej {g['before']})", ""]
        lines += [f"- **{channel_label(c)}**: {s}" for c, s in g["snippets"].items()]
        lines.append("")
    lines += ["## Tytuły raportów", ""]
    for c, r in today.items():
        lines.append(f"- **{channel_label(c)}** ([PDF]({report_url(day, c)}), wydań: {len(set(r.shows))}): {r.title}")
    return "\n".join(lines) + "\n"
