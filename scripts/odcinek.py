"""Working draft of a vertical episode from a storyboard YAML: PNG plates, MP4 with crossfades, SRT, voice-over text.

Prototype for the pilot (not part of `plx`). Output goes to data/odcinki/<id>/ (outside git).
Usage: .venv\\Scripts\\python scripts\\odcinek.py events\\scenariusze\\<id>.odcinek.yaml [--bez-mp4]
"""
import argparse
import html
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from paralaksa.board.render import HEIGHT, WIDTH, clip_words, find_browser, screenshot
from paralaksa.events.check import load_card

FADE_S = 0.4
FPS = 30
COUNTRY = {"PL": "Polska", "UA": "Ukraina", "DE": "Niemcy", "UK": "Wielka Brytania", "EU": "Europa",
           "FR": "Francja", "AZ": "Azerbejdżan", "US": "USA", "RU": "Rosja"}
DAYS = ["pon", "wt", "śr", "czw", "pt", "sob", "nd"]

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 1080px; height: 1920px; overflow: hidden; }
body { font-family: "Segoe UI", Arial, sans-serif; color: #111; background-color: #f3ead3;
  background-image: radial-gradient(rgba(0,0,0,.12) 1.3px, transparent 1.4px); background-size: 11px 11px;
  position: relative; }
.top { position: absolute; top: 48px; left: 50px; right: 50px; display: flex; justify-content: space-between; align-items: center; }
.brand { background: #111; color: #f3ead3; font-family: "Arial Black", Impact, sans-serif; letter-spacing: .12em;
  font-size: 30px; padding: 8px 18px; transform: rotate(-1.2deg); }
.draft { font-family: "Arial Black", Impact, sans-serif; font-size: 22px; color: #b3261e; border: 4px solid #b3261e;
  padding: 4px 12px; transform: rotate(2deg); background: rgba(255,255,255,.7); }
.stage { position: absolute; top: 150px; left: 50px; right: 50px; bottom: 470px; display: flex; flex-direction: column;
  justify-content: center; gap: 34px; }
