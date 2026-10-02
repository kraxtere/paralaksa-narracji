import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "v2"))
import okladka  # noqa: E402
import paski  # noqa: E402
import widok_obrazkowy as w  # noqa: E402

DATA = {
    "sprawy": [{"key": "sprawa-1", "tytul": "Próba porwania samolotu", "opis": "", "kraje": ["DE", "UK", "PL"],
                "naglowki": [], "od": "2026-09-30"},
               {"key": "sprawa-2", "tytul": "Nieudana egzekucja", "opis": "", "kraje": ["US", "PL", "DE"],
                "naglowki": [], "od": None}],
    "roznice": [{"key": "roznica-1", "temat": "Działania hybrydowe", "tekst": "",
                 "strony": [{"kraj": "IL", "nastawienie": "głównie neutralnie", "rama": "Udaremniony atak"},
                            {"kraj": "TR", "nastawienie": "krytycznie", "rama": "Śledztwo bez motywu"}]}],
    "autoobraz": {"key": "obraz-kraju", "kraj": "CN", "zewn": ["UK", "DE"], "o_sobie": "", "z_zewnatrz": "",
                  "tekst_o_sobie": "Jedność narodowa.", "tekst_z_zewnatrz": "Kontrola informacji."},
    "n_krajow": 14,
}


def test_cover_html_sections_titles_flags_and_no_poster():
    """All cover texts in HTML: day title, sections, story titles, 'continued' tag, flags, two columns, footer."""
    page = okladka.cover_html(DATA)
    day = f"{w.DAY[8:10]}.{w.DAY[5:7]}"
    assert f'<h1>Co tam w prasie piszczy<span class="okl-d">{day}</span></h1><p>Jeden dzień, wiele perspektyw</p>' in page
    heads = ["Tego dnia", "Tonacje", "Autoportret"]
    assert [page.index(f'class="pp-sek">{h}<') for h in heads] == sorted(page.index(f'class="pp-sek">{h}<') for h in heads)
    assert page.count('class="pp-k"') == page.count('class="pp-obr" href=') == 4 and 'href="sprawa-1.html"' in page and 'href="obraz-kraju.html"' in page
    assert page.count('class="okl-t"') == 4                       # tytuł zawsze w tym samym miejscu: gradient u dołu pasa
    assert "<b>Próba porwania samolotu</b>" in page and "3 kraje" in page
    assert page.count("Ciąg dalszy · od 30.09") == 1
    first = page[page.index('href="sprawa-1.html"'):page.index('href="sprawa-2.html"')]
    assert first.count('class="flaga"') == 3 and 'aria-label="Niemcy"' in first
    diff = page[page.index('href="roznica-1.html"'):page.index('href="obraz-kraju.html"')]
    assert diff.count('class="pp-kol"') == 2 and "Izrael · głównie neutralnie" in diff and "Śledztwo bez motywu" in diff
    assert "Chiny o sobie" in page and "<b>Z zewnątrz</b>" in page and page.count("<p data-zwin>") == 4
    assert "Niżej: tematy dnia" not in page                       # stopka strony mówi to samo
    assert 'src="okl-sprawa-1.webp"' in page and "powitanie.png" not in page and "data-theme" not in page


def test_cover_without_differences_and_self_image():
    page = okladka.cover_html({**DATA, "roznice": [], "autoobraz": None})
    assert "Tonacje" not in page and "Autoportret" not in page and page.count('class="pp-k"') == 2


def test_strip_prompt_poster_style_without_captions():
    """Strips keep the poster's newspaper mascots and comic style; no captions, names or labels, NO_TEXT instead."""
    text = paski.prompt([okladka.scene(i, DATA) for i in okladka.items(DATA)][:3], okladka.STYLE)
    assert "folded newspaper with a face" in text and paski.NO_TEXT in text and "EXACTLY 3 full-width" in text
    assert "the Niemcy mascot (scarf black-red-gold)" in text
    assert "exactly:" not in text and "Caption" not in text and "Label" not in text
    last = okladka.scene(okladka.items(DATA)[-1], DATA)
    assert "mirror" in last and last.count("mascot (scarf") == 3


def test_cover_css_uses_variables_only():
    css = w.STRIPS_CSS[w.STRIPS_CSS.index(".pp-sek"):]
    assert "#" not in css.replace("var(--", "")


def test_country_strips_use_headlines_and_one_mascot():
    """„Czym żyją kraje”: concrete story with easter eggs from its headlines and one hidden mascot of the country."""
    import kraje
    text = kraje.strip_prompt("PL", [{"tytul": "Zarzuty w uczelni", "opis": "Opis.", "ids": [7, 8]}],
                              {"7": "Jedenaście osób z zarzutami", "9": "Inny"})
    assert "Headlines: Jedenaście osób z zarzutami." in text and "easter eggs" in text and "Inny" not in text
    assert text.count("Polska newspaper mascot") == 1 and paski.NO_TEXT in text
