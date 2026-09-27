"""Stories of the TV day: at most a few concrete events where the reports of different channels give different versions
(a number, the status of a decision, who did it, the outcome, the role of an actor), instead of an archive of topics.

Three steps (models: MODEL, GROUP_MODEL, VERIFY_MODEL), only by `plx site` / `plx gdelt tv-historie`, never by the daily run:
1. per report: claims about concrete events, each pointing at its sentences; sections where the report's author (Gemini)
   speculates (hypotheses, foresight, risks, blind spots, "red team" scenarios, information war) are left out first,
   so a hypothesis is never compared with a channel's account;
2. one call over all claims: events told by several channels and, for those with a concrete difference, the versions;
3. per candidate: the original sentences are shown again; the model keeps or drops the difference and marks the words
   that differ, which must be verbatim in the sentence (checked here).
It compares the reports' summaries of the channels, not the broadcasts: every story is to be checked in the broadcast
before use. Cached next to the reports: `<day>/<CODE>.claims.json` and `<day>/historie.json`."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable

from difflib import SequenceMatcher

from paralaksa.gdelt import tv
from paralaksa.extract.llm_client import LLMRequest, model_extra_params
from paralaksa.site.stories import _as_int, _json as _raw_json

PROMPT_VERSION = "tv-historie-v11"   # krok 3 (weryfikacja)
GROUP_VERSION = "tv-grupy-v1"       # krok 2: kandydaci zapisani osobno, żeby zmiana weryfikacji ich nie losowała na nowo
CLAIMS_VERSION = "tv-tezy-v1"       # krok 1: tezy z raportów
# Modele kroków; porównanie weryfikatorów na tych samych kandydatach 19, 22 i 25.09 (data/gdelt/burza/sedziowie-*.md):
# DeepSeek Pro przepuszczał wnioski („co sugeruje”) i różne zakresy, Haiku i Sonnet odrzucały je podobnie; Haiku ~2,5× taniej.
MODEL = "deepseek-flash"                        # 1: tezy z każdego raportu (dużo tekstu, proste zadanie)
GROUP_MODEL = "deepseek-v4-pro"                 # 2: zdarzenia i wersje (flash łączył „do stycznia” z „do 10 stycznia”)
VERIFY_MODEL = "claude-haiku-4-5-20251001"      # 3: weryfikacja kandydatów
MODELS = (MODEL, GROUP_MODEL, VERIFY_MODEL)
MAX_CLAIMS = 25       # tez z jednego raportu
MAX_CANDIDATES = 8    # kandydatów z kroku 2; weryfikacja część odrzuci
MAX_STORIES = 3       # na stronie na wierzchu; pozostałe zweryfikowane pod „więcej”
WORKERS = 6
SAME_NAME = 0.75         # podobieństwo zapisu słów różnicujących, od którego „tożsamość” to tylko pisownia
APPROX = 0.10            # margines liczb ze słowem „około”, „ponad” itp.
# Weryfikator z myśleniem (effort high) sprawdzony 19 i 21.09: odrzucał więcej, ale 4× drożej, 4 min na dzień i nadal
# przepuszczał transliterację. Zamiast tego reguły w kodzie (_numbers_differ, _names_differ).

# nagłówki sekcji raportu (stały szablon GDELT) → sekcja; kolejność: dłuższe przed krótszymi
HEADINGS: list[tuple[str, str]] = [
    ("MAJOR DEVELOPMENTS", "major"), ("KEY GOVERNANCE TOPICS", "governance"), ("DEEP DIVE", "trends"),
    ("TRENDS AND THEMES", "trends"), ("INTERNAL DYNAMICS", "internal"), ("DOMESTIC INSTABILITY", "internal"),
    ("EXTERNAL DYNAMICS", "external"), ("GLOBAL POSTURE", "external"), ("THE ECONOMIC ENVIRONMENT", "economy"),
    ("LEADERSHIP CHANGES", "leaders"), ("EDITORIAL POSTURE", "hierarchy"), ("STORY HIERARCHY", "hierarchy"),
    ("GEOPOLITICAL FRAMING", "framing"), ("INFORMATION WARFARE ENVIRONMENT", "infowar"),
    ("HYPOTHESES AND FUTURE OUTLOOK", "hypotheses"), ("STRATEGIC FORESIGHT", "foresight"), ("RISK ASSESSMENT", "risk"),
    ("BLIND SPOTS", "blind"), ("CONTRARIAN NARRATIVE SCENARIOS", "contrarian"), ("LEGISLATIVE ROUNDUP", "legislative"),
    ("BILLS DISCUSSED/DEBATED", "legislative"), ("PRESS EVENTS", "press"), ("KEY STORIES", "key"),
    ("CORPORATE ACTORS", "corporate"),
]
# sekcje, w których autor raportu przewiduje, ocenia albo dopisuje hipotezy: nie porównujemy ich z przekazem stacji
SPECULATIVE = {"infowar", "hypotheses", "foresight", "risk", "blind", "contrarian"}
HEADING = re.compile("|".join(re.escape(h) for h, _ in HEADINGS))
SECTION_OF = dict(HEADINGS)

REJECT_IF = ("zaokraglenie", "dokladniejsza", "pisownia", "akcent", "inna_miara", "to_samo")   # pytania kontrolne weryfikacji
TYPES = {"liczba": "różne liczby", "status": "obietnica czy decyzja", "tożsamość": "kto", "przebieg": "różny przebieg",
         "przyczyna": "różna przyczyna", "rola": "różna rola aktora", "ocena": "różna ocena"}


def sections(text: str) -> list[str]:
    """Section of each sentence of `tv.sentences(text)`: the one open at the start of the sentence, or the heading the
    sentence begins with."""
    out, current = [], "glance"
    for s in tv.sentences(text):
        heads = list(HEADING.finditer(s))
        out.append(SECTION_OF[heads[0].group()] if heads and heads[0].start() <= 2 else current)
        if heads:
            current = SECTION_OF[heads[-1].group()]
    return out


def usable(report: tv.Report) -> list[tuple[int, str]]:
    """Sentences outside the speculative sections, with their index in `tv.sentences`."""
    sents = tv.sentences(report.text)
    return [(i, s) for i, (s, sec) in enumerate(zip(sents, sections(report.text))) if sec not in SPECULATIVE]


CLAIMS_PROMPT = """Poniżej zdania z raportu o dniu wydań jednej stacji telewizyjnej ({channel}). Raport napisał model
językowy po angielsku, streszczając, co stacja pokazywała. Każdy wiersz: numer | zdanie.

