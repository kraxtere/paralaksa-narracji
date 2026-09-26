import json
from pathlib import Path
from types import SimpleNamespace

from paralaksa.site import titles
from seed import DAY, article_with, seed_sources

ASSETS = Path(__file__).resolve().parents[1] / "src" / "paralaksa" / "site" / "assets"


def test_parse_translations_drops_copies_and_unknown_ids():
    items = [{"id": 1, "lang": "ru", "t": "Ми-8 залетел в Польшу"}, {"id": 2, "lang": "en", "t": "Fort Trump"},
             {"id": 3, "lang": "de", "t": "Drohne über Polen"}]
    text = json.dumps({"tlumaczenia": [{"id": 1, "pl": "Mi-8  wleciał do Polski"}, {"id": "#2", "pl": "fort trump"},
                                       {"id": 3, "pl": "Dron nad Polską"}, {"id": 99, "pl": "obcy"}]})
    assert titles.parse_translations(text, items) == {1: "Mi-8 wleciał do Polski", 3: "Dron nad Polską"}


def test_title_items_skip_polish(conn):
    seed_sources(conn)
    a = article_with(conn, "pl1")
    b = article_with(conn, "ua1")
    conn.execute("UPDATE articles SET language = 'pl' WHERE id = ?", (a,))
    assert [i["id"] for i in titles.title_items(conn, {a, b})] == [b]
    assert titles.title_items(conn, set()) == []


class FakeClient:
    def __init__(self):
        self.prompts = []

    def complete(self, req):
        prompt = req.messages[0]["content"]
        self.prompts.append(prompt)
        ids = [int(line.split(" | ")[0][1:]) for line in prompt.splitlines() if line.startswith("#")]
        text = json.dumps({"tlumaczenia": [{"id": i, "pl": f"polski {i}"} for i in ids]})
        return SimpleNamespace(ok=True, text=text, cost_usd=0.01, input_tokens=1, output_tokens=1, error=None)


def test_translate_caches_and_only_adds_new(tmp_path, monkeypatch):
    monkeypatch.setattr(titles, "CHUNK", 2)
    client = FakeClient()
    items = [{"id": i, "lang": "en", "t": f"headline {i}"} for i in (1, 2, 3)]
    out = titles.translate(client, "deepseek-test", DAY, items, tmp_path)
    assert out["tytuly"] == {1: "polski 1", 2: "polski 2", 3: "polski 3"} and len(client.prompts) == 2
    assert out["translated"] == 3 and out["missing"] == 0 and out["run_cost"] == 0.02

    more = items + [{"id": 4, "lang": "en", "t": "headline 4"}]
    out = titles.translate(client, "deepseek-test", DAY, more, tmp_path)
    assert len(client.prompts) == 3 and "#4 | en | headline 4" in client.prompts[-1] and "#1 |" not in client.prompts[-1]
    assert titles.cached(tmp_path, DAY)[4] == "polski 4"
    saved = json.loads((tmp_path / f"{DAY}.json").read_text(encoding="utf-8"))
    assert saved["prompt"] == titles.PROMPT_VERSION and saved["cost_usd"] == 0.03


def test_daily_clicks_do_not_match_the_dark_mode_attribute():
    # tryb ciemny ustawia data-theme na <html>; closest("[data-theme]") łapał wtedy każde kliknięcie na stronie
    for js in ASSETS.glob("*.js"):
        text = js.read_text(encoding="utf-8")
        assert "[data-theme]" not in text and "dataset.theme" not in text.replace("documentElement.dataset.theme", ""), js.name
