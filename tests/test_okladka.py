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
    assert f"<h1>Przegląd prasy · {day}</h1><p>Jeden dzień, wiele perspektyw</p>" in page
    heads = [w.EVENTS_HEADER, "Gdzie prasa się różni", "Jak kraj widzi siebie"]
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
    assert "14 krajów · Niżej: tematy dnia" in page
    assert 'src="okl-sprawa-1.webp"' in page and "powitanie.png" not in page and "data-theme" not in page


def test_cover_without_differences_and_self_image():
    page = okladka.cover_html({**DATA, "roznice": [], "autoobraz": None})
    assert "Gdzie prasa się różni" not in page and "Jak kraj widzi siebie" not in page and page.count('class="pp-k"') == 2


def test_styled_prompt_leads_with_common_style_and_forbids_text():
    text = paski.styled_prompt(["scene one", "scene two", "scene three"])
    body = text[text.index("PROMPT:\n") + 8:]
    assert body.startswith(w.IMAGE_STYLE) and "EXACTLY 3 full-width" in body
    assert "Strip 3 (from the top): scene three" in body and paski.NO_TEXT in body and "mascots" in body
    assert "paper tones" not in body and "#f4f0e8" not in body     # wspólna część nie narzuca palety


def test_cover_css_uses_variables_only():
    css = w.STRIPS_CSS[w.STRIPS_CSS.index(".pp-sek"):]
    assert "#" not in css.replace("var(--", "")