Wypisz do {max_claims} tez o KONKRETNYCH zdarzeniach, o których raport mówi, że stacja je przedstawiała: decyzje, ataki,
głosowania, spotkania, wypowiedzi, wyniki, liczby, zatrzymania, a także wyraźne przedstawienie konkretnego aktora
(państwa, osoby, organizacji) w roli, np. „mediator”, „agresor”. Pomiń ogólne tematy i tła („napięcia w regionie”).
Najważniejsze najpierw.

Dla każdej tezy:
- "zdarzenie": krótka neutralna nazwa zdarzenia po polsku (kto, co, gdzie), do 10 słów, taka sama dla tego samego
  zdarzenia niezależnie od stacji (np. „USA: licencja na produkcję Patriotów dla Ukrainy”);
- "teza": co raport podaje o tym zdarzeniu, po polsku, do 30 słów, wiernie: z liczbami, nazwami i statusem
  (obiecane, rozważane, ogłoszone, wykonane; kto to twierdzi), bez dodawania ocen;
- "zdania": numery zdań, na których teza się opiera (1–3).

Odpowiedz wyłącznie obiektem JSON: {{"tezy": [{{"zdarzenie": "...", "teza": "...", "zdania": [numery]}}]}}

Zdania:
{items}
"""

GROUP_PROMPT = """Masz tezy wypisane z raportów o dniu wydań {n} stacji telewizyjnych z różnych krajów (raporty napisał
model językowy, streszczając każdą stację). Każdy wiersz: id tezy | stacja (kraj) | zdarzenie | teza.

