"""Okładka dnia 2.0 z pasów (od 02.10, próba na 01.10): górny blok „Przegląd prasy” bez tekstu w obrazkach.

Jeden pas na pozycję: sprawy dnia, „Gdzie prasa się różni” i „Jak kraj widzi siebie” (te same dane co dawny plakat,
widok_powitanie.poster_data). Opisy scen pisze Codex (model tekstowy) z danych pozycji, zapis w okladka-sceny.json
(do ręcznej poprawki przed rysowaniem); obrazki: paski.styled_prompt (wspólny IMAGE_STYLE), 3 pasy ~2:1 na obrazek.
Wszystkie napisy (tytuł dnia, sekcje, tytuły, flagi, kolumny krajów, stopka) w HTML: cover_html().

  DZIEN=2026-10-01 python scripts/v2/okladka.py sceny   # opisy scen (Codex, tekst)
  DZIEN=2026-10-01 python scripts/v2/okladka.py paski   # pasy okładki (Codex, obrazki; tylko brakujące)
potem `widok_obrazkowy.py strona` składa index.html z tym blokiem zamiast plakatu powitanie.png.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from widok_obrazkowy import (DAY, EVENTS_HEADER, NAMES, OUT, PASKI, codex_text, esc, flag_html,  # noqa: E402
                             n_kraje)
from widok_tresci import read_cache, save_cache  # noqa: E402

SCENES_FILE = OUT / "okladka-sceny.json"
SUBTITLE = "Jeden dzień, wiele perspektyw"


def strip(key: str) -> Path:
    return OUT / f"okl-{key}.webp"


def items(data: dict) -> list[dict]:
    """Cover positions in page order, each with the facts its scene may use (nothing else goes to the scene writer)."""
    out = [{"key": e["key"], "typ": "sprawa", "tytul": e["tytul"], "opis": e["opis"],
            "kraje_prasy": e["kraje"], "naglowki": e["naglowki"]} for e in data["sprawy"]]
    out += [{"key": d["key"], "typ": "roznica", "temat": d["temat"], "opis": d["tekst"]} for d in data["roznice"]]
    if data["autoobraz"]:
        si = data["autoobraz"]
        out.append({"key": si["key"], "typ": "autoobraz", "kraj": NAMES[si["kraj"]],
                    "o_sobie": si["tekst_o_sobie"], "z_zewnatrz": si["tekst_z_zewnatrz"]})
    return out


def scenes_prompt(its: list[dict]) -> str:
    return (
        "You write scene descriptions (in English) for a strip illustration of a press review cover; each item gets ONE "
        "scene. Use ONLY facts from the item data below; invent no names, places, numbers or details that are not there.\n"
        "Each scene: 2-4 sentences. Start with the time of day and colour mood (every item a different one; never two "
        "sunsets or two sunrises), then ONE main motif in the centre, then 3-5 concrete details that tie the scene to the "
        "place and the event (recognisable architecture or landscape of the named place, vehicles, services, buildings), "
        "and 2-6 people as simplified participants (officials, soldiers, passengers, journalists with cameras), never "
        "real persons' portraits, no crowds, no mascots, no speech bubbles, no text, signs or logos.\n"
        "Flags, airline liveries, uniforms and other national markings ONLY when they follow unambiguously from the item "
        "data; when in doubt keep them neutral (no flag, an aircraft in neutral white and grey). Flags never with writing.\n"
        "Violence, death and executions: show the place and the aftermath calmly (buildings, vehicles, officials), never "
        "the act, weapons in use, bodies or medical procedures.\n"
        "Items of type 'roznica' (press differ on a topic) and 'autoobraz' (how a country's press sees itself vs. "
        "foreign press): ONE scene of the topic itself, not two sides, no mirrors, no newspapers; its main motif must NOT "
        "repeat the main motif of any 'sprawa' item of the same cover (e.g. no second aircraft when a story already shows "
        "one): pick another place or object from the item data.\n"
        "The bottom fifth of each scene stays calm (plain ground, floor or road).\n"
        "Reply ONLY with a JSON object {\"<key>\": \"<scene>\", ...} with all keys. Do not write files.\n\nITEMS:\n"
        + json.dumps(its, ensure_ascii=False, indent=1))


def scenes(data: dict, write: bool = False) -> dict[str, str]:
    """Scene per cover key, cached in okladka-sceny.json (hand edits survive while the data stays the same)."""
    its = items(data)
    text = scenes_prompt(its)
    res = read_cache(SCENES_FILE, {"prompt": text}, "okladka-sceny-v1")
    if res is None and write:
        raw = codex_text(OUT / "_okladka-sceny", text)
        res = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
        if set(res) != {i["key"] for i in its}:
            raise SystemExit(f"opisy scen: klucze {sorted(res)} zamiast {[i['key'] for i in its]}")
        save_cache(SCENES_FILE, res, {"prompt": text}, "okladka-sceny-v1")
    return res or {}


def strip_jobs(data: dict) -> list[tuple[str, object]]:
    """Codex image jobs for the missing cover strips, 3 strips (~2:1) per image in page order."""
    import paski
    sc = scenes(data)
    keys = [i["key"] for i in items(data)]
    if set(keys) - set(sc):
        raise SystemExit("najpierw: okladka.py sceny")
    jobs = []
    for k, part in enumerate(keys[i:i + 3] for i in range(0, len(keys), 3)):
        name = f"okladka2-{'ABC'[k]}"
        if all(strip(x).exists() for x in part):
            continue
        jobs.append((name, lambda part=part, name=name: paski.make(
            OUT / f"_gen-{name}", paski.styled_prompt([sc[x] for x in part]), [strip(x) for x in part],
            PASKI / f"{name}.png")))
    return jobs


def ready(data: dict) -> bool:
    return all(strip(i["key"]).exists() for i in items(data))


def flags(cs: list[str]) -> str:
    return '<span class="flagi">' + "".join(flag_html(c) for c in cs) + "</span>"


def card(key: str, caption: str, cols: str = "") -> str:
    """One position: clickable strip with the caption on the bottom gradient (same place in every strip), columns under
    (outside the link: their „więcej ›” is a button, v2/pasek.js data-zwin)."""
    return (f'<div class="pp-k"><a class="pp-obr" href="{key}.html"><img src="{strip(key).name}" alt="">'
            f'<span class="okl-t">{caption}</span></a>{cols}</div>')


def col(cs: list[str], label: str, text: str) -> str:
    return f'<div class="pp-kol">{flags(cs)}<b>{esc(label)}</b><p data-zwin>{esc(text)}</p></div>'


def cover_html(data: dict) -> str:
    """The welcome block in HTML over the strips; texts exactly from poster_data()."""
    parts = [f'<header class="okl-h"><h1>Przegląd prasy · {DAY[8:10]}.{DAY[5:7]}</h1><p>{SUBTITLE}</p></header>',
             f'<h2 class="pp-sek">{esc(EVENTS_HEADER)}</h2>']
    for e in data["sprawy"]:
        tag = f'<span class="pp-ciag">Ciąg dalszy · od {e["od"][8:10]}.{e["od"][5:7]}</span>' if e["od"] else ""
        parts.append(card(e["key"], f'{tag}<b>{esc(e["tytul"])}</b><span class="okl-n">{n_kraje(len(e["kraje"]))}</span>'
                          + flags(e["kraje"])))
    if data["roznice"]:
        parts.append('<h2 class="pp-sek">Gdzie prasa się różni</h2>')
        for d in data["roznice"]:
            cols = "".join(col([s["kraj"]], f'{NAMES[s["kraj"]]} · {s["nastawienie"]}', s["rama"]) for s in d["strony"])
            parts.append(card(d["key"], f'<b>{esc(d["temat"])}</b>' + flags([s["kraj"] for s in d["strony"]]),
                              f'<div class="pp-kols">{cols}</div>'))
    si = data["autoobraz"]
    if si:
        parts.append('<h2 class="pp-sek">Jak kraj widzi siebie</h2>')
        cols = (col([si["kraj"]], f'{NAMES[si["kraj"]]} o sobie', si["tekst_o_sobie"])
                + col(si["zewn"], "Z zewnątrz", si["tekst_z_zewnatrz"]))
        parts.append(card(si["key"], f'<b>{esc(NAMES[si["kraj"]])}</b>' + flags([si["kraj"]] + si["zewn"]),
                          f'<div class="pp-kols">{cols}</div>'))
    parts.append(f'<p class="okl-s">{data["n_krajow"]} krajów · Niżej: tematy dnia · Opis przekazu analizowanych źródeł, '
                 'nie faktów · Paralaksa</p>')
    return '<div class="okl pp" data-sekcja="okladka">' + "".join(parts) + "</div>"


def main():
    from widok_powitanie import poster_data
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    data = poster_data()
    if cmd == "sceny":
        res = scenes(data, write=True)
        print(SCENES_FILE, len(res))
    elif cmd == "paski":
        import paski
        PASKI.mkdir(parents=True, exist_ok=True)
        paski.run_all(strip_jobs(data))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
