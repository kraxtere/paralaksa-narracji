import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "v2"))
import widok_obrazkowy as w  # noqa: E402


def test_theme_page_summary_block_and_country_pills(monkeypatch):
    """Summary of all countries in its own block, then one anchor pill per country card, in card order."""
    t = {"temat": "x", "nazwa": "Temat", "kraje": {"DE": 0.5, "PL": 0.3, "UA": 0.2}}
    opisy = {"dane": {c: {"zrodla": []} for c in t["kraje"]}, "opisy": {}}
    cs = [{"kraj": "PL", "article_id": 1, "zrodlo": "x", "naglowek": "n"}]       # PL z plakatu idzie pierwsza
    monkeypatch.setattr(w, "article_info", lambda ids: {})
    monkeypatch.setattr(w, "theme_articles", lambda *a: [])
    monkeypatch.setattr(w, "summaries", lambda *a: {"_opis": "Opis zbiorczy."})
    monkeypatch.setattr(w, "strips_mode", lambda: True)
    page = w.theme_page(t, opisy, {}, cs)
    assert page.index('class="s">3 krajów pisało') < page.index('class="pods"') < page.index('class="kraje-nav"')
    assert "Podsumowanie wszystkich krajów</div><p>Opis zbiorczy.</p>" in page
    nav = page[page.index('class="kraje-nav"'):page.index("</nav>")]
    assert [nav.index(f'href="#kraj-{c}"') for c in ("PL", "DE", "UA")] == sorted(nav.index(f'href="#kraj-{c}"')
                                                                                for c in ("PL", "DE", "UA"))
    assert nav.count('class="flaga"') == 3 and ">Niemcy</a>" in nav
    assert all(f'<section id="kraj-{c}">' in page for c in t["kraje"])
