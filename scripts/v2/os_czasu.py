"""Ad hoc PROTOTYP (2026-10-01): ciągła oś wydarzeń przez wszystkie dni, dopisywana dzień po dniu, z przeskakiwaniem dni
i filtrem wątków (zastępuje osobne tygodnie z data/os_tygodnia.py).

Dane: Sprawy dnia z data/stories/<dzień>.json (plx site), godziny publikacji z data/prod.db (tylko do odczytu).
Godzina na osi = najwcześniejszy pokazany nagłówek w analizowanych źródłach, nie godzina samego zdarzenia.
  python scripts/v2/os_czasu.py z-tygodnia 2026-09-30   # jednorazowo: start z planu i kadrów tygodnia 24–30.09
  python scripts/v2/os_czasu.py dzien 2026-10-01        # Codex (tekst): Sprawy nowego dnia -> nowe zdarzenia / dalszy ciąg
  python scripts/v2/os_czasu.py pominiete               # jednorazowo: sprawy pominięte przed 01.10 też na oś
  python scripts/v2/os_czasu.py opisy                   # Codex (tekst): 2–3 zdania pod nagłówkiem karty (nowe i rozszerzone)
  python scripts/v2/os_czasu.py obrazki                 # Codex (obraz): kadr bez tekstu dla zdarzeń bez obrazka
  python scripts/v2/os_czasu.py strona                  # index.html + skrot.json (wejście z paska stron dnia)
Wynik: data/widok/os/ (plx site kopiuje do v2/os/ i v2/os.json).
"""
import html
import json
import re
import shutil
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from widok_obrazkowy import FAVICON, NAMES, PEOPLE_STYLE, run_codex, src_name  # noqa: E402

from paralaksa.extract.llm_client import LLMRequest, build_client  # noqa: E402

OUT = Path("data/widok/os")
PLAN = OUT / "plan.json"
TEXT_MODEL = "codex:gpt-6.1-sol:medium"
WAW = ZoneInfo("Europe/Warsaw")
DAY_NAMES = ["pon.", "wt.", "śr.", "czw.", "pt.", "sob.", "niedz."]
STYLE = ("Square 1:1 editorial comic panel, clean flat illustration, warm paper background (#f4f0e8), dark ink outlines, "
         "muted palette with brick red accents (#8a3b2a), calm and neutral, no gore. Officials, diplomats and politicians "
         "wear ordinary business suits unless the scene names other clothing; no religious or ethnic stereotypes. ")


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def day_stories(day: str) -> dict[str, dict]:
    path = Path(f"data/stories/{day}.json")
    if not path.exists():
        raise SystemExit(f"brak {path}: najpierw plx site dla tego dnia (Sprawy dnia)")
    return {f"{day}#{n}": {**h, "dzien": day, "n": n}
            for n, h in enumerate(json.loads(path.read_text(encoding="utf-8"))["historie"], 1)}


def all_stories(days: list[str]) -> dict[str, dict]:
    out = {}
    for d in days:
        out.update(day_stories(d))
    return out


def load() -> dict:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def save(plan: dict) -> None:
    plan["dni"] = sorted(set(plan["dni"]))
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


