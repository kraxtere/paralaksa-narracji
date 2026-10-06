"""Archiwum 2.0, interfejs w przeglądarce (Playwright + Chromium; bez nich testy się pomijają): kategoria jako filtr
podstawowy, filtry progresywne (liczby, ukryte opcje bez wyników), wykres, karta artykułu i link do Tłumacza Google.
Paczki syntetyczne, serwer lokalny na 127.0.0.1, bez sieci."""
import functools
import http.server
import threading
from pathlib import Path
from urllib.parse import quote

import pytest

from paralaksa.board.render import find_browser
from paralaksa.site import archive
from paralaksa.site.data import COUNTRY_NAMES

sync_api = pytest.importorskip("playwright.sync_api")
BROWSER = find_browser()
pytestmark = pytest.mark.skipif(not BROWSER, reason="brak przeglądarki Chromium")

JS = (Path(__file__).parents[1] / "src" / "paralaksa" / "site" / "assets" / "archiwum.js").read_text(encoding="utf-8")
SOURCES = {"pl1": {"name": "Polska Gazeta", "kraj": "PL"}, "ua1": {"name": "Ukr Wire", "kraj": "UA"},
           "ru1": {"name": "RU Daily", "kraj": "RU"}}
THEMES = {"ukraine_war": "Wojna w Ukrainie", "elections_politics": "Wybory i polityka"}
URL_UA = "https://ua1.example/a?x=1&y=2"


def day_packs() -> dict[str, list[list]]:
    """Rows as in `archive.records`: [source, title, Polish title, url, signals, lemmas, category, time, kind, description, origin]."""
    def bare(src, title, url, lem, cat, stamp, desc, kind="p"):          # bez sygnałów: kategoria i opis z zajawki
        return [src, title, "", url, [], lem, cat, stamp, kind, desc, "zajawka"]
    return {
        "2026-10-05": [
            bare("pl1", "Wybory w Polsce", "https://pl1.example/a", "wybory polska", "polityka", "2026-10-05T10:00Z", "Opis wyborów w Polsce."),
            bare("pl1", "Finał mistrzostw", "https://pl1.example/b", "final mistrzostwo", "sport", "2026-10-05T11:00Z", "Opis finału."),
            ["ua1", "Війна", "Wojna w Ukrainie", URL_UA, [["ukraine_war", "alarm", "RU", "rama wojny", "Streszczenie wojny."]],
             "wojna ukraina", "", "2026-10-05T12:00Z", "p", "", "analiza"],
            *[bare("pl1", f"Grenlandia {i}", f"https://pl1.example/g{i}", "grenlandia", "polityka", f"2026-10-05T0{i}:00Z", f"Opis {i}.")
              for i in (1, 2, 3)]],
        "2026-10-04": [
            ["ru1", "Выборы", "Wybory w Rosji", "https://ru1.example/a", [["elections_politics", "neutralny", "RU", "rama wyborów", "Streszczenie wyborów."]],
             "wybory rosja", "", "2026-10-04T09:00Z", "p", "", "analiza"],
            bare("ru1", "Погода", "https://ru1.example/b", "pogoda moskwa", "pogoda i środowisko", "2026-10-04T08:00Z", "Deszcz w Moskwie.", "f")],
    }


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    dest = tmp_path_factory.mktemp("archiwum")
    archive.write(dest, day_packs(), SOURCES, THEMES, "data:,", JS)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(dest)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    srv.shutdown()
    srv.server_close()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch(executable_path=BROWSER)
        yield b
        b.close()


@pytest.fixture
def open_page(browser, site):
    pages = []

    def _open(fragment="", locale="pl-PL"):
        page = browser.new_context(viewport={"width": 390, "height": 844}, locale=locale).new_page()
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.goto(site + "#okres=all" + fragment)                      # brak pasek.js (404) nie przeszkadza
        page.wait_for_selector(".wyniki li, .wyniki .pusto")
        pages.append(page)
        return page

    yield _open
    for page in pages:
        assert page.errors == []                                         # żaden wyjątek skryptu


def texts(page, selector):
    return page.eval_on_selector_all(selector, "els => els.map(e => e.textContent.trim())")


def test_category_row_is_primary_filter_with_counts(open_page):
    page = open_page()
    assert texts(page, ".kategorie button") == ["wszystkie8", "tematy analizy2", "polityka4", "pogoda i środowisko1", "sport1"]
    page.click("button[data-kat='polityka']")
    assert page.locator(".wyniki li").count() == 4 and page.inner_text(".info").startswith("4 z 8 artykułów")
    assert "kat=polityka" in page.evaluate("location.hash")
    page.click("button[data-kat='polityka']")                           # drugi klik wraca do wszystkich
    assert page.locator(".wyniki li").count() == 8


def test_filters_are_progressive_zero_options_hidden(open_page):
    page = open_page("&kraj=PL")
    assert texts(page, ".kategorie button") == ["wszystkie5", "polityka4", "sport1"]       # brak „pogoda” i „tematy analizy”
    assert texts(page, "select[data-f=kraj] option")[1:] == [f"{COUNTRY_NAMES['PL']} · 5", f"{COUNTRY_NAMES['RU']} · 2",
                                                            f"{COUNTRY_NAMES['UA']} · 1"]
    assert texts(page, "select[data-f=src] option")[1:] == ["Polska Gazeta (PL) · 5"]       # źródła tylko wybranego kraju
    page = open_page("&kat=polityka")
    assert texts(page, "select[data-f=kraj] option")[1:] == [f"{COUNTRY_NAMES['PL']} · 4"]
    assert page.is_disabled("select[data-f=th]") and page.is_disabled("select[data-f=st]")   # bez sygnałów nie ma tematów i tonów
    page = open_page("&th=ukraine_war")
    assert texts(page, "select[data-f=st] option")[1:] == ["poza neutralnym · 1", "alarm · 1"]
    assert texts(page, ".kategorie button") == ["wszystkie1", "tematy analizy1"]


