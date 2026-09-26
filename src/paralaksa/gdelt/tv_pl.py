"""Polish translations of the TV reports (title and every sentence) for the site's Telewizja tab, with the English
original kept for the language switch. Built only by `plx site`, never by the daily run. Cached per day and channel
next to the report (`<day>/<CODE>.pl.json`), aligned with `tv.sentences`: a missing sentence falls back to English."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from typing import Any

from paralaksa.gdelt import tv
from paralaksa.site.stories import _as_int, _call, _json

PROMPT_VERSION = "tv-pl-v2"
MODEL = "deepseek-flash"   # tłumaczenie, nie analiza: najtańszy model DeepSeek (~0,1–0,2 $ dziennie za 17 raportów)
CHUNK = 40                 # zdań na wywołanie; przy 60 długie raporty przekraczały max_tokens (25.09 Rossija 1)
WORKERS = 4

PROMPT = """Przetłumacz na polski zdania z raportu o dniu wydań jednej stacji telewizyjnej ({channel}). Raport napisał
model językowy po angielsku. Każdy wiersz: numer | zdanie. Wiersz 0 to tytuł raportu (wersalikami): przetłumacz go
zwykłą pisownią zdania.

Tłumacz wiernie: bez dodawania, pomijania, łagodzenia ani zaostrzania. Zachowaj cudzysłowy, bo to często słowa stacji.
Wtrącone nagłówki sekcji na początku zdania (np. "MAJOR DEVELOPMENTS", "Kyivstar Office Hit:") też przetłumacz.
Nazwy własne w przyjętej polskiej pisowni (Netanjahu, Zełenski, Kijów, Ławrow); nazwy stacji, programów i firm bez zmian.
Żargon raportów po polsku zrozumiale: statecraft = polityka państwa, kinetic = zbrojny/militarny, narrative = przekaz.
Nigdy nie przepisuj angielskiego oryginału; zawsze podaj polskie tłumaczenie.

Odpowiedz wyłącznie obiektem JSON z tłumaczeniem każdego wiersza:
{{"t": [{{"id": numer, "pl": "tłumaczenie"}}]}}

Zdania:
{items}
"""


def path_for(cache: Path, day: str, code: str) -> Path:
    return cache / day / f"{code}.pl.json"


def cached(cache: Path, day: str, code: str, n: int) -> dict | None:
    """The saved translation if it still matches the report (same prompt and number of sentences)."""
    p = path_for(cache, day, code)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return d if d.get("prompt") == PROMPT_VERSION and len(d.get("sentences") or []) == n else None


def build_prompt(channel: str, lines: list[tuple[int, str]]) -> str:
    return PROMPT.format(channel=channel, items="\n".join(f"{i} | {s}" for i, s in lines))


def parse(text: str, lines: list[tuple[int, str]]) -> dict[int, str]:
    """Only ids from the chunk; a copied English original is dropped (the view shows the original instead)."""
    src = dict(lines)
    out = {}
    for o in _json(text).get("t") or []:
        if not isinstance(o, dict):
            continue
        i, pl = _as_int(o.get("id")), " ".join(str(o.get("pl") or "").split())
        if i in src and pl and pl.casefold() != src[i].casefold():
            out[i] = pl
    return out


def translate(client: Any, model: str, day: str, report: tv.Report, cache: Path) -> dict:
    """Translate one report (title as line 0, sentences as 1..n) and save it; returns the saved dict plus the cost."""
    sents = tv.sentences(report.text)
    lines = [(0, report.title)] + [(i + 1, s) for i, s in enumerate(sents)]
    chunks = [lines[k:k + CHUNK] for k in range(0, len(lines), CHUNK)]
    label = tv.channel_label(report.code)

    def run(n_chunk):
        n, chunk = n_chunk
        res = _call(client, model, f"tv-pl-{day}-{report.code}-{n}", build_prompt(label, chunk))
        return parse(res.text, chunk), res.cost_usd

    got: dict[int, str] = {}
    cost = 0.0
    errors = []
    with ThreadPoolExecutor(WORKERS) as pool:
        for fut in [pool.submit(run, nc) for nc in enumerate(chunks, 1)]:
            try:
                part, c = fut.result()
            except RuntimeError as e:
                errors.append(str(e))
                continue
            got.update(part)
            cost += c
    out = {"prompt": PROMPT_VERSION, "model": model, "title": got.get(0),
           "sentences": [got.get(i + 1) for i in range(len(sents))], "cost_usd": round(cost, 5)}
    if not errors:   # z błędem nie zapisujemy: następna budowa spróbuje jeszcze raz
        p = path_for(cache, day, report.code)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return {**out, "errors": errors}
