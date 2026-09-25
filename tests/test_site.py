import json
import re

from paralaksa.aggregate.metrics import compute_daily_metrics
from paralaksa.config import load_themes
from paralaksa.ingest.dedup import url_hash
from paralaksa.site.build import build_site
from paralaksa.site.data import event_payload, event_summary, markdown_html, report_item, standouts
from paralaksa.site.stories import build_verify_prompt, parse_candidates, parse_stories
from seed import DAY, article_with, seed_sources

CARD = """---
id: 2026-09-23-test
tytul: Zdarzenie testowe
status: kandydat
powod_odrzucenia: null
droga: od_wiadomosci
dziedzina: [polityka_zagraniczna]
forma: kilka_perspektyw
fakt:
  czas: '2026-09-23T03:00Z'
  opis: 'Coś się stało.'
  zrodlo_pierwotne: null
stan_wiedzy_zmienial_sie: false
os_czasu: []
watki:
  - {{id: w1, nazwa: 'Partnerstwo', opis: 'opis'}}
relacje:
  - id: r1
    kraj: PL
    kto: Redakcja A
    typ: prywatne
    rola: redakcja
    gatunek: wiadomosc
    link: {link}
    publikacja: '2026-09-23T06:00+02:00'
    aktualizacja: null
    porownywana_wersja: null
    archiwum: {{link: null, wykonano: null}}
    naglowek: 'Nagłówek </script> A'
    tlumaczenie: null
    zostawia_z: 'Coś.'
    watek: w1
    sprawdzil: 'człowiek 2026-09-24'
  - id: r2
    kraj: RU
    kto: Redakcja B
    rola: redakcja
    gatunek: komentarz
    link: https://b.example/x
    publikacja: null
    aktualizacja: null
    porownywana_wersja: null
    archiwum: {{link: null, wykonano: null}}
    naglowek: 'Заголовок'
    tlumaczenie: 'Nagłówek B'
    zostawia_z: null
    sprawdzil: 'Claude 2026-09-24'
kontrasty:
  - miedzy: [r1, r2]
    rodzaj: dobor_slow
    opis: 'Różnica.'
    zastrzezenia: null
jak_szukano: ['baza']
---

## Fakt
Tekst **pogrubiony** i https://example.org/x.

- [x] zrobione
- [ ] do zrobienia
"""


def _seed(conn) -> int:
    seed_sources(conn)
    aid = article_with(conn, "pl1", theme="russia", frame="Rosja zagraża", stance="alarm")
    article_with(conn, "pl2", theme="russia", frame="Rosja zagraża", stance="krytyka")
    article_with(conn, "ua1", theme="emergent:test-topic")
    compute_daily_metrics(conn, DAY)
    url = conn.execute("SELECT url FROM articles WHERE id = ?", (aid,)).fetchone()[0]
    conn.execute("UPDATE articles SET url_hash = ? WHERE id = ?", (url_hash(url), aid))  # seed ma sztuczne hashe
    return aid


def test_event_payload(tmp_path, conn):
    aid = _seed(conn)
    url = conn.execute("SELECT url FROM articles WHERE id = ?", (aid,)).fetchone()[0]
    card = tmp_path / "2026-09-23-test.md"
    card.write_text(CARD.format(link=url), encoding="utf-8")
    ev = event_payload(card, conn)
    r1, r2 = ev["relacje"]
    assert r1["watek"] == "w1" and r1["typ"] == "prywatne" and r1["czlowiek"]
    assert r1["t"] == 1790136000000  # 2026-09-23T04:00Z
    assert r1["baza"] == {"id": aid, "source_id": "pl1", "day": DAY}
    assert r2["t"] is None and r2["baza"] is None and not r2["czlowiek"]
    assert ev["watki"][0]["nazwa"] == "Partnerstwo" and ev["fakt"]["t"] is not None
    assert "<strong>pogrubiony</strong>" in ev["opis_html"] and "☑" in ev["opis_html"]


def test_event_summary_teaser(tmp_path):
    card = tmp_path / "2026-09-23-test.md"
    card.write_text(CARD.format(link="https://a.example/x"), encoding="utf-8")
    ev = event_payload(card)
    s = event_summary(ev)
    assert [z["kto"] for z in s["zapowiedz"]] == ["Redakcja A", "Redakcja B"]
    assert s["zapowiedz"][1]["naglowek"] == "Nagłówek B" and s["rodzaj"] == "dobor_slow"
    ev["kontrasty"] = []
    assert [z["kto"] for z in event_summary(ev)["zapowiedz"]] == ["Redakcja A"]  # jeden wątek: jedna relacja


def test_markdown_escapes_html():
    out = markdown_html("## Tytuł\nzwykły <script>alert(1)</script> tekst\n\n- a\n  ciąg dalszy\n- b")
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert out.startswith("<h3>Tytuł</h3>")
    assert "<li>a ciąg dalszy</li>" in out and out.count("<li>") == 2


def test_report_item_flattens_sections():
    item = report_item({"temat": "russia", "tekst": "t", "kraje": [{"kraj": "PL", "n_zrodel": 2, "rama": "r",
                        "stance": "alarm", "article_ids": [3]}], "pewnosc": {"poziom": "niski", "uzasadnienie": "u"},
                        "sygnaly_przeciwne": {"tekst": "brak", "dowody": [{"article_id": 7}]}})
    assert item["pewnosc"] == "niski" and item["uzasadnienie"] == "u"
    assert item["artykuly"] == [3, 7]
    assert ["Sygnały przeciwne", "brak"] in item["dodatki"]


