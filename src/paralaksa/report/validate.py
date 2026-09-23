"""Report validator (SPEC §3, §9.4): references, counter-signals, confidence, thresholds, quote length.

`validate_report` returns error messages for the retry prompt; `sanitize_report` is the last resort
after a failed retry: it drops what cannot be backed by data, so every published claim has a link.
"""

from __future__ import annotations

import re

from paralaksa.report.schema import CountryLine, ReportOutput

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
    """Drop unknown ids and every claim left without references; force trends without a baseline."""
    def keep(ids: list[int]) -> list[int]:
        return [i for i in ids if i in known_ids]

    def lines(ks: list[CountryLine]) -> list[CountryLine]:
        return [k.model_copy(update={"article_ids": keep(k.article_ids)}) for k in ks if keep(k.article_ids)]

    candidates = {c["temat"] for c in package.get("zbieznosc_kandydaci", [])}
    min_countries = package["progi"]["min_krajow"]
    has_baseline = package["linia_bazowa"]["dostepna"]

    patterns = []
    for p in report.wzorce_zbieznosci:
        ks = lines(p.kraje)
        if p.temat in candidates and len({k.kraj for k in ks}) >= min_countries:
            counter = p.sygnaly_przeciwne.model_copy(update={"article_ids": keep(p.sygnaly_przeciwne.article_ids)})
            patterns.append(p.model_copy(update={
                "kraje": ks, "sygnaly_przeciwne": counter,
                "trend": p.trend if has_baseline else NO_BASELINE,
            }))
    divergences = [d.model_copy(update={"kraje": lines(d.kraje)}) for d in report.rozbieznosci if len(lines(d.kraje)) >= 2]

    def claims(items):
        return [c.model_copy(update={"article_ids": keep(c.article_ids)}) for c in items if keep(c.article_ids)]

    cleaned = ReportOutput(
        w_skrocie=claims(report.w_skrocie),
        wzorce_zbieznosci=patterns,
        rozbieznosci=divergences,
        autoobraz=claims(report.autoobraz),
        co_sie_przesuwa=claims(report.co_sie_przesuwa),
        nieobecne_w_polsce=claims(report.nieobecne_w_polsce),
        slabe_sygnaly=claims(report.slabe_sygnaly),
    )
    return ReportOutput.model_validate(_map_strings(cleaned.model_dump(), shorten_quotes))


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
