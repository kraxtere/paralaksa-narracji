"""Paski: jeden obrazek Codex z N poziomymi pasami w ciemnych ramkach, cięty po ramkach (wspólne dla okładki dnia,
pasków krajów na stronach tematów i „Tylko tutaj”, scripts/v2/kraje.py).

Zawsze: w obrazku żadnego tekstu; oryginał zapisany przed cięciem (obok plik .json z listą wyników, więc
`python scripts/v2/paski.py pokroj ORYGINAŁ.png` tnie ponownie bez Codex); przy niezgodnej liczbie pasków jedno
ponowienie, potem pozycja odrzucona (nic nie zapisane).
Współbieżność (run_all): do 8 procesów Codex, starty co 15 s; po pierwszym 429 4 procesy co 20 s i ponowienie.
"""

import json
import re
import shutil
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

NO_TEXT = ("ABSOLUTELY NO TEXT anywhere: no letters, numbers, captions, speech bubbles, signs, logos or flags with "
           "writing.")


def prompt(scenes: list[str], style: str = "") -> str:
    """Codex instruction for one 1024×1536 image: len(scenes) full-width strips, scene i in strip i from the top."""
    rows = "\n".join(f"Strip {i} (from the top): {scene}" for i, scene in enumerate(scenes, 1))
    return ("Use your built-in image generation tool to create ONE image from the prompt below, then copy it into the "
            "current directory as pasy.png. Do not write code or other files. Reply only with the file name.\n\nPROMPT:\n"
            "Portrait image 1024×1536 (2:3), clean flat editorial illustration, warm paper tones (#f4f0e8), dark ink, muted "
            f"palette with brick red accents (#8a3b2a). The WHOLE image is a stack of EXACTLY {len(scenes)} full-width "
            "horizontal strips of equal height, one under another. Strips are separated by thick solid uniform dark bars "
            "(#1d1b18, about 14 px), and the same thick dark border runs around the whole image. No gutters, nothing drawn "
            "across the bars, no title, no header, no footer. " + style + "\n" + rows + "\n" + NO_TEXT)


def split(items: list, max_per: int = 6) -> list[list]:
    """One image up to max_per strips, otherwise two as even as possible (first one larger)."""
    if len(items) <= max_per:
        return [items]
    half = (len(items) + 1) // 2
    return [items[:half], items[half:]]


def runs_strips(png: Path) -> list[tuple[int, int, int, int]]:
    """Pixel boxes (x0, y0, x1, y1) of the strips between thick dark horizontal bars spanning the image width."""
    from PIL import Image
    im = Image.open(png).convert("L")
    w, h = im.size
    px = im.load()

    def runs(flags):
        out, start = [], None
        for i, f in enumerate(flags + [False]):
            if f and start is None:
                start = i
            elif not f and start is not None:
                out.append((start, i - 1))
                start = None
        return out

    def longest(y):
        best = cur = 0
        for x in range(w):
            cur = cur + 1 if px[x, y] < 90 else 0
            best = max(best, cur)
        return best

    # ramka = poziomy ciemny pas przez >= 90% szerokości, gruby na >= 4 px (krawędzie w scenie są cieńsze)
    bars = [(a, b) for a, b in runs([longest(y) >= 0.9 * w for y in range(h)]) if b - a >= 3]
    bars = [(-1, -1)] + bars + [(h, h)]                       # brzegi obrazka, gdy brak ramki zewnętrznej
    boxes = []
    for (_, top), (bottom, _) in zip(bars, bars[1:]):
        y0, y1 = top + 1, bottom - 1
        if y1 - y0 < 0.06 * h:                              # wąska szczelina między ramkami albo margines
            continue
        cols = runs([sum(px[x, y] < 90 for y in range(y0, y1 + 1, 4)) >= 0.9 * len(range(y0, y1 + 1, 4))
                     for x in range(w)])
        left = [b for a, b in cols if a < 0.1 * w]
        right = [a for a, b in cols if b > 0.9 * w]
        boxes.append((left[0] + 1 if left else 0, y0, right[-1] - 1 if right else w - 1, y1))
    return boxes


def chosen_strips(png: Path, n: int) -> list[tuple[int, int, int, int]]:
    """Pixel boxes (x0, y0, x1, y1) of exactly n strips, or [] when no set of n-1 inner bars fits.

    A bar is a horizontal band 6 px to 3% of the height thick whose rows are >= 95% dark pixels of one uniform tone
    (thicker dark bands are scenery). Of all choices of n-1 bars leaving every strip >= 40% of the mean strip height,
    the one with the thickest bars (then the most even strips) wins, so dark lines inside the scenes do not change the count."""
    from itertools import combinations
    from PIL import Image, ImageStat
    im = Image.open(png).convert("L")
    w, h = im.size
    px = im.load()
    mask = im.point(lambda v: 255 if v < 90 else 0)

    def is_bar_row(y):
        if ImageStat.Stat(mask.crop((0, y, w, y + 1))).mean[0] < 0.95 * 255:
            return False
        dark = [px[x, y] for x in range(0, w, 2) if px[x, y] < 90]
        mean = sum(dark) / len(dark)
        return (sum((v - mean) ** 2 for v in dark) / len(dark)) ** 0.5 <= 20

    flags = [is_bar_row(y) for y in range(h)]
    bands, start = [], None
    for y, f in enumerate(flags + [False]):
        if f and start is None:
            start = y
        elif not f and start is not None:
            bands.append((start, y - 1))
            start = None
    thin = [(a, b) for a, b in bands if b - a + 1 <= 0.03 * h]
    top = next((b for a, b in thin if a == 0), -1)                    # ramka zewnętrzna (gdy jest)
    bottom = next((a for a, b in thin if b == h - 1), h)
    inner = [(a, b) for a, b in thin if b - a >= 5 and a > top and b < bottom]
    least, best = 0.4 * (bottom - top) / n, None
    for pick in combinations(inner, n - 1):
        edges = [(top, top), *pick, (bottom, bottom)]
        heights = [nxt[0] - prev[1] - 1 for prev, nxt in zip(edges, edges[1:])]
        if min(heights) >= least:
            weight = (sum(b - a for a, b in pick), -(max(heights) - min(heights)))   # remis: równiejsze paski
            if best is None or weight > best[0]:
                best = (weight, edges)
    if best is None:
        return []
    bars = best[1]
    boxes = []
    for (_, t), (bt, _) in zip(bars, bars[1:]):
        y0, y1 = t + 1, bt - 1
        ys = range(y0, y1 + 1, 4)
        cols = [sum(px[x, y] < 90 for y in ys) >= 0.9 * len(ys) for x in range(w)]
        left = next((x for x in range(int(0.1 * w)) if cols[x] and not cols[x + 1]), -1)
        right = next((x for x in range(w - 1, int(0.9 * w), -1) if cols[x] and not cols[x - 1]), w)
        boxes.append((left + 1, y0, right - 1, y1))
    return boxes


