"""Missing relations for a card: the model proposes search phrases in many languages and scripts, BigQuery finds
matching GDELT headlines around the card's day, the model checks each headline (is it about this event?) and translates.
Outlets already in the card are listed separately. The card itself is never changed."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from itertools import zip_longest
from typing import Any
from urllib.parse import urlsplit

from paralaksa.gdelt.bq import GKG, LANG, LANG_PL, TITLE, UNESCAPE_UDF, day_literal, phrase_regex
from paralaksa.site.stories import _as_int, _call, _json

DAYS_BEFORE = 1
MAX_ROWS = 2000
MAX_CHECK = 300        # nagłówków do sprawdzenia przez model (po jednym na redakcję, na zmianę językami)
CHECK_CHUNK = 80

LANGS = ["en", "pl", "de", "fr", "es", "it", "tr", "ru", "uk", "ar", "he", "fa", "zh"]
PHRASES_PROMPT = """Karta zdarzenia z naszego projektu (porównanie nagłówków z różnych krajów). Podaj frazy, po których
znajdziemy nagłówki o TYM zdarzeniu w mediach z całego świata. Szukamy w samych nagłówkach, w oryginalnym języku.

Dla KAŻDEGO języka z listy {langs} podaj 2–4 frazy we własnym alfabecie i słowach tego języka, tak jak redakcja
z tego kraju napisałaby nagłówek (nie tłumacz dosłownie polskich nagłówków z karty).
- najlepsze są nazwy i określenia charakterystyczne dla zdarzenia („Fort Trump”, „Форт Трамп”, „Ми-8”);
- nazwy własne w transkrypcji tego języka; przy odmianie używaj rdzenia („Польш”, „Braniew”, „Nawrock”);
- gdy jedno słowo nie wystarcza, połącz 2 części znakiem " & " (obie muszą wystąpić), np. "вертол & Польш",
  "Hubschrauber & Polen"; nie łącz nazwy mało znanej miejscowości z innymi słowami, bo obce nagłówki rzadko ją podają;
- każda część to 1–2 słowa albo rdzeń, nigdy całe wyrażenie: nagłówki odmieniają słowa i zmieniają szyk
  (dobrze: "Нетаньяху & зал", "Netanyahu & walk"; źle: "выход из зала & Нетаньяху", "Netanyahu & UN General Assembly");
- nie podawaj ogólnych słów samych w sobie („Trump”, „Polska”, „helicopter”).

Odpowiedz wyłącznie obiektem JSON: {{"frazy": {{"en": ["..."], "ru": ["..."], ...}}}}

Tytuł: {title}
Fakt: {fact}
Dzień: {day}
Nagłówki z karty:
{headlines}
"""

CHECK_PROMPT = """Zdarzenie: {title}. {fact}
Dzień: {day}

Dla każdego nagłówka oceń, czy dotyczy BEZPOŚREDNIO tego zdarzenia. Reakcje na nie i jego ciąg dalszy w tych dniach
(wypowiedzi polityków o nim, komentarze, odpowiedź drugiej strony) też są true. Nagłówek o innej sprawie z tymi samymi
osobami albo miejscem: false.
Dla true podaj "pl": tłumaczenie nagłówka NA JĘZYK POLSKI, wierne, bez dodawania ani pomijania informacji.
Przykład: „Российский Ми-8 залетел в Польшу” → „Rosyjski Mi-8 wleciał do Polski”. Nigdy nie przepisuj obcego oryginału;
tylko nagłówek już po polsku zostaje bez zmian.

Odpowiedz wyłącznie obiektem JSON z oceną każdego nagłówka:
{{"oceny": [{{"id": numer, "o_zdarzeniu": true albo false, "pl": "tłumaczenie na polski albo pusty"}}]}}

