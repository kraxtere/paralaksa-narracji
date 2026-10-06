"""Słowa kluczowe archiwum bez modelu: lematy z polskich tytułów i „słowa rosnące” (dziś vs średnia z poprzednich dni).
Liczone przy budowie (lematyzacja simplemma, czysty Python); przeglądarka dostaje gotowe lematy i tylko sumuje.
Tytuł bez polskiego tłumaczenia jest pomijany (nie mieszamy języków)."""
from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

import simplemma

WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
STOP = set("""
że się nie jest są był była było były będzie będą ale jak już czy tak tylko jeszcze przez przed nad pod bez dla oraz
lub także też oto kto co gdzie kiedy który która które którzy których jego jej ich mu go ją nas was wam nam mnie
tym tej ten ta to te tego temu tych tą po na do od za ze we wo przy pod między przeciw wobec około według
może mają ma mieć być miał miała mają został została zostało zostały można trzeba będzie bardzo więcej mniej
nowy nowa nowe nowych nowej pierwszy pierwsza pierwsze jeden jedna jedno dwa dwie dwóch trzy lat rok roku
dzień dni dnia po-raz raz lata roku roczny
wszystek poza podczas gdy drugi wielki wielka wielkie sprawa kraj mówi mówią powiedział powiedziała twierdzi uważa chce chcą podał podała ujawnił ujawnia
""".split())


OVERRIDE = {"niemiec": "niemcy", "niemca": "niemcy", "niemców": "niemcy", "niemcom": "niemcy", "niemcami": "niemcy",
            "niemczech": "niemcy", "niemcach": "niemcy"}      # simplemma bierze „Niemcy” za rzeczownik „Niemiec”


@lru_cache(maxsize=200_000)
def lemma(word: str) -> str:
    lem = simplemma.lemmatize(word, lang="pl").lower()
    return OVERRIDE.get(lem, OVERRIDE.get(word, lem))


CLAUSE = re.compile(r"[,.:;!?()\[\]„”\"«»—–|/]|\s-\s")


def lemmas(title: str) -> list[str]:
    """Unikalne lematy jednego tytułu (kolejność pierwszego wystąpienia), bez stoplisty i liczb, a po nich pary
    sąsiednich słów z jednego zdania/członu (donald_trump, wybory_prezydencki); stoplista zrywa sąsiedztwo."""
    singles: list[str] = []
    pairs: list[str] = []
    for part in CLAUSE.split(title.lower()):
        prev = None
        for w in WORD.findall(part):
            lem = None if w in STOP or len(w) < 3 else lemma(w)
            if lem is None or lem in STOP or len(w) < 3 or len(lem) < 3:
                prev = None
                continue
            if lem not in singles:
                singles.append(lem)
            if prev and prev != lem and f"{prev}_{lem}" not in pairs:
                pairs.append(f"{prev}_{lem}")
            prev = lem
    return singles + pairs


def rising(today: Counter, previous: list[Counter], min_today: int = 5) -> list[tuple[str, int, float, float]]:
    """Słowa rosnące: (lemat, dziś, średnia z poprzednich dni, wynik). Wynik = dziś / (średnia + 1) wygładzone
    (zapobiega skokom z 0 → 1); słowa z mniej niż `min_today` wystąpieniami dziś odpadają."""
    n = max(len(previous), 1)
    rows = []
    for w, c in today.items():
        if c < min_today:
            continue
        avg = sum(p.get(w, 0) for p in previous) / n
        rows.append((w, c, round(avg, 2), round(c / (avg + 1), 2)))
    return sorted(rows, key=lambda r: (-r[3], -r[1], r[0]))


def fixed_pairs(titles: list[list[str]], min_pair: int = 3, ratio: float = 0.7) -> dict[str, set[str]]:
    """Stałe pary (nazwy wielowyrazowe): para a_b z co najmniej `min_pair` trafieniami, w której słowo występuje
    prawie wyłącznie razem z partnerem (≥ `ratio` jego wszystkich trafień). Zwraca {para: słowa do zdjęcia}:
    Donald Trump zdejmuje „donald” (zawsze z Trumpem), ale zostawia „trump” (często samotny)."""
    single: Counter = Counter()
    pair: Counter = Counter()
    for t in titles:
        for w in t:
            (pair if "_" in w else single)[w] += 1
    out: dict[str, set[str]] = {}
    for p, n in pair.items():
        if n < min_pair:
            continue
        drop = {w for w in p.split("_") if n >= ratio * single[w]}
        if drop:
            out[p] = drop
    return out


def fold_pairs(titles: list[list[str]], pairs: dict[str, set[str]]) -> list[list[str]]:
    """Zdejmuje z każdego tytułu słowa pokryte stałą parą, która w nim występuje."""
    out = []
    for t in titles:
        gone = set().union(*(pairs[w] for w in t if w in pairs)) if any(w in pairs for w in t) else set()
        out.append([w for w in t if w not in gone])
    return out
