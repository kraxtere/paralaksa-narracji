import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "v2"))
from kraje import check, check_ciag  # noqa: E402
from paski import detect_strips, split  # noqa: E402


def test_check_topics():
    items = [{"id": i} for i in (1, 2, 3)]
    assert check([{"tytul": "Śledztwo w sprawie uczelni", "opis": " ".join(["słowo"] * 45), "ids": [1, 2]}], items) == []
    errors = check([{"tytul": "Jeden", "opis": "Krótki opis.", "ids": [1, 9]},
                    {"tytul": "a b c d e f g", "opis": " ".join(["słowo"] * 71), "ids": [1]}], items)
    assert any("#9 spoza" in e for e in errors) and any("#1 powtórzony" in e for e in errors)
    assert any("tytuł ma 7" in e for e in errors) and any("opis ma 71" in e for e in errors)
    assert any("opis ma 2 " in e for e in check([{"tytul": "x", "opis": "Krótki opis.", "ids": [3]}], items))
    assert check([{"tytul": "x", "opis": "y", "ids": [1]}] * 6, items)


def test_check_ciag():
    prev = {"2026-09-30": [{"tytul": "a"}, {"tytul": "b"}]}
    assert check_ciag([{"temat": 1, "od": "2026-09-30#2"}], 3, prev) == []
    errors = check_ciag([{"temat": 1, "od": "2026-09-29#1"}, {"temat": 2, "od": "2026-09-30#3"},
                         {"temat": 2, "od": "2026-09-30#1"}, {"temat": 4, "od": "2026-09-30#1"}], 3, prev)
    assert [e.split(":")[0] for e in errors] == ["temat 1", "temat 2", "temat 2", "temat 4"]
    assert "nie istnieje" in errors[0] and "nie ma takiego" in errors[1] and "powtórzony" in errors[2]



def test_detect_strips_ignores_dark_line_inside_strip(tmp_path):
    from PIL import Image, ImageDraw
    im = Image.new("L", (200, 300), 230)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 199, 299), outline=20, width=8)            # ramka zewnętrzna
    d.rectangle((0, 96, 199, 103), fill=20)                         # ramki między paskami (N = 3)
    d.rectangle((0, 196, 199, 203), fill=20)
    d.rectangle((60, 196, 67, 203), fill=230)                       # przedmiot przecina ramkę (4% szerokości)
    d.rectangle((0, 120, 199, 127), fill=20)                        # gruba ciemna linia w scenie paska 2
    png = tmp_path / "pasy.png"
    im.save(png)
    assert detect_strips(png, 3) == [(8, 8, 191, 95), (8, 104, 191, 195), (8, 204, 191, 291)]
    assert detect_strips(png, 5) == []                              # w oknach N = 5 brak ramki


def test_lives_title_every_country():
    import widok_obrazkowy as W
    assert W.lives_title("PL") == "Czym żyje Polska" and W.lives_title("DE") == "Czym żyją Niemcy"
    assert W.lives_title("TR") == "Czym żyje Turcja" and set(W.LIVES) == set(W.NAMES)
