import json
from datetime import date

import pytest

from paralaksa.gdelt.bq import day_literal, phrase_regex, sql_string
from paralaksa.gdelt.rezonans import build_prompt, headline_items, parse_events, render, titles_sql
from paralaksa.gdelt.szukaj import hit_items, in_card, parse_checks, parse_phrases, search_sql


def test_sql_literals_are_safe():
    assert day_literal("2026-09-25") == "2026-09-25"
    with pytest.raises(ValueError):
        day_literal("2026-09-25') OR 1=1 --")
    assert sql_string("o'neil\\x") == "'o\\'neil\\\\x'"
    assert phrase_regex("L'Express (Mi-8)") == r"l.express\ \(mi\-8\)"
    assert "'o\\'neil'" in titles_sql("2026-09-25", ["o'neil"])


def test_parse_phrases_per_language_and_filters():
    text = json.dumps({"frazy": {"en": ["Fort Trump", "x"], "ru": ["Форт Трамп", "вертол & Польш", "Ми & Польш"]}})
    assert parse_phrases(text) == ["Fort Trump", "Форт Трамп", "вертол & Польш"]   # za krótkie części odpadają
    sql = search_sql(["Fort Trump", "вертол & Польш"], date(2026, 9, 21), date(2026, 9, 25))
    assert "CAST((REGEXP_CONTAINS(LOWER(t), r'fort\\ trump')) AS INT64) + CAST((REGEXP_CONTAINS(LOWER(t), r'вертол') AND" in sql
    assert "ORDER BY score DESC, DATE" in sql
    assert "TIMESTAMP('2026-09-21') AND TIMESTAMP('2026-09-25')" in sql


def test_hit_items_one_per_outlet_languages_take_turns():
    rows = [{"src": s, "lang": l, "url": f"https://{s}/{n}", "t": f"t{n}", "DATE": 20260923120000}
            for n, (s, l) in enumerate([("a.ru", "rus"), ("a.ru", "rus"), ("b.ru", "rus"), ("c.ru", "rus"), ("d.de", "deu")])]
    items = hit_items(rows)
    assert [i["src"] for i in items] == ["a.ru", "d.de", "b.ru", "c.ru"]
    assert items[0]["czas"] == "2026-09-23 12:00"


def test_parse_checks_rejects_copied_original():
    items = [{"id": 1, "lang": "rus", "src": "a.ru", "t": "Ми-8 залетел в Польшу"},
             {"id": 2, "lang": "pol", "src": "b.pl", "t": "Mi-8 nad Braniewem"},
             {"id": 3, "lang": "deu", "src": "c.de", "t": "Drohne"}]
    text = json.dumps({"oceny": [{"id": 1, "o_zdarzeniu": True, "pl": "Ми-8 залетел в  Польшу"},
                                 {"id": "#2", "o_zdarzeniu": True, "pl": "Mi-8 nad Braniewem"},
                                 {"id": 3, "o_zdarzeniu": False}]})
    found = parse_checks([text], items)
    assert [(f["id"], f["pl"]) for f in found] == [(1, ""), (2, "Mi-8 nad Braniewem")]


def test_in_card_matches_subdomains():
    domains = {"wiadomosci.onet.pl", "ria.ru"}
    assert in_card("onet.pl", domains) and in_card("www.ria.ru", domains) and not in_card("lenta.ru", domains)


def test_rezonans_groups_events_with_separate_reasons():
    stats = [{"ent": "benjamin netanyahu", "redakcje": 800, "jezyki": 23, "wczesniej": 400.0},
             {"ent": "susan sarandon", "redakcje": 260, "jezyki": 9, "wczesniej": 11.4}]
    rows = [{"ent": "benjamin netanyahu", "lang": "pol", "src": "a.pl", "url": "u1", "t": "Netanjahu  w ONZ", "DATE": 1},
            {"ent": "susan sarandon", "lang": "eng", "src": "b.com", "url": "u2", "t": "Sarandon detained", "DATE": 1},
            {"ent": "benjamin netanyahu", "lang": "eng", "src": "b.com", "url": "u2", "t": "Sarandon detained", "DATE": 1}]
    items = headline_items(rows)
    assert len(items) == 2 and items[1]["ents"] == ["susan sarandon", "benjamin netanyahu"]
    assert "## susan sarandon\n#2 | eng | b.com | Sarandon detained" in build_prompt(stats, items)
    text = json.dumps({"wydarzenia": [
        {"tytul": "Przemówienie", "opis": "o", "dziedzina": "polityka", "grupy": ["Benjamin Netanyahu"],
         "naglowki": [{"id": 1, "pl": "Netanjahu w ONZ"}, {"id": 99}]},
        {"tytul": "Protest", "opis": "p", "dziedzina": "polityka", "grupy": ["susan sarandon", "nieznana"],
         "naglowki": [{"id": 2, "pl": "Sarandon zatrzymana"}, {"id": 1}]},
        {"tytul": "Pusty", "grupy": ["susan sarandon"], "naglowki": []}]})
    events = parse_events(text, stats, items)
    assert [e["tytul"] for e in events] == ["Przemówienie", "Protest"]   # bez nagłówków: odpada
    assert [h["id"] for h in events[1]["naglowki"]] == [2]               # nagłówek tylko w jednym wydarzeniu
    assert events[1]["powody"]["grupa"] == "benjamin netanyahu" and events[1]["powody"]["wzrost"] == 2.0
    md = render({"dzien": "2026-09-25", "gb": 0.5, "cost_usd": 0.02, "wydarzenia": events, "pominiete": []})
    assert "| polski | [a.pl](u1) | Netanjahu w ONZ | Netanjahu w ONZ |" in md
