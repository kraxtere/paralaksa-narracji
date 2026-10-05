from collections import Counter

from paralaksa.site.slowa import lemmas, rising


def test_lemmas_unify_inflection_and_drop_stopwords():
    got = lemmas("Rosja atakuje Ukrainę, a w Rosji i Rosję krytykują Niemcy z Niemiec")
    assert got.count("rosja") == 1 and "ukraina" in got and got.count("niemcy") == 1
    assert "nie" not in lemmas("To nie jest nowy atak") and "atak" in lemmas("To nie jest nowy atak")
    assert "donald_trump" in lemmas("Donald Trump, prezydent USA") and "trump_prezydent" not in lemmas("Donald Trump, prezydent USA")


def test_lemmas_skip_numbers_and_short_words():
    assert lemmas("W 2026 r. 15 osób na ul. X") == ["osoba"]


def test_rising_prefers_new_words_and_respects_min_today():
    today = Counter({"huragan": 8, "iran": 20, "rzadko": 2})
    prev = [Counter({"iran": 18}), Counter({"iran": 22}), Counter({"huragan": 0})]
    rows = rising(today, prev, min_today=5)
    assert [r[0] for r in rows] == ["huragan", "iran"] and all(r[0] != "rzadko" for r in rows)
    assert rows[0][1:3] == (8, 0.0)


def test_archive_rows_carry_lemmas_and_category_and_rising_words():
    from paralaksa.site import archive

    def art(i, src, pl, sig=()):
        return {"id": i, "src": src, "tytul": pl, "pl": pl, "url": f"u{i}", "pub": None, "s": list(sig)}

    payload = {"publikacja": {"publication_window_start": "2026-01-01T00:00:00+00:00"},
               "artykuly": [art(1, "a", "Huragan uderza w Meksyk"), art(2, "a", "Huragan nad Kubą"), art(3, "b", "Mecz w Lidze")]
               + [art(10 + i, "a", "Huragan zalewa wybrzeże") for i in range(4)]}
    rows = archive.records(payload, {3: "sport", 1: "pogoda"})
    assert rows[0][5].startswith("huragan") and rows[0][6] == "pogoda" and rows[2][6] == "sport"
    sources = {"a": {"name": "A", "kraj": "UA"}, "b": {"name": "B", "kraj": "PL"}}
    days = {"2026-05-02": rows, "2026-05-01": [r[:5] + ["liga", ""] for r in rows]}
    out = archive.rising_words(days, sources)
    assert out[""][0][0] == "huragan" and out["UA"][0][0] == "huragan"
