from paralaksa.gdelt import tv

RAW = """TODAY'S MEDIA TRENDSKAN11
TODAY'S
MEDIA
TRENDS
KAN11
SEPTEMBER 24, 2026
NETANYAHU DEFIES
CHARGES AT UN
DAY-AT -A-GLANCE
Prime Minister Benjamin Netanyahu spoke at the UN.
•
TODAY'S MEDIA TRENDS BY THE GDELT PROJECT
Critical Infrastructure Security
ABOUT THIS REPORT
Gemini 3 wrote this."""


def rep(code, text):
    return tv.Report(code, "", text)


def test_clean_title_and_body():
    text = tv.clean(RAW)
    assert "ABOUT THIS REPORT" not in text and "GDELT PROJECT" not in text and "•" not in text
    assert tv.title_of(text) == "NETANYAHU DEFIES CHARGES AT UN"
    assert tv.body(text).startswith("DAY-AT -A-GLANCE Prime Minister")


def test_names_come_after_lower_case_words_not_from_headings():
    names, counts = tv.vocabulary([rep("A", "Critical Infrastructure Security The strike hit the Firepoint warehouse. "
                                             "Firepoint denied it in September.")])
    assert "firepoint" in names and "infrastructure" not in names and "september" not in names
    assert counts["A"]["firepoint"] == 2


def test_trends_new_names_grouped_with_one_sentence_per_channel():
    today = {
        "RUSSIA1": rep("RUSSIA1", "Strikes destroyed the Firepoint depot in Boryspil. Trump met Xi."),
        "1TV": rep("1TV", "Strikes hit the Firepoint warehouse in Boryspil. Moscow praised the Trump summit."),
        "ESPRESO": rep("ESPRESO", "Drones hit Kyiv. Russia claims the Firepoint site in Boryspil was hit. Trump met Xi."),
        "BBCNEWS": rep("BBCNEWS", "The summit with Trump was thin."),
    }
    before = {c: rep(c, "Yesterday the Trump visit began.") for c in ("RUSSIA1", "1TV", "BBCNEWS")}
    groups = tv.trends(today, before)
    assert len(groups) == 1 and set(groups[0]["keys"]) == {"firepoint", "boryspil"}   # Trump był już wczoraj; te same zdania
    g = groups[0]
    assert g["channels"] == ["RUSSIA1", "1TV", "ESPRESO"] and g["before"] == 0
    assert g["snippets"]["ESPRESO"] == "Russia claims the Firepoint site in Boryspil was hit."
    assert tv.trends(today, before, min_channels=4) == []


def test_phrase_snippets_ignore_case_and_diacritics():
    today = {"TVPINFO": rep("TVPINFO", "An attack in Jarosław shocked Poland."),
             "RUSSIA24": rep("RUSSIA24", "Reports from Jaroslaw fuel tension."),
             "BBCNEWS": rep("BBCNEWS", "Nothing here.")}
    assert list(tv.phrase_snippets(today, "jaroslaw")) == ["TVPINFO", "RUSSIA24"]


def test_load_downloads_once_and_skips_missing(tmp_path):
    calls = []

    def fetch(url):
        calls.append(url)
        return None if "M1" in url else b"pdf"

    def parse(data):
        return RAW, ["KAN11_20260924_155500"]

    out = tv.load("2026-09-24", ["KAN11", "M1"], tmp_path, fetch, parse)
    assert list(out) == ["KAN11"] and out["KAN11"].title == "NETANYAHU DEFIES CHARGES AT UN"
    assert calls[0] == "https://data.gdeltproject.org/gdeltv5/iatv/todaysmediatrends/20260924.KAN11.pdf"
    tv.load("2026-09-24", ["KAN11"], tmp_path, fetch, parse)
    assert len(calls) == 2   # drugi raz z pamięci podręcznej
    md = tv.render("2026-09-24", out, "2026-09-23", {}, [], {"Netanyahu": {"KAN11": "x"}}, ["M1"])
    assert "brak raportu: M1" in md and "## Fraza: Netanyahu (1 kanałów)" in md and "Kan 11 (IL)" in md