def from_week(end: str) -> None:
    """Start of the continuous axis from the week prototype (plan and pictures kept, numbers kept)."""
    week = Path("data/widok/tydzien") / end
    src = json.loads((week / "plan.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    events = [{**e, "nr": i} for i, e in enumerate(src["zdarzenia"], 1)]
    for e in events:
        if (week / f"ev-{e['nr']}.png").exists():
            shutil.copy2(week / f"ev-{e['nr']}.png", OUT / f"ev-{e['nr']}.png")
    save({"model": src["model"], "dni": src["dni"], "watki": src["watki"], "zdarzenia": events,
          "pominiete": sorted(set(all_stories(src["dni"])) - {s for e in events for s in e["historie"]})})
    print(f"oś: {len(events)} zdarzeń z tygodnia do {end}")


def day_prompt(plan: dict, new: dict[str, dict]) -> str:
    st = all_stories(plan["dni"])
    events = "\n".join(f"#{e['nr']} | {st[e['historie'][0]]['dzien'][8:10]}.{st[e['historie'][0]]['dzien'][5:7]} | "
                       f"wątek: {e['watek'] or '-'} | {e['tytul']}" for e in plan["zdarzenia"])
    threads = "\n".join(f"{w['id']}: {w['nazwa']}" for w in plan["watki"]) or "(brak)"
    stories = "\n".join(f"[{sid}] {len(s['kraje'])} krajów | {s['tytul']} — {s['opis']}" for sid, s in new.items())
    return (
        "Prowadzimy oś wydarzeń z przeglądu prasy: najważniejsze sprawy dzień po dniu, połączone w wątki. Dochodzą "
        "„Sprawy dnia” z kolejnego dnia (wydarzenia opisywane jednocześnie przez redakcje z co najmniej 3 krajów). "
        "Dla KAŻDEJ nowej sprawy zdecyduj:\n"
        "- \"nowe\": nowe zdarzenie na osi. Każda sprawa trafia na oś (wszystkie są opisywane w kilku krajach), "
        "więc jeśli nie jest dalszym ciągiem, to jest nowym zdarzeniem.\n"
        "- \"dalszy_ciag\": ta sama rzecz co istniejące zdarzenie, bez nowego rozwoju (np. kolejny dzień tej samej wizyty) "
        "-> podaj \"zdarzenie\": numer. Nowy rozwój tej samej sprawy (np. propozycja, potem odrzucenie) to \"nowe\" "
        "w tym samym wątku.\n"
        "Dla \"nowe\": \"tytul\" do 8 słów po polsku, co się stało, neutralnie, sprawy sporne przypisane stronie "
        "(„Estonia oskarża Rosję…”); \"watek\": id istniejącego wątku, nowego wątku albo null; \"scena\": jedno zdanie po "
        "angielsku, co narysować (miejsce, ludzie, przedmioty), bez napisów, liter, liczb i logo; prawdziwe osoby jako "
        "uproszczone postacie z prawdziwymi atrybutami (strój, wygląd), bez stereotypów wobec osób nieznanych.\n"
        "Nowy wątek (\"nowe_watki\": id małymi literami z myślnikami, nazwa do 4 słów) tylko wtedy, gdy łączy co najmniej "
        "dwa zdarzenia; do istniejących zdarzeń możesz go przypisać w \"przypisz\".\n"
        "Nie wymyślaj zdarzeń spoza listy. Zwróć wyłącznie JSON:\n"
        '{"nowe_watki":[{"id":"...","nazwa":"..."}],"przypisz":[{"zdarzenie":3,"watek":"..."}],'
        '"decyzje":[{"historia":"2026-10-01#1","typ":"nowe","tytul":"...","watek":null,"scena":"..."},'
        '{"historia":"2026-10-01#2","typ":"dalszy_ciag","zdarzenie":5}]}\n\n'
        f"WĄTKI:\n{threads}\n\nZDARZENIA NA OSI:\n{events}\n\nNOWE SPRAWY:\n{stories}")


def validate(plan: dict, new: dict[str, dict], ans: dict) -> list[str]:
    errors = []
    threads = {w["id"] for w in plan["watki"]} | {w.get("id") for w in ans.get("nowe_watki", [])}
    nrs = {e["nr"] for e in plan["zdarzenia"]}
    seen = [d.get("historia") for d in ans.get("decyzje", [])]
    errors += [f"brak decyzji dla {s}" for s in new if s not in seen]
    errors += [f"nieznana sprawa {s}" for s in seen if s not in new]
    errors += [f"sprawa {s} dwa razy" for s in set(seen) if seen.count(s) > 1]
    n_new = 0
    for d in ans.get("decyzje", []):
        if d.get("typ") == "nowe":
            n_new += 1
            if not d.get("tytul") or len(d["tytul"].split()) > 10:
                errors.append(f"{d.get('historia')}: tytuł pusty albo dłuższy niż 10 słów")
            if d.get("watek") not in threads | {None}:
                errors.append(f"{d.get('historia')}: nieznany wątek {d.get('watek')}")
            if not d.get("scena") or re.search(r"[\"„”]", d["scena"]):
                errors.append(f"{d.get('historia')}: brak sceny albo cudzysłów w scenie (napis na obrazie)")
        elif d.get("typ") == "dalszy_ciag":
            if d.get("zdarzenie") not in nrs:
                errors.append(f"{d.get('historia')}: dalszy ciąg nieznanego zdarzenia {d.get('zdarzenie')}")
        else:
            errors.append(f"{d.get('historia')}: nieznany typ {d.get('typ')}")
    for p in ans.get("przypisz", []):
        if p.get("zdarzenie") not in nrs or p.get("watek") not in threads:
            errors.append(f"przypisanie {p}: nieznane zdarzenie albo wątek")
    return errors


def add_day(day: str) -> None:
    plan = load()
    if day in plan["dni"]:
        raise SystemExit(f"{day} już jest na osi")
    plan["dni"].append(day)
    decide(plan, day_stories(day), day)


def add_skipped() -> None:
    """Once: stories skipped before 2026-10-01 (then 1–4 new events a day) go onto the axis as well."""
    plan = load()
    st = all_stories(plan["dni"])
    todo = {s: st[s] for s in sorted(plan.pop("pominiete", []))}
    if todo:
        decide(plan, todo, "pominiete")


def decide(plan: dict, new: dict[str, dict], label: str) -> None:
    client = build_client(TEXT_MODEL, None, 1, 1)
    messages = [{"role": "user", "content": day_prompt(plan, new)}]
    for _ in range(2):
        res = client.complete(LLMRequest(custom_id=f"os-{label}", model=TEXT_MODEL, max_tokens=8000, messages=messages))
        if not res.ok:
            raise SystemExit(res.error)
        try:
            ans = json.loads(res.text[res.text.find("{"): res.text.rfind("}") + 1])
            errors = validate(plan, new, ans)
        except json.JSONDecodeError as e:
            ans, errors = None, [f"niepoprawny JSON: {e}"]
        if not errors:
            break
        print("błędy:", errors)
        messages += [{"role": "assistant", "content": res.text},
                     {"role": "user", "content": "Popraw te błędy i zwróć cały JSON jeszcze raz:\n" + "\n".join(errors)}]
    else:
        raise SystemExit(f"{label}: odpowiedź nie przeszła kontroli po ponowieniu")
    plan["watki"] += [{"id": w["id"], "nazwa": w["nazwa"]} for w in ans.get("nowe_watki", [])]
    by_nr = {e["nr"]: e for e in plan["zdarzenia"]}
    for p in ans.get("przypisz", []):
        by_nr[p["zdarzenie"]]["watek"] = p["watek"]
    nr = max(by_nr, default=0)
    for d in ans["decyzje"]:
        if d["typ"] == "nowe":
            nr += 1
            plan["zdarzenia"].append({"nr": nr, "historie": [d["historia"]], "tytul": d["tytul"], "watek": d["watek"],
                                      "scena": d["scena"]})
        else:
            by_nr[d["zdarzenie"]]["historie"].append(d["historia"])
    save(plan)
    for d in ans["decyzje"]:
        print(d["historia"], d["typ"], d.get("tytul") or d.get("zdarzenie") or "", f"[{d.get('watek') or ''}]")


def first_seen(ids: list[int]) -> dict[int, tuple[str, str, str]]:
    conn = sqlite3.connect("file:data/prod.db?mode=ro", uri=True)
    q = f"SELECT id, published_at, source_id, url FROM articles WHERE id IN ({','.join(map(str, ids))})"
    return {r[0]: r[1:] for r in conn.execute(q)}


def events(plan: dict) -> list[dict]:
    """Plan + data: time of the earliest shown headline, countries and headlines of all merged stories."""
    st = all_stories(plan["dni"])
    seen = first_seen([k["article_id"] for s in st.values() for k in s["kraje"]])
    out = []
    for ev in plan["zdarzenia"]:
        heads, countries = [], []
        for sid in ev["historie"]:
            for k in st[sid]["kraje"]:
                if k["article_id"] in seen:
                    pub, src, url = seen[k["article_id"]]
                    heads.append({"kraj": k["kraj"], "naglowek": k.get("naglowek_pl", ""), "zrodlo": src, "url": url,
                                  "czas": datetime.fromisoformat(pub).astimezone(WAW), "dzien": st[sid]["dzien"]})
                    if k["kraj"] not in countries:
                        countries.append(k["kraj"])
        heads.sort(key=lambda h: h["czas"])
        page = next((f"../{st[s]['dzien']}/sprawa-{st[s]['n']}.html" for s in ev["historie"]
                     if st[s]["n"] <= 3 and (Path("data/widok") / st[s]["dzien"] / f"sprawa-{st[s]['n']}.html").exists()), "")
        out.append({**ev, "czas": heads[0]["czas"], "naglowki": heads, "kraje": countries, "strona": page,
                    "dni": sorted({h["dzien"] for h in heads})})
    out.sort(key=lambda e: e["czas"])
    return out


def describe() -> None:
    """2–3 sentences per event from the stories and headlines of all its days; again when the event got new days."""
    plan = load()
    st = all_stories(plan["dni"])
    todo = [e for e in plan["zdarzenia"] if e.get("opis_z") != e["historie"]]
    if not todo:
        return
    blocks = []
    for e in todo:
        lines = [f"- {st[s]['dzien'][8:10]}.{st[s]['dzien'][5:7]}: {st[s]['opis']} | nagłówki: "
                 + "; ".join(f"{k['kraj']}: {k.get('naglowek_pl', '')}" for k in st[s]["kraje"]) for s in e["historie"]]
        blocks.append(f"#{e['nr']} {e['tytul']}\n" + "\n".join(lines))
    prompt = (
        "Oś wydarzeń z przeglądu prasy. Dla każdego zdarzenia napisz po polsku 2–3 krótkie zdania (razem 25–60 słów) "
        "pod nagłówkiem karty: co się stało i, jeśli zdarzenie trwa kilka dni, jak się rozwijało. Opieraj się wyłącznie "
        "na podanych opisach i nagłówkach, bez wiedzy spoza nich, bez ocen i prognoz. Sprawy sporne przypisz stronie "
        "(„według Iranu…”, „policja podała…”). Nie powtarzaj tytułu słowo w słowo, nie wymieniaj redakcji ani krajów "
        "redakcji (są na karcie). Nie podawaj dat dziennych (daty przy opisach to dni przeglądu, nie zdarzeń); kolejność oddaj słowami („potem”, „następnie”). Liczby ofiar, uczestników i strat przypisz źródłu („według doniesień”, „władze podały”). Zwróć wyłącznie JSON: {\"opisy\":[{\"nr\":1,\"opis\":\"...\"}]}\n\n"
        + "\n\n".join(blocks))
    client = build_client(TEXT_MODEL, None, 1, 1)
    want = {e["nr"] for e in todo}
    messages = [{"role": "user", "content": prompt}]
    for _ in range(2):
        res = client.complete(LLMRequest(custom_id="os-opisy", model=TEXT_MODEL, max_tokens=16000, messages=messages))
        if not res.ok:
            raise SystemExit(res.error)
        try:
            got = {d["nr"]: d["opis"].strip() for d in
                   json.loads(res.text[res.text.find("{"): res.text.rfind("}") + 1])["opisy"]}
            errors = [f"brak opisu #{n}" for n in want - set(got)]
            errors += [f"#{n}: {len(t.split())} słów, ma być 25–60" for n, t in got.items()
                       if n in want and not 20 <= len(t.split()) <= 70]
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
            got, errors = {}, [f"niepoprawny JSON: {e}"]
        if not errors:
            break
        print("błędy:", errors)
        messages += [{"role": "assistant", "content": res.text},
                     {"role": "user", "content": "Popraw te błędy i zwróć cały JSON jeszcze raz:\n" + "\n".join(errors)}]
    else:
        raise SystemExit("opisy: odpowiedź nie przeszła kontroli po ponowieniu")
    for e in todo:
        e["opis"], e["opis_z"] = got[e["nr"]], list(e["historie"])
    save(plan)
    print(f"opisy: {len(todo)}")


def image_prompt(ev: dict) -> str:
    return ("Use your built-in image generation tool to create ONE image from the prompt below, then copy it into the "
            "current directory as kadr.png. Do not write code or other files. Reply only with the file name.\n\nPROMPT:\n"
            + STYLE + PEOPLE_STYLE + " Scene: " + ev["scena"] + " Absolutely no text, letters, numbers, captions, "
            "signs, logos or flags with writing anywhere in the image.")


def images() -> None:
    todo = [e for e in load()["zdarzenia"] if not (OUT / f"ev-{e['nr']}.png").exists()]

    def one(ev):
        work = OUT / f"_gen-{ev['nr']}"
        run_codex(work, image_prompt(ev))
        if (work / "kadr.png").exists():
            (work / "kadr.png").replace(OUT / f"ev-{ev['nr']}.png")
            return f"ev-{ev['nr']}.png"
        return f"ev-{ev['nr']}: BRAK (zob. {work / 'codex.log'})"

    with ThreadPoolExecutor(6) as ex:
        for line in ex.map(one, todo):
            print(line, flush=True)


CSS = """
body{margin:0;background:#f4f0e8;color:#1d1b18;font-family:Segoe UI,sans-serif}
.head{max-width:720px;margin:auto;padding:18px 16px 2px}.head h1{margin:0;color:#8a3b2a;font-size:1.6em}
.head p{margin:6px 0 0;color:#7a746a;font-size:.9em;line-height:1.4}
.wybor-dni{position:sticky;top:0;z-index:2;background:#f4f0e8;border-bottom:1px solid #e3dccf;margin-top:10px}
.wybor-dni .in{display:flex;align-items:center;gap:6px;max-width:720px;margin:auto;padding:8px 10px}
.wybor-dni .lista{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;flex:1;scroll-behavior:smooth}
.wybor-dni .lista::-webkit-scrollbar,.filtry::-webkit-scrollbar{display:none}
.dzien{flex:none;font:inherit;font-size:.85em;line-height:1.15;padding:5px 9px;border-radius:9px;border:1px solid #cfc6b6;
 background:#fbf8f2;color:#1d1b18;cursor:pointer;text-align:center}.dzien small{display:block;color:#7a746a;font-size:.8em}
.dzien.on{background:#1d1b18;border-color:#1d1b18;color:#f4f0e8}.dzien.on small{color:#cfc6b6}.dzien.pusty{opacity:.35}
.strz{flex:none;font:inherit;width:34px;height:34px;border-radius:50%;border:1px solid #cfc6b6;background:#fbf8f2;cursor:pointer;
 font-size:1.1em;color:#1d1b18}.strz:disabled{opacity:.3;cursor:default}
.filtry{display:flex;gap:8px;overflow-x:auto;padding:10px 16px 2px;max-width:720px;margin:auto;scrollbar-width:none}
.filtry button{flex:none;font:inherit;font-size:.88em;padding:5px 11px;border-radius:999px;border:1px solid #cfc6b6;
 background:#fbf8f2;color:#1d1b18;cursor:pointer}.filtry button.on{background:#8a3b2a;border-color:#8a3b2a;color:#fff}
.os{position:relative;display:flex;gap:14px;overflow-x:auto;scroll-snap-type:x mandatory;padding:10px 16px 20px;
 scroll-padding:16px;scrollbar-width:thin}
.ev{flex:0 0 min(80vw,330px);scroll-snap-align:start;position:relative}.ev.ukryte{display:none}
.data{display:flex;align-items:baseline;gap:6px;height:30px;padding-left:2px}.data b{font-size:1.25em;color:#8a3b2a}
.data span{color:#7a746a;font-size:.85em}
.linia{height:3px;background:#d8cfbf;margin:2px -14px 8px 0;position:relative}
.linia i{position:absolute;left:2px;top:-6px;width:13px;height:13px;border-radius:50%;background:#8a3b2a;border:3px solid #f4f0e8}
.ev.start .linia i{background:#1d1b18;width:15px;height:15px;top:-7px}
.karta{background:#fbf8f2;border:1px solid #ddd5c7;border-radius:14px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,.06)}
.karta img{width:100%;aspect-ratio:1;object-fit:cover;display:block;background:#ebe4d6}
.tresc{padding:10px 12px 12px}.tresc h2{font-size:1.08em;margin:0 0 6px;line-height:1.3}
.watek{display:inline-block;font-size:.75em;color:#8a3b2a;border:1px solid #e3c9c0;border-radius:999px;padding:1px 8px;
 margin-bottom:6px;cursor:pointer;background:none;font-family:inherit}
.opis{margin:0 0 6px;font-size:.9em;line-height:1.4;color:#3a362f}.kraje{color:#7a746a;font-size:.82em;margin:4px 0}.tresc details{margin-top:6px;font-size:.88em}
.tresc summary{cursor:pointer;color:#8a3b2a}.tresc li{margin:6px 0;line-height:1.35}.tresc li a{color:#1d1b18}
.s{color:#7a746a;font-size:.85em}.wiecej{display:inline-block;margin-top:8px;color:#8a3b2a;font-weight:600;text-decoration:none}
@media(min-width:720px){.os{padding-left:max(16px,calc(50% - 360px));scroll-padding-left:max(16px,calc(50% - 360px))}}
"""

JS = """
const os=document.querySelector('.os'),evs=[...os.querySelectorAll('.ev')],chips=[...document.querySelectorAll('.dzien')],
 ws=[...document.querySelectorAll('.filtry button')],prev=document.querySelector('.strz.w'),next=document.querySelector('.strz.d');
let watek='*',cur='';
const vis=()=>evs.filter(e=>!e.classList.contains('ukryte'));
function idz(d,smooth){const e=vis().find(x=>x.dataset.d>=d)||vis().at(-1);if(!e)return;
 os.scrollTo({left:e.offsetLeft-parseFloat(getComputedStyle(os).scrollPaddingLeft||16),behavior:smooth?'smooth':'auto'});zaznacz(e.dataset.d)}
function zaznacz(d){if(d===cur)return;cur=d;chips.forEach(c=>{c.classList.toggle('on',c.dataset.d===d);
 if(c.dataset.d===d)c.scrollIntoView({inline:'center',block:'nearest'})});
 const ds=dniWidoczne(),i=ds.indexOf(d);prev.disabled=i<=0;next.disabled=i<0||i>=ds.length-1;
 history.replaceState(null,'','#d='+d+(watek==='*'?'':'&w='+watek))}
const dniWidoczne=()=>[...new Set(vis().map(e=>e.dataset.d))];
os.addEventListener('scroll',()=>{const x=os.scrollLeft+40,e=vis().find(v=>v.offsetLeft+v.offsetWidth>x);if(e)zaznacz(e.dataset.d)},{passive:true});
chips.forEach(c=>c.onclick=()=>idz(c.dataset.d,true));
prev.onclick=()=>{const ds=dniWidoczne(),i=ds.indexOf(cur);if(i>0)idz(ds[i-1],true)};
next.onclick=()=>{const ds=dniWidoczne(),i=ds.indexOf(cur);if(i<ds.length-1)idz(ds[i+1],true)};
function filtr(w){watek=w;ws.forEach(b=>b.classList.toggle('on',b.dataset.w===w));
 evs.forEach(e=>e.classList.toggle('ukryte',w!=='*'&&e.dataset.w!==w));
 const ds=dniWidoczne();chips.forEach(c=>c.classList.toggle('pusty',!ds.includes(c.dataset.d)));
 evs.forEach(e=>e.classList.remove('start'));let last='';vis().forEach(e=>{if(e.dataset.d!==last)e.classList.add('start');last=e.dataset.d});
 const keep=cur;cur='';idz(w==='*'?(ds.includes(keep)?keep:ds.at(-1)):ds[0])}
ws.forEach(b=>b.onclick=()=>filtr(b.dataset.w));
document.querySelectorAll('.watek').forEach(b=>b.onclick=()=>{filtr(b.dataset.w);scrollTo({top:0,behavior:'smooth'})});
const q=new URLSearchParams(location.hash.slice(1));
if(q.get('w')&&ws.some(b=>b.dataset.w===q.get('w')))filtr(q.get('w'));else filtr('*');
if(q.get('d'))idz(q.get('d'));
"""


def n_kraje(n: int) -> str:
    return f"{n} kraje" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else f"{n} krajów"


def page() -> str:
    plan = load()
    evs = events(plan)
    names = {w["id"]: w["nazwa"] for w in plan["watki"]}
    counts = {w: sum(e["watek"] == w for e in evs) for w in names}
    shown = [w for w in plan["watki"] if counts[w["id"]] >= 2]          # wątek z jednym zdarzeniem: bez filtra
    chips = '<button data-w="*" class="on">Wszystko</button>' + "".join(
        f'<button data-w="{esc(w["id"])}">{esc(w["nazwa"])} <span class="s">{counts[w["id"]]}</span></button>' for w in shown)
    first, last_day = min(e["czas"].date() for e in evs), max(e["czas"].date() for e in evs)
    days = [date.fromordinal(n) for n in range(first.toordinal(), last_day.toordinal() + 1)]   # pusty dzień też widać
    day_chips = "".join(f'<button class="dzien" data-d="{d.isoformat()}">{d:%d.%m}<small>{DAY_NAMES[d.weekday()]}</small></button>'
                        for d in days)
    cards = []
    for e in evs:
        t = e["czas"]
        w = e["watek"] if e["watek"] in {x["id"] for x in shown} else ""
        heads = "".join(f'<li>{esc(NAMES.get(h["kraj"], h["kraj"]))}: <a href="{esc(h["url"])}" rel="noopener" target="_blank">'
                        f'{esc(h["naglowek"])}</a> <span class="s">{esc(src_name(h["zrodlo"]))}, '
                        f'{h["czas"]:%d.%m %H:%M}</span></li>' for h in e["naglowki"])
        img = f'<img src="ev-{e["nr"]}.png" alt="" loading="lazy">' if (OUT / f"ev-{e['nr']}.png").exists() else ""
        more = f' · {len(e["dni"])} dni w Sprawach dnia' if len(e["dni"]) > 1 else ""
        tag = f'<button class="watek" data-w="{esc(w)}">{esc(names[w])}</button>' if w else ""
        cards.append(
            f'<article class="ev" data-d="{t.date().isoformat()}" data-w="{esc(w)}"><div class="data"><b>{t:%d.%m}</b>'
            f'<span>{DAY_NAMES[t.weekday()]} {t:%H:%M}</span></div><div class="linia"><i></i></div><div class="karta">{img}'
            f'<div class="tresc">{tag}<h2>{esc(e["tytul"])}</h2>'
            + (f'<p class="opis">{esc(e["opis"])}</p>' if e.get("opis") else "")
            + f'<div class="kraje">{n_kraje(len(e["kraje"]))}: '
            f'{esc(", ".join(NAMES.get(k, k) for k in e["kraje"]))}{more}</div>'
            f'<details><summary>Nagłówki ({len(e["naglowki"])})</summary><ul>{heads}</ul></details>'
            + (f'<a class="wiecej" href="{esc(e["strona"])}">Sprawa dnia →</a>' if e["strona"] else "")
            + '</div></div></article>')
    last = max(plan["dni"])
    body = (f'<div id="pasek" data-dzien="{last}" data-wstecz></div><script src="../pasek.js"></script>'
            f'<div class="head"><h1>Oś czasu</h1><p>Najważniejsze sprawy dzień po dniu. Przesuń w bok albo wybierz dzień; '
            f'wątek zawęża oś do jednej sprawy. Godzina to pierwszy nagłówek w analizowanych źródłach (czas polski), '
            f'nie godzina samego zdarzenia.</p></div>'
            f'<nav class="wybor-dni" aria-label="Dni"><div class="in"><button class="strz w" aria-label="Poprzedni dzień">‹</button>'
            f'<div class="lista">{day_chips}</div><button class="strz d" aria-label="Następny dzień">›</button></div></nav>'
            f'<nav class="filtry" aria-label="Wątki">{chips}</nav>'
            f'<div class="os" data-sekcja="os">{"".join(cards)}</div><script>{JS}</script>')
    return (f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            f'<meta name="robots" content="noindex"><title>Oś czasu · Paralaksa</title><link rel="icon" href="{FAVICON}">'
            f'<link rel="manifest" href="../../manifest.webmanifest"><meta name="theme-color" content="#1d1b18">'
            f'<style>{CSS}</style></head><body>{body}</body></html>')


def summary() -> dict:
    """skrot.json for the entry under the bar of day pages: range and the newest pictures."""
    plan = load()
    # najnowszy dzień, w nim kolejność Spraw dnia (pierwsza = najszerzej opisywana)
    newest = sorted(plan["zdarzenia"], key=lambda e: max((s.split("#")[0], -int(s.split("#")[1])) for s in e["historie"]),
                    reverse=True)
    shown = [e for e in newest if (OUT / f"ev-{e['nr']}.png").exists()][:4]
    evs = events(plan)
    days = [e["czas"].date().isoformat() for e in evs]        # jak wybór dni na osi: daty pierwszych nagłówków
    # kafelek „Dzień po dniu”: ostatnie 5 dni osi, po 2 kadry (najszerzej opisywane sprawy dnia)
    rank = {e["nr"]: min(int(s.split("#")[1]) for s in e["historie"]) for e in plan["zdarzenia"]}
    strip = []
    for d in sorted(set(days))[-5:]:
        pics = sorted((e for e in evs if e["czas"].date().isoformat() == d and (OUT / f"ev-{e['nr']}.png").exists()),
                      key=lambda e: rank[e["nr"]])[:2]
        strip.append({"d": d, "obrazki": [f"ev-{e['nr']}.png" for e in pics]})
    return {"od": min(days), "do": max(days), "n": len(plan["zdarzenia"]), "dni": strip,
            "obrazki": [f"ev-{e['nr']}.png" for e in shown], "tytuly": [e["tytul"] for e in shown]}


if __name__ == "__main__":
    cmd, arg = (sys.argv[1:] + ["", ""])[:2]
    if cmd == "z-tygodnia":
        from_week(arg)
    elif cmd == "dzien":
        date.fromisoformat(arg)
        add_day(arg)
    elif cmd == "pominiete":
        add_skipped()
    elif cmd == "opisy":
        describe()
    elif cmd == "obrazki":
        images()
    elif cmd == "strona":
        (OUT / "index.html").write_text(page(), encoding="utf-8")
        (OUT / "skrot.json").write_text(json.dumps(summary(), ensure_ascii=False), encoding="utf-8")
        print(OUT / "index.html")
    else:
        raise SystemExit(__doc__)
