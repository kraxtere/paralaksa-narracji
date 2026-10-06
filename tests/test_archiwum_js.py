"""Archiwum 2.0 (src/paralaksa/site/assets/archiwum.js): flagi jak na stronach dnia, wiersz paczki czytany w całości."""
import json
import re
import sys
from pathlib import Path

from paralaksa.site import archive

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "v2"))
import widok_obrazkowy as w  # noqa: E402

JS = (Path(__file__).parents[1] / "src" / "paralaksa" / "site" / "assets" / "archiwum.js").read_text(encoding="utf-8")


def test_archive_flags_match_day_pages():
    flags = json.loads(re.search(r"const FLAGS = (\{.*?\});\n", JS).group(1))
    assert flags == w.FLAG_SVG                                  # kopia w JS = FLAG_SVG stron dnia (kraje-nav)


def test_archive_ui_reads_every_pack_field():
    names = re.search(r"const row = d => \(\[(.*?)\]\)", JS).group(1).split(", ")
    payload = {"publikacja": {"publication_window_start": "2026-09-22T00:00:00+00:00",
                              "publication_window_end_exclusive": "2026-09-24T00:00:00+00:00"},
               "artykuly": [{"id": 1, "src": "pl1", "kraj": "PL", "tytul": "Tytuł", "url": "https://pl1.example/1",
                             "pub": "2026-09-23T04:00:00+00:00", "s": []}]}
    assert len(names) == len(archive.records(payload)[0])     # nowe pole w paczce wymaga obsługi w interfejsie