Znajdź do {max_cand} konkretnych zdarzeń, o których mówią co najmniej dwie stacje i w których wersje stacji się
KONKRETNIE różnią. Rodzaje różnic:
- "liczba": inna liczba tego samego (ofiar, frekwencji, dni, kwoty);
- "status": to samo raz jako obietnica/rozważane, raz jako decyzja wykonana (albo brak potwierdzenia);
- "tożsamość": inna osoba, państwo albo sprawca tego samego;
- "przebieg": wykluczające się wyniki (np. okrążenie zamknięte vs obrona utrzymana);
- "przyczyna": ten sam skutek, inne wyjaśnienie;
- "rola": ten sam aktor w przeciwnych rolach (np. mediator vs strona wroga);
- "ocena": to samo zdarzenie oceniane przeciwnie (sukces vs porażka).
Warunek: wersje NIE MOGĄ być jednocześnie prawdziwe (dla "liczba", "status", "tożsamość", "przebieg", "przyczyna")
albo są przeciwne (dla "rola", "ocena"). To NIE jest różnica: jedna stacja podaje szczegół, którego inna nie podaje;
jedna wersja jest tylko dokładniejsza („do stycznia” i „do 10 stycznia”); różny akcent albo wybór wątków.
Ta sama rzecz bywa różnie nazwana w różnych stacjach (np. „okrążenie Dobropola” i „obrona w sektorze Dobropola”):
porównuj treść tez, nie tylko nazwy zdarzeń. Najpierw różnice najbardziej konkretne i sprawdzalne.

Dla każdego zdarzenia:
- "tytul": neutralna nazwa po polsku, do 10 słów;
- "typ": jeden z rodzajów wyżej;
- "roznica": jedno zdanie po polsku: czym dokładnie różnią się wersje i które stacje je podają;
- "wersje": 2–3 wersje, każda {{"etykieta": do 4 słów po polsku (np. „obiecana”, „przyznana”, „59,8%”),
  "tezy": [id tez]}};
- "wszystkie": id wszystkich tez o tym zdarzeniu (także tych, które nie należą do żadnej wersji).

Używaj wyłącznie id z listy. Nie łącz różnych zdarzeń z tymi samymi osobami. Lepiej mniej zdarzeń niż naciągane.

Odpowiedz wyłącznie obiektem JSON: {{"zdarzenia": [{{"tytul": "...", "typ": "...", "roznica": "...",
"wersje": [...], "wszystkie": [...]}}]}}

Tezy:
{items}
"""

VERIFY_PROMPT = """Sprawdź jedną proponowaną różnicę między raportami o wydaniach stacji telewizyjnych. Raporty napisał
model językowy po angielsku; obok jest tłumaczenie na polski.

Propozycja: {title}. Rodzaj: {kind}. {diff}

Zdania, według wersji (stacja | numer zdania | angielski oryginał || polskie tłumaczenie):
{items}

Najpierw odpowiedz na pytania kontrolne (tylko na podstawie tych zdań), w polu "kontrola":
- "to_samo_zdarzenie": czy wszystkie zdania dotyczą tego samego konkretnego zdarzenia?
- "wersje_wprost": czy każda wersja jest podana WPROST w zdaniu swojej stacji? (Milczenie, „nie wspomina”,
  „nie podaje”, „nie potwierdza” albo wniosek „co sugeruje” to NIE jest wersja; wyjątek: zdanie wprost mówi
  o zaprzeczeniu albo braku potwierdzenia.)
- "zaokraglenie": czy liczby różnią się tylko zaokrągleniem albo przybliżeniem (38% i 37,9%; „ponad 44%” i 44,37%;
  „kilkadziesiąt sekund” i 42 sekundy; 6,5 i 6,52; „ok. 57%” i „ponad 57%”)?
- "dokladniejsza": czy jedna wersja jest tylko dokładniejsza albo pełniejsza od drugiej („do stycznia” i „do 10 stycznia”;
  „CNN i Politico” i „CNN, MSNBC i Politico”; jedna stacja podaje liczbę, druga nie)?
- "pisownia": czy różni się tylko zapis albo transliteracja nazwy (Kambolow, Kambołow, Kabulow)?
- "akcent": czy to tylko inny akcent, ton albo wybór wątków, a nie przeciwne twierdzenia?
- "inna_miara": czy wersje mierzą albo opisują co innego: inną wielkość (procent głosów i procent mandatów), inny zakres
  (Europa i Francja; całość i trzy miesiące; atak na Moskwę i zestrzelenia na wszystkich frontach), inne miejsce albo czas?
- "to_samo": czy wersje mówią to samo innymi słowami (355 mandatów i 79% z 450 miejsc; „bezprecedensowe” i „pierwsze
  od dekady”)?
- "aktualizacja": czy to może być aktualizacja w ciągu dnia albo różny zakres czasu (wtedy zaznacz w "uwaga")?

Potem podaj:
- "typ" (liczba, status, tożsamość, przebieg, przyczyna, rola, ocena) i "roznica": jedno zdanie po polsku, poprawione
  ściśle według zdań, z nazwami stacji;
