"""Stories of the day for the internal site: the model groups a day's headlines into events covered by several
countries (one call), then checks every candidate article (chunked calls) and translates one headline per country.
Built only by `plx site`, never by the daily run; cached per day."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paralaksa.extract.llm_client import LLMRequest, model_extra_params

PROMPT_VERSION = "historie-v4"
MIN_COUNTRIES = 3
MAX_STORIES = 6        # na stronie
MAX_CANDIDATES = 8     # w pierwszym kroku: więcej, bo weryfikacja część odrzuci
VERIFY_CHUNK = 60      # artykułów na jedno wywołanie weryfikacji; duży dzień nie mieści się w limicie odpowiedzi
SUMMARY_CHARS = 220

PROMPT = """Dostajesz listę artykułów z jednego dnia z mediów z różnych krajów. Każdy wiersz: numer artykułu, kraj, redakcja,
oryginalny nagłówek i krótkie streszczenie po polsku.

Zadanie: znajdź do {max_stories} konkretnych wydarzeń, o których pisały media z co najmniej {min_countries} różnych krajów.
Wydarzenie to coś, co się stało w określonym momencie (wystąpienie, wizyta, atak, decyzja, głosowanie), a nie ogólny temat
(np. „wojna w Ukrainie” albo „polityka USA” to nie są wydarzenia). Kolejność: od wydarzenia opisywanego w największej
liczbie krajów.

Dla każdego wydarzenia:
- "tytul": neutralna nazwa wydarzenia po polsku, do 12 słów, bez ocen i bez przejmowania języka którejkolwiek strony;
- "opis": jedno zdanie po polsku, co się stało, wyłącznie na podstawie nagłówków i streszczeń z listy;
- "kraje": dla każdego kraju, który o nim pisał, JEDEN artykuł najbardziej bezpośrednio o tym wydarzeniu:
  {{"kraj": kod kraju z listy, "article_id": numer, "naglowek_pl": wierne tłumaczenie jego oryginalnego nagłówka na polski
  (bez dodawania ani pomijania informacji; nagłówek po polsku przepisz bez zmian)}};
- "pozostale": numery innych artykułów bezpośrednio o tym wydarzeniu (dowolne kraje).

Zasady: używaj wyłącznie numerów z listy. Artykuł należy do najwyżej jednego wydarzenia. Pomiń artykuły, które tylko
wspominają wydarzenie przy okazji albo dotyczą innego wydarzenia z tymi samymi osobami. Nie dobieraj artykułów na siłę:
lepiej pominąć kraj albo całe wydarzenie niż dopisać artykuł nie na temat.

Odpowiedz wyłącznie obiektem JSON: {{"historie": [{{"tytul": "...", "opis": "...", "kraje": [...], "pozostale": [...]}}]}}

Artykuły:
{items}
"""


VERIFY_PROMPT = """Masz listę wydarzeń (numer, nazwa, opis) i listę artykułów (numer, kraj, redakcja, oryginalny nagłówek,
streszczenie po polsku). Przypisz każdy artykuł do wydarzenia, o którym jego nagłówek albo streszczenie mówi bezpośrednio.
Artykuł o tym samym temacie, o tych samych osobach przy innej okazji albo o innym wydarzeniu dostaje null.
Dla przypisanych podaj wierne tłumaczenie oryginalnego nagłówka na polski, bez dodawania ani pomijania informacji
(nagłówek po polsku przepisz bez zmian).

Odpowiedz wyłącznie obiektem JSON, z oceną każdego artykułu z listy:
{{"oceny": [{{"article_id": numer, "wydarzenie": numer wydarzenia albo null, "naglowek_pl": "tłumaczenie albo pusty"}}]}}

Wydarzenia:
{events}

Artykuły:
{articles}
"""


def story_items(conn: sqlite3.Connection, day: str, eligible: set[int]) -> list[dict]:
    """Articles of the day's comparison sample with their first signal summary (Polish, helps across languages)."""
    items: dict[int, dict] = {}
    for r in conn.execute(
        """SELECT a.id, s.country, s.name, a.title FROM articles a JOIN sources s ON s.id = a.source_id
           WHERE substr(a.fetched_at,1,10) = ? ORDER BY a.id""", (day,)):
        if r[0] in eligible:
            items[r[0]] = {"id": r[0], "kraj": r[1], "zrodlo": r[2], "tytul": r[3] or "", "streszczenie": ""}
    if items:
        marks = ",".join("?" * len(items))
        for aid, summary in conn.execute(
                f"SELECT article_id, summary_pl FROM signals WHERE article_id IN ({marks}) ORDER BY id", list(items)):
            if not items[aid]["streszczenie"] and summary:
                items[aid]["streszczenie"] = summary[:SUMMARY_CHARS]
    return list(items.values())


def input_hash(items: list[dict]) -> str:
    return hashlib.sha256(json.dumps([PROMPT_VERSION, [i["id"] for i in items]]).encode()).hexdigest()[:16]


def build_prompt(items: list[dict]) -> str:
    lines = [f"#{i['id']} | {i['kraj']} | {i['zrodlo']} | {' '.join(i['tytul'].split())} | {' '.join(i['streszczenie'].split())}"
             for i in items]
    return PROMPT.format(max_stories=MAX_CANDIDATES, min_countries=MIN_COUNTRIES, items="\n".join(lines))


