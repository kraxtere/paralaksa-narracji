"""Data package for the synthesis (SPEC §9.3).

Every item carries article ids so the synthesis can reference concrete articles. Direction
convergence uses a coarse stance direction instead of frame-label embeddings (embeddings: KM4).
Keys are Polish because the package goes verbatim into a Polish prompt.
"""

from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import combinations

from paralaksa.aggregate.metrics import (
    SignalRow, compute_daily_metrics, country_article_counts, day_signals, top_frames,
)
from paralaksa.aggregate.stats import coarse_direction, distribution, js_divergence, z_score
from paralaksa.config import Settings, Theme
from paralaksa.aggregate.sample import publication_meta, sample_metadata, sample_articles, independence_count

MAX_IDS = 10                 # ile article_ids na pozycję trafia do payloadu (walidator zna wszystkie)
MAX_FRAME_IDS = 5
MAX_DIVERGENCES = 8
MIN_SIGNALS_DIVERGENCE = 3   # min. sygnałów kraju w temacie, żeby liczyć rozkład stance
MAX_SHIFTS = 10


def _r(x: float | None, nd: int = 3) -> float | None:
    return None if x is None else round(x, nd)


def _shift(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


# ------------------------------------------------------------------ representative signals

def representative(signals: list[SignalRow], n: int, prefer: str | None = None) -> list[dict]:
    """Up to n signals, one per article, spread over sources; strongest (and `prefer` direction) first."""
    ranked = sorted(signals, key=lambda s: (
        prefer is not None and coarse_direction(s.stance) != prefer,
        s.stance == "neutralny", -s.intensity, s.id,
    ))
    picked: list[SignalRow] = []
    seen_articles: set[int] = set()
    for pass_new_sources in (True, False):
        used_sources = {p.source_id for p in picked}
        for s in ranked:
            if len(picked) >= n:
                break
            if s.article_id in seen_articles or (pass_new_sources and s.source_id in used_sources):
                continue
            picked.append(s)
            seen_articles.add(s.article_id)
            used_sources.add(s.source_id)
    return [signal_dict(s) for s in picked]


def signal_dict(s: SignalRow) -> dict:
    # Bez URL: model odwołuje się do article_id, a render rozwiązuje id -> URL z bazy (krótszy payload).
    return {
        "signal_id": s.id, "theme_id": s.theme_id, "subject_actor": s.subject_actor,
        "content_group": s.content_group or str(s.article_id), "publisher_group": s.publisher_group or s.source_id,
        "article_id": s.article_id, "kraj": s.country, "zrodlo": s.source_id, "typ_zrodla": s.source_type,
        "rama": s.frame, "stance": s.stance, "intensywnosc": s.intensity, "streszczenie": s.summary_pl,
    }


def _ids(signals: list[SignalRow]) -> list[int]:
    return sorted({s.article_id for s in signals})[:MAX_IDS]


def _frames(signals: list[SignalRow], n: int = 3) -> list[dict]:
    return [{"rama": f, "n_artykulow": na, "n_zrodel": ns, "article_ids": ids[:MAX_FRAME_IDS]}
            for f, na, ns, ids in top_frames(signals, n)]


# ------------------------------------------------------------------ history

def _history(conn: sqlite3.Connection, start: str, end: str):
    """Shares from daily_metrics in [start, end): {(theme, country): {day: share}}, {country: set(days)}."""
    shares: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    days: dict[str, set[str]] = defaultdict(set)
    for r in conn.execute(
        "SELECT date, theme_id, country, article_share FROM daily_metrics WHERE date >= ? AND date < ? "
        "AND date != COALESCE((SELECT MIN(substr(fetched_at,1,10)) FROM articles), '')",
        (start, end),
    ):
        shares[(r[1], r[2])][r[0]] = r[3]
        days[r[2]].add(r[0])
    return shares, days


# ------------------------------------------------------------------ package parts

def _country_direction(sigs: list[SignalRow], min_nonneutral: float) -> tuple[str, float]:
    dirs = Counter(coarse_direction(s.stance) for s in sigs)
    nonneutral = dirs["negatywny"] + dirs["pozytywny"]
    share = nonneutral / len(sigs)
    if share < min_nonneutral:
        return "neutralny", share
    if dirs["negatywny"] == dirs["pozytywny"]:
        return "mieszany", share
    return ("negatywny" if dirs["negatywny"] > dirs["pozytywny"] else "pozytywny"), share


def _convergence(by_theme: dict[str, dict[str, list[SignalRow]]], settings: Settings, n_rep: int):
    th = settings.thresholds
    candidates, weak = [], []
    for theme, per_country in sorted(by_theme.items()):
        info = {}
        for country, sigs in per_country.items():
            direction, share = _country_direction(sigs, th.direction_min_nonneutral)
            info[country] = (direction, share, independence_count(sigs))
        for direction in ("negatywny", "pozytywny"):
            same = [c for c, (d, _, _) in info.items() if d == direction]
            qualified = [c for c in same if info[c][2] >= th.min_sources_per_country]
            if len(same) < 2:
                continue
            others = [c for c in info if c not in same]
            item = {
                "temat": theme, "kierunek": direction,
                "kraje": [{
                    "kraj": c, "n_zrodel": info[c][2], "spelnia_prog_zrodel": c in qualified,
                    "n_artykulow": len({s.article_id for s in per_country[c]}),
                    "udzial_nieneutralnych": _r(info[c][1], 2),
                    "ramy": _frames(per_country[c]),
                    "sygnaly": representative(per_country[c], n_rep, prefer=direction),
                } for c in sorted(same)],
                # Sygnały przeciwne: inne kierunki w tych samych krajach i kraje o innym kierunku.
                "sygnaly_przeciwne": representative(
                    [s for c in same for s in per_country[c]
                     if coarse_direction(s.stance) not in (direction, "neutralny")], n_rep)
                    + [dict(sd, kierunek_kraju=info[sd["kraj"]][0]) for c in sorted(others)
                       for sd in representative(per_country[c], 1)],
            }
            if len(qualified) >= th.min_countries:
                candidates.append(item)
            else:
                below = sorted(c for c in same if c not in qualified)
                item["powod"] = (f"{len(qualified)} kraj(e) z tym kierunkiem spełnia próg "
                                 f"{th.min_sources_per_country} źródeł (wymagane {th.min_countries})"
                                 + (f"; poniżej progu źródeł: {', '.join(below)}" if below else ""))
                weak.append(item)
    return candidates, weak


def _divergences(by_theme: dict[str, dict[str, list[SignalRow]]], n_rep: int) -> list[dict]:
    out = []
    for theme, per_country in by_theme.items():
        eligible = {c: sigs for c, sigs in per_country.items() if len(sigs) >= MIN_SIGNALS_DIVERGENCE}
        if len(eligible) < 2:
            continue
        dists = {c: distribution(s.stance for s in sigs) for c, sigs in eligible.items()}
        pairs = sorted(((js_divergence(dists[a], dists[b]), a, b) for a, b in combinations(sorted(eligible), 2)),
                       reverse=True)
        js, a, b = pairs[0]
        out.append({
            "temat": theme,
            "max_js": _r(js), "para": [a, b],
            "kraje": [{
                "kraj": c, "n_sygnalow": len(sigs), "n_zrodel": independence_count(sigs),
                "rozklad_stance": {k: _r(v, 2) for k, v in dists[c].items() if v},
                "ramy": _frames(sigs)[:2],
                "sygnaly": representative(sigs, 2),
            } for c, sigs in sorted(eligible.items())],
        })
    out.sort(key=lambda d: (-d["max_js"], -len(d["kraje"]), d["temat"]))
    return out[:MAX_DIVERGENCES]


def _self_image(signals: list[SignalRow], countries: list[str], settings: Settings, n_rep: int):
    th = settings.thresholds
    items, skipped = [], []
    for k in countries:
        about = [s for s in signals if s.subject_actor == k]
        own = [s for s in about if s.country == k]
        ext = [s for s in about if s.country != k]
        if len(own) < th.min_signals_self_image or len(ext) < th.min_signals_self_image:
            skipped.append({"kraj": k, "n_wlasne": len(own), "n_zewnetrzne": len(ext)})
            continue
        p, q = distribution(s.stance for s in own), distribution(s.stance for s in ext)
        items.append({
            "kraj": k, "n_wlasne": len(own), "n_zewnetrzne": len(ext),
            "kraje_zewnetrzne": dict(Counter(s.country for s in ext).most_common()),
            "stance_wlasne": {s: _r(v, 2) for s, v in p.items() if v},
            "stance_zewnetrzne": {s: _r(v, 2) for s, v in q.items() if v},
            "js": _r(js_divergence(p, q)),
            "intensywnosc_wlasna": _r(sum(s.intensity for s in own) / len(own), 2),
            "intensywnosc_zewnetrzna": _r(sum(s.intensity for s in ext) / len(ext), 2),
            "ramy_wlasne": _frames(own), "ramy_zewnetrzne": _frames(ext),
            "sygnaly_wlasne": representative(own, n_rep), "sygnaly_zewnetrzne": representative(ext, n_rep),
        })
    items.sort(key=lambda i: -i["js"])
    return items, skipped


def _absent_in_pl(by_theme, shares_today: dict[tuple[str, str], float], countries: list[str],
                  settings: Settings, n_rep: int) -> list[dict]:
    th = settings.thresholds
    if "PL" not in countries:
        return []
    out = []
    for theme, per_country in sorted(by_theme.items()):
        loud = {c: shares_today[(theme, c)] for c in per_country
                if c != "PL" and shares_today[(theme, c)] >= th.absent_in_pl_min_share}
        if len(loud) < 2:
            continue
        avg = sum(loud.values()) / len(loud)
        pl = shares_today.get((theme, "PL"), 0.0)
        if pl < th.absent_in_pl_ratio * avg:
            sigs = [s for c in loud for s in per_country[c]]
            out.append({
                "temat": theme, "udzial_pl": _r(pl), "srednia_innych": _r(avg),
                "udzialy": {c: _r(v) for c, v in sorted(loud.items(), key=lambda kv: -kv[1])},
                "article_ids": _ids(sigs), "sygnaly": representative(sigs, n_rep),
            })
    out.sort(key=lambda i: -i["srednia_innych"])
    return out


def _spillover(conn, day: str, today_metrics: list[dict], settings: Settings) -> list[dict]:
    th = settings.thresholds
    recent_start = _shift(day, -(th.spillover_days - 1))
    before_start = _shift(recent_start, -th.baseline_days)
    before, before_days = _history(conn, before_start, recent_start)
    recent, _ = _history(conn, recent_start, day)
    for m in today_metrics:
        recent[(m["theme_id"], m["country"])][day] = m["article_share"]

    out = []
    for (theme, country), by_day in sorted(recent.items()):
        if len(before_days.get(country, ())) < th.min_history_days_for_trends:
            continue  # bez historii nie wiadomo, czy temat "wcześniej nie występował"
        if (theme, country) in before:
            continue
        earlier = sorted(c for (t, c) in before if t == theme)
        rows = conn.execute(
            """
            SELECT DISTINCT g.article_id FROM signals g JOIN articles a ON a.id = g.article_id
            JOIN sources s ON s.id = a.source_id
            WHERE g.theme_id = ? AND s.country = ? AND substr(a.fetched_at, 1, 10) BETWEEN ? AND ?
            ORDER BY g.article_id DESC
            """,
            (theme, country, recent_start, day),
        ).fetchall()
        out.append({
            "temat": theme, "kraj": country, "pierwszy_dzien": min(by_day),
            "dni_obecnosci": len(by_day), "kraje_wczesniej": earlier,
            "article_ids": sorted(r[0] for r in rows[:MAX_IDS]),
        })
    return out


# ------------------------------------------------------------------ package

def build_data_package(conn: sqlite3.Connection, day: str, settings: Settings, themes: list[Theme]) -> dict:
    th = settings.thresholds
    n_rep = settings.report.representative_signals_per_item
    names = {t.id: t.name_pl for t in themes}
    signals = day_signals(conn, day)
    sample = sample_articles(conn, day)
    publication = publication_meta(conn, day)
    totals = country_article_counts(conn, day)
    countries = sorted(totals)
    metrics = compute_daily_metrics(conn, day, save=False)
    shares_today = defaultdict(float, {(m["theme_id"], m["country"]): m["article_share"] for m in metrics})

    by_theme: dict[str, dict[str, list[SignalRow]]] = defaultdict(lambda: defaultdict(list))
    for s in signals:
        by_theme[s.theme_id][s.country].append(s)

    # --- linia bazowa (dni z metrykami przed dniem raportu)
    hist, hist_days = _history(conn, _shift(day, -th.baseline_days), day)
    baseline = {c: len(hist_days.get(c, ())) for c in countries}
    has_baseline = {c: n >= th.min_history_days_for_trends for c, n in baseline.items()}

    # --- udziały tematów + ramy dominujące. Tematy wyłaniające się z jednego artykułu nie niosą
    # porównania między krajami, więc idą tylko jako zwięzła lista (awans tematów: KM4).
    def article_count(theme: str) -> int:
        return len({s.article_id for sigs in by_theme[theme].values() for s in sigs})

    singletons = sorted(t for t in by_theme if t.startswith("emergent:") and article_count(t) < 2)
    theme_ids = (set(by_theme) - set(singletons)) | {t for (t, c) in hist if has_baseline.get(c)}
    topics, shifts = [], []
    for theme in sorted(theme_ids, key=lambda t: (-sum(shares_today[(t, c)] for c in countries), t)):
        per_country = {}
        for c in countries:
            today = shares_today[(theme, c)]
            sigs = by_theme.get(theme, {}).get(c, [])
            source_totals = Counter(a["source_id"] for a in sample if a["country"] == c)
            source_theme = {sid: len({s.article_id for s in sigs if s.source_id == sid}) for sid in source_totals}
            balanced = sum(source_theme[sid] / total for sid, total in source_totals.items()) / max(1, len(source_totals))
            entry: dict = {"udzial": _r(today), "udzial_rowne_redakcje": _r(balanced),
                           "roznica_wag_pp": _r(100*(today-balanced), 1),
                           "wrazliwosc_wag": abs(today-balanced) >= 0.10,
                           "udzial_po_deduplikacji": _r(
                               len({s.content_group or str(s.article_id) for s in sigs}) /
                               max(1,len({a['content_group'] or str(a['id']) for a in sample if a['country']==c})))}
            if has_baseline[c]:
                series = [hist.get((theme, c), {}).get(d, 0.0) for d in sorted(hist_days[c])]
                mean = sum(series) / len(series)
                z = z_score(today, series, th.min_history_days_for_trends)
                entry.update(srednia_28d=_r(mean), roznica_pp=_r((today - mean) * 100, 1), z=_r(z, 2))
                if abs(today - mean) > 0:
                    shifts.append({"temat": theme, "kraj": c, "udzial": _r(today), "srednia_28d": _r(mean),
                                   "roznica_pp": _r((today - mean) * 100, 1), "z": _r(z, 2),
                                   "article_ids": _ids(sigs)})
            if not sigs and "srednia_28d" not in entry:
                continue
            if sigs:
                entry.update(n_artykulow=len({s.article_id for s in sigs}),
                             n_zrodel=independence_count(sigs),
                             sr_intensywnosc=_r(sum(s.intensity for s in sigs) / len(sigs), 2),
                             ramy=_frames(sigs))
            per_country[c] = entry
        topics.append({"temat": theme, "nazwa": names.get(theme, theme), "kraje": per_country})
    shifts.sort(key=lambda s: (-(abs(s["z"]) if s["z"] is not None else 0), -abs(s["roznica_pp"])))

    candidates, weak = _convergence(by_theme, settings, n_rep)
    self_image, self_image_skipped = _self_image(signals, countries, settings, n_rep)

    return {
        "data": day,
        "publikacje": {k:v for k,v in publication.items() if k != "eligible_ids"},
        "mianowniki_zrodel": sample_metadata(conn, day),
        "dowody": [signal_dict(s) for s in signals],
        "metryka_js": "odległość rozkładów nacechowania; nie mierzy podobieństwa ram",
        "porownania_wewnatrz_krajow": [
            {"kraj": c, "temat": t, "redakcje": [
                {"zrodlo": sid, "rozklad_stance": distribution(s.stance for s in sigs if s.source_id == sid),
                 "sygnaly": representative([s for s in sigs if s.source_id == sid], 2)}
                for sid in sorted({s.source_id for s in sigs})]}
            for t, countries_ in by_theme.items() for c, sigs in countries_.items()
            if len({s.source_id for s in sigs}) >= 2],
        "progi": {"min_krajow": th.min_countries, "min_zrodel_na_kraj": th.min_sources_per_country,
                  "linia_bazowa_dni": th.baseline_days, "min_dni_historii": th.min_history_days_for_trends},
        "linia_bazowa": {
            "dni_historii": baseline,
            "dostepna": any(has_baseline.values()),
            "uwaga": None if any(has_baseline.values()) else
            f"brak linii bazowej (mniej niż {th.min_history_days_for_trends} dni danych) – nie formułuj trendów",
        },
        "kraje": {c: {
            "n_artykulow": totals[c],
            "n_zrodel": independence_count([s for s in signals if s.country == c]),
            "n_sygnalow": sum(1 for s in signals if s.country == c),
            "udzial_sygnalow_tylko_lead": _r(
                sum(1 for s in signals if s.country == c and s.source_depth == "lead_only")
                / max(1, sum(1 for s in signals if s.country == c)), 2),
        } for c in countries},
        "tematy": topics,
        "tematy_wylaniajace_sie_pojedyncze": len(singletons),
        "zbieznosc_kandydaci": candidates,
        "zbieznosc_slabe": weak,
        "rozbieznosci": _divergences(by_theme, n_rep),
        "autoobraz": self_image,
        "autoobraz_pominiete": self_image_skipped,
        "co_sie_przesuwa": shifts[:MAX_SHIFTS],
        "rozlewanie": _spillover(conn, day, metrics, settings),
        "nieobecne_w_polsce": _absent_in_pl(by_theme, shares_today, countries, settings, n_rep),
    }


def known_article_ids(conn: sqlite3.Connection, day: str) -> set[int]:
    """Articles the report may reference: all with signals up to the report day (spillover spans days)."""
    return {r[0] for r in conn.execute(
        "SELECT DISTINCT g.article_id FROM signals g JOIN articles a ON a.id = g.article_id "
        "WHERE substr(a.fetched_at, 1, 10) <= ?", (day,))}