def test_build_site_self_contained(tmp_path, conn):
    aid = _seed(conn)
    url = conn.execute("SELECT url FROM articles WHERE id = ?", (aid,)).fetchone()[0]
    events = tmp_path / "events"
    events.mkdir()
    (events / "2026-09-23-test.md").write_text(CARD.format(link=url), encoding="utf-8")
    (events / "README.md").write_text("# nie karta", encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / f"{DAY}.json").write_text(json.dumps({"report": {"w_skrocie": [
        {"theme_id": "russia", "tekst": "Teza.", "pewnosc": "niski", "article_ids": [aid], "dowody": []}]},
        "warnings": ["uwaga"], "semantic_review": "pending"}), encoding="utf-8")
    out = tmp_path / "site"
    res = build_site(out, events, reports, conn, {t.id: t.name_pl for t in load_themes()})

    assert res.events == ["2026-09-23-test"] and res.days == [DAY] and not res.errors
    daily = (out / "dziennik" / f"{DAY}.html").read_text(encoding="utf-8")
    event = (out / "zdarzenia" / "2026-09-23-test.html").read_text(encoding="utf-8")
    assert (out / "index.html").exists()
    for page in (daily, event):
        assert "<script src=" not in page and '<link rel="stylesheet"' not in page  # działa z file://
        assert 'content="noindex, nofollow"' in page
    assert "Nagłówek <\\/script> A" in event  # dane nie zamykają znacznika <script>
    data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', daily, re.S).group(1))
    assert {a["id"] for a in data["artykuly"]} == {aid, aid + 1, aid + 2}
    assert data["raport"][0]["pozycje"][0]["artykuly"] == [aid]
    assert data["tematy"]["russia"] == "Rosja" and data["tematy"]["emergent:test-topic"] == "nowy: test topic"
    assert data["zdarzenia"] == [{"id": "2026-09-23-test", "tytul": "Zdarzenie testowe"}]
    # bez pełnych tekstów, leadów i cytatów dowodowych
    assert "Lead." not in daily and "dowód" not in daily


def test_standouts_more_and_less():
    metrics = [
        {"theme_id": "middle_east", "country": "IL", "article_share": 0.5, "n_articles": 10, "n_sources": 2},
        {"theme_id": "middle_east", "country": "PL", "article_share": 0.05, "n_articles": 1, "n_sources": 1},
        {"theme_id": "middle_east", "country": "DE", "article_share": 0.1, "n_articles": 2, "n_sources": 1},
        {"theme_id": "ukraine_war", "country": "PL", "article_share": 0.3, "n_articles": 6, "n_sources": 2},
        {"theme_id": "ukraine_war", "country": "DE", "article_share": 0.3, "n_articles": 6, "n_sources": 2},
        {"theme_id": "emergent:x", "country": "IL", "article_share": 0.9, "n_articles": 9, "n_sources": 1},
    ]
    out = standouts(metrics, {"IL": 20, "PL": 20, "DE": 20, "CN": 5}, {"IL": 1, "PL": 2, "DE": 2})
    got = {(o["kraj"], o["temat"], o["kierunek"]) for o in out}
    assert ("IL", "middle_east", "wiecej") in got and ("IL", "ukraine_war", "mniej") in got
    assert all(o["temat"] != "emergent:x" and o["kraj"] != "CN" for o in out)   # poza taksonomią, mała próbka
    assert next(o for o in out if o["temat"] == "middle_east")["zrodla"] == 1


def test_stories_verification_moves_and_drops_articles():
    items = [{"id": i, "kraj": k, "zrodlo": "z", "tytul": f"t{i}", "streszczenie": ""}
             for i, k in [(1, "PL"), (2, "DE"), (3, "UK"), (4, "US"), (5, "PL"), (6, "CN")]]
    first = json.dumps({"historie": [
        {"tytul": "A", "opis": "a", "kraje": [{"kraj": "PL", "article_id": 1}, {"kraj": "DE", "article_id": 2}],
         "pozostale": [3, 99]},
        {"tytul": "B", "opis": "b", "kraje": [{"kraj": "US", "article_id": "#4"}, {"article_id": 1}], "pozostale": [5, 6]}]})
    cands = parse_candidates(first, items)
    assert cands[0]["ids"] == [1, 2, 3] and cands[1]["ids"] == [4, 5, 6]   # nieznane id i powtórki odpadają
    assert "#3 | UK" in build_verify_prompt(cands, items)
    verify = json.dumps({"oceny": [
        {"article_id": 1, "wydarzenie": 1, "naglowek_pl": "Nagłówek 1"}, {"article_id": 2, "wydarzenie": 1},
        {"article_id": 3, "wydarzenie": None}, {"article_id": 4, "wydarzenie": 1, "naglowek_pl": "N4"},
        {"article_id": 5, "wydarzenie": 1}, {"article_id": 6, "wydarzenie": 2}]})
    stories = parse_stories(cands, verify, items)
    assert len(stories) == 1   # B zostaje z jednym krajem
    a = stories[0]
    assert [k["kraj"] for k in a["kraje"]] == ["PL", "DE", "US"] and a["pozostale"] == [5]
    assert a["kraje"][0]["naglowek_pl"] == "Nagłówek 1" and a["kraje"][1]["naglowek_pl"] == "t2"   # brak tłumaczenia: oryginał
    assert a["odrzucone"] == [3]
