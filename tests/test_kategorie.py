import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "v2"))
import kategorie  # noqa: E402


def test_parsuj_accepts_known_categories_only():
    text = "1|sport\n2: Polityka\n3|„gospodarka”\n4|astrologia\n9|sport\nśmieci"
    assert kategorie.parsuj(text, [10, 20, 30, 40]) == {"10": "sport", "20": "polityka", "30": "gospodarka"}
