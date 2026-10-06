import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "v2"))
import kategorie  # noqa: E402


def test_parsuj_accepts_known_categories_and_descriptions():
    text = "1|sport|Mecz w Madrycie.\n2: Polityka|\n3|„gospodarka”|Ceny rosną.\n4|astrologia|x\n9|sport|y\nśmieci"
    got = kategorie.parsuj(text, [10, 20, 30, 40])
    assert got == {"10": {"k": "sport", "o": "Mecz w Madrycie."}, "20": {"k": "polityka", "o": ""},
                   "30": {"k": "gospodarka", "o": "Ceny rosną."}}


def test_parsuj_opisy_and_old_format(tmp_path):
    assert kategorie.parsuj_opisy("1|Pierwszy.\n2|\n5|poza", [7, 8]) == {"7": "Pierwszy.", "8": ""}
    f = tmp_path / "k.json"
    f.write_text('{"1": "sport", "2": {"k": "nauka", "o": "Opis."}}', encoding="utf-8")
    assert kategorie.wczytaj(f) == {"1": {"k": "sport"}, "2": {"k": "nauka", "o": "Opis."}}