def _as_int(v: Any) -> int | None:
    if isinstance(v, int):
        return v
    if isinstance(v, str) and re.fullmatch(r"#?\d+", v.strip()):
        return int(v.strip().lstrip("#"))
    return None


def _json(text: str | None) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    return json.loads(m.group(0)) if m else {}


def parse_candidates(text: str, items: list[dict]) -> list[dict]:
    """First call: events with candidate articles; only known ids, each article in at most one event."""
    by_id = {i["id"]: i for i in items}
    used: set[int] = set()
    out = []
    for st in _json(text).get("historie") or []:
        if not isinstance(st, dict) or not st.get("tytul"):
            continue
        ids = [_as_int(k.get("article_id")) for k in st.get("kraje") or [] if isinstance(k, dict)]
        ids += [_as_int(v) for v in st.get("pozostale") or []]
        ids = [i for i in dict.fromkeys(ids) if i in by_id and i not in used]
        used.update(ids)
        out.append({"tytul": str(st["tytul"]).strip(), "opis": str(st.get("opis") or "").strip(), "ids": ids})
    return out


def build_verify_prompt(cands: list[dict], items: list[dict], ids: list[int] | None = None) -> str:
    by_id = {i["id"]: i for i in items}
    events = "\n".join(f"{n}. {c['tytul']}: {c['opis']}" for n, c in enumerate(cands, 1))
    ids = ids if ids is not None else [i for c in cands for i in c["ids"]]
    articles = "\n".join(f"#{i} | {by_id[i]['kraj']} | {by_id[i]['zrodlo']} | {' '.join(by_id[i]['tytul'].split())} | "
                         f"{' '.join(by_id[i]['streszczenie'].split())}" for i in ids)
    return VERIFY_PROMPT.format(events=events, articles=articles)


def parse_stories(cands: list[dict], verify_texts: list[str], items: list[dict]) -> list[dict]:
    """Second step decides: each candidate article goes to the event it directly concerns (possibly another one than
    the first call guessed) or nowhere. One article per country (in candidate order), >= MIN_COUNTRIES countries.
    The step may be split into several calls (VERIFY_CHUNK); their answers are merged."""
    by_id = {i["id"]: i for i in items}
    pool = [i for c in cands for i in c["ids"]]
    assigned: dict[int, tuple[int, str]] = {}
    for o in [o for t in verify_texts for o in _json(t).get("oceny") or []]:
        if not isinstance(o, dict):
            continue
        aid, n = _as_int(o.get("article_id")), _as_int(o.get("wydarzenie"))
        if aid in by_id and aid in pool and n is not None and 1 <= n <= len(cands):
            assigned[aid] = (n, str(o.get("naglowek_pl") or "").strip())
    stories = []
    for n, c in enumerate(cands, 1):
        mine = [i for i in pool if assigned.get(i, (None,))[0] == n]
        countries, rest, seen = [], [], set()
        for i in mine:
            art = by_id[i]
            if art["kraj"] in seen:
                rest.append(i)
                continue
            seen.add(art["kraj"])
            countries.append({"kraj": art["kraj"], "article_id": i, "naglowek_pl": assigned[i][1] or art["tytul"]})
        if len(countries) >= MIN_COUNTRIES:
            stories.append({"tytul": c["tytul"], "opis": c["opis"], "kraje": countries, "pozostale": rest,
                            "odrzucone": [i for i in c["ids"] if i not in assigned]})
    stories.sort(key=lambda s: -len(s["kraje"]))
    return stories[:MAX_STORIES]


def load_cached(cache_dir: Path, day: str, items: list[dict]) -> dict | None:
    path = cache_dir / f"{day}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if data.get("input_hash") == input_hash(items) else None


def _call(client: Any, model: str, custom_id: str, prompt: str) -> Any:
    extra = model_extra_params(model, "disabled", None)
    if model.startswith("deepseek"):
        extra["response_format"] = {"type": "json_object"}
    extra["temperature"] = 0
    res = client.complete(LLMRequest(custom_id=custom_id, model=model, max_tokens=8000,
                                     messages=[{"role": "user", "content": prompt}], extra=extra))
    if not res.ok:
        raise RuntimeError(f"{custom_id}: {res.error}")
    return res


def generate(client: Any, model: str, day: str, items: list[dict], cache_dir: Path) -> dict:
    """Find events with candidates, then verify each candidate and translate the ones that pass (in chunks of
    VERIFY_CHUNK articles). The result (also an empty one) is cached, so rebuilding the site does not pay again."""
    first = _call(client, model, f"historie-{day}", build_prompt(items))
    cands = parse_candidates(first.text, items)
    calls = [first]
    pool = [i for c in cands for i in c["ids"]]
    for n, k in enumerate(range(0, len(pool), VERIFY_CHUNK), 1):
        calls.append(_call(client, model, f"historie-weryfikacja-{day}-{n}",
                           build_verify_prompt(cands, items, pool[k:k + VERIFY_CHUNK])))
    out = {"day": day, "model": model, "prompt": PROMPT_VERSION, "input_hash": input_hash(items),
           "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "cost_usd": round(sum(c.cost_usd for c in calls), 4),
           "input_tokens": sum(c.input_tokens for c in calls), "output_tokens": sum(c.output_tokens for c in calls),
           "kandydaci": cands, "historie": parse_stories(cands, [c.text for c in calls[1:]], items)}
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{day}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
