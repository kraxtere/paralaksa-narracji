"""Okładka dnia 2.0 z pasów (od 02.10, próba na 01.10): górny blok „Przegląd prasy” bez tekstu w obrazkach.

Jeden pas na pozycję: „Tego dnia”, „Tonacje” i „Autoportret” (te same dane co dawny plakat,
widok_powitanie.poster_data). Sceny i styl jak w dawnym plakacie (gazetki z szalikami, komiks), bez tytułów, podpisów i
nazw; paski.prompt (NO_TEXT), 3 pasy ~2:1 na obrazek.
Wszystkie napisy (tytuł dnia, sekcje, tytuły, flagi, kolumny krajów, stopka) w HTML: cover_html().

  DZIEN=2026-10-01 python scripts/v2/okladka.py paski   # pasy okładki (Codex, obrazki; tylko brakujące)
potem `widok_obrazkowy.py strona` składa index.html z tym blokiem zamiast plakatu powitanie.png.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from widok_obrazkowy import (DAY, FLAGS, NAMES, OUT, PASKI, PEOPLE_STYLE, esc, flag_html,  # noqa: E402
                             n_kraje)

SUBTITLE = "Jeden dzień, wiele perspektyw"
TITLE = "Co w prasie piszczy"
# nazwy sekcji okładki (decyzja właściciela 2026-10-02)
EVENTS, TONES, SELF = "Tego dnia", "Tonacje", "Autoportret"


def strip(key: str) -> Path:
    return OUT / f"okl-{key}.webp"


def items(data: dict) -> list[dict]:
    """Cover positions in page order (one strip each)."""
    out = [{"key": e["key"], "typ": "sprawa", "tytul": e["tytul"], "opis": e["opis"],
            "kraje_prasy": e["kraje"], "naglowki": e["naglowki"]} for e in data["sprawy"]]
    out += [{"key": d["key"], "typ": "roznica", "temat": d["temat"], "opis": d["tekst"]} for d in data["roznice"]]
    if data["autoobraz"]:
        si = data["autoobraz"]
        out.append({"key": si["key"], "typ": "autoobraz", "kraj": NAMES[si["kraj"]],
                    "o_sobie": si["tekst_o_sobie"], "z_zewnatrz": si["tekst_z_zewnatrz"]})
    return out


def scene(it: dict, data: dict) -> str:
    """Scene of one cover strip: the old poster panel (widok_powitanie.main) without any captions, names or labels."""
    if it["typ"] == "sprawa":
        cs = data["sprawy"][[e["key"] for e in data["sprawy"]].index(it["key"])]["kraje"][:3]
        return (f"a scene illustrating: \"{it['tytul']}\". Hidden in different places of the scene: "
                + ", ".join(mascot(c) for c in cs) + ".")
    if it["typ"] == "roznica":
        d = data["roznice"][[x["key"] for x in data["roznice"]].index(it["key"])]
        a, b = d["strony"]
        return (f"comparison on the topic \"{d['temat']}\": two small mascots facing each other, each with an expression "
                f"matching its tone. Left {mascot(a['kraj'])} ({a['nastawienie']}); right {mascot(b['kraj'])} "
                f"({b['nastawienie']}).")
    si = data["autoobraz"]
    return (f"how a country sees itself: {mascot(si['kraj'])} looking in a mirror. Next to it "
            + ", ".join(mascot(c) for c in si["zewn"]) + " looking at it from outside.")


def mascot(c: str) -> str:
    return f"the {NAMES[c]} mascot (scarf {FLAGS[c]})"


# styl dawnego plakatu powitanie.png (widok_powitanie.main): komiks, gazetki z szalikami; bez tytułów i podpisów
STYLE = ("Comic style like a newspaper front page summary. Countries appear only as small friendly cartoon mascots (a "
         "folded newspaper with a face wearing a scarf in the country's flag colours), at most 4 in a strip. Mascots stand "
         "for the PRESS of a country: like in \"Where's Wally\", place them in different spots of the scene (never in the "
         "lowest fifth) in small funny side situations: peeking from behind a wall, holding a fire hose, taking a photo, "
         "sitting on a roof or a lamp post; they never play the main roles (never police, soldiers, attackers, victims "
         "or arsonists). Show the events as they are, without softening. " + PEOPLE_STYLE + " Only the countries "
         "named as mascots in a strip may appear as mascots there. Flags, liveries, uniforms and other national markings "
         "only when they follow unambiguously from the strip; when in doubt keep them neutral. The scene fills every "
         "strip edge to edge down to the bottom bar, NO empty band; only its lowest fifth is simpler (ground, floor, road "
         "or water) because a title is overlaid there later. No forecasts or risk sections.")


def strip_jobs(data: dict) -> list[tuple[str, object]]:
    """Codex image jobs for the missing cover strips, 3 strips (~2:1) per image in page order."""
    import paski
    its = items(data)
    jobs = []
    for k, part in enumerate(its[i:i + 3] for i in range(0, len(its), 3)):
        name = f"okladka2-{'ABC'[k]}"
        if all(strip(x["key"]).exists() for x in part):
            continue
        jobs.append((name, lambda part=part, name=name: paski.make(
            OUT / f"_gen-{name}", paski.prompt([scene(x, data) for x in part], STYLE),
            [strip(x["key"]) for x in part], PASKI / f"{name}.png")))
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
    parts = [f'<header class="okl-h"><h1>{TITLE}<span class="okl-d">{DAY[8:10]}.{DAY[5:7]}</span></h1><p>{SUBTITLE}</p></header>',
             f'<h2 class="pp-sek">{EVENTS}</h2>']
    for e in data["sprawy"]:
        tag = f'<span class="pp-ciag">Ciąg dalszy · od {e["od"][8:10]}.{e["od"][5:7]}</span>' if e["od"] else ""
        parts.append(card(e["key"], f'{tag}<b>{esc(e["tytul"])}</b><span class="okl-n">{n_kraje(len(e["kraje"]))}</span>'
                          + flags(e["kraje"])))
    if data["roznice"]:
        parts.append(f'<h2 class="pp-sek">{TONES}</h2>')
        for d in data["roznice"]:
            cols = "".join(col([s["kraj"]], f'{NAMES[s["kraj"]]} · {s["nastawienie"]}', s["rama"]) for s in d["strony"])
            parts.append(card(d["key"], f'<b>{esc(d["temat"])}</b>' + flags([s["kraj"] for s in d["strony"]]),
                              f'<div class="pp-kols">{cols}</div>'))
    si = data["autoobraz"]
    if si:
        parts.append(f'<h2 class="pp-sek">{SELF}</h2>')
        cols = (col([si["kraj"]], f'{NAMES[si["kraj"]]} o sobie', si["tekst_o_sobie"])
                + col(si["zewn"], "Z zewnątrz", si["tekst_z_zewnatrz"]))
        parts.append(card(si["key"], f'<b>{esc(NAMES[si["kraj"]])}</b>' + flags([si["kraj"]] + si["zewn"]),
                          f'<div class="pp-kols">{cols}</div>'))
    return '<div class="okl pp" data-sekcja="okladka">' + "".join(parts) + "</div>"


def image_jobs() -> list[tuple[str, object]]:
    """Codex jobs of the cover strips for scripts/v2/dzien.py (only missing ones)."""
    from widok_powitanie import poster_data
    PASKI.mkdir(parents=True, exist_ok=True)
    return strip_jobs(poster_data())


def main():
    from widok_powitanie import poster_data
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    data = poster_data()
    if cmd == "paski":
        import paski
        PASKI.mkdir(parents=True, exist_ok=True)
        paski.run_all(strip_jobs(data))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