def test_selected_option_stays_visible_with_zero(open_page):
    page = open_page("&kat=sport&kraj=RU")
    assert texts(page, ".kategorie button") == ["wszystkie2", "tematy analizy1", "pogoda i środowisko1", "sport0"]
    assert page.get_attribute("button[data-kat='sport']", "aria-pressed") == "true"
    assert page.input_value("select[data-f=kraj]") == "RU" and "Nic nie pasuje" in page.inner_text(".wyniki")


def test_chart_click_narrows_by_day_and_country(open_page):
    page = open_page()
    assert page.locator(".wyniki li").count() == 8 and page.locator(".wykres").is_visible()
    page.click(".wk .bc >> nth=0")                                       # słupek 04.10 (kolumny rosnąco)
    assert page.locator(".wyniki li").count() == 2 and "tylko 04.10" in page.inner_text(".info")
    page.click(".zdejmij")
    assert page.locator(".wyniki li").count() == 8 and "dz=" not in page.evaluate("location.hash")
    page.click(".wk .kr[data-kraj='PL']")                                # kod kraju, jak dotąd
    assert page.locator(".wyniki li").count() == 5
    page.click(".wk .kr[data-kraj='PL']")
    page.click(".wk .c[data-k='RU'][data-d='2026-10-04']")               # kratka: kraj i dzień naraz
    assert page.locator(".wyniki li").count() == 2
    assert "kraj=RU" in page.evaluate("location.hash") and "dz=2026-10-04" in page.evaluate("location.hash")
    page.click(".wk .c[data-k='RU'][data-d='2026-10-04']")               # drugi klik zdejmuje oba
    assert page.locator(".wyniki li").count() == 8


def test_card_title_description_meta_and_details(open_page):
    page = open_page()
    card = page.locator(".wyniki li").first                              # najnowszy: Ukr Wire 12:00 UTC
    assert card.locator(".tt a").inner_text() == "Wojna w Ukrainie" and card.locator(".tt a").get_attribute("href") == URL_UA
    assert card.locator(".opis").inner_text() == "Streszczenie wojny."   # bez prefiksu „z analizy:”, pełny
    assert "Ukr Wire" in card.locator(".meta").inner_text() and card.locator(".meta .flaga").count() == 1
    assert card.locator(".szcz").is_hidden()
    card.locator(".rozwin").click()
    details = card.locator(".szcz")
    assert details.is_visible()
    for part in ("tytuł oryginalny", "Війна", "opis: analiza", "godzina publikacji", "Wojna w Ukrainie", "ton", "alarm"):
        assert part in details.inner_text()
    assert page.locator(".wyniki li").nth(1).locator(".szcz").is_hidden()     # inne karty zostają zwinięte
    page.click("button[data-kat='sport']")                               # przerysowanie listy zachowuje rozwinięcie
    assert page.locator(".wyniki li .rozwin[aria-expanded=true]").count() == 0
    page.click("button[data-kat='sport']")
    assert page.locator(".wyniki li").first.locator(".szcz").is_visible()
    bare = page.locator(".wyniki li").filter(has_text="Finał mistrzostw")
    bare.locator(".rozwin").click()
    assert "opis: zajawka" in bare.locator(".szcz").inner_text()
    assert bare.locator(".opis").inner_text() == "Opis finału."
    page.goto(page.url.split("#")[0] + "#okres=all&kat=pogoda i środowisko")
    page.reload()
    page.wait_for_selector(".wyniki li")
    page.locator(".wyniki li .rozwin").click()
    assert "godzina pobrania" in page.locator(".wyniki li .szcz").inner_text()    # czas pobrania, nie publikacji


def test_translate_link_uses_browser_language(open_page):
    page = open_page()
    link = page.locator(".wyniki li").first.locator(".tlum")
    assert link.inner_text() == "Przetłumacz" and link.get_attribute("target") == "_blank"
    assert link.get_attribute("rel") == "noopener noreferrer"
    assert link.get_attribute("href") == f"https://translate.google.com/translate?sl=auto&tl=pl&u={quote(URL_UA, safe='')}"
    assert page.locator(".wyniki li").filter(has_text="Wybory w Polsce").locator(".tlum").count() == 0   # polski artykuł, polska przeglądarka
    page = open_page(locale="en-US")
    assert page.locator(".wyniki li").first.locator(".tlum").get_attribute("href").startswith("https://translate.google.com/translate?sl=auto&tl=en&u=")
    assert page.locator(".wyniki li").filter(has_text="Wybory w Polsce").locator(".tlum").count() == 1


def test_words_panel_follows_filters_and_rising_words_are_computed(open_page):
    page = open_page("&kat=polityka")
    page.click(".slowa summary")
    page.wait_for_selector(".ros button")
    assert texts(page, ".czeste button") == ["grenlandia3"]               # najczęstsze: tylko powtarzające się w wynikach
    assert texts(page, ".ros button") == ["grenlandia×3"] and "Rosnące 05.10" in page.inner_text(".ros")
    page = open_page("&kraj=PL")                                         # bez zawężania: słowa rosnące z paczki budowy strony
    page.click(".slowa summary")
    page.wait_for_selector(".ros button")
    assert texts(page, ".ros button") == ["grenlandia×3"]
    page.click(".ros button")                                            # klik dodaje hasło i zawęża wyniki
    assert texts(page, ".haslo") == ["grenlandia×"] and page.locator(".wyniki li").count() == 3
