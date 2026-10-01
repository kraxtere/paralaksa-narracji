"""Ad hoc TEST: plakat powitalny dnia (styl GDELT „Today's Media Trends”, bez prognoz) z danych produkcji.
Sprawy dnia: data/stories/<dzień>.json (historie z plx site); różnice i autoobraz: reports/<dzień>.json (synteza Sonnet).
  python scripts/v2/widok_powitanie.py   -> data/widok/<dzień>/powitanie.png (Codex)
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from widok_obrazkowy import DAY, OUT, NAMES, FLAGS, PEOPLE_STYLE, run_codex, OPISY, n_kraje, continued  # noqa: E402

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


def main():
    stories = json.loads(Path(f"data/stories/{DAY}.json").read_text(encoding="utf-8"))["historie"][:3]
    rep = json.loads(Path(f"reports/{DAY}.json").read_text(encoding="utf-8"))["report"]
    n_countries = len(json.loads(OPISY.read_text(encoding="utf-8"))["dane"])
    cont = continued()                # os_czasu.py ciag: sprawa ciągnie się od wcześniejszego dnia
    events = []
    for i, h in enumerate(stories, 1):
        cs = [k["kraj"] for k in h["kraje"]]
        c = cont.get(f"sprawa-{i}")
        tag = (f"Above the label a small brick-red tag, exactly: \"Ciąg dalszy · od {c['od'][8:10]}.{c['od'][5:7]}\". "
               if c else "")
        events.append(f"Event panel {i}: a scene illustrating: \"{h['tytul']}\". {tag}Label, exactly: \"{h['tytul']}\". Under it, "
                      f"exactly: \"{n_kraje(len(cs))}\" and a row of small round flag badges: "
                      + ", ".join(FLAGS.get(c, c) for c in cs[:8]) + ".")
    diffs = []
    for d in rep["rozbieznosci"][:2]:
        a, b = d["kraje"][:2]
        diffs.append(f"Comparison \"{THEME.get(d['temat'], d['temat'])}\": two small mascots facing each other. Left the "
                     f"{NAMES[a['kraj']]} mascot (scarf {FLAGS[a['kraj']]}) with caption exactly: \"{NAMES[a['kraj']]} "
                     f"({stance(a['stance'])}): {a['rama'].split(';')[0].strip()}\". Right the {NAMES[b['kraj']]} mascot (scarf "
                     f"{FLAGS[b['kraj']]}) with caption exactly: \"{NAMES[b['kraj']]} ({stance(b['stance'])}): "
                     f"{b['rama'].split(';')[0].strip()}\".")
    self_box = ""                     # 24.09: raport bez różnic i autoobrazu (za mało źródeł), wtedy same sprawy dnia
    for si in rep["autoobraz"][:1]:
        ext = [c for c in dict.fromkeys(e["kraj"] for e in si["dowody"]) if c != si["kraj"] and c in NAMES][:3]
        self_box = (f"Box \"Jak kraj widzi siebie\": the {NAMES[si['kraj']]} mascot (scarf {FLAGS[si['kraj']]}) looking in a mirror. "
                    f"Caption exactly: \"{NAMES[si['kraj']]} o sobie: {gist(si['jak_opisuje_siebie'])}\". Next to it "
                    + ", ".join(f"the {NAMES[c]} mascot (scarf {FLAGS[c]})" for c in ext)
                    + f" looking at it from outside, caption exactly: \"Prasa z zewnątrz ({', '.join(NAMES[c] for c in ext)}): "
                    f"{gist(si['jak_opisuja_go_inni'])}\".")
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
        "Section header, exactly: \"Sprawy dnia\" — three wide panels stacked, one per event:\n" + "\n".join(events) +
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
