"""Ad hoc TEST: plakat powitalny dnia (styl GDELT „Today's Media Trends”, bez prognoz) z danych produkcji.
Sprawy dnia: data/stories/<dzień>.json (historie z plx site); różnice i autoobraz: reports/<dzień>.json (synteza Sonnet).
  python scripts/v2/widok_powitanie.py   -> data/widok/<dzień>/powitanie.png (Codex)
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from widok_obrazkowy import DAY, OUT, NAMES, FLAGS, PEOPLE_STYLE, run_codex, OPISY, n_kraje, continued, EVENTS_HEADER  # noqa: E402

from paralaksa.config import load_themes  # noqa: E402
THEME = {t.id: t.name_pl for t in load_themes()}   # nazwa sporu = nazwa tematu raportu


def stance(s):   # "krytyka (67%)" -> "krytycznie"
    w = s.split()[0].strip(",")
    return {"krytyka": "krytycznie", "neutralny": "głównie neutralnie", "poparcie": "z poparciem", "alarm": "alarmująco",
            "uspokojenie": "uspokajająco"}.get(w, w)


def gist(text: str, words: int = 13) -> str:
    """Short caption from a report sentence: the listing after the dash, first two items, without quotes/parentheses.
    Without a dash: drop the lead-in „Analizowane źródło X (KRAJ) przedstawia/opisuje Chiny”."""
    part = re.split(r"\s[–—-]\s", text, maxsplit=1)
    part = part[1] if len(part) > 1 else re.sub(
        r"^Analizowane źródł\w*\s.*?\b(przedstawia|przedstawiają|opisuje|opisują)\s+\S+\s+", "", part[0])
    part = re.sub(r"\([^)]*\)", "", part).replace("'", "").strip(" .")
    items = [x.strip() for x in part.split(",") if x.strip()][:2]
    out = ", ".join(items).split()
    return " ".join(out[:words]) + ("…" if len(out) > words else "")


def poster_data() -> dict:
    """Contents of the day's welcome block (old poster prompt and the HTML cover from strips, scripts/v2/okladka.py):
    three stories, up to two press differences and one self-image, exactly as the poster has written them."""
    stories = json.loads(Path(f"data/stories/{DAY}.json").read_text(encoding="utf-8"))["historie"][:3]
    rep = json.loads(Path(f"reports/{DAY}.json").read_text(encoding="utf-8"))["report"]
    cont = continued()                # os_czasu.py ciag: sprawa ciągnie się od wcześniejszego dnia
    events = [{"key": f"sprawa-{i}", "tytul": h["tytul"], "opis": h.get("opis", ""), "kraje": [k["kraj"] for k in h["kraje"]],
               "naglowki": [k.get("naglowek_pl", "") for k in h["kraje"]],
               "od": (cont.get(f"sprawa-{i}") or {}).get("od")} for i, h in enumerate(stories, 1)]
    diffs = [{"key": f"roznica-{i}", "temat": THEME.get(d["temat"], d["temat"]), "tekst": d["tekst"],
              "strony": [{"kraj": c["kraj"], "nastawienie": stance(c["stance"]), "rama": c["rama"].split(";")[0].strip()}
                         for c in d["kraje"][:2]]}
             for i, d in enumerate(rep["rozbieznosci"][:2], 1)]
    self_image = None                 # 24.09: raport bez różnic i autoobrazu (za mało źródeł), wtedy same sprawy dnia
    for si in rep["autoobraz"][:1]:
        ext = [c for c in dict.fromkeys(e["kraj"] for e in si["dowody"]) if c != si["kraj"] and c in NAMES][:3]
        self_image = {"key": "obraz-kraju", "kraj": si["kraj"], "zewn": ext, "o_sobie": gist(si["jak_opisuje_siebie"]),
                      "z_zewnatrz": gist(si["jak_opisuja_go_inni"]), "tekst_o_sobie": si["jak_opisuje_siebie"],
                      "tekst_z_zewnatrz": si["jak_opisuja_go_inni"]}
    return {"sprawy": events, "roznice": diffs, "autoobraz": self_image,
            "n_krajow": len(json.loads(OPISY.read_text(encoding="utf-8"))["dane"])}


def main():
    data = poster_data()
    n_countries = data["n_krajow"]
    events = []
    for i, e in enumerate(data["sprawy"], 1):
        tag = (f"Above the label a small brick-red tag, exactly: \"Ciąg dalszy · od {e['od'][8:10]}.{e['od'][5:7]}\". "
               if e["od"] else "")
        events.append(f"Event panel {i}: a scene illustrating: \"{e['tytul']}\". {tag}Label, exactly: \"{e['tytul']}\". Under it, "
                      f"exactly: \"{n_kraje(len(e['kraje']))}\" and a row of small round flag badges: "
                      + ", ".join(FLAGS.get(c, c) for c in e["kraje"][:8]) + ".")
    diffs = []
    for d in data["roznice"]:
        a, b = d["strony"]
        diffs.append(f"Comparison \"{d['temat']}\": two small mascots facing each other. Left the "
                     f"{NAMES[a['kraj']]} mascot (scarf {FLAGS[a['kraj']]}) with caption exactly: \"{NAMES[a['kraj']]} "
                     f"({a['nastawienie']}): {a['rama']}\". Right the {NAMES[b['kraj']]} mascot (scarf "
                     f"{FLAGS[b['kraj']]}) with caption exactly: \"{NAMES[b['kraj']]} ({b['nastawienie']}): {b['rama']}\".")
    self_box = ""
    si = data["autoobraz"]
    if si:
        ext = si["zewn"]
        self_box = (f"Box \"Jak kraj widzi siebie\": the {NAMES[si['kraj']]} mascot (scarf {FLAGS[si['kraj']]}) looking in a mirror. "
                    f"Caption exactly: \"{NAMES[si['kraj']]} o sobie: {si['o_sobie']}\". Next to it "
                    + ", ".join(f"the {NAMES[c]} mascot (scarf {FLAGS[c]})" for c in ext)
                    + f" looking at it from outside, caption exactly: \"Prasa z zewnątrz ({', '.join(NAMES[c] for c in ext)}): "
                    f"{si['z_zewnatrz']}\".")
    diff_section = ("\nSection header, exactly: \"Gdzie prasa się różni\" — "
                    + ("two side-by-side boxes" if len(diffs) > 1 else "one wide box") + ":\n" + "\n".join(diffs)) if diffs else ""
    prompt = (
        "Use your built-in image generation tool to create ONE image from the prompt below, then copy it into the current "
        "directory as powitanie.png. Do not write code or other files. Reply only with the file name.\n\nPROMPT:\n"
        "Vertical 9:16 editorial infographic poster in comic style (like a newspaper front page summary), clean flat "
        "illustration, warm paper background (#f4f0e8), dark ink, muted palette with brick red accents (#8a3b2a). Countries "
        "appear only as small friendly cartoon mascots (a folded newspaper with a face wearing a scarf in the country's flag "
        "colours). Mascots stand for the PRESS of a country: they only watch, point at or comment on events from the side; they never act IN the events (never as police, soldiers, attackers, victims or arsonists). " + PEOPLE_STYLE + " Only these countries may appear as mascots: the ones named with a scarf below; no other country (e.g. a country only mentioned in an event) gets a mascot. Big title, exactly: \"Przegląd prasy · "
        f"{DAY[8:10]}.{DAY[5:7]}\". Subtitle, exactly: \"Jeden dzień, wiele perspektyw\".\n"
        f"Section header, exactly: \"{EVENTS_HEADER}\" — three wide panels stacked, one per event:\n" + "\n".join(events) +
        diff_section + ("\n" + self_box if self_box else "") +
        f"\nFooter small text, exactly: \"{n_countries} krajów · Niżej: tematy dnia · Opis przekazu analizowanych źródeł, nie faktów · Paralaksa\". "
        "Use correct Polish diacritics. No other text anywhere. No forecasts or risk sections.")
    run_codex(OUT / "_gen-powitanie", prompt)
    (OUT / "_gen-powitanie" / "powitanie.png").replace(OUT / "powitanie.png")
    print("powitanie.png")


def edit_subtitle():
    """Edit of an existing poster: new subtitle, country count in the footer, rest untouched (old copy in _stare/)."""
    n_countries = len(json.loads(OPISY.read_text(encoding="utf-8"))["dane"])
    work = OUT / "_edit-powitanie"
    work.mkdir(parents=True, exist_ok=True)
    (OUT / "_stare").mkdir(exist_ok=True)
    old = OUT / "_stare" / "powitanie-przed-podtytulem.png"
    if not old.exists():                      # kopia, nie przeniesienie: przy nieudanej edycji strona zostaje cała
        old.write_bytes((OUT / "powitanie.png").read_bytes())
    (work / "stary.png").write_bytes(old.read_bytes())
    (work / "powitanie.png").unlink(missing_ok=True)
    prompt = (
        "Use your built-in image generation tool to EDIT the attached image (the same picture is in the current "
        "directory as stary.png). Change ONLY these two texts and keep everything else exactly as it is (layout, panels, "
        "illustrations, mascots, flags, all other text, colours, proportions, size):\n"
        "1. The subtitle directly under the big title must read exactly: \"Jeden dzień, wiele perspektyw\" (it replaces "
        "the current subtitle).\n"
        f"2. The small footer line at the very bottom must read exactly: \"{n_countries} krajów · Niżej: tematy dnia · "
        "Opis przekazu analizowanych źródeł, nie faktów · Paralaksa\".\n"
        "Use correct Polish diacritics. Save the edited image in the current directory as powitanie.png. Do not write "
        "code or other files. Reply only with the file name.")
    run_codex(work, prompt, image=work / "stary.png")
    if not (work / "powitanie.png").exists():
        raise SystemExit(f"{DAY}: edycja nie dała obrazu (zob. {work / 'codex.log'}); stary plakat w _stare/")
    (work / "powitanie.png").replace(OUT / "powitanie.png")
    print("powitanie.png (edycja)")


if __name__ == "__main__":
    edit_subtitle() if sys.argv[1:] == ["popraw"] else main()
