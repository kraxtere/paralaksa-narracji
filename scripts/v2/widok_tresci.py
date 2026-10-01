"""Grounded inputs and versioned caches for the image-driven prototype."""

import hashlib
import json
import re
import sqlite3
from pathlib import Path

WELCOME_VERSION = "powitanie-opisy-v3"   # v3: opisy o połowę krótsze (2026-10-01)


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def cache_meta(path: Path) -> Path:
    return path.with_name("_" + path.stem + "-meta.json")


def save_cache(path: Path, value, inputs, version: str) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")
    cache_meta(path).write_text(json.dumps({"input_hash": fingerprint(inputs), "version": version,
                                         "output_hash": fingerprint(value)}, indent=1), encoding="utf-8")


def read_cache(path: Path, inputs, version: str, adopt: bool = False):
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    meta_path = cache_meta(path)
    if not meta_path.exists():
        # Jednorazowo zachowujemy dotychczasowe podsumowania i sprawdzone regiony.
        # Kolejne zmiany danych, instrukcji lub obrazu unieważniają tę bazę.
        if not adopt:
            return None
        save_cache(path, value, inputs, version)
        return value
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("input_hash") == fingerprint(inputs) and meta.get("version") == version:
        # Ręczna korekta treści jest dozwolona, jeżeli dane wejściowe nadal pasują.
        return value
    return None