- "tytul": neutralna nazwa zdarzenia po polsku, do 10 słów;
- "wersje": dla każdej wersji {{"etykieta": do 4 słów, "stacje": [{{"stacja": kod, "zdanie": numer,
  "en": słowa różnicujące SKOPIOWANE DOSŁOWNIE z angielskiego zdania (2–8 słów),
  "pl": odpowiadające im słowa SKOPIOWANE DOSŁOWNIE z polskiego tłumaczenia,
  "wprost": true tylko wtedy, gdy zdanie tej stacji samo, wprost podaje tę wersję o tym zdarzeniu}}]}};
  pomiń stacje, których zdanie nie wspiera wersji;
- "uwaga": zastrzeżenie w jednym zdaniu albo pusty tekst;
- "sila": 3 = wersje podane wprost się wykluczają i łatwo to sprawdzić w wydaniu, 2 = wyraźna różnica,
  1 = słaba.

Odpowiedz wyłącznie obiektem JSON: {{"kontrola": {{"to_samo_zdarzenie": true/false, "wersje_wprost": true/false,
"zaokraglenie": true/false, "dokladniejsza": true/false, "pisownia": true/false, "akcent": true/false,
"inna_miara": true/false, "to_samo": true/false, "aktualizacja": true/false}}, "tytul": "...", "typ": "...", "roznica": "...", "wersje": [...], "uwaga": "...", "sila": 1–3}}
"""


def _claims_path(cache: Path, day: str, code: str) -> Path:
    return cache / day / f"{code}.claims.json"


def _stories_path(cache: Path, day: str) -> Path:
    return cache / day / "historie.json"


def _digest(reports: dict[str, tv.Report]) -> str:
    raw = "|".join(f"{c}:{len(r.text)}" for c, r in sorted(reports.items()))
    return hashlib.sha256(f"{PROMPT_VERSION}|{raw}".encode()).hexdigest()[:16]


QUOTE_FIX = re.compile(r'„([^"„”\n]{0,300})"')


def _json(text: str | None) -> dict:
    """JSON of an answer; Haiku writes „cytat" (Polish opening, ASCII closing quote), which breaks the string: fixed first."""
    try:
        return _raw_json(text)
    except ValueError:
        return _raw_json(QUOTE_FIX.sub(r"„\1”", text or ""))


def _call(client: Any, model: str, custom_id: str, prompt: str) -> Any:
    """One call without reasoning; JSON mode and temperature 0 only where the provider takes them (DeepSeek)."""
    extra = model_extra_params(model, "disabled", None)
    if model.startswith("deepseek"):
        extra.update(response_format={"type": "json_object"}, temperature=0)
    res = client.complete(LLMRequest(custom_id=custom_id, model=model, max_tokens=8000,
                                     messages=[{"role": "user", "content": prompt}], extra=extra))
    if not res.ok:
        raise RuntimeError(f"{custom_id}: {res.error}")
    return res


def _ask(client: Any, model: str, custom_id: str, prompt: str, parse) -> tuple[Any, float]:
    """One call parsed by `parse`; a broken JSON answer is asked once more, then it is an error (RuntimeError)."""
    cost = 0.0
    for attempt in (1, 2):
        res = _call(client, model, f"{custom_id}-{attempt}", prompt)
        cost += res.cost_usd
        try:
            return parse(res.text), cost
        except ValueError as e:
            err = e
    raise RuntimeError(f"{custom_id}: niepoprawny JSON ({err})")


def parse_claims(text: str, allowed: set[int]) -> list[dict]:
    out = []
    for o in _json(text).get("tezy") or []:
        if not isinstance(o, dict):
            continue
        ids = [i for i in (_as_int(x) for x in o.get("zdania") or []) if i in allowed]
        ev, claim = " ".join(str(o.get("zdarzenie") or "").split()), " ".join(str(o.get("teza") or "").split())
        if ids and ev and claim:
            out.append({"zdarzenie": ev, "teza": claim, "zdania": ids[:3]})
    return out[:MAX_CLAIMS]


