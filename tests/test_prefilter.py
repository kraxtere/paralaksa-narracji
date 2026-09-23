import pytest

from paralaksa.ingest.prefilter import is_offtopic


@pytest.mark.parametrize(
    "url,title",
    [
        ("https://www.bbc.co.uk/sport/football/123", "Late winner"),
        ("https://sport.onet.pl/pilka-nozna/abc", "Wynik meczu"),
        ("https://sportowefakty.wp.pl/x", "Mecz"),
        ("https://www.tagesschau.de/wetter/sturm", "Sturm"),
        ("https://example.com/news/1", "Horoskop na wtorek"),
        ("https://example.com/news/2", "Прогноз погоди на тиждень"),
        ("https://example.com/news/3", "Bundesliga: Bayern gewinnt"),
        ("https://example.com/news/4", "Premier League round-up"),
        ("https://wiadomosci.onet.pl/wroclaw/wroclaw-prognoza-pogody-w-dniu-23092026/x", "Wrocław. Jaka pogoda czeka nas?"),
        ("https://example.com/news/5", "Toruń - 23.09.2026. Jaka będzie pogoda w mieście?"),
    ],
)
def test_offtopic(url, title):
    assert is_offtopic(url, title)


@pytest.mark.parametrize(
    "url,title",
    [
        ("https://news.example.com/world/extreme-weather-displaces-thousands", "Extreme weather displaces thousands"),
        ("https://www.theguardian.com/world/2026/sep/23/nato", "NATO summit"),
        ("https://www.pravda.com.ua/news/2026/09/23/1/", "Україна отримала ППО"),
        ("https://www.spiegel.de/ausland/ostflanke", "Bundeswehr an der Ostflanke"),
        # ogólne słowa w tytule nie wystarczają – to artykuł polityczny
        ("https://www.bbc.co.uk/news/articles/c8r4", "How Ceuta, football and Israel are shaping Morocco's elections"),
        ("https://www.bbc.co.uk/news/articles/cpwl", "Why a Bollywood celebrity manager's death case has been reopened"),
    ],
)
def test_ontopic(url, title):
    assert not is_offtopic(url, title)


def test_offtopic_by_category_and_section():
    assert is_offtopic("https://example.com/a", "Result", categories=["Football"])
    assert is_offtopic("https://example.com/a", "Result", section="sport")
