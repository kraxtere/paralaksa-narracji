"""Polish translations of all headlines of a day for the internal site (the article list, comparisons, the drawer).
Built only by `plx site`, never by the daily run. Cached per day and per article id: headlines do not change for
an id, so later builds translate only new articles."""
from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paralaksa.site.stories import _as_int, _call, _json

PROMPT_VERSION = "tytuly-v1"
CHUNK = 120        # nagłówków na wywołanie; odpowiedź musi się zmieścić w max_tokens
WORKERS = 4

PROMPT = """Przetłumacz nagłówki prasowe na polski. Każdy wiersz: numer, kod języka, oryginalny nagłówek.
Tłumacz wiernie: bez dodawania, pomijania ani łagodzenia informacji, zachowaj cudzysłowy i ton nagłówka.
Nazwy własne w przyjętej polskiej pisowni (np. Netanjahu, Zełenski, Xi Jinping). Nigdy nie przepisuj oryginału
w obcym alfabecie ani języku; zawsze podaj polskie tłumaczenie.

Odpowiedz wyłącznie obiektem JSON z tłumaczeniem każdego nagłówka z listy:
{{"tlumaczenia": [{{"id": numer, "pl": "tłumaczenie"}}]}}

Nagłówki:
{items}
"""


def title_items(conn: sqlite3.Connection, ids: set[int]) -> list[dict]:
    """Headlines to translate: every article of the day's sample not written in Polish."""
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    rows = conn.execute(
        f"""SELECT a.id, a.title, COALESCE(a.language, s.language, '') FROM articles a JOIN sources s ON s.id = a.source_id
            WHERE a.id IN ({marks}) ORDER BY a.id""", sorted(ids))
    return [{"id": r[0], "lang": r[2], "t": " ".join((r[1] or "").split())}
            for r in rows if r[1] and not str(r[2]).lower().startswith("pl")]


def build_prompt(items: list[dict]) -> str:
    return PROMPT.format(items="\n".join(f"#{i['id']} | {i['lang']} | {i['t']}" for i in items))


def parse_translations(text: str, items: list[dict]) -> dict[int, str]:
    """Only ids from the chunk; a copied original is not a translation and is dropped (the site shows the original)."""
    by_id = {i["id"]: i for i in items}
    out: dict[int, str] = {}
    for o in _json(text).get("tlumaczenia") or []:
        if not isinstance(o, dict):
            continue
        aid, pl = _as_int(o.get("id")), " ".join(str(o.get("pl") or "").split())
        if aid in by_id and pl and pl.casefold() != by_id[aid]["t"].casefold():
            out[aid] = pl
    return out


def load_cache(cache_dir: Path, day: str) -> dict:
    path = cache_dir / f"{day}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("prompt") == PROMPT_VERSION:
            data["tytuly"] = {int(k): v for k, v in data.get("tytuly", {}).items()}
            return data
    return {"prompt": PROMPT_VERSION, "tytuly": {}, "cost_usd": 0.0}


def cached(cache_dir: Path, day: str) -> dict[int, str]:
    return load_cache(cache_dir, day)["tytuly"]


def translate(client: Any, model: str, day: str, items: list[dict], cache_dir: Path) -> dict:
    """Translate headlines missing from the cache (chunks in parallel), merge and save. Returns the cache plus
    this run's cost and number of translated headlines."""
    data = load_cache(cache_dir, day)
    todo = [i for i in items if i["id"] not in data["tytuly"]]
    chunks = [todo[k:k + CHUNK] for k in range(0, len(todo), CHUNK)]

    def run(n_chunk):
        n, chunk = n_chunk
        return chunk, _call(client, model, f"tytuly-{day}-{n}", build_prompt(chunk))

    cost, errors = 0.0, []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(run, nc) for nc in enumerate(chunks, 1)]
        for f in futures:
            try:
                chunk, res = f.result()
            except RuntimeError as e:        # jedna porcja nie psuje reszty; brakujące nagłówki dojdą przy następnej budowie
                errors.append(str(e))
                continue
            cost += res.cost_usd
            data["tytuly"].update(parse_translations(res.text, chunk))
    data.update({"model": model, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                 "cost_usd": round(data.get("cost_usd", 0.0) + cost, 4)})
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{day}.json").write_text(json.dumps({**data, "tytuly": {str(k): v for k, v in sorted(data["tytuly"].items())}},
                                                      ensure_ascii=False, indent=0), encoding="utf-8")
    return {"tytuly": data["tytuly"], "run_cost": round(cost, 4), "translated": sum(1 for i in todo if i["id"] in data["tytuly"]),
            "missing": sum(1 for i in items if i["id"] not in data["tytuly"]), "errors": errors}
