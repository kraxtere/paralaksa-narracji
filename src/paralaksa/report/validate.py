"""Report validator (SPEC §3, §9.4): references, counter-signals, confidence, thresholds, quote length.

`validate_report` returns error messages for the retry prompt; `sanitize_report` is the last resort
after a failed retry: it drops what cannot be backed by data, so every published claim has a link.
"""

from __future__ import annotations

import re

from paralaksa.report.schema import ReportOutput

MAX_QUOTE_WORDS = 15
# Tekst w cudzysłowie: „…”, "…", “…”, «…», »…«.
QUOTE_RE = re.compile(r"„([^”\"]+)[”\"]|\"([^\"]+)\"|“([^”]+)”|«([^»]+)»|»([^«]+)«")
NO_BASELINE = "brak linii bazowej"


def long_quotes(text: str) -> list[str]:
    out = []
    for m in QUOTE_RE.finditer(text):
        quote = next(g for g in m.groups() if g is not None)
        if len(quote.split()) > MAX_QUOTE_WORDS:
            out.append(quote)
    return out


def _texts(report: ReportOutput) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i, s in enumerate(report.w_skrocie):
        out.append((f"w_skrocie.{i}", s.tekst))
    for i, p in enumerate(report.wzorce_zbieznosci):
        out += [(f"wzorce_zbieznosci.{i}", t) for t in
                (p.wspolny_kierunek, p.sygnaly_przeciwne.tekst, p.pewnosc.uzasadnienie, *(k.rama for k in p.kraje))]
    for i, d in enumerate(report.rozbieznosci):
        out += [(f"rozbieznosci.{i}", t) for t in (d.tekst, d.pewnosc.uzasadnienie, *(k.rama for k in d.kraje))]
    for i, a in enumerate(report.autoobraz):
        out += [(f"autoobraz.{i}", t) for t in (a.jak_opisuje_siebie, a.jak_opisuja_go_inni, a.komentarz)]
    for name in ("co_sie_przesuwa", "nieobecne_w_polsce", "slabe_sygnaly"):
        out += [(f"{name}.{i}", c.tekst) for i, c in enumerate(getattr(report, name))]
    return out


def _refs(report: ReportOutput) -> list[tuple[str, list[int]]]:
    """Every claim that must carry at least one reference (counter-signals may legitimately be empty)."""
    out: list[tuple[str, list[int]]] = []
    for i, s in enumerate(report.w_skrocie):
        out.append((f"w_skrocie.{i}", s.article_ids))
    for section in ("wzorce_zbieznosci", "rozbieznosci"):
        for i, item in enumerate(getattr(report, section)):
            out += [(f"{section}.{i}.kraje.{k.kraj}", k.article_ids) for k in item.kraje]
    for i, a in enumerate(report.autoobraz):
        out.append((f"autoobraz.{i}", a.article_ids))
    for name in ("co_sie_przesuwa", "nieobecne_w_polsce", "slabe_sygnaly"):
        out += [(f"{name}.{i}", c.article_ids) for i, c in enumerate(getattr(report, name))]
    return out


def validate_report(report: ReportOutput, package: dict, known_ids: set[int]) -> list[str]:
    errors: list[str] = []
    for path, ids in _refs(report):
        if not ids:
            errors.append(f"{path}: twierdzenie bez odnośnika (article_ids jest puste)")
        unknown = sorted(set(ids) - known_ids)
        if unknown:
            errors.append(f"{path}: nieistniejące article_ids {unknown} (używaj tylko id z DANYCH)")
    for i, p in enumerate(report.wzorce_zbieznosci):
        unknown = sorted(set(p.sygnaly_przeciwne.article_ids) - known_ids)
        if unknown:
            errors.append(f"wzorce_zbieznosci.{i}.sygnaly_przeciwne: nieistniejące article_ids {unknown}")
    errors += _threshold_errors(report, package)
    errors += provenance_errors(report, package)
    errors += language_errors(report, package)
    errors += attribution_errors(report, package)
    for path, text in _texts(report):
        for q in long_quotes(text):
            errors.append(f"{path}: cytat dłuższy niż {MAX_QUOTE_WORDS} słów: „{' '.join(q.split()[:6])}…”")
    return errors