def detect_strips(png: Path, n: int) -> list[tuple[int, int, int, int]]:
    """Strips by all wide dark bars (runs_strips); when their count is not n or a strip is under 40% of the mean
    strip height (a scene line taken for a bar), the best choice of n-1 bars (chosen_strips)."""
    boxes = runs_strips(png)
    if len(boxes) == n and min(b[3] - b[1] for b in boxes) + 1 >= 0.4 * sum(b[3] - b[1] + 1 for b in boxes) / n:
        return boxes
    return chosen_strips(png, n)


def cut(original: Path, dest: list[Path]) -> bool:
    """Slices the saved original into len(dest) strips (webp); False and nothing written when the bars do not match."""
    from PIL import Image
    boxes = detect_strips(original, len(dest))
    if len(boxes) != len(dest):
        return False
    im = Image.open(original).convert("RGB")
    for box, path in zip(boxes, dest):
        path.parent.mkdir(parents=True, exist_ok=True)
        im.crop((box[0], box[1], box[2] + 1, box[3] + 1)).save(path, quality=85)
    return True


def make(work: Path, prompt_text: str, dest: list[Path], original: Path) -> str:
    """Generates and slices one strip image: "ok", "429", "odrzucony" (strips did not match twice) or "brak obrazka"."""
    from widok_obrazkowy import run_codex
    result = "brak obrazka"
    for _ in range(2):
        png = work / "pasy.png"
        png.unlink(missing_ok=True)
        run_codex(work, prompt_text)
        if not png.exists():
            log = (work / "codex.log").read_text(encoding="utf-8", errors="replace") if (work / "codex.log").exists() else ""
            if re.search(r"\b429\b|rate.?limit|usage limit", log, re.I):
                return "429"
            continue
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(png, original)                                  # oryginał przed cięciem
        original.with_suffix(".json").write_text(json.dumps([str(p) for p in dest], ensure_ascii=False), encoding="utf-8")
        if cut(original, dest):
            return "ok"
        result = "odrzucony"
    return result


def run_all(jobs: list[tuple[str, object]]) -> dict[str, str]:
    """Runs (label, callable -> status) jobs: up to 8 at once, starts every 15 s; after the first 429 4 at once every
    20 s, and the job that hit 429 is queued once more. Prints the count first and one summary line at the end."""
    print(f"obrazków do zrobienia: {len(jobs)}", flush=True)
    t0, state, lock = time.time(), {"width": 8, "gap": 15, "hits": 0}, threading.Lock()
    queue, running, results = [(label, fn, 0) for label, fn in jobs], [], {}

    def work(label, fn, tries):
        try:
            res = fn()
        except BaseException as e:                                   # SystemExit z limit_guard też
            res = f"błąd: {e}"
        with lock:
            if res == "429":
                state["hits"] += 1
                state["width"], state["gap"] = 4, 20
                if tries == 0:
                    queue.append((label, fn, 1))
                    return
            results[label] = res

    last = 0.0
    while True:
        running = [t for t in running if t.is_alive()]
        with lock:
            if not queue and not running:
                break
            ready = queue and len(running) < state["width"] and time.time() - last >= state["gap"]
            job = queue.pop(0) if ready else None
        if job:
            th = threading.Thread(target=work, args=job)
            th.start()
            running.append(th)
            last = time.time()
        else:
            time.sleep(1)
    bad = {k: v for k, v in results.items() if v != "ok"}
    took = int(time.time() - t0)
    print(f"zrobione {len(results) - len(bad)}, odrzucone {len(bad)}"
          + (" (" + "; ".join(f"{k}: {v}" for k, v in bad.items()) + ")" if bad else "")
          + f", 429: {state['hits']}, czas {took // 60} min {took % 60} s", flush=True)
    return results


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "pokroj":           # pokroj ORYGINAŁ.png [...]: ponowne cięcie bez Codex
        for arg in sys.argv[2:]:
            png = Path(arg)
            dest = [Path(p) for p in json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))]
            print(png.name, "ok" if cut(png, dest) else f"odrzucony ({len(dest)} pasków oczekiwanych)")
    else:
        raise SystemExit(__doc__)