def welcome_input(day: str, pl: dict, names: dict, sources: dict) -> dict:
    """Verified story members; exact report evidence, never unrelated article signals."""
    stories = json.loads(Path(f"data/stories/{day}.json").read_text(encoding="utf-8"))["historie"][:3]
    report = json.loads(Path(f"reports/{day}.json").read_text(encoding="utf-8"))["report"]
    opisy = json.loads(Path(f"data/dzien_prasy/{day}/opisy.json").read_text(encoding="utf-8"))
    theme_names = {b["temat"]: b["nazwa"] for c in opisy["dane"].values() for b in c["tematy"]}
    conn = sqlite3.connect("file:data/prod.db?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    def article(aid: int, evidence: list[dict] | None = None):
        a = conn.execute("SELECT a.*, s.country FROM articles a JOIN sources s ON s.id=a.source_id WHERE a.id=?",
                         (aid,)).fetchone()
        if a is None:
            raise ValueError(f"Brak artykułu {aid}")
        sigs = conn.execute("SELECT id, article_id, theme_id, frame, stance, summary_pl FROM signals WHERE article_id=?",
                            (aid,)).fetchall()
        if evidence is not None:
            checked = []
            for e in evidence:
                match = next((s for s in sigs if s["id"] == e["signal_id"] and s["theme_id"] == e["theme_id"]), None)
                if match is None or e["article_id"] != aid or e["kraj"] != a["country"] or e["zrodlo"] != a["source_id"]:
                    raise ValueError(f"Niezgodne pochodzenie dowodu: {e}")
                checked.append(match)
            sigs = checked
        return {"article_id": aid, "kraj": a["country"], "zrodlo_id": a["source_id"],
                "zrodlo": sources.get(a["source_id"], a["source_id"]), "naglowek": pl.get(aid) or a["title"],
                "sygnaly": [dict(s) for s in sigs],
                # Tylko historie wymagają materiału bez sygnałów (np. Pike).
                "lead": a["lead"] if evidence is None else None,
                "tekst_lokalny": (a["fulltext"] or "")[:14000] if evidence is None else None}

    items = {}
    for i, story in enumerate(stories, 1):
        ids = list(dict.fromkeys([c["article_id"] for c in story["kraje"]] + story.get("pozostale", [])))
        rejected = set(story.get("odrzucone", []))
        countries = {}
        for aid in ids:
            if aid not in rejected:
                a = article(aid)
                countries.setdefault(a["kraj"], []).append(a)
        items[f"sprawa-{i}"] = {"typ": "sprawa", "tytul": story["tytul"],
                                "opis_do_przeredagowania": story.get("opis", ""), "kraje": countries}

    def evidence_countries(evidence):
        by_article = {}
        for e in evidence:
            by_article.setdefault(e["article_id"], []).append(e)
        countries = {}
        for aid, es in by_article.items():
            a = article(aid, es)
            countries.setdefault(a["kraj"], []).append(a)
        return countries

    for i, diff in enumerate(report["rozbieznosci"][:2], 1):
        evidence = [e for c in diff["kraje"] for e in c["dowody"]]
        items[f"roznica-{i}"] = {"typ": "roznica", "tytul": "Gdzie prasa się różni: " + theme_names.get(diff["temat"], diff["temat"]),
                                "opis_do_przeredagowania": diff["tekst"], "pewnosc": diff["pewnosc"],
                                "ograniczenia": diff.get("ograniczenia", []), "kraje": evidence_countries(evidence)}
    if report["autoobraz"]:
        si = report["autoobraz"][0]
        items["obraz-kraju"] = {"typ": "autoobraz", "tytul": "Jak kraj widzi siebie: " + names.get(si["kraj"], si["kraj"]),
                                 "kraj": si["kraj"], "pewnosc": si["pewnosc"],
                                 "opis_do_przeredagowania": [si["jak_opisuje_siebie"], si["jak_opisuja_go_inni"], si.get("komentarz", "")],
                                 "ograniczenia": si.get("ograniczenia", []), "kraje": evidence_countries(si["dowody"])}
    conn.close()
    return {"dzien": day, "karty": items}


def validate_welcome(value: dict, inputs: dict) -> None:
    """Each paragraph must point to supplied articles of the correct country's outlets."""
    cards = inputs["karty"]
    if set(value) != set(cards):
        raise ValueError("Podsumowania powitania: niezgodne karty")
    for key, item in cards.items():
        summary = value[key]
        if "tytul" in summary and (not isinstance(summary["tytul"], str) or not summary["tytul"].strip()):
            raise ValueError(f"{key}: pusty tytuł")
        if not isinstance(summary.get("opis"), str) or not summary["opis"].strip():
            raise ValueError(f"{key}: brak wstępu")
        if set(summary.get("kraje", {})) != set(item["kraje"]):
            raise ValueError(f"{key}: niezgodne kraje")
        texts = [summary["opis"]]
        for country, paragraphs in summary["kraje"].items():
            allowed = {a["article_id"] for a in item["kraje"][country]}
            if not paragraphs:
                raise ValueError(f"{key}/{country}: brak opisu")
            for p in paragraphs:
                if not isinstance(p.get("tekst"), str) or not p["tekst"].strip() or not p.get("article_ids"):
                    raise ValueError(f"{key}/{country}: pusty opis lub brak odnośników")
                if not set(p["article_ids"]) <= allowed:
                    raise ValueError(f"{key}/{country}: artykuł spoza wskazanych dowodów")
                texts.append(p["tekst"])
        for text in texts:
            if any(len(quote.split()) > 15 for quote in re.findall(r'["„“]([^"„“”]+)["”]', text)):
                raise ValueError(f"{key}: cytat dłuższy niż 15 słów")


def welcome_prompt(inputs: dict) -> str:
    return (
        "Przygotuj rozbudowane opisy kart Paralaksy po polsku. Opisujemy przekaz REDAKCJI, nie ustalone fakty. "
        "Wyłącznie dane poniżej, żadnej wiedzy spoza nich. Pole opis_do_przeredagowania to kontekst, "
        "każdą jego tezę trzeba sprawdzić w dostarczonym materiale. Dla spraw dnia korzystaj z nagłówków, "
        "leadów, tekstów i sygnałów tylko dotyczących tej historii, pomijaj inne tematy przeglądów wiadomości. "
        "Dla różnic i autoobrazu korzystaj wyłącznie ze wskazanych sygnałów. "
        "Pisz zwięźle i rzeczowo: konkretne wątki zamiast ogólników, bez zdań wprowadzających. "
        "Wstęp (opis) 3–4 zdania, około 60–90 słów: porównaj, które redakcje piszą o jakich wątkach "
        "i czym różni się ich dobór spraw lub perspektywa; nie wyliczaj wszystkich redakcji, nazwij te, które najlepiej "
        "pokazują różnice. Nie powtarzaj samego tytułu. "
        "Dla każdego kraju jeden akapit, 2–3 zdania, około 30–60 słów, "
        "krócej przy skąpych danych. Nazywaj redakcje, przedstaw konkretne wątki, perspektywy i różnice. "
        "Zarzuty przypisuj rozmówcom/redakcjom; pojedynczy wydawca nie reprezentuje całej prasy kraju. "
        "Nie mieszaj różnych etapów sprawy. Bez prognoz jako faktów, cytaty najwyżej 15 słów, "
        "nie kopiuj leadów ani pełnych tekstów. Każdy akapit ma article_ids materiałów, na których się opiera. "
        "W różnicach i autoobrazie zachowaj ostrożność wynikającą z pewności i liczby źródeł. "
        "Dodaj opcjonalne pole tytul, jeśli tytuł wejściowy przedstawia zarzut lub podejrzenie jako ustalony fakt. "
        "Taki tytuł powinien jasno wskazywać, że chodzi o doniesienia lub podejrzenie. "
        "Odpowiedz wyłącznie JSON: {KLUCZ_KARTY:{\"opis\":\"...\",\"kraje\":{KOD:[{\"tekst\":\"...\","
        "\"article_ids\":[123]}]}}}. Wszystkie karty i kraje dokładnie jak w danych.\n\n"
        + json.dumps(inputs, ensure_ascii=False))