def _threshold_errors(report: ReportOutput, package: dict) -> list[str]:
    errors = []
    candidates = {c["temat"] for c in package.get("zbieznosc_kandydaci", [])}
    min_countries = package["progi"]["min_krajow"]
    has_baseline = package["linia_bazowa"]["dostepna"]
    for i, p in enumerate(report.wzorce_zbieznosci):
        if p.temat not in candidates:
            errors.append(f"wzorce_zbieznosci.{i}: temat '{p.temat}' nie jest kandydatem na zbieżność "
                          f"w danych (poniżej progów) – przenieś go do 'slabe_sygnaly'")
        if len({k.kraj for k in p.kraje}) < min_countries:
            errors.append(f"wzorce_zbieznosci.{i}: {len(p.kraje)} kraje, wymagane co najmniej {min_countries}")
        if not has_baseline and NO_BASELINE not in p.trend.lower():
            errors.append(f"wzorce_zbieznosci.{i}.trend: brak linii bazowej – wpisz '{NO_BASELINE}'")
    return errors


def sanitize_report(report: ReportOutput, package: dict, known_ids: set[int]) -> ReportOutput:
    """Drop whole invalid claims after retry; never detach a bad link from unchanged prose."""
    cleaned = ReportOutput.model_validate(_map_strings(report.model_dump(), shorten_quotes))
    if not package['linia_bazowa']['dostepna']:
        for pattern in cleaned.wzorce_zbieznosci:
            pattern.trend = NO_BASELINE
    bad = validate_report(cleaned, package, known_ids)
    for section in ReportOutput.model_fields:
        rejected = {int(e.split(".")[1].split(":")[0]) for e in bad
                    if e.startswith(section + ".")}
        setattr(cleaned, section, [v for i,v in enumerate(getattr(cleaned, section)) if i not in rejected])
    return cleaned


def shorten_quotes(text: str) -> str:
    def cut(m: re.Match) -> str:
        quote = next(g for g in m.groups() if g is not None)
        words = quote.split()
        if len(words) <= MAX_QUOTE_WORDS:
            return m.group(0)
        return "„" + " ".join(words[:MAX_QUOTE_WORDS]) + "…”"
    return QUOTE_RE.sub(cut, text)


def _map_strings(obj, fn):
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [_map_strings(x, fn) for x in obj]
    if isinstance(obj, dict):
        return {k: _map_strings(v, fn) for k, v in obj.items()}
    return obj


def evidence_items(report):
    for section in ('w_skrocie', 'slabe_sygnaly', 'co_sie_przesuwa', 'nieobecne_w_polsce'):
        for i, item in enumerate(getattr(report, section)):
            yield f'{section}.{i}', item, item.theme_id, None
    for section in ('wzorce_zbieznosci', 'rozbieznosci'):
        for i, item in enumerate(getattr(report, section)):
            for line in item.kraje:
                yield f'{section}.{i}.kraje.{line.kraj}', line, item.temat, line.kraj
            if section == 'wzorce_zbieznosci':
                yield f'{section}.{i}.sygnaly_przeciwne', item.sygnaly_przeciwne, item.temat, None
    for i, item in enumerate(report.autoobraz):
        yield f'autoobraz.{i}', item, None, None


def _independent(evidence, registry):
    from types import SimpleNamespace
    from paralaksa.aggregate.sample import independence_count
    return independence_count([SimpleNamespace(source_id=e.zrodlo, article_id=e.article_id,
        publisher_group=registry.get(e.signal_id, {}).get('publisher_group'),
        content_group=registry.get(e.signal_id, {}).get('content_group')) for e in evidence])