def claims(client: Any, model: str, day: str, report: tv.Report, cache: Path) -> tuple[list[dict], float]:
    """Claims of one report (cached per report and prompt version); returns them and the cost of this run."""
    p = _claims_path(cache, day, report.code)
    n = len(tv.sentences(report.text))
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("prompt") == CLAIMS_VERSION and d.get("n") == n:
            return d["tezy"], 0.0
    lines = usable(report)
    prompt = CLAIMS_PROMPT.format(channel=tv.channel_label(report.code), max_claims=MAX_CLAIMS,
                                  items="\n".join(f"{i} | {s}" for i, s in lines))
    got, cost = _ask(client, model, f"tv-tezy-{day}-{report.code}", prompt,
                     lambda text: parse_claims(text, {i for i, _ in lines}))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"prompt": CLAIMS_VERSION, "n": n, "tezy": got}, ensure_ascii=False, indent=1),
                 encoding="utf-8")
    return got, cost


def parse_groups(text: str, ids: dict[str, dict]) -> list[dict]:
    """Candidates with at least two versions from at least two channels; unknown ids are dropped."""
    out = []
    for o in _json(text).get("zdarzenia") or []:
        if not isinstance(o, dict):
            continue
        versions = []
        for v in o.get("wersje") or []:
            if not isinstance(v, dict):
                continue
            tids = [t for t in (str(x).strip() for x in v.get("tezy") or []) if t in ids]
            if tids:
                versions.append({"etykieta": str(v.get("etykieta") or "").strip(), "tezy": tids})
        channels = {ids[t]["kod"] for v in versions for t in v["tezy"]}
        if len(versions) < 2 or len(channels) < 2:
            continue
        every = [t for t in (str(x).strip() for x in o.get("wszystkie") or []) if t in ids]
        out.append({"tytul": str(o.get("tytul") or "").strip(), "typ": str(o.get("typ") or "").strip(),
                    "roznica": str(o.get("roznica") or "").strip(), "wersje": versions,
                    "wszystkie": sorted(set(every) | {t for v in versions for t in v["tezy"]})})
    return out[:MAX_CANDIDATES]


def _verbatim(part: str, sentence: str | None) -> str:
    """The marked words if they really are in the sentence (case-insensitive), else empty."""
    part = " ".join(str(part or "").split()).strip(" .,\"'“”„")
    if not part or not sentence:
        return ""
    i = sentence.casefold().find(part.casefold())
    return sentence[i:i + len(part)] if i >= 0 else ""


NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
AT_LEAST = re.compile(r"\b(?:over|more than|above|at least|exceed(?:s|ed|ing)?|surpass(?:es|ed|ing)?|top(?:s|ped)|"
                      r"past|upwards of|in excess of)\s+\W{0,2}$", re.I)
AT_MOST = re.compile(r"\b(?:under|less than|below|up to|fewer than|at most)\s+\W{0,2}$", re.I)
ABOUT = re.compile(r"\b(?:about|around|nearly|almost|approximately|roughly|close to|some|an estimated|near)\s+\W{0,2}$", re.I)


def _numbers(text: str) -> list[tuple[float, float]]:
    """Numbers as intervals: exact to half a unit of the last written digit (38 → 37,5–38,5; 37,9 → 37,85–37,95);
    "over 108" is 108 and up, "up to 60" is 60 and down, "about 57" is ±APPROX (the word right before the number)."""
    out = []
    text = (text or "").replace(" ", " ")
    for m in NUMBER.finditer(text):
        g = m.group()
        raw = g.replace(",", ".") if re.fullmatch(r"\d+,\d{1,2}", g) else g.replace(",", "")
        v = float(raw)
        half = 0.5 * 10 ** -(len(raw.split(".")[1]) if "." in raw else 0)
        before = text[:m.start()]
        if AT_LEAST.search(before):
            out.append((v - half, float("inf")))
        elif AT_MOST.search(before):
            out.append((float("-inf"), v + half))
        elif ABOUT.search(before):
            out.append((v - max(half, APPROX * v), v + max(half, APPROX * v)))
        else:
            out.append((v - half, v + half))
    return out


def _numbers_differ(versions: list[dict]) -> bool:
    """False when every pair of versions has two numbers whose intervals overlap (a rounding or an approximation)."""
    nums = [[n for r in v["stacje"] for n in _numbers(r.get("_ctx") or r["en"])] for v in versions]

    def close(a, b):
        return any(lo1 <= hi2 + 1e-9 and lo2 <= hi1 + 1e-9 for lo1, hi1 in a for lo2, hi2 in b)

    return not all(close(nums[i], nums[j]) for i in range(len(nums)) for j in range(i + 1, len(nums)))


