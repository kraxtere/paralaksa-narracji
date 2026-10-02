"""Ad hoc PROTOTYP (2026-10-01): ciągła oś wydarzeń przez wszystkie dni, dopisywana dzień po dniu, z przeskakiwaniem dni
i filtrem wątków (zastępuje osobne tygodnie z data/os_tygodnia.py).

Dane: Sprawy dnia z data/stories/<dzień>.json (plx site) i dalsze zdarzenia dnia z data/widok/os/dodatkowe/<dzień>.json,
godziny publikacji z data/prod.db (tylko do odczytu).
Godzina na osi = najwcześniejszy pokazany nagłówek w analizowanych źródłach, nie godzina samego zdarzenia.
  python scripts/v2/os_czasu.py z-tygodnia 2026-09-30   # jednorazowo: start z planu i kadrów tygodnia 24–30.09
  python scripts/v2/os_czasu.py dzien 2026-10-01        # Codex (tekst): dalsze zdarzenia dnia (>= 2 kraje), potem Sprawy dnia
                                                        # i dalsze -> nowe zdarzenia / dalszy ciąg, 4–8 nowych na dzień;
                                                        # dzień już na osi: tylko sprawy jeszcze nierozstrzygnięte
  python scripts/v2/os_czasu.py ciag 2026-10-01         # Codex (tekst): czy Sprawy dnia 1–3 to ciąg dalszy wcześniejszych dni
                                                        # i co nowego (okładka i strony spraw); przed widok_powitanie.py
  python scripts/v2/os_czasu.py opisy                   # Codex (tekst): 2–3 zdania pod nagłówkiem karty (nowe i rozszerzone)
  python scripts/v2/os_czasu.py obrazki [api]           # Codex (obraz): kadr bez tekstu dla zdarzeń bez obrazka;
                                                        # api: OpenAI Images API (płatnie, ok. 0,05 $ za kadr)
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
EXTRA = OUT / "dodatkowe"     # dalsze zdarzenia dnia (poza Sprawami dnia), tylko na osi
CIAG = OUT / "ciag"           # Sprawy dnia 1–3 jako ciąg dalszy wcześniejszych dni (okładka, strony spraw)
EXTRA_FROM = 101              # numery dalszych zdarzeń w dniu: po Sprawach dnia, bez strony sprawy
EXTRA_MAX = 12
EXTRA_MIN_COUNTRIES = 2
NEW_PER_DAY = (4, 8)          # nowych zdarzeń na dzień (decyzja właściciela 2026-10-01)
TEXT_MODEL = "codex:gpt-6.1-sol:medium"
API_IMAGE_MODEL = "gpt-image-2"   # obrazki api: płatnie, gdy dobowy limit obrazków Codex się skończył
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
    out = {f"{day}#{n}": {**h, "dzien": day, "n": n}
           for n, h in enumerate(json.loads(path.read_text(encoding="utf-8"))["historie"], 1)}
    extra = EXTRA / f"{day}.json"
    if extra.exists():
        out.update({f"{day}#{n}": {**h, "dzien": day, "n": n, "dodatkowa": True}
                    for n, h in enumerate(json.loads(extra.read_text(encoding="utf-8"))["historie"], EXTRA_FROM)})
    return out


def extra_events(day: str) -> None:
    """Further events of the day for the axis (>= 2 countries) beyond the Stories of the day, by the same two steps as
    paralaksa.site.stories (candidates, then every article checked and its headline translated), on Codex."""
    from paralaksa.aggregate.sample import publication_meta
    from paralaksa.site import stories as S
    path = EXTRA / f"{day}.json"
    if path.exists():
        return
    conn = sqlite3.connect("file:data/prod.db?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    eligible = set(publication_meta(conn, day)["eligible_ids"])
    main = json.loads(Path(f"data/stories/{day}.json").read_text(encoding="utf-8"))["historie"]
    taken = {k["article_id"] for h in main for k in h["kraje"]} | {i for h in main for i in h.get("pozostale", [])}
    items = [i for i in S.story_items(conn, day, eligible) if i["id"] not in taken]
    conn.close()
    lines = "\n".join(f"#{i['id']} | {i['kraj']} | {i['zrodlo']} | {' '.join(i['tytul'].split())} | "
                      f"{' '.join(i['streszczenie'].split())}" for i in items)
    skip = "\n".join(f"- {h['tytul']}" for h in main)
    client = build_client(TEXT_MODEL, None, 1, 1)

    def call(cid: str, prompt: str) -> str:
        res = client.complete(LLMRequest(custom_id=cid, model=TEXT_MODEL, max_tokens=16000,
                                         messages=[{"role": "user", "content": prompt}]))
        if not res.ok:
            raise SystemExit(f"{cid}: {res.error}")
        return res.text

    first = call(f"os-dodatkowe-{day}", f"Te wydarzenia są już opisane osobno, pomiń je:\n{skip}\n\n"
                 + S.PROMPT.format(max_stories=EXTRA_MAX, min_countries=EXTRA_MIN_COUNTRIES, items=lines))
    cands = S.parse_candidates(first, items)
    pool = [i for c in cands for i in c["ids"]]
    checks = [call(f"os-dodatkowe-weryfikacja-{day}-{k}", S.build_verify_prompt(cands, items, pool[k:k + S.VERIFY_CHUNK]))
              for k in range(0, len(pool), S.VERIFY_CHUNK)]
    found = S.parse_stories(cands, checks, items, min_countries=EXTRA_MIN_COUNTRIES, limit=EXTRA_MAX)
    EXTRA.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"day": day, "model": TEXT_MODEL, "kandydaci": cands, "historie": found},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"dalsze zdarzenia {day}: {len(found)} z {len(cands)} kandydatów")
    for h in found:
        print(f"  {len(h['kraje'])} krajów | {h['tytul']}")


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
    stories = "\n".join(f"[{sid}] {'DALSZE' if s.get('dodatkowa') else 'SPRAWA DNIA'} | {len(s['kraje'])} krajów | "
                        f"{s['tytul']} — {s['opis']}" for sid, s in new.items())
    lo, hi = NEW_PER_DAY
    return (
        "Prowadzimy oś wydarzeń z przeglądu prasy: najważniejsze sprawy dzień po dniu, połączone w wątki. Dochodzą "
        "sprawy z kolejnego dnia: SPRAWA DNIA (opisywana jednocześnie przez redakcje z co najmniej 3 krajów) i DALSZE "
        "(co najmniej 2 kraje). Dla KAŻDEJ nowej sprawy zdecyduj:\n"
        "- \"nowe\": nowe zdarzenie na osi.\n"
        "- \"dalszy_ciag\": ta sama rzecz co istniejące zdarzenie, bez nowego rozwoju (np. kolejny dzień tej samej wizyty) "
        "-> podaj \"zdarzenie\": numer. Nowy rozwój tej samej sprawy (np. propozycja, potem odrzucenie) to \"nowe\" "
        "w tym samym wątku.\n"
        "- \"pomin\": tylko dla DALSZE: drobne, lokalne, sportowe, rozrywkowe albo mniej ważne od pozostałych.\n"
        f"Każda SPRAWA DNIA trafia na oś (\"nowe\" albo \"dalszy_ciag\"). Z DALSZYCH wybierz najważniejsze tak, żeby z tego "
        f"dnia razem było od {lo} do {hi} nowych zdarzeń (jeśli wszystkich spraw jest mniej, wszystkie, które nie są "
        "dalszym ciągiem). Liczą się konkretne zdarzenia (decyzja, atak, głosowanie, katastrofa, wystąpienie), nie tematy.\n"
        "Dla \"nowe\": \"tytul\" do 8 słów po polsku, co się stało, neutralnie, sprawy sporne przypisane stronie "
        "(„Estonia oskarża Rosję…”); \"watek\": id istniejącego wątku, nowego wątku albo null; \"scena\": jedno zdanie po "
        "angielsku, co narysować (miejsce, ludzie, przedmioty), bez napisów, liter, liczb i logo; prawdziwe osoby jako "
        "uproszczone postacie z prawdziwymi atrybutami (strój, wygląd), bez stereotypów wobec osób nieznanych.\n"
        "Nowy wątek (\"nowe_watki\": id małymi literami z myślnikami, nazwa do 4 słów) tylko wtedy, gdy łączy co najmniej "
        "dwa zdarzenia; do istniejących zdarzeń możesz go przypisać w \"przypisz\".\n"
        "Nie wymyślaj zdarzeń spoza listy. Zwróć wyłącznie JSON:\n"
        '{"nowe_watki":[{"id":"...","nazwa":"..."}],"przypisz":[{"zdarzenie":3,"watek":"..."}],'
        '"decyzje":[{"historia":"2026-10-01#1","typ":"nowe","tytul":"...","watek":null,"scena":"..."},'
        '{"historia":"2026-10-01#2","typ":"dalszy_ciag","zdarzenie":5},{"historia":"2026-10-01#103","typ":"pomin"}]}\n\n'
        f"WĄTKI:\n{threads}\n\nZDARZENIA NA OSI:\n{events}\n\nNOWE SPRAWY:\n{stories}")


def validate(plan: dict, new: dict[str, dict], ans: dict) -> list[str]:
    errors = []
    threads = {w["id"] for w in plan["watki"]} | {w.get("id") for w in ans.get("nowe_watki", [])}
    nrs = {e["nr"] for e in plan["zdarzenia"]}
    seen = [d.get("historia") for d in ans.get("decyzje", [])]
    errors += [f"brak decyzji dla {s}" for s in new if s not in seen]
    errors += [f"nieznana sprawa {s}" for s in seen if s not in new]
    errors += [f"sprawa {s} dwa razy" for s in set(seen) if seen.count(s) > 1]
    for d in ans.get("decyzje", []):
        if d.get("typ") == "pomin":
            if not new.get(d.get("historia"), {}).get("dodatkowa"):
                errors.append(f"{d.get('historia')}: Sprawy dnia nie pomijamy")
        elif d.get("typ") == "nowe":
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
    # 4–8 nowych na dzień: liczą się też zdarzenia z tego dnia, które już są na osi (dzień uzupełniany)
    days = {s.split("#")[0] for s in new}
    kinds = {d.get("historia"): d.get("typ") for d in ans.get("decyzje", [])}
    lo, hi = NEW_PER_DAY
    for day in days:
        before = sum(e["historie"][0].startswith(day + "#") for e in plan["zdarzenia"])
        n_new = before + sum(t == "nowe" for s, t in kinds.items() if s and s.startswith(day + "#"))
        extra_new = sum(t == "nowe" for s, t in kinds.items() if s in new and new[s].get("dodatkowa") and s.startswith(day + "#"))
        skipped = sum(t == "pomin" for s, t in kinds.items() if s and s.startswith(day + "#"))
        if n_new > hi and extra_new:
            errors.append(f"{day}: {n_new} nowych zdarzeń, ma być najwyżej {hi} (pomiń mniej ważne DALSZE)")
        if n_new < lo and skipped:
            errors.append(f"{day}: {n_new} nowych zdarzeń, ma być co najmniej {lo} (dodaj pominięte DALSZE)")
    return errors


def add_day(day: str) -> None:
    """New day, or a day already on the axis with stories not yet decided (e.g. further events added later)."""
    extra_events(day)
    plan = load()
    if day not in plan["dni"]:
        plan["dni"].append(day)
    placed = {s for e in plan["zdarzenia"] for s in e["historie"]} | set(plan.get("pominiete", []))
    todo = {s: h for s, h in day_stories(day).items() if s not in placed}
    if not todo:
        raise SystemExit(f"{day}: wszystkie sprawy już rozstrzygnięte")
    decide(plan, todo, day)


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
        elif d["typ"] == "pomin":
            plan.setdefault("pominiete", []).append(d["historia"])
        else:
            by_nr[d["zdarzenie"]]["historie"].append(d["historia"])
    save(plan)
    for d in ans["decyzje"]:
        print(d["historia"], d["typ"], d.get("tytul") or d.get("zdarzenie") or "", f"[{d.get('watek') or ''}]")


def continuation(day: str) -> None:
    """Stories 1–3 of the day (cover, story pages) that continue a case from earlier days: the same event on the axis,
    or an event of the same thread (Codex decides, a broad thread like a war holds different cases) and what is new
    today. data/widok/os/ciag/<day>.json: {"sprawa-1": {"od": day, "zdarzenie": nr, "watek": id, "nowe": "..."}}."""
    plan = load()
    st = all_stories(plan["dni"])

    def lines(sids):
        return "\n".join(f"  {st[s]['dzien'][8:10]}.{st[s]['dzien'][5:7]}: {st[s]['opis']} | nagłówki: "
                         + "; ".join(k.get("naglowek_pl", "") for k in st[s]["kraje"]) for s in sids)

    cases, blocks = {}, []
    for n in (1, 2, 3):
        sid = f"{day}#{n}"
        ev = next((e for e in plan["zdarzenia"] if sid in e["historie"]), None)
        if ev is None:
            continue
        earlier = {e["nr"]: [s for s in e["historie"] if st[s]["dzien"] < day] for e in plan["zdarzenia"]
                   if e is ev or (ev["watek"] and e["watek"] == ev["watek"])}
        earlier = {nr: ss for nr, ss in earlier.items() if ss}
        if not earlier:
            continue
        cases[f"sprawa-{n}"] = (ev, earlier)
        blocks.append(f"[sprawa-{n}] DZIŚ: {st[sid]['tytul']}\n{lines([sid])}\nWCZEŚNIEJ:\n"
                      + "\n".join(f" #{nr}:\n{lines(ss)}" for nr, ss in earlier.items()))
    CIAG.mkdir(parents=True, exist_ok=True)
    out = {}
    if cases:
        prompt = (
            "Przegląd prasy dzień po dniu. Dla każdej dzisiejszej sprawy masz zdarzenia z wcześniejszych dni z tej samej "
            "osi lub wątku. Zdecyduj, czy dzisiejsza sprawa to ciąg dalszy tej samej konkretnej sprawy (ta sama osoba, "
            "ten sam incydent, ta sama decyzja i jej skutki), a nie tylko ten sam szeroki temat (inny atak w tej samej "
            "wojnie to NIE ciąg dalszy). Jeśli tak, podaj numer zdarzenia, którego to ciąg dalszy, i \"nowe\": jedno "
            "zdanie po polsku, 8–22 słowa, co dzisiejsze nagłówki dodają względem wcześniejszych dni (nowy rozwój, nowe "
            "ustalenia, reakcje). Wyłącznie na podstawie podanych opisów i nagłówków, bez ocen i prognoz; sprawy sporne "
            "przypisz stronie; bez dat dziennych i bez nazw redakcji. Jeśli dziś nie ma nic nowego, napisz, co redakcje "
            "dalej opisują. Zwróć wyłącznie JSON: {\"sprawa-1\":{\"ciag\":true,\"zdarzenie\":17,\"nowe\":\"...\"},"
            "\"sprawa-2\":{\"ciag\":false}}\n\n" + "\n\n".join(blocks))
        client = build_client(TEXT_MODEL, None, 1, 1)
        messages = [{"role": "user", "content": prompt}]
        for _ in range(2):
            res = client.complete(LLMRequest(custom_id=f"os-ciag-{day}", model=TEXT_MODEL, max_tokens=4000, messages=messages))
            if not res.ok:
                raise SystemExit(res.error)
            try:
                ans = json.loads(res.text[res.text.find("{"): res.text.rfind("}") + 1])
                errors = [f"brak {k}" for k in cases if not isinstance(ans.get(k), dict)]
                for k, (ev, earlier) in cases.items():
                    a = ans.get(k) or {}
                    if a.get("ciag") and (a.get("zdarzenie") not in earlier or not isinstance(a.get("nowe"), str)
                                          or not 6 <= len(a["nowe"].split()) <= 26):
                        errors.append(f"{k}: zdarzenie spoza listy albo zdanie „nowe” puste lub nie 8–22 słowa")
            except (json.JSONDecodeError, AttributeError) as e:
                ans, errors = {}, [f"niepoprawny JSON: {e}"]
            if not errors:
                break
            print("błędy:", errors)
            messages += [{"role": "assistant", "content": res.text},
                         {"role": "user", "content": "Popraw te błędy i zwróć cały JSON jeszcze raz:\n" + "\n".join(errors)}]
        else:
            raise SystemExit(f"ciag {day}: odpowiedź nie przeszła kontroli po ponowieniu")
        by_nr = {e["nr"]: e for e in plan["zdarzenia"]}
        for k, (ev, earlier) in cases.items():
            a = ans[k]
            if a.get("ciag"):
                prev = by_nr[a["zdarzenie"]]
                out[k] = {"od": min(st[s]["dzien"] for s in earlier[a["zdarzenie"]]), "zdarzenie": a["zdarzenie"],
                          "watek": prev["watek"] or ev["watek"], "nowe": a["nowe"].strip()}
    (CIAG / f"{day}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(f"{k}: ciąg dalszy od {v['od']} (#{v['zdarzenie']}): {v['nowe']}")
    print(f"ciąg dalszy {day}: {len(out)} z 3 spraw")


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
                    heads.append({"id": k["article_id"], "kraj": k["kraj"], "naglowek": k.get("naglowek_pl", ""), "zrodlo": src, "url": url,
                                  "czas": datetime.fromisoformat(pub).astimezone(WAW), "dzien": st[sid]["dzien"]})
                    if k["kraj"] not in countries:
                        countries.append(k["kraj"])
        heads.sort(key=lambda h: h["czas"])
        page = next((f"../{st[s]['dzien']}/sprawa-{st[s]['n']}.html" for s in ev["historie"]
                     if st[s]["n"] <= 3 and (Path("data/widok") / st[s]["dzien"] / f"sprawa-{st[s]['n']}.html").exists()), "")
        out.append({**ev, "czas": heads[0]["czas"], "dzien": date.fromisoformat(min(st[s]["dzien"] for s in ev["historie"])),
                    "naglowki": heads, "kraje": countries, "strona": page,
                    "dni": sorted({h["dzien"] for h in heads})})
    out.sort(key=lambda e: (e["dzien"], e["czas"]))      # dzień przeglądu, w którym zdarzenie weszło (decyzja 2026-10-01)
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


def api_image(ev: dict) -> str:
    """Fallback when the Codex image quota is used up (decision 2026-10-01): OpenAI Images API, paid, ~0.05 $ per frame."""
    import base64
    import os
    import httpx
    from dotenv import load_dotenv
    load_dotenv()
    prompt = (STYLE + PEOPLE_STYLE + " Scene: " + ev["scena"] + " Absolutely no text, letters, numbers, captions, signs, "
              "logos or flags with writing anywhere in the image.")
    r = httpx.post("https://api.openai.com/v1/images/generations", timeout=300,
                   headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                   json={"model": API_IMAGE_MODEL, "prompt": prompt, "size": "1024x1024", "quality": "medium", "n": 1})
    if r.status_code != 200:
        return f"ev-{ev['nr']}: BRAK (API {r.status_code}: {r.text[:200]})"
    (OUT / f"ev-{ev['nr']}.png").write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))
    return f"ev-{ev['nr']}.png (API)"


def images(api: bool = False) -> None:
    todo = [e for e in load()["zdarzenia"] if not (OUT / f"ev-{e['nr']}.png").exists()]

    def one(ev):
        if api:
            return api_image(ev)
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
let watek='*',cur='',auto=0;
const vis=()=>evs.filter(e=>!e.classList.contains('ukryte'));
const lewo=e=>e.offsetLeft-(parseFloat(getComputedStyle(os).paddingLeft)||16);
function przewin(e,smooth){if(smooth){clearTimeout(auto);auto=setTimeout(()=>auto=0,900)}
 os.scrollTo({left:lewo(e),behavior:smooth?'smooth':'auto'})}
function idz(d,smooth){const e=vis().find(x=>x.dataset.d>=d)||vis().at(-1);if(!e)return;przewin(e,smooth);zaznacz(e.dataset.d)}
// scrollIntoView would cancel the smooth scroll of .os in Chromium, so the chip bar is scrolled directly
function zaznacz(d){if(d===cur)return;cur=d;chips.forEach(c=>{c.classList.toggle('on',c.dataset.d===d);
 if(c.dataset.d===d){const p=c.parentElement,r=c.getBoundingClientRect(),pr=p.getBoundingClientRect();
  p.scrollLeft+=r.left-pr.left-(p.clientWidth-r.width)/2}});
 const ds=dniWidoczne(),i=ds.indexOf(d);prev.disabled=i<=0;next.disabled=i<0||i>=ds.length-1;
 history.replaceState(null,'','#d='+d+(watek==='*'?'':'&w='+watek))}
const dniWidoczne=()=>[...new Set(vis().map(e=>e.dataset.d))];
os.addEventListener('scrollend',()=>{clearTimeout(auto);auto=0});
let kolko=0,kolkoT=0;
os.addEventListener('wheel',ev=>{if(ev.ctrlKey||!ev.target.closest('.karta')||Math.abs(ev.deltaX)>=Math.abs(ev.deltaY))return;
 const v=vis(),x=os.scrollLeft,i=v.findIndex(e=>lewo(e)>=x-5),j=ev.deltaY>0?i+1:i-1;
 if(i<0||j<0||j>=v.length)return;ev.preventDefault();
 if(Date.now()<kolkoT)return;kolko+=ev.deltaY;if(Math.abs(kolko)<40)return;
 kolko=0;kolkoT=Date.now()+250;przewin(v[j],true);zaznacz(v[j].dataset.d)},{passive:false});
os.addEventListener('scroll',()=>{if(auto)return;const x=os.scrollLeft,e=vis().find(v=>lewo(v)+v.offsetWidth/2>x);if(e)zaznacz(e.dataset.d)},{passive:true});
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
    first, last_day = min(e["dzien"] for e in evs), max(e["dzien"] for e in evs)
    days = [date.fromordinal(n) for n in range(first.toordinal(), last_day.toordinal() + 1)]   # pusty dzień też widać
    day_chips = "".join(f'<button class="dzien" data-d="{d.isoformat()}">{d:%d.%m}<small>{DAY_NAMES[d.weekday()]}</small></button>'
                        for d in days)
    cards = []
    for e in evs:
        t, d = e["czas"], e["dzien"]
        when = f"{t:%H:%M}" if t.date() == d else f"{t:%d.%m %H:%M}"
        w = e["watek"] if e["watek"] in {x["id"] for x in shown} else ""
        heads = "".join(f'<li>{esc(NAMES.get(h["kraj"], h["kraj"]))}: <a href="{esc(h["url"])}" data-a="{h["id"]}" rel="noopener" target="_blank">'
                        f'{esc(h["naglowek"])}</a> <span class="s">{esc(src_name(h["zrodlo"]))}, '
                        f'{h["czas"]:%d.%m %H:%M}</span></li>' for h in e["naglowki"])
        img = f'<img src="ev-{e["nr"]}.png" alt="" loading="lazy">' if (OUT / f"ev-{e['nr']}.png").exists() else ""
        more = f' · {len(e["dni"])} dni w Wydarzeniach dnia' if len(e["dni"]) > 1 else ""
        tag = f'<button class="watek" data-w="{esc(w)}">{esc(names[w])}</button>' if w else ""
        cards.append(
            f'<article class="ev" data-d="{d.isoformat()}" data-w="{esc(w)}"><div class="data"><b>{d:%d.%m}</b>'
            f'<span>{DAY_NAMES[d.weekday()]} · 1. nagłówek {when}</span></div><div class="linia"><i></i></div><div class="karta">{img}'
            f'<div class="tresc">{tag}<h2>{esc(e["tytul"])}</h2>'
            + (f'<p class="opis">{esc(e["opis"])}</p>' if e.get("opis") else "")
            + f'<div class="kraje">{n_kraje(len(e["kraje"]))}: '
            f'{esc(", ".join(NAMES.get(k, k) for k in e["kraje"]))}{more}</div>'
            f'<details><summary>Nagłówki ({len(e["naglowki"])})</summary><ul>{heads}</ul></details>'
            + (f'<a class="wiecej" href="{esc(e["strona"])}">Wydarzenie dnia →</a>' if e["strona"] else "")
            + '</div></div></article>')
    last = max(plan["dni"])
    body = (f'<div id="pasek" data-dzien="{last}" data-wstecz></div><script src="../pasek.js"></script>'
            f'<div class="head"><h1>Oś czasu</h1><p>Najważniejsze sprawy dzień po dniu. Przesuń w bok albo wybierz dzień; '
            f'wątek zawęża oś do jednej sprawy. Dzień to przegląd prasy, w którym sprawa pojawiła się pierwszy raz; '
            f'godzina to pierwszy nagłówek w analizowanych źródłach (czas polski), nie godzina samego zdarzenia.</p></div>'
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
    days = [e["dzien"].isoformat() for e in evs]               # jak wybór dni na osi: dni przeglądu
    # kafelek „Dzień po dniu”: ostatnie 5 dni osi, po 2 kadry (najszerzej opisywane sprawy dnia)
    rank = {e["nr"]: min(int(s.split("#")[1]) for s in e["historie"]) for e in plan["zdarzenia"]}
    strip = []
    for d in sorted(set(days))[-5:]:
        pics = sorted((e for e in evs if e["dzien"].isoformat() == d and (OUT / f"ev-{e['nr']}.png").exists()),
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
    elif cmd == "ciag":
        date.fromisoformat(arg)
        continuation(arg)
    elif cmd == "opisy":
        describe()
    elif cmd == "obrazki":
        images(api=arg == "api")
    elif cmd == "strona":
        (OUT / "index.html").write_text(page(), encoding="utf-8")
        (OUT / "skrot.json").write_text(json.dumps(summary(), ensure_ascii=False), encoding="utf-8")
        print(OUT / "index.html")
    else:
        raise SystemExit(__doc__)