Nagłówki (numer | język | redakcja | nagłówek):
{items}
"""


def card_day(card: dict) -> date:
    return date.fromisoformat(str(card["id"])[:10])


def card_domains(card: dict) -> set[str]:
    return {urlsplit(r.get("link") or "").netloc.lower().removeprefix("www.")
            for r in card.get("relacje") or [] if r.get("link")}


def in_card(src: str, domains: set[str]) -> bool:
    src = src.lower().removeprefix("www.")
    return any(src == d or d.endswith("." + src) or src.endswith("." + d) for d in domains)


def phrases_prompt(card: dict) -> str:
    fact = (card.get("fakt") or {}).get("opis") or ""
    heads = "\n".join(f"- {r.get('kraj')}: {r.get('naglowek')}" for r in card.get("relacje") or [] if r.get("naglowek"))
    return PHRASES_PROMPT.format(langs=", ".join(LANGS), title=card.get("tytul") or card["id"], fact=" ".join(str(fact).split()),
                                 day=card_day(card).isoformat(), headlines=heads or "(brak)")


def parse_phrases(text: str) -> list[str]:
    raw = _json(text).get("frazy") or []
    if isinstance(raw, dict):   # frazy per język
        raw = [p for v in raw.values() for p in (v if isinstance(v, list) else [v])]
    out = []
    for p in raw:
        parts = [x.strip() for x in str(p).split("&") if x.strip()]
        if parts and all(len(x) >= 3 for x in parts):
            out.append(" & ".join(parts))
    return list(dict.fromkeys(out))


def search_sql(phrases: list[str], start: date, end: date) -> str:
    conds = []
    for p in phrases:
        parts = [phrase_regex(x) for x in p.split("&") if x.strip()]
        conds.append("(" + " AND ".join(f"REGEXP_CONTAINS(LOWER(t), r'{x}')" for x in parts) + ")")
    return f"""{UNESCAPE_UDF}
SELECT DATE, src, url, lang, t, score FROM (
  SELECT *, {' + '.join(f"CAST({c} AS INT64)" for c in conds)} score FROM (
    SELECT DATE, SourceCommonName src, DocumentIdentifier url, {LANG} lang, {TITLE} t
    FROM {GKG}
    WHERE _PARTITIONTIME BETWEEN TIMESTAMP('{day_literal(start)}') AND TIMESTAMP('{day_literal(end)}'))
  WHERE t IS NOT NULL)