.title { font-family: "Arial Black", Impact, sans-serif; font-size: 96px; line-height: 1.02; }
.title small { display: block; font-family: "Segoe UI", Arial, sans-serif; font-size: 34px; font-weight: 700; color: #555; margin-top: 18px; }
.text { font-size: 50px; font-weight: 700; line-height: 1.22; }
.text.small { font-size: 36px; font-weight: 600; color: #333; }
.hl .text.small { margin-top: 12px; }
.note { font-size: 30px; color: #333; border-top: 4px solid #111; padding-top: 14px; }
.hl { position: relative; background: #fff; border: 6px solid #111; box-shadow: 12px 12px 0 #111; padding: 54px 34px 30px; }
.hl.small { padding: 44px 28px 20px; border-width: 5px; box-shadow: 8px 8px 0 #111; }
.hl:nth-child(odd) { transform: rotate(-.5deg); } .hl:nth-child(even) { transform: rotate(.5deg); }
.cap { position: absolute; top: -26px; left: 24px; background: #ffd23f; border: 4px solid #111;
  font-family: "Arial Black", Impact, sans-serif; font-size: 28px; padding: 2px 14px; text-transform: uppercase; }
.time { position: absolute; top: -26px; right: 24px; background: #111; color: #fff; font-weight: 800; font-size: 28px; padding: 4px 14px; }
.who { font-size: 30px; font-weight: 700; color: #555; }
.q { font-size: 58px; font-weight: 900; line-height: 1.12; margin-top: 8px; }
.hl.small .q { font-size: 34px; font-style: italic; font-weight: 600; color: #333; }
.hl.small .pl { font-size: 38px; font-weight: 800; line-height: 1.16; margin-top: 6px; }
.q.pl-only { font-style: normal; }
mark { background: #ffd23f; padding: 0 6px; box-shadow: 0 0 0 3px #111 inset; }
.halves { display: flex; gap: 26px; }
.half { flex: 1; background: #fff; border: 6px solid #111; box-shadow: 10px 10px 0 #111; padding: 30px 26px; }
.half b { display: block; font-family: "Arial Black", Impact, sans-serif; font-size: 110px; line-height: 1; }
.half span { display: block; font-size: 34px; font-weight: 700; margin-top: 14px; line-height: 1.2; }
.half.plus { transform: rotate(-1.5deg); } .half.minus { transform: rotate(1.5deg); background: #ffe3de; }
.axis { position: absolute; left: 50px; right: 50px; bottom: 300px; height: 120px; }
.axis .line { position: absolute; left: 0; right: 0; top: 60px; height: 6px; background: #111; }
.axis .tick { position: absolute; top: 48px; width: 14px; height: 30px; margin-left: -7px; background: #fff; border: 4px solid #111; border-radius: 7px; }
.axis .tick.past { background: #999; }
.axis .now { position: absolute; top: 36px; width: 34px; height: 54px; margin-left: -17px; background: #ffd23f; border: 5px solid #111; border-radius: 10px; }
.axis .label { position: absolute; top: -6px; transform: translateX(-50%); white-space: nowrap; background: #111; color: #fff;
  font-weight: 800; font-size: 28px; padding: 4px 12px; }
.axis .day { position: absolute; top: 96px; font-size: 22px; font-weight: 700; color: #444; transform: translateX(-50%); white-space: nowrap; }
.axis .mid { position: absolute; top: 40px; width: 3px; height: 46px; background: #111; opacity: .5; }
.copies { background: #fff; border: 6px solid #111; box-shadow: 12px 12px 0 #111; padding: 26px 28px; }
.copies .who { margin-bottom: 14px; }
.copy { display: flex; align-items: center; gap: 18px; padding: 12px 0; }
.copy + .copy { border-top: 3px dashed #111; }
.copy .t { background: #111; color: #fff; font-weight: 800; font-size: 26px; padding: 4px 10px; white-space: nowrap; }
.copy .v { flex: none; width: 58px; height: 58px; border: 5px solid #111; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-family: "Arial Black", Impact, sans-serif; font-size: 30px; background: #fff; }
.copy .v.B { background: #ffd23f; }
.copy .x { font-size: 27px; font-weight: 700; line-height: 1.2; }
.cal { display: flex; flex-direction: column; gap: 18px; }
.cal .row { display: flex; gap: 22px; align-items: baseline; background: #fff; border: 5px solid #111; box-shadow: 8px 8px 0 #111; padding: 16px 22px; }
.cal .row.hot { background: #ffd23f; }
.cal .d { flex: none; width: 250px; font-family: "Arial Black", Impact, sans-serif; font-size: 34px; }
.cal .e { font-size: 32px; font-weight: 700; line-height: 1.2; }
.sub { position: absolute; left: 50px; right: 50px; bottom: 60px; min-height: 200px; display: flex; align-items: center;
  background: rgba(17,17,17,.9); color: #fff; font-size: 38px; font-weight: 600; line-height: 1.28; padding: 22px 30px; }
"""


def esc(s) -> str:
    return html.escape(str(s))


def marked(text: str, needle: str | None) -> str:
    out = esc(text)
    if needle:  # całe słowa, żeby „po” nie trafiło w środek wyrazu
        out = re.sub(rf"(?<!\w){re.escape(esc(needle))}(?!\w)", lambda m: f"<mark>{m.group(0)}</mark>", out, count=1)
    return out


def block_html(b: dict) -> str:
    t = b["typ"]
    if t == "tytul":
        small = f"<small>{esc(b['maly'])}</small>" if b.get("maly") else ""
        return f"<div class='title'>{esc(b['tekst'])}{small}</div>"
    if t == "tekst":
        return f"<div class='text{' small' if b.get('maly') else ''}'>{esc(b['tekst'])}</div>"
    if t == "stopka":
        return f"<div class='note'>{esc(b['tekst'])}</div>"
    if t == "dwie_polowy":
        return (f"<div class='halves'><div class='half plus'><b>{esc(b['lewa'])}</b><span>{esc(b['lewa_opis'])}</span></div>"
                f"<div class='half minus'><b>{esc(b['prawa'])}</b><span>{esc(b['prawa_opis'])}</span></div></div>")
    if t == "naglowek":
        quote = clip_words(b["tekst"])  # cytaty maks. 15 słów
        small = " small" if b.get("maly") else ""
        head = (f"<div class='cap'>{esc(COUNTRY.get(b['kraj'], b['kraj']))}</div>"
                f"<div class='time'>{esc(b['godzina'])}</div><div class='who'>{esc(b['kto'])}</div>")
        if b.get("pl"):
            body = f"<div class='q'>{esc(quote)}</div><div class='pl'>{marked(b['pl'], b.get('podkresl'))}</div>"
            if not small:
                body = f"<div class='q'>{esc(quote)}</div><div class='text small'>{marked(b['pl'], b.get('podkresl'))}</div>"
        else:
            body = f"<div class='q pl-only'>{marked(quote, b.get('podkresl'))}</div>"
        return f"<div class='hl{small}'>{head}{body}</div>"
    if t == "kopie":  # kolejne kopie archiwum pod jednym adresem: godzina, wariant, nagłówek
        rows = "".join(
            f"<div class='copy'><div class='t'>{esc(c['godzina'])}</div><div class='v {esc(c['wariant'])}'>{esc(c['wariant'])}</div>"
            f"<div class='x'>{marked(clip_words(c['tekst']), c.get('podkresl'))}</div></div>" for c in b["kopie"])
        return f"<div class='copies'><div class='who'>{esc(b['kto'])}</div>{rows}</div>"
    if t == "kalendarium":
        rows = "".join(f"<div class='row{' hot' if w.get('wyroznij') else ''}'><div class='d'>{esc(w['data'])}</div>"
                       f"<div class='e'>{esc(w['co'])}</div></div>" for w in b["wpisy"])
        return f"<div class='cal'>{rows}</div>"
    raise ValueError(f"nieznany blok: {t}")


def axis_html(ep: dict, now: str | None, stamps: list[str]) -> str:
    start, end = (datetime.fromisoformat(ep["os"][k]) for k in ("od", "do"))
    span = (end - start).total_seconds()

    def pos(dt: datetime) -> float:
        return max(0.0, min(100.0, (dt - start).total_seconds() / span * 100))

    parts = ["<div class='line'></div>"]
    day = start.replace(hour=0, minute=0, second=0)
    while day <= end:
        nxt = day + timedelta(days=1)
        if day > start:  # kreska o północy
            parts.append(f"<div class='mid' style='left:{pos(day):.2f}%'></div>")
        center = (pos(max(day, start)) + pos(min(nxt, end))) / 2
        parts.append(f"<div class='day' style='left:{center:.2f}%'>{DAYS[day.weekday()]} {day:%d.%m}</div>")
        day = nxt
    now_dt = datetime.fromisoformat(now) if now else None
    for s in stamps:
        dt = datetime.fromisoformat(s)
        cls = "tick past" if now_dt and dt < now_dt else "tick"
        parts.append(f"<div class='{cls}' style='left:{pos(dt):.2f}%'></div>")
    if now_dt:
        p = pos(now_dt)
        parts.append(f"<div class='now' style='left:{p:.2f}%'></div>")
        label_p = min(max(p, 12), 88)
        parts.append(f"<div class='label' style='left:{label_p:.2f}%'>{DAYS[now_dt.weekday()]} {now_dt:%d.%m · %H:%M}</div>")
    return f"<div class='axis'>{''.join(parts)}</div>"


def shot_html(ep: dict, shot: dict, stamps: list[str]) -> str:
    draft = "<div class='draft'>WERSJA ROBOCZA</div>" if ep.get("wersja") == "robocza" else ""
    blocks = "".join(block_html(b) for b in shot["bloki"])
    axis = axis_html(ep, shot.get("zegar"), stamps)
    return (f"<!doctype html><html lang='pl'><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
            f"<div class='top'><div class='brand'>PARALAKSA ZDARZEŃ</div>{draft}</div>"
            f"<div class='stage'>{blocks}</div>{axis}<div class='sub'>{esc(shot.get('lektor', ''))}</div></body></html>")


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def offsets(durations: list[float]) -> list[float]:
    """Start of each shot in the video with crossfades (each fade overlaps the previous shot)."""
    out, t = [], 0.0
    for d in durations:
        out.append(t)
        t += d - FADE_S
    return out


def build_mp4(pngs: list[Path], durations: list[float], out: Path) -> None:
    ffmpeg = shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"
    args = [ffmpeg, "-y", "-loglevel", "error"]
    for png, d in zip(pngs, durations):
        args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.2f}", "-i", str(png)]
    chain, prev = [], "[0:v]"
    for i, start in enumerate(offsets(durations)[1:], start=1):
        label = f"[v{i}]"
        chain.append(f"{prev}[{i}:v]xfade=transition=fade:duration={FADE_S}:offset={start:.2f}{label}")
        prev = label
    graph = ";".join(chain) + f";{prev}format=yuv420p[out]" if chain else "[0:v]format=yuv420p[out]"
    args += ["-filter_complex", graph, "-map", "[out]", "-r", str(FPS), "-c:v", "libx264", "-crf", "20", str(out)]
    subprocess.run(args, check=True)


def description(ep: dict, card_path: Path) -> str:
    """Video description: every relation shown in the episode with link and archive copy, in order of appearance."""
    card = load_card(card_path)
    rels = {str(r.get("id")): r for r in card.get("relacje") or []}
    used = [r for s in ep["ujecia"] for b in s["bloki"] for r in ([b["rel"]] if isinstance(b.get("rel"), str) else b.get("rel") or [])]
    lines = [ep.get("tytul", ""), "", "Źródła (kolejność jak w odcinku; godziny: czas polski):"]
    for rid in dict.fromkeys(used):
        r = rels[rid]
        arch = (r.get("archiwum") or {}).get("link") or "kopia archiwalna: brak (do zrobienia)"
        lines.append(f"- {r.get('kto')}: {r.get('link')}\n  archiwum: {arch}")
    for z in ep.get("zrodla") or []:  # dokumenty spoza relacji (decyzje, raporty)
        lines.append(f"- {z['kto']}: {z['link']}")
    lines += ["", "Tłumaczenia robocze. Nagłówki cytowane w oryginale, bez oceny redakcji."]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("storyboard", type=Path)
    ap.add_argument("-o", "--out-dir", type=Path, default=Path("data/odcinki"))
    ap.add_argument("--bez-mp4", action="store_true", help="tylko plansze PNG")
    a = ap.parse_args()

    ep = yaml.safe_load(a.storyboard.read_text(encoding="utf-8"))
    shots = ep["ujecia"]
    out = a.out_dir / ep["id"]
    out.mkdir(parents=True, exist_ok=True)
    browser = find_browser()
    if not browser:
        print("Brak Chrome/Edge (ustaw PLX_BROWSER).", file=sys.stderr)
        return 1
    stamps = sorted({s["zegar"] for s in shots if s.get("zegar")}, key=datetime.fromisoformat)
    pngs, durations = [], []
    for i, shot in enumerate(shots, start=1):
        page = out / f"{i:02d}.html"
        page.write_text(shot_html(ep, shot, stamps), encoding="utf-8")
        png = out / f"{i:02d}.png"
        screenshot(page, png, browser)
        pngs.append(png)
        durations.append(float(shot["czas"]))
        print(f"plansza {i:02d}: {png}")

    starts = offsets(durations)
    srt = []
    for i, (shot, t, d) in enumerate(zip(shots, starts, durations), start=1):
        srt.append(f"{i}\n{srt_time(t)} --> {srt_time(t + d - FADE_S)}\n{shot.get('lektor', '')}\n")
    (out / "napisy.srt").write_text("\n".join(srt), encoding="utf-8")
    (out / "lektor.txt").write_text("\n\n".join(s.get("lektor", "") for s in shots) + "\n", encoding="utf-8")
    if ep.get("karta"):
        (out / "opis.txt").write_text(description(ep, Path(ep["karta"])), encoding="utf-8")
    if not a.bez_mp4:
        build_mp4(pngs, durations, out / "odcinek.mp4")
        total = starts[-1] + durations[-1]
        print(f"film: {out / 'odcinek.mp4'} ({total:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
