"""Markdown rendering of the daily report (SPEC §10, without "Ciekawostki" – KM4)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from paralaksa import db
from paralaksa.config import Settings, Source, Theme
from paralaksa.report.schema import CountryLine, ReportOutput

CONFIDENCE_PL = {"niski": "niska", "średni": "średnia", "wysoki": "wysoka"}

LEAD_ONLY_WARN = 0.5   # udział sygnałów "tylko lead", od którego kraj jest oznaczany jako materiał niepełny


@dataclass
class CountryMeta:
    country: str
    sources: list[str]
    articles: int
    signals: int
    lead_only_share: float


@dataclass
class ReportMeta:
    date: str
    countries: list[CountryMeta]
    inactive_sources: list[str]
    stale_sources: list[str]
    cost_by_purpose: dict[str, float]
    extract_models: list[str]
    extract_prompts: list[str]
    synth_model: str
    synth_prompt: str
    pending_articles: int
    theme_names: dict[str, str]
    urls: dict[int, str]
    emergent_singletons: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return sum(self.cost_by_purpose.values())


def collect_meta(conn: sqlite3.Connection, day: str, settings: Settings, sources: list[Source],
                 themes: list[Theme], package: dict, synth_model: str, synth_prompt: str,
                 warnings: list[str]) -> ReportMeta:
    countries = []
    for c, info in package["kraje"].items():
        srcs = [r[0] for r in conn.execute(
            "SELECT DISTINCT a.source_id FROM articles a JOIN sources s ON s.id = a.source_id "
            "WHERE s.country = ? AND substr(a.fetched_at, 1, 10) = ? ORDER BY 1", (c, day))]
        countries.append(CountryMeta(c, srcs, info["n_artykulow"], info["n_sygnalow"],
                                     info["udzial_sygnalow_tylko_lead"]))
    active = [s for s in sources if s.active]
    one = lambda sql, *p: [r[0] for r in conn.execute(sql, p)]  # noqa: E731
    return ReportMeta(
        date=day,
        countries=countries,
        inactive_sources=[f"{s.id} ({s.country})" for s in sources if not s.active],
        stale_sources=db.stale_sources(conn, [s.id for s in active], settings.ingest.stale_source_days),
        cost_by_purpose=dict(conn.execute(
            "SELECT purpose, SUM(cost_usd) FROM api_usage WHERE date = ? GROUP BY purpose", (day,)).fetchall()),
        extract_models=one(
            "SELECT DISTINCT g.model FROM signals g JOIN articles a ON a.id = g.article_id "
            "WHERE substr(a.fetched_at, 1, 10) = ? ORDER BY 1", day),
        extract_prompts=one(
            "SELECT DISTINCT g.prompt_version FROM signals g JOIN articles a ON a.id = g.article_id "
            "WHERE substr(a.fetched_at, 1, 10) = ? AND g.prompt_version IS NOT NULL ORDER BY 1", day),
        synth_model=synth_model,
        synth_prompt=synth_prompt,
        pending_articles=conn.execute(
            "SELECT COUNT(*) FROM articles WHERE extracted = 0 AND substr(fetched_at, 1, 10) = ?", (day,)
        ).fetchone()[0],
        theme_names={t.id: t.name_pl for t in themes},
        urls=dict(conn.execute("SELECT id, url FROM articles").fetchall()),
        emergent_singletons=package.get("tematy_wylaniajace_sie_pojedyncze", 0),
        warnings=list(warnings),
    )


# ------------------------------------------------------------------ helpers

def _refs(ids: list[int], meta: ReportMeta) -> str:
    links = [f"[#{i}]({meta.urls[i]})" if i in meta.urls else f"#{i}" for i in ids]
    return "[" + ", ".join(links) + "]" if links else ""


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _theme(theme_id: str, meta: ReportMeta) -> str:
    return meta.theme_names.get(theme_id, theme_id)


def _country_line(k: CountryLine, meta: ReportMeta) -> str:
    names = sorted({e.zrodlo for e in k.dowody})
    label = ", ".join(names) + f" ({k.kraj})" if k.n_zrodel == 1 and names else f"analizowane źródła z {k.kraj}"
    return f"- **{label}** (źródła: {k.n_zrodel}): {k.rama}, {k.stance} – {_refs(k.article_ids, meta)}"


# ------------------------------------------------------------------ render

def render_markdown(report: ReportOutput, package: dict, meta: ReportMeta) -> str:
    out: list[str] = [f"# Paralaksa narracji – {meta.date}", ""]
    publication = package.get("publikacje", {})
    if publication:
        out += [f"> **Raport {publication['status']}**. Pobranie: {meta.date} UTC. "
                f"Wykryte daty publikacji: {publication['published_min'] or 'brak'} — {publication['published_max'] or 'brak'}.",
                f"> Starsze niż 24 h: {publication['older_than_24h']}; starsze niż 48 h: {publication['older_than_48h']}; "
                f"bez daty: {publication['missing_publication']}; spóźnione poza oknem: {publication['late_articles']} "
                f"({publication['late_share']:.1%}); przyszłe daty: {publication['future_publication']}.", ""]
        if publication['status'] == 'regularny':
            out += [f"> Okno publikacji: [{publication['publication_window_start']}, "
                    f"{publication['publication_window_end_exclusive']}). Starsze i niedatowane uzupełnienia "
                    "nie wchodzą do porównań tego przebiegu.", ""]
        else:
            out += ["> Pierwszy odczyt RSS obejmuje zaległość. Nie służy do oceny trendów ani jako materiał marketingowy.", ""]
    out += ["> **Kontrola semantyczna:** nie wykonano audytu człowieka; automatyczna walidacja sprawdza "
            "powiązania temat–kraj–sygnał, nie dowodzi prawdziwości zdarzeń ani pełnego wynikania tekstu tezy.", ""]
    if meta.warnings:
        out += ["> **Ostrzeżenia walidacji:**"] + [f"> - {w}" for w in meta.warnings] + [""]
    baseline = package["linia_bazowa"]
    if not baseline["dostepna"]:
        days = max(baseline["dni_historii"].values(), default=0)
        out += [f"> Brak linii bazowej: {days} dni historii (wymagane {package['progi']['min_dni_historii']}). "
                "Raport nie formułuje trendów.", ""]
    incomplete = _incomplete(meta)
    if incomplete:
        out += [f"> **Materiał niepełny:** {'; '.join(incomplete)}.", ""]

    out += ["## W skrócie", ""]
    out += [f"- {s.tekst} (pewność: {CONFIDENCE_PL[s.pewnosc]}) {_refs(s.article_ids, meta)}" for s in report.w_skrocie] \
        or ["_Synteza nie zwróciła podsumowania._"]

    out += ["", "## Wzorce zbieżności", ""]
    if not report.wzorce_zbieznosci:
        th = package["progi"]
        out.append(f"_Brak wzorców spełniających progi ({th['min_krajow']} kraje, "
                   f"{th['min_zrodel_na_kraj']} źródła na kraj)._")
    for p in report.wzorce_zbieznosci:
        out += [f"### {_theme(p.temat, meta)}: {p.kierunek}", ""]
        out += [_country_line(k, meta) for k in p.kraje]
        out += [
            "",
            f"**Wspólny kierunek:** {p.wspolny_kierunek}  ",
            f"**Sygnały przeciwne:** {p.sygnaly_przeciwne.tekst} {_refs(p.sygnaly_przeciwne.article_ids, meta)}  ",
            f"**Pewność:** {CONFIDENCE_PL[p.pewnosc.poziom]} – {p.pewnosc.uzasadnienie}  ",
            f"**Trend:** {p.trend}",
            "",
        ]

    out += ["", "## Rozbieżne przekazy", ""]
    if not report.rozbieznosci:
        out.append("_Brak._")
    for d in report.rozbieznosci:
        out += [f"### {_theme(d.temat, meta)}", "", d.tekst, ""]
        out += [_country_line(k, meta) for k in d.kraje]
        out += ["", f"**Pewność:** {CONFIDENCE_PL[d.pewnosc.poziom]} – {d.pewnosc.uzasadnienie}", ""]

    out += ["", "## Autoobraz vs obraz zewnętrzny", ""]
    js = {a["kraj"]: a for a in package.get("autoobraz", [])}
    if report.autoobraz:
        out += ["| kraj | jak opisuje siebie | jak opisują go inni | odległość rozkładów nacechowania (JS) | sygnały (własne/zewn.) | komentarz |",
                "|---|---|---|---|---|---|"]
        for a in report.autoobraz:
            data = js.get(a.kraj, {})
            value = f"{data['js']:.2f}" if "js" in data else "–"
            counts = f"{data.get('n_wlasne', '–')}/{data.get('n_zewnetrzne', '–')}"
            out.append(f"| {a.kraj} | {_cell(a.jak_opisuje_siebie)} | {_cell(a.jak_opisuja_go_inni)} | {value} | "
                       f"{counts} | pewność: {CONFIDENCE_PL[a.pewnosc]}; {_cell(a.komentarz)} {_refs(a.article_ids, meta)} |")
    else:
        out.append("_Brak._")

    out += ["", "## Co się przesuwa", ""]
    if not baseline["dostepna"]:
        out.append("_Brak linii bazowej – zmian względem 28 dni jeszcze nie liczymy._")
    out += [f"- {c.tekst} {_refs(c.article_ids, meta)}" for c in report.co_sie_przesuwa]
    if baseline["dostepna"] and not report.co_sie_przesuwa:
        out.append("_Brak istotnych zmian._")

    out += ["", "## Nieobecne w Polsce", ""]
    out += [f"- **{_theme(c.temat, meta)}**: {c.tekst} {_refs(c.article_ids, meta)}" for c in report.nieobecne_w_polsce] \
        or ["_Brak._"]

    if report.slabe_sygnaly:
        out += ["", "## Słabe sygnały (poniżej progów)", ""]
        out += [f"- {c.tekst} {_refs(c.article_ids, meta)}" for c in report.slabe_sygnaly]

    out += ["", "## Zakres i mianowniki pobranej próbki", "",
            "Udziały dotyczą pobranej próbki. Nie są udziałami całego przekazu krajów. "
            "JS porównuje nacechowanie; ramy są analizowane jakościowo.", "",
            "| redakcja / kraj / język | zakres | pobrane / w porównaniu | pełny tekst / lead | news / opinion / unknown | oczekujące / błędy |",
            "|---|---|---|---|---|---|"]
    for row in package.get('mianowniki_zrodel', []):
        genres = row['genres']
        out.append(f"| {_cell(row['name'])} / {row['country']} / {row['language']} | {_cell(row['scope'] or 'nieznany')} | "
                   f"{row['articles']} / {row['eligible']} | {row['fulltext']} / {row['lead_only']} | "
                   f"{genres.get('news',0)} / {genres.get('opinion',0)} / {genres.get('unknown',0)} | "
                   f"{row['pending']} / {row['failed']} |")
    out += ["", "### Wrażliwość na ważenie redakcji", "",
            "Porównujemy udział liczony po artykułach i średni udział przy równej wadze każdej redakcji. "
            "Flaga pojawia się od różnicy 10 punktów procentowych; nie jest testem istotności.", "",
            "| temat / kraj | po artykułach | równe redakcje | po deduplikacji | wrażliwość |", "|---|---|---|---|---|"]
    for topic in package.get('tematy', []):
        for country, values in topic['kraje'].items():
            if 'udzial_rowne_redakcje' in values:
                out.append(f"| {_theme(topic['temat'],meta)} / {country} | {values['udzial']:.1%} | "
                           f"{values['udzial_rowne_redakcje']:.1%} | {values['udzial_po_deduplikacji']:.1%} | {'TAK' if values['wrazliwosc_wag'] else '—'} |")
    out += ["", "Syndykacja: identyczne długie teksty/leady nie zwiększają liczby niezależnych głosów. "
            "Przeredagowane i tłumaczone depesze mogą pozostać nierozpoznane.", "", *_metadata(meta), ""]
    return "\n".join(out)


def _incomplete(meta: ReportMeta) -> list[str]:
    notes = [f"{c.country}: {c.lead_only_share:.0%} sygnałów tylko z tytułu i leadu"
             for c in meta.countries if c.lead_only_share >= LEAD_ONLY_WARN]
    if meta.pending_articles:
        notes.append(f"{meta.pending_articles} artykułów bez ekstrakcji (limit kosztów lub błędy przejściowe)")
    return notes


def _metadata(meta: ReportMeta) -> list[str]:
    out = ["## Metadane", "",
           "| kraj | źródła | artykuły | sygnały | tylko lead |", "|---|---|---|---|---|"]
    for c in meta.countries:
        out.append(f"| {c.country} | {', '.join(c.sources)} | {c.articles} | {c.signals} | {c.lead_only_share:.0%} |")
    costs = ", ".join(f"{k} ${v:.3f}" for k, v in sorted(meta.cost_by_purpose.items()))
    out += [
        "",
        f"- Koszt API dnia: ${meta.total_cost:.3f}" + (f" ({costs})" if costs else ""),
        f"- Modele: ekstrakcja {', '.join(meta.extract_models) or '–'}; synteza {meta.synth_model}",
        f"- Prompty: {', '.join(meta.extract_prompts) or '–'}; {meta.synth_prompt}",
        f"- Źródła nieaktywne: {', '.join(meta.inactive_sources) or 'brak'}",
        f"- Źródła bez nowych artykułów: {', '.join(meta.stale_sources) or 'brak'}",
        f"- Tematy wyłaniające się z pojedynczych artykułów (poza raportem): {meta.emergent_singletons}",
        "- Raport opisuje przekaz medialny, nie fakty. Odnośniki prowadzą do artykułów źródłowych.",
    ]
    return out