def _names_differ(versions: list[dict]) -> bool:
    """False when the marked words of the versions are written almost the same (a transliteration or a longer list)."""
    words = [[r["en"].casefold() for r in v["stacje"] if r["en"]] for v in versions]
    pairs = [(a, b) for i in range(len(words)) for j in range(i + 1, len(words)) for a in words[i] for b in words[j]]
    return not pairs or not all(SequenceMatcher(None, a, b).ratio() >= SAME_NAME for a, b in pairs)


def parse_verdict(text: str, cand: dict, ids: dict[str, dict], texts: dict[str, tuple[list[str], list]]) -> dict | None:
    """A verified story, or None. Every station's sentence must be one of the sentences its claims cited."""
    d = _json(text)
    k = d.get("kontrola") if isinstance(d.get("kontrola"), dict) else {}
    # decyduje kod, nie model: każde pytanie kontrolne musi wypaść na korzyść różnicy
    if not (k.get("to_samo_zdarzenie") is True and k.get("wersje_wprost") is True
            and all(k.get(f) is False for f in REJECT_IF)):
        return None
    allowed = {(ids[t]["kod"], i) for v in cand["wersje"] for t in v["tezy"] for i in ids[t]["zdania"]}
    versions = []
    for v in d.get("wersje") or []:
        if not isinstance(v, dict):
            continue
        rows = []
        for s in v.get("stacje") or []:
            if not isinstance(s, dict):
                continue
            code, i = str(s.get("stacja") or "").strip().upper(), _as_int(s.get("zdanie"))
            if (code, i) not in allowed or any(r["stacja"] == code for r in rows) or s.get("wprost") is not True:
                continue
            en, pl = texts[code]
            mark = _verbatim(s.get("en"), en[i])
            at = en[i].find(mark) if mark else -1
            rows.append({"stacja": code, "zdanie": i, "en": mark,
                         "pl": _verbatim(s.get("pl"), pl[i] if pl and i < len(pl) else None),
                         # do reguły liczb: słowa różnicujące z trzema słowami przed nimi („above”, „nearly”)
                         "_ctx": " ".join(en[i][:at].split()[-3:] + [mark]) if at >= 0 else ""})
        if rows:
            versions.append({"etykieta": str(v.get("etykieta") or "").strip(), "stacje": rows})
    kind = str(d.get("typ") or cand["typ"]).strip()
    kind = kind if kind in TYPES else cand["typ"]
    if kind == "liczba":   # wersja bez liczby w słowach różnicujących to brak szczegółu, nie inna wersja
        versions = [v for v in versions if any(_numbers(r["en"]) for r in v["stacje"])]
    ok = (kind != "liczba" or _numbers_differ(versions)) and (kind != "tożsamość" or _names_differ(versions))
    for v in versions:
        for r in v["stacje"]:
            r.pop("_ctx", None)
    if len(versions) < 2 or len({r["stacja"] for v in versions for r in v["stacje"]}) < 2:
        return None
    if not ok:
        return None
    shown = {r["stacja"] for v in versions for r in v["stacje"]}
    return {"tytul": str(d.get("tytul") or cand["tytul"]).strip(), "typ": kind,
            "roznica": str(d.get("roznica") or cand["roznica"]).strip(), "wersje": versions,
            "wspomina": sorted({ids[t]["kod"] for t in cand["wszystkie"]} - shown),
            "uwaga": str(d.get("uwaga") or "").strip(), "sila": _as_int(d.get("sila")) or 1}


def cached(cache: Path, day: str, reports: dict[str, tv.Report]) -> list[dict] | None:
    """Saved stories of a day if they match the reports and the prompt (no model)."""
    path = _stories_path(cache, day)
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    return d["historie"] if d.get("hash") == _digest(reports) else None


