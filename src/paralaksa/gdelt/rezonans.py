"""Day candidates from GDELT: people and organisations whose coverage jumped against the previous week (all languages,
names are in English in GKG), their headlines, and one model call that groups them into events and translates.
The reasons stay separate (outlets, languages, growth); nothing is folded into a single score."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from paralaksa.gdelt.bq import ENTITIES, GKG, LANG, LANG_PL, TITLE, UNESCAPE_UDF, day_literal, sql_string
from paralaksa.site.stories import _as_int, _call, _json

BASE_DAYS = 7
MIN_SOURCES = 40      # redakcji w dniu
MIN_LANGS = 6         # języków w dniu
TOP_ENTITIES = 40
PER_LANG = 2
PER_ENTITY = 20
MAX_EVENTS = 8
MAX_HEADLINES = 12
SKIP_FIELDS = {"rozrywka", "sport"}

PROMPT = """Dostajesz nagłówki z mediów z wielu krajów z jednego dnia. Są pogrupowane według osoby albo organizacji,
o której tego dnia pisało wyraźnie więcej redakcji niż zwykle. Każdy nagłówek: numer | język | redakcja | nagłówek.

Zadanie: wskaż do {max_events} konkretnych wydarzeń, które stoją za tymi grupami. Wydarzenie to coś, co się stało
w określonym momencie (wystąpienie, wizyta, atak, decyzja, zatrzymanie), a nie ogólny temat. Kilka grup może dotyczyć
jednego wydarzenia: połącz je. Jedna grupa może kryć kilka wydarzeń (np. przemówienie i protest przeciw niemu):
rozdziel je. Kolejność: od wydarzenia opisywanego w największej liczbie języków.

Dla każdego wydarzenia:
- "tytul": neutralna nazwa po polsku, do 12 słów, bez ocen i bez języka którejkolwiek strony;
- "opis": jedno zdanie po polsku, co się stało, wyłącznie na podstawie nagłówków;
- "dziedzina": jedno z: polityka, konflikt, gospodarka, spoleczenstwo, nauka_technika, rozrywka, sport, inne;
- "grupy": nazwy grup (dokładnie jak w liście), które dotyczą tego wydarzenia;
- "naglowki": do {max_headlines} nagłówków BEZPOŚREDNIO o tym wydarzeniu, możliwie z różnych języków i redakcji:
  {{"id": numer, "pl": wierne tłumaczenie na polski, bez dodawania ani pomijania informacji (polski przepisz bez zmian)}}.

Pomiń nagłówki o innej sprawie z tymi samymi osobami. Nie dobieraj na siłę: lepiej mniej nagłówków niż nie na temat.
Odpowiedz wyłącznie obiektem JSON: {{"wydarzenia": [{{"tytul": "...", "opis": "...", "dziedzina": "...", "grupy": [...],
"naglowki": [...]}}]}}

Grupy:
{groups}
"""


def spike_sql(day: str, limit: int = TOP_ENTITIES) -> str:
    d = day_literal(day)
    start = (date.fromisoformat(d) - timedelta(days=BASE_DAYS)).isoformat()
    return f"""
WITH p AS (
  SELECT DATE(_PARTITIONTIME) d, SourceCommonName src, {LANG} lang, ent
  FROM {GKG},
    UNNEST(ARRAY(SELECT DISTINCT LOWER(REGEXP_EXTRACT(x, r'^([^,]+)'))
                 FROM UNNEST(SPLIT({ENTITIES}, ';')) x WHERE x != '')) ent
  WHERE _PARTITIONTIME BETWEEN TIMESTAMP('{start}') AND TIMESTAMP('{d}'))
SELECT ent,
  COUNT(DISTINCT IF(d = '{d}', src, NULL)) redakcje,
  COUNT(DISTINCT IF(d = '{d}', lang, NULL)) jezyki,
  ROUND(COUNT(DISTINCT IF(d < '{d}', CONCAT(CAST(d AS STRING), src), NULL)) / {BASE_DAYS}, 1) wczesniej
FROM p WHERE ent IS NOT NULL GROUP BY ent
HAVING redakcje >= {MIN_SOURCES} AND jezyki >= {MIN_LANGS}
ORDER BY redakcje / (wczesniej + 15) DESC LIMIT {int(limit)}"""


def titles_sql(day: str, entities: list[str]) -> str:
    """Up to PER_ENTITY headlines per entity, first one per outlet, at most PER_LANG per language (spread of languages);
    within a language a fixed pseudo-random pick, so alphabetical outlet names do not decide."""
    d = day_literal(day)
    ents = ", ".join(sql_string(e) for e in entities)
    return f"""{UNESCAPE_UDF}
SELECT ent, lang, src, url, t, DATE FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY ent ORDER BY rn_lang, lang) rn_ent FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY ent, lang ORDER BY FARM_FINGERPRINT(url)) rn_lang FROM (
      SELECT e ent, {LANG} lang, SourceCommonName src, DocumentIdentifier url, {TITLE} t, DATE,
             ROW_NUMBER() OVER (PARTITION BY e, SourceCommonName ORDER BY DATE) rn_src
      FROM {GKG}, UNNEST([{ents}]) e
      WHERE _PARTITIONTIME = TIMESTAMP('{d}') AND STRPOS(LOWER({ENTITIES}), e) > 0)
    WHERE rn_src = 1 AND t IS NOT NULL AND t != '')
  WHERE rn_lang <= {PER_LANG})
