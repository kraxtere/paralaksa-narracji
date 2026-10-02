import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "v2"))
from kraje import check  # noqa: E402


def test_check_topics():
    items = [{"id": i} for i in (1, 2, 3)]
    assert check([{"tytul": "Śledztwo w sprawie uczelni", "opis": "Prasa pisze o zarzutach.", "ids": [1, 2]}], items) == []
    errors = check([{"tytul": "Jeden", "opis": "Krótki opis.", "ids": [1, 9]},
                    {"tytul": "a b c d e f g", "opis": " ".join(["słowo"] * 26), "ids": [1]}], items)
    assert any("#9 spoza" in e for e in errors) and any("#1 powtórzony" in e for e in errors)
    assert any("tytuł ma 7" in e for e in errors) and any("opis ma 26" in e for e in errors)
    assert check([{"tytul": "x", "opis": "y", "ids": [1]}] * 6, items)