def generate(client_for: Callable[[str], Any], day: str, reports: dict[str, tv.Report], pl: dict[str, dict | None],
             cache: Path) -> dict:
    """Stories of a day (cached; a rebuild is free), strongest first. `client_for(model)` gives the client of each step's
    model (MODEL, GROUP_MODEL, VERIFY_MODEL). Returns {"historie": [...], "cost_usd": this run, "errors": [...]}."""
    path = _stories_path(cache, day)
    digest = _digest(reports)
    known = cached(cache, day, reports)
    if known is not None:
        return {"historie": known, "cost_usd": 0.0, "errors": []}
    cost, errors = 0.0, []

    def one(r):
        return r.code, claims(client_for(MODEL), MODEL, day, r, cache)

    ids: dict[str, dict] = {}
    with ThreadPoolExecutor(WORKERS) as pool:
        futs = [pool.submit(one, r) for r in reports.values()]
        results = []
        for f in futs:
            try:
                results.append(f.result())
            except RuntimeError as e:
                errors.append(str(e))
    for code, (got, c) in sorted(results, key=lambda x: list(tv.CHANNELS).index(x[0])):
        cost += c
        for n, t in enumerate(got, 1):
            ids[f"{code}-{n}"] = {**t, "kod": code}
    if errors:   # bez kompletu tez nie porównujemy: następna budowa spróbuje jeszcze raz
        return {"historie": [], "cost_usd": cost, "errors": errors}

    items = "\n".join(f"{k} | {tv.channel_label(t['kod'])} | {t['zdarzenie']} | {t['teza']}" for k, t in ids.items())
    gpath = cache / day / "historie-kandydaci.json"
    gkey = hashlib.sha256(f"{GROUP_VERSION}|{items}".encode()).hexdigest()[:16]
    saved = json.loads(gpath.read_text(encoding="utf-8")) if gpath.exists() else {}
    if saved.get("hash") == gkey:
        cands = saved["kandydaci"]
    else:
        try:
            cands, c = _ask(client_for(GROUP_MODEL), GROUP_MODEL, f"tv-grupy-{day}",
                            GROUP_PROMPT.format(n=len(reports), max_cand=MAX_CANDIDATES, items=items),
                            lambda text: parse_groups(text, ids))
        except RuntimeError as e:
            return {"historie": [], "cost_usd": cost, "errors": [str(e)]}
        cost += c
        gpath.write_text(json.dumps({"hash": gkey, "kandydaci": cands}, ensure_ascii=False, indent=1), encoding="utf-8")

    texts = {c: (tv.sentences(r.text), (pl.get(c) or {}).get("sentences") or []) for c, r in reports.items()}
    # surowe odpowiedzi weryfikacji według treści promptu: zmiana reguł w kodzie nie wymaga nowych wywołań
    vpath = cache / day / "historie-weryfikacja.json"
    answers: dict[str, str] = json.loads(vpath.read_text(encoding="utf-8")) if vpath.exists() else {}

    def verdict_of(key, cand):
        def parse(text):
            story = parse_verdict(text, cand, ids, texts)
            answers[key] = text   # tylko poprawny JSON
            return story
        return parse

    def check(cand):
        lines = []
        for v in cand["wersje"]:
            lines.append(f"Wersja „{v['etykieta']}”:")
            for t in v["tezy"]:
                code = ids[t]["kod"]
                en, plx = texts[code]
                for i in ids[t]["zdania"]:
                    lines.append(f"{code} | {i} | {en[i]} || {plx[i] if i < len(plx) and plx[i] else '(brak)'}")
        prompt = VERIFY_PROMPT.format(title=cand["tytul"], kind=cand["typ"], diff=cand["roznica"], items="\n".join(lines))
        key = hashlib.sha256(f"{VERIFY_MODEL}|{prompt}".encode()).hexdigest()[:16]
        if key in answers:
            return parse_verdict(answers[key], cand, ids, texts), 0.0
        return _ask(client_for(VERIFY_MODEL), VERIFY_MODEL, f"tv-spr-{day}", prompt, verdict_of(key, cand))

    stories, unchecked = [], []
    with ThreadPoolExecutor(WORKERS) as pool:
        for f in [pool.submit(check, c) for c in cands]:
            try:
                story, c = f.result()
            except RuntimeError as e:   # po ponowieniu: kandydat odpada, dzień i tak się zapisuje
                unchecked.append(str(e))
                continue
            cost += c
            if story:
                stories.append(story)
    vpath.write_text(json.dumps(answers, ensure_ascii=False, indent=1), encoding="utf-8")
    stories.sort(key=lambda x: -x["sila"])   # stabilnie: przy równej sile kolejność z kroku 2
    out = {"prompt": PROMPT_VERSION, "hash": digest, "kandydaci": len(cands), "historie": stories,
           "odrzucone": len(cands) - len(stories), "niesprawdzone": len(unchecked), "model": " + ".join(MODELS)}
    if not errors:
        path.write_text(json.dumps({**out, "cost_usd": round(cost, 5)}, ensure_ascii=False, indent=1), encoding="utf-8")
    return {**out, "cost_usd": cost, "errors": errors, "warnings": unchecked}