WHERE rn_ent <= {PER_ENTITY}
ORDER BY ent, lang"""


def headline_items(rows: list[dict]) -> list[dict]:
    """Numbered headlines; the same article under several entities keeps one number."""
    items, by_url = [], {}
    for r in rows:
        if r["url"] in by_url:
            by_url[r["url"]]["ents"].append(r["ent"])
            continue
        it = {"id": len(items) + 1, "ents": [r["ent"]], "lang": r["lang"], "src": r["src"], "url": r["url"],
              "t": " ".join(str(r["t"]).split()), "czas": str(r.get("DATE") or "")}
        by_url[r["url"]] = it
        items.append(it)
    return items


def build_prompt(stats: list[dict], items: list[dict]) -> str:
    blocks = []
    for s in stats:
        lines = [f"#{i['id']} | {i['lang']} | {i['src']} | {i['t']}" for i in items if s["ent"] in i["ents"]]
        if lines:
            blocks.append(f"## {s['ent']}\n" + "\n".join(lines))
    return PROMPT.format(max_events=MAX_EVENTS, max_headlines=MAX_HEADLINES, groups="\n\n".join(blocks))


def parse_events(text: str, stats: list[dict], items: list[dict]) -> list[dict]:
    by_id = {i["id"]: i for i in items}
    by_ent = {s["ent"]: s for s in stats}
    used: set[int] = set()
    out = []
    for ev in _json(text).get("wydarzenia") or []:
        if not isinstance(ev, dict) or not ev.get("tytul"):
            continue
        heads = []
        for h in ev.get("naglowki") or []:
            hid = _as_int(h.get("id")) if isinstance(h, dict) else None
            if hid in by_id and hid not in used:
                used.add(hid)
                heads.append({**by_id[hid], "pl": str(h.get("pl") or "").strip()})
        groups = [by_ent[g] for g in dict.fromkeys(str(x).lower() for x in ev.get("grupy") or []) if g in by_ent]
        groups += [by_ent[e] for h in heads for e in h["ents"] if by_ent[e] not in groups]
        if not heads or not groups:
            continue
        top = max(groups, key=lambda g: g["redakcje"])
        out.append({"tytul": str(ev["tytul"]).strip(), "opis": str(ev.get("opis") or "").strip(),
                    "dziedzina": str(ev.get("dziedzina") or "inne").strip(), "grupy": [g["ent"] for g in groups],
                    "powody": {"grupa": top["ent"], "redakcje": top["redakcje"], "jezyki": top["jezyki"],
                               "wczesniej": top["wczesniej"], "wzrost": round(top["redakcje"] / max(top["wczesniej"], 1), 1),
                               "jezyki_naglowkow": len({h["lang"] for h in heads})},
                    "naglowki": heads})
    return out


def find(runner: Any, client: Any, model: str, day: str) -> dict:
    stats = runner.run(spike_sql(day))
    items = headline_items(runner.run(titles_sql(day, [s["ent"] for s in stats]))) if stats else []
    res = _call(client, model, f"gdelt-rezonans-{day}", build_prompt(stats, items)) if items else None
    events = parse_events(res.text, stats, items) if res else []
    return {"dzien": day, "model": model, "cost_usd": round(res.cost_usd, 4) if res else 0.0,
            "gb": round(runner.scanned / 1e9, 2), "grupy": stats,
            "wydarzenia": [e for e in events if e["dziedzina"] not in SKIP_FIELDS],
            "pominiete": [{"tytul": e["tytul"], "dziedzina": e["dziedzina"]} for e in events if e["dziedzina"] in SKIP_FIELDS]}


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render(out: dict) -> str:
    lines = [f"# Kandydaci z GDELT: {out['dzien']}", "",
             f"Wzrost liczony względem średniej z {BASE_DAYS} poprzednich dni. Nagłówki to podpowiedzi z GDELT: "
             "przed wpisaniem do karty otworzyć stronę i sprawdzić nagłówek i godzinę.", "",
             f"Koszt: {out['gb']} GB zapytań BigQuery, {out['cost_usd']:.3f} $ modelu.", ""]
    for n, ev in enumerate(out["wydarzenia"], 1):
        p = ev["powody"]
        lines += [f"## {n}. {ev['tytul']}", "", ev["opis"], "",
                  f"- dziedzina: {ev['dziedzina']}; grupy GDELT: {', '.join(ev['grupy'])}",
                  f"- „{p['grupa']}”: {p['redakcje']} redakcji w {p['jezyki']} językach, zwykle ok. {p['wczesniej']:g} "
                  f"dziennie (×{p['wzrost']:g}); nagłówki niżej w {p['jezyki_naglowkow']} językach", "",
                  "| język | redakcja | nagłówek | po polsku |", "|---|---|---|---|"]
        for h in ev["naglowki"]:
            lines.append(f"| {LANG_PL.get(h['lang'], h['lang'])} | [{_cell(h['src'])}]({h['url']}) | {_cell(h['t'])} "
                         f"| {_cell(h['pl'])} |")
        lines.append("")
    if out["pominiete"]:
        lines += ["Pominięte (rozrywka, sport): " + "; ".join(e["tytul"] for e in out["pominiete"]), ""]
    return "\n".join(lines)