WHERE score > 0
ORDER BY score DESC, DATE LIMIT {MAX_ROWS}"""


def hit_items(rows: list[dict]) -> list[dict]:
    """Rows come best first (more matched phrases, then earlier), so a generic phrase alone does not fill the queue.
    One article per outlet; then languages take turns, so a flood in one language does not crowd out the rest."""
    first: dict[str, dict] = {}
    for r in rows:
        first.setdefault(r["src"], r)
    by_lang: dict[str, list[dict]] = {}
    for r in first.values():
        by_lang.setdefault(r["lang"], []).append(r)
    order = [r for group in zip_longest(*by_lang.values()) for r in group if r]
    return [{"id": n, "lang": r["lang"], "src": r["src"], "url": r["url"], "t": " ".join(str(r["t"]).split()),
             "czas": _gdelt_time(r["DATE"])} for n, r in enumerate(order[:MAX_CHECK], 1)]


def _gdelt_time(value: Any) -> str:
    try:
        return datetime.strptime(str(value), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return str(value)


def check_prompt(card: dict, items: list[dict]) -> str:
    fact = (card.get("fakt") or {}).get("opis") or ""
    return CHECK_PROMPT.format(title=card.get("tytul") or card["id"], fact=" ".join(str(fact).split()),
                               day=card_day(card).isoformat(),
                               items="\n".join(f"#{i['id']} | {i['lang']} | {i['src']} | {i['t']}" for i in items))


def parse_checks(texts: list[str], items: list[dict]) -> list[dict]:
    """Headlines the model judged to be about the event; a copied foreign original does not count as a translation."""
    by_id = {i["id"]: i for i in items}
    kept = {}
    for o in [o for t in texts for o in _json(t).get("oceny") or []]:
        if isinstance(o, dict) and o.get("o_zdarzeniu") is True and _as_int(o.get("id")) in by_id:
            kept[_as_int(o["id"])] = str(o.get("pl") or "").strip()
    out = []
    for i in items:
        if i["id"] in kept:
            pl = kept[i["id"]]
            copied = i["lang"] != "pol" and " ".join(pl.split()).lower() == i["t"].lower()
            out.append({**i, "pl": "" if copied else pl})
    return out


def search(runner: Any, client: Any, model: str, card: dict, days_after: int = 3,
           phrases: list[str] | None = None, check: bool = True, today: date | None = None) -> dict:
    calls = []
    if not phrases:
        res = _call(client, model, f"gdelt-frazy-{card['id']}", phrases_prompt(card))
        calls.append(res)
        phrases = parse_phrases(res.text)
    if not phrases:
        raise RuntimeError("model nie podał fraz do wyszukania; podaj je ręcznie przez --fraza")
    day = card_day(card)
    end = min(day + timedelta(days=days_after), today or datetime.now(timezone.utc).date())
    rows = runner.run(search_sql(phrases, day - timedelta(days=DAYS_BEFORE), end))
    items = hit_items(rows)
    if check and items:
        checks = [_call(client, model, f"gdelt-sprawdz-{card['id']}-{n}", check_prompt(card, items[k:k + CHECK_CHUNK]))
                  for n, k in enumerate(range(0, len(items), CHECK_CHUNK), 1)]
        calls += checks
        found = parse_checks([c.text for c in checks], items)
    else:
        found = [{**i, "pl": ""} for i in items]
    domains = card_domains(card)
    return {"karta": card["id"], "tytul": card.get("tytul"), "okno": [(day - timedelta(days=DAYS_BEFORE)).isoformat(),
            end.isoformat()], "frazy": phrases, "model": model, "gb": round(runner.scanned / 1e9, 2),
            "cost_usd": round(sum(c.cost_usd for c in calls), 4), "wierszy": len(rows), "sprawdzonych": len(items),
            "nowe": [f for f in found if not in_card(f["src"], domains)],
            "odrzucone": [i for i in items if i["id"] not in {f["id"] for f in found}] if check else [],
            "w_karcie": [f for f in found if in_card(f["src"], domains)], "sprawdzone": check}


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render(out: dict) -> str:
    langs: dict[str, list[dict]] = {}
    for f in out["nowe"]:
        langs.setdefault(f["lang"], []).append(f)
    lines = [f"# GDELT do karty {out['karta']}", "", f"{out['tytul'] or ''}", "",
             f"Okno {out['okno'][0]} – {out['okno'][1]} (dni UTC), {out['wierszy']} trafień, po jednym na redakcję "
             f"{out['sprawdzonych']}; " + ("model uznał za dotyczące zdarzenia " if out["sprawdzone"] else "bez sprawdzenia modelem: ")
             + f"{len(out['nowe']) + len(out['w_karcie'])}, z tego {len(out['nowe'])} spoza karty.",
             f"Koszt: {out['gb']} GB zapytań BigQuery, {out['cost_usd']:.3f} $ modelu.", "",
             "To podpowiedzi, nie relacje: przed wpisaniem do karty otworzyć stronę, sprawdzić nagłówek, godzinę i gatunek.", "",
             "Frazy: " + "; ".join(f"`{p}`" for p in out["frazy"]), ""]
    lines += ["## Redakcje spoza karty", ""]
    for lang, group in sorted(langs.items(), key=lambda kv: -len(kv[1])):
        lines += [f"### {LANG_PL.get(lang, lang)} ({len(group)})", "", "| czas GDELT (UTC) | redakcja | nagłówek | po polsku |",
                  "|---|---|---|---|"]
        lines += [f"| {f['czas']} | [{_cell(f['src'])}]({f['url']}) | {_cell(f['t'])} | {_cell(f['pl'] or '(bez tłumaczenia)')} |"
                  for f in group]
        lines.append("")
    if out["odrzucone"]:
        lines += [f"Model uznał za niedotyczące zdarzenia: {len(out['odrzucone'])} (lista w JSON, pole odrzucone).", ""]
    if out["w_karcie"]:
        lines += ["## Redakcje już w karcie", ""] + [f"- {f['src']}: {f['t']}" for f in out["w_karcie"]] + [""]
    return "\n".join(lines)


def dump(out: dict) -> str:
    return json.dumps(out, ensure_ascii=False, indent=1, default=str)