def provenance_errors(report, package):
    registry = {s['signal_id']: s for s in package.get('dowody', [])}
    errors = []
    for path, item, theme, country in evidence_items(report):
        if not item.article_ids and path.endswith('sygnaly_przeciwne'):
            if item.dowody:
                errors.append(f'{path}: dowody bez article_ids')
            continue
        if not item.dowody:
            errors.append(f'{path}: brak powiązania tezy z sygnałami (dowody)')
        if getattr(item, 'temat', theme) != theme:
            errors.append(f'{path}: temat nagłówka różni się od theme_id dowodów')
        if theme == '':
            errors.append(f'{path}: wymagany theme_id')
        if set(item.article_ids) != {e.article_id for e in item.dowody}:
            errors.append(f'{path}: article_ids nie odpowiadają dowodom')
        for e in item.dowody:
            actual = registry.get(e.signal_id)
            if not actual or any(actual[k] != v for k,v in e.model_dump().items()):
                errors.append(f'{path}: obcy dowód #{e.article_id}; niezgodne ID, temat, kraj lub źródło')
            elif (theme and e.theme_id != theme) or (country and e.kraj != country):
                errors.append(f'{path}: artykuł #{e.article_id} poza tematem/segmentem tezy')
        if path.startswith('autoobraz.'):
            valid = [registry[e.signal_id] for e in item.dowody if e.signal_id in registry]
            if any(s['subject_actor'] != item.kraj for s in valid) or not (
                any(s['kraj'] == item.kraj for s in valid) and any(s['kraj'] != item.kraj for s in valid)):
                errors.append(f'{path}: autoobraz wymaga osobnych dowodów własnych i zewnętrznych o tym samym aktorze')
        if hasattr(item, 'n_zrodel'):
            if item.n_zrodel != _independent(item.dowody, registry):
                errors.append(f'{path}: n_zrodel nie odpowiada niezależnym przywołanym dowodom')
        level = getattr(item, 'pewnosc', None)
        if isinstance(level, str):
            countries = {e.kraj for e in item.dowody}
            counts = [_independent([e for e in item.dowody if e.kraj == c], registry) for c in countries]
            if level != 'niski' and (not counts or min(counts) < package['progi']['min_zrodel_na_kraj']):
                errors.append(f'{path}: jeden niezależny głos w kraju wymaga niskiej pewności')
            if level == 'wysoki' and len(countries) < package['progi']['min_krajow']:
                errors.append(f'{path}: wysoka pewność wymaga progu krajów')
    for section in ('wzorce_zbieznosci', 'rozbieznosci'):
        for i, item in enumerate(getattr(report, section)):
            if section == 'wzorce_zbieznosci':
                qualified = {k['kraj'] for c in package.get('zbieznosc_kandydaci', [])
                             if c['temat'] == item.temat for k in c['kraje'] if k['spelnia_prog_zrodel']}
                if len({k.kraj for k in item.kraje} & qualified) < package['progi']['min_krajow']:
                    errors.append(f'{section}.{i}: kraje nie należą do kwalifikowanego segmentu zbieżności')
                allowed_counter = {s['signal_id'] for c in package.get('zbieznosc_kandydaci', [])
                                   if c['temat'] == item.temat for s in c['sygnaly_przeciwne']}
                if any(e.signal_id not in allowed_counter for e in item.sygnaly_przeciwne.dowody):
                    errors.append(f'{section}.{i}: dowód nie należy do segmentu sygnałów przeciwnych')
            counts = [_independent(k.dowody, registry) for k in item.kraje]
            level = item.pewnosc.poziom
            if (section == 'wzorce_zbieznosci' or level != 'niski') and (
                    not counts or min(counts) < package['progi']['min_zrodel_na_kraj']):
                errors.append(f'{section}.{i}: niespełniony próg niezależnych źródeł na kraj')
            if level == 'wysoki' and len({k.kraj for k in item.kraje}) < package['progi']['min_krajow']:
                errors.append(f'{section}.{i}: wysoka pewność poniżej progu krajów')
    return errors


