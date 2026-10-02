import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "v2"))
import paski  # noqa: E402


def strips_png(path: Path, n: int, h: int = 300) -> None:
    """Synthetic image: outer border and n-1 uniform dark bars between n equal strips."""
    from PIL import Image, ImageDraw
    im = Image.new("L", (200, h), 230)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 199, h - 1), outline=20, width=8)
    for k in range(1, n):
        y = 8 + k * (h - 16) // n
        d.rectangle((0, y - 4, 199, y + 3), fill=20)
    im.save(path)


def test_split_even_halves():
    assert paski.split(list(range(6))) == [list(range(6))]
    assert paski.split(list(range(7))) == [[0, 1, 2, 3], [4, 5, 6]]
    assert [len(p) for p in paski.split(list(range(14)))] == [7, 7]


def test_prompt_counts_strips_and_forbids_text():
    text = paski.prompt(["a", "b", "c"], "STYLE.")
    assert "EXACTLY 3 full-width" in text and "Strip 3 (from the top): c" in text
    assert "STYLE." in text and "NO TEXT" in text and "speech bubbles" in text


def test_cut_writes_strips_or_nothing(tmp_path):
    png = tmp_path / "o.png"
    strips_png(png, 3)
    dest = [tmp_path / f"p{k}.webp" for k in range(3)]
    assert paski.cut(png, dest) and all(p.exists() for p in dest)
    wrong = [tmp_path / f"q{k}.webp" for k in range(5)]
    assert not paski.cut(png, wrong) and not any(p.exists() for p in wrong)


def test_make_retries_once_then_rejects(tmp_path, monkeypatch):
    import widok_obrazkowy
    calls = []

    def fake_codex(folder, prompt_text, image=None):
        calls.append(prompt_text)
        folder.mkdir(parents=True, exist_ok=True)
        strips_png(folder / "pasy.png", 2 if len(calls) == 1 else 3)   # 1. próba: zła liczba pasków

    monkeypatch.setattr(widok_obrazkowy, "run_codex", fake_codex)
    dest = [tmp_path / f"p{k}.webp" for k in range(3)]
    original = tmp_path / "_paski" / "x.png"
    assert paski.make(tmp_path / "gen", "P", dest, original) == "ok"
    assert len(calls) == 2 and original.exists() and original.with_suffix(".json").exists()

    calls.clear()
    monkeypatch.setattr(widok_obrazkowy, "run_codex", lambda folder, p, image=None: (
        calls.append(p), folder.mkdir(parents=True, exist_ok=True), strips_png(folder / "pasy.png", 2)))
    dest4 = [tmp_path / f"r{k}.webp" for k in range(4)]
    assert paski.make(tmp_path / "gen2", "P", dest4, tmp_path / "_paski" / "y.png") == "odrzucony"
    assert len(calls) == 2 and not any(p.exists() for p in dest4)
    assert (tmp_path / "_paski" / "y.png").exists()                   # oryginał zostaje do ponownego cięcia


def test_make_reports_429(tmp_path, monkeypatch):
    import widok_obrazkowy

    def limited(folder, prompt_text, image=None):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "codex.log").write_text("ERROR: 429 Too Many Requests", encoding="utf-8")

    monkeypatch.setattr(widok_obrazkowy, "run_codex", limited)
    assert paski.make(tmp_path / "g", "P", [tmp_path / "a.webp"], tmp_path / "o.png") == "429"
