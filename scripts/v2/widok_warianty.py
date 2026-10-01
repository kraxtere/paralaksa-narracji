"""Ad hoc: kilka wariantów promptu plakatu równolegle (przy blokadach moderacji), do skutku albo max N rund.
  DZIEN=2026-09-26 python scripts/v2/widok_warianty.py us_policy [rundy]
Wynik: data/widok/<dzień>/_wariant-<tema>-<id>.png (do ręcznego wyboru jako plakat-<tema>.png)."""
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).parent))
import widok_obrazkowy as w  # noqa: E402

VARIANTS = {
    "A1": w.PEOPLE_STYLE,
    "A2": ("People named in the text may appear only as simple paper-cut silhouette figures with a plain blank oval "
           "instead of a face (no eyes, no facial features at all), each recognisable by one attribute such as a "
           "hairstyle shape, a wide-brimmed hat or a clothing colour; neutral and dignified. Everyone else is a small "
           "generic stylised figure."),
    "B1": ("Do not draw any people. Named people are represented only by their attributes as objects in the scene, e.g. "
           "a wide-brimmed hat resting on a chair, an empty lectern with a flag pin, a red tie on a coat hanger, two "
           "teacups on a table, an empty press pool seat with a camera."),
    "B2": ("Do not draw any people at all. Show only places, buildings, objects, documents, flags, microphones, cameras "
           "and symbolic arrangements that convey each headline."),
}


def attempt(theme: str, key: str, prompt: str) -> bool:
    folder = w.OUT / f"_gen-{theme}-{key}"
    png = folder / "plakat.png"
    png.unlink(missing_ok=True)
    w.run_codex(folder, prompt)
    if png.exists():
        png.replace(w.OUT / f"_wariant-{theme}-{key}.png")
        return True
    return False


def main():
    theme, rounds = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3
    t = next(x for x in json.loads((w.OUT / "tematy.json").read_text(encoding="utf-8")) if x["temat"] == theme)
    cs = json.loads((w.OUT / f"plakat-{theme}.json").read_text(encoding="utf-8"))
    prompts = {}
    for key, style in VARIANTS.items():
        w.PEOPLE_STYLE = style
        prompts[key] = w.poster_prompt(t, cs)
    todo = dict(prompts)
    for r in range(1, rounds + 1):
        with ThreadPoolExecutor(len(todo)) as ex:
            res = dict(zip(todo, ex.map(lambda k: attempt(theme, k, todo[k]), todo)))
        ok = [k for k, v in res.items() if v]
        print(f"runda {r}: udane {ok or '-'}, zablokowane {[k for k, v in res.items() if not v] or '-'}", flush=True)
        if ok:
            return
    print("brak udanego wariantu")


if __name__ == "__main__":
    main()