def language_errors(report, package):
    errors = []
    single = {c for c, info in package.get('kraje', {}).items() if info['n_zrodel'] <= 1}
    adjectives = {'CN':'chińsk', 'QA':'katarsk', 'US':'amerykańsk', 'IL':'izraelsk',
                  'PS':'palestyńsk', 'TR':'tureck', 'BR':'brazylijsk', 'PL':'polsk',
                  'UA':'ukraińsk', 'DE':'niemieck', 'UK':'brytyjsk'}
    for path, text in _texts(report):
        for country in single:
            code = re.escape(country)
            adj = adjectives.get(country, '(?!)')
            if re.search(rf'(?:media|medi(?:ów|ach|ami)|źródła|źródeł)\s+(?:(?:z|w)\s+)?(?:{code}\b|{adj}\w*)', text, re.I):
                errors.append(f'{path}: kraj {country} z jednym źródłem — podaj nazwę redakcji')
        # A conservative tripwire; semantic review remains necessary for paraphrases.
        for sentence in re.split(r'[.!?;\n]', text):
            if re.search(r'\bJS\b|Jensen', sentence, re.I) and re.search(
                    r'(?:pokryw|podob|zbież|rozbież|rozjazd).*ram|ram.*(?:pokryw|podob|zbież|rozbież)', sentence, re.I):
                if not re.search(r'nie (?:mierzy|oznacza|dowodzi)', sentence, re.I):
                    errors.append(f'{path}: JS mierzy rozkłady nacechowania, nie podobieństwo ram')
        if not package.get('publikacje', {}).get('today_language_allowed', False) and re.search(
                r'\bdziś\b|\bdzisiaj\b|dzisiejsz', text, re.I):
            errors.append(f'{path}: data pobrania nie dowodzi publikacji dzisiaj')
        if re.search(r'\bmedia\b|\bmedi(?:ach|ów|ami)\b', text, re.I) and not re.search(r'analizowan|badanych|prób', text, re.I):
            errors.append(f'{path}: opisz analizowane źródła, nie wszystkie media kraju')
        if not package['linia_bazowa']['dostepna'] and re.search(r'rośnie od|maleje od|trend wzrost|trend spad|nowy temat', text, re.I):
            errors.append(f'{path}: trend bez linii bazowej')
    if not package['linia_bazowa']['dostepna']:
        errors += [f'co_sie_przesuwa.{i}: brak linii bazowej' for i,_ in enumerate(report.co_sie_przesuwa)]
    return errors


def _attributed_texts(report):
    """(path, prose, evidence) for every place where the text names publishers or countries."""
    for section in ('w_skrocie', 'slabe_sygnaly', 'co_sie_przesuwa', 'nieobecne_w_polsce'):
        for i, item in enumerate(getattr(report, section)):
            yield f'{section}.{i}', item.tekst, item.dowody
    for i, p in enumerate(report.wzorce_zbieznosci):
        yield f'wzorce_zbieznosci.{i}', f'{p.kierunek} {p.wspolny_kierunek}', [e for k in p.kraje for e in k.dowody]
        yield f'wzorce_zbieznosci.{i}.sygnaly_przeciwne', p.sygnaly_przeciwne.tekst, p.sygnaly_przeciwne.dowody
    for i, d in enumerate(report.rozbieznosci):
        yield f'rozbieznosci.{i}', d.tekst, [e for k in d.kraje for e in k.dowody]
    for i, a in enumerate(report.autoobraz):
        yield f'autoobraz.{i}', f'{a.jak_opisuje_siebie} {a.jak_opisuja_go_inni} {a.komentarz}', a.dowody


def attribution_errors(report, package):
    """Every publisher named in a claim and every country code it uses must be backed by its evidence.

    Metadata checks alone let prose credit BBC for a view whose five signals come from other
    newsrooms (report 2026-09-23). Aliases are word-start prefixes, so Polish inflection matches
    ("Guardian" -> "Guardiana"). Country adjectives ("brytyjskie media") are not detected.
    """
    sources = package.get('mianowniki_zrodel', [])
    countries = set(package.get('kraje', {})) | {s['country'] for s in sources}
    alias_re = {s['source_id']: re.compile('|'.join(r'(?<!\w)' + re.escape(a) for a in s.get('aliases') or [s['name']]))
                for s in sources}
    errors = []
    for path, text, evidence in _attributed_texts(report):
        if not evidence and path.endswith('sygnaly_przeciwne'):
            continue
        cited_sources = {e.zrodlo for e in evidence}
        cited_countries = {e.kraj for e in evidence}
        for sid, rx in alias_re.items():
            if sid not in cited_sources and rx.search(text):
                errors.append(f'{path}: tekst wymienia redakcję {sid}, ale żaden dowód nie pochodzi z {sid} — '
                              'usuń ją z tekstu albo dodaj jej sygnał')
        allowed = {'PL'} if path.startswith('nieobecne_w_polsce') else set()
        for code in sorted(countries - cited_countries - allowed):
            if re.search(rf'(?<![\w-]){code}(?![\w-])', text):
                errors.append(f'{path}: tekst przypisuje przekaz krajowi {code}, ale żaden dowód nie pochodzi z {code}')
    return errors
