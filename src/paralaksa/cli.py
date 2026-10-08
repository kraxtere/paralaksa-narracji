"""Command-line interface: plx."""

from __future__ import annotations

import json
import os
import logging
from datetime import date
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from paralaksa import db
from paralaksa.config import DEFAULT_CONFIG_DIR, load_settings, load_sources, load_themes
from paralaksa.ingest.http import PoliteClient
from paralaksa.ingest.rss import ingest_sources

app = typer.Typer(help="Paralaksa narracji – analiza przekazu medialnego z wielu krajów.", no_args_is_help=True)

ConfigDir = typer.Option(DEFAULT_CONFIG_DIR, "--config-dir", help="Katalog z plikami YAML.")
DbPath = typer.Option(None, "--db", help="Ścieżka do bazy (domyślnie z settings.yaml).")


def _open_db(config_dir: Path, db_path: Optional[Path]):
    settings = load_settings(config_dir)
    conn = db.connect(db_path or settings.resolved_db_path())
    db.init_db(conn)
    return settings, conn


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Więcej logów.")) -> None:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


@app.command("init-db")
def init_db_cmd(config_dir: Path = ConfigDir, db_path: Optional[Path] = DbPath) -> None:
    """Utwórz bazę i schemat, wczytaj źródła z konfiguracji."""
    settings, conn = _open_db(config_dir, db_path)
    sources = load_sources(config_dir)
    db.upsert_sources(conn, sources)
    load_themes(config_dir)  # walidacja taksonomii
    typer.echo(f"Baza gotowa: {db_path or settings.resolved_db_path()} ({len(sources)} źródeł w konfiguracji)")


@app.command()
def sources(config_dir: Path = ConfigDir) -> None:
    """Pokaż listę źródeł i ich status."""
    all_sources = load_sources(config_dir)
    active = [s for s in all_sources if s.active]
    typer.echo(f"Aktywne źródła ({len(active)}):")
    for s in active:
        feeds = ", ".join(f.section or f.url for f in s.feeds)
        typer.echo(f"  {s.id:<14} {s.country}  {s.language}  {s.type:<10} {s.name}  [{feeds}]")
    inactive = [s for s in all_sources if not s.active]
    if inactive:
        typer.echo(f"\nNieaktywne ({len(inactive)}):")
        for s in inactive:
            typer.echo(f"  {s.id:<14} {s.country}  {s.name}: {s.note or 'brak komentarza'}")


@app.command()
def ingest(
    source: Optional[list[str]] = typer.Option(None, "--source", "-s", help="Tylko wskazane źródła (id); można powtórzyć."),
    no_fulltext: bool = typer.Option(False, "--no-fulltext", help="Nie pobieraj pełnych tekstów."),
    config_dir: Path = ConfigDir,
    db_path: Optional[Path] = DbPath,
) -> None:
    """Pobierz nowe artykuły z aktywnych kanałów RSS."""
    settings, conn = _open_db(config_dir, db_path)
    all_sources = load_sources(config_dir)
    if source:
        known = {s.id for s in all_sources}
        unknown = sorted(set(source) - known)
        if unknown:
            typer.echo(f"Nieznane źródła: {', '.join(unknown)}", err=True)
            raise typer.Exit(code=2)
        selected = [s for s in all_sources if s.id in source and s.feeds and s.active]
    else:
        selected = [s for s in all_sources if s.active]
    if not selected:
        typer.echo("Brak źródeł do pobrania.", err=True)
        raise typer.Exit(code=1)

    _run_ingest(conn, settings, selected, fulltext=not no_fulltext)
    conn.close()


def _run_ingest(conn, settings, selected, fulltext: bool) -> int:
    cfg = settings.ingest
    with PoliteClient(cfg.user_agent, cfg.per_domain_delay_s, cfg.timeout_s) as client:
        results = ingest_sources(conn, client, selected, settings, fulltext=fulltext)

    typer.echo(f"{'źródło':<14} {'pobrane':>8} {'nowe':>6} {'odfiltr.':>9} {'duplik.':>8} {'pełny tekst':>12} {'błędy':>6}")
    for r in results:
        typer.echo(
            f"{r.source_id:<14} {r.fetched:>8} {r.new:>6} {r.filtered:>9} {r.duplicates:>8} {r.fulltext_ok:>12} {len(r.errors):>6}"
        )
    total_new = sum(r.new for r in results)
    typer.echo(f"Razem nowych artykułów: {total_new}")
    for r in results:
        for err in r.errors:
            typer.echo(f"BŁĄD [{r.source_id}] {err}", err=True)

    stale = db.stale_sources(conn, [s.id for s in selected], cfg.stale_source_days)
    for sid in stale:
        typer.echo(f"OSTRZEŻENIE: źródło '{sid}' nie dało nowych artykułów od {cfg.stale_source_days} dni.", err=True)
    return total_new


@app.command()
def extract(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Maks. liczba artykułów."),
    no_batch: bool = typer.Option(False, "--no-batch", help="Zawsze wywołania bezpośrednie (bez Batches API)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Tylko szacunek kosztu, bez wywołań API."),
    config_dir: Path = ConfigDir,
    db_path: Optional[Path] = DbPath,
) -> None:
    """Wydobądź sygnały narracyjne z nieprzetworzonych artykułów (LLM)."""
    from paralaksa.extract.signals import estimate_pending

    settings, conn = _open_db(config_dir, db_path)
    themes = load_themes(config_dir)
    budget = settings.budget.max_daily_usd
    spent = db.spent_on(conn, db.utc_now().date().isoformat())

    if dry_run:
        n, tokens, cost, mode = estimate_pending(conn, settings, themes, limit, use_batch=not no_batch)
        typer.echo(f"Artykuły do ekstrakcji: {n} (tryb: {mode}, model: {settings.models.extract})")
        typer.echo(f"Szacunek: ~{tokens:,} tokenów wejścia, ~${cost:.3f}")
        typer.echo(f"Wydano dziś: ${spent:.3f} z limitu ${budget:.2f}")
        conn.close()
        return

    stats = _run_extract(conn, settings, themes, limit, use_batch=not no_batch)
    conn.close()
    if stats.failed or stats.deferred:
        raise typer.Exit(code=1)


def _run_extract(conn, settings, themes, limit, use_batch: bool):
    from paralaksa.extract.llm_client import build_client
    from paralaksa.extract.signals import extract_pending

    cfg = settings.extract
    llm = build_client(settings.models.extract, settings.pricing, cfg.batch_poll_interval_s, cfg.batch_timeout_h)
    stats = extract_pending(conn, llm, settings, themes, limit, use_batch=use_batch)

    typer.echo(f"Tryb: {stats.mode}" + (f" (batch {stats.batch_id})" if stats.batch_id else ""))
    typer.echo(
        f"Artykuły: {stats.pending} | przetworzone: {stats.done} | sygnały: {stats.signals} | "
        f"ponowienia: {stats.retries} | błędy trwałe: {stats.failed} | odłożone: {stats.deferred}"
    )
    typer.echo(f"Naprawione evidence_span: {stats.repairs} | odrzucone sygnały: {stats.dropped} | "
               f"pominięte poza oknem publikacji: {stats.skipped}")
    total = db.spent_on(conn, db.utc_now().date().isoformat())
    typer.echo(f"Koszt przebiegu: ${stats.cost_usd:.4f} | wydano dziś: ${total:.4f} "
               f"z limitu ${settings.budget.max_daily_usd:.2f}")
    if stats.budget_stopped:
        typer.echo("OSTRZEŻENIE: osiągnięto dzienny limit kosztów – część artykułów czeka na kolejny przebieg.", err=True)
    return stats


def _parse_day(value: Optional[str]) -> str:
    if value is None:
        return db.utc_now().date().isoformat()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        typer.echo(f"Niepoprawna data '{value}' (oczekiwano RRRR-MM-DD).", err=True)
        raise typer.Exit(code=2)


DayOpt = typer.Option(None, "--date", "-d", help="Dzień RRRR-MM-DD (UTC, wg daty pobrania artykułów); domyślnie dziś.")
OutDir = typer.Option(None, "--out-dir", help="Katalog raportów (domyślnie z settings.yaml: reports/).")


@app.command()
def aggregate(day: Optional[str] = DayOpt, config_dir: Path = ConfigDir, db_path: Optional[Path] = DbPath) -> None:
    """Policz metryki dzienne (udziały tematów per kraj) i zapisz w daily_metrics."""
    from paralaksa.aggregate.metrics import compute_daily_metrics

    settings, conn = _open_db(config_dir, db_path)
    d = _parse_day(day)
    rows = compute_daily_metrics(conn, d)
    typer.echo(f"{d}: zapisano {len(rows)} wierszy daily_metrics "
               f"({len({r['theme_id'] for r in rows})} tematów, {len({r['country'] for r in rows})} krajów)")
    conn.close()


def _run_report(conn, settings, config_dir: Path, d: str, out_dir: Optional[Path]):
    from paralaksa.extract.llm_client import build_client
    from paralaksa.report.pipeline import generate_report

    cfg = settings.extract
    llm = build_client(settings.models.synthesize, settings.pricing, cfg.batch_poll_interval_s, cfg.batch_timeout_h)
    result = generate_report(conn, llm, settings, load_sources(config_dir), load_themes(config_dir), d,
                             out_dir or settings.report.resolved_output_dir())
    s = result.synth
    typer.echo(f"Raport: {result.path}")
    typer.echo(f"Synteza: {s.model} | wywołania: {s.calls} | ponowienie: {'tak' if s.retried else 'nie'} | "
               f"tokeny: {s.input_tokens:,} wej. / {s.output_tokens:,} wyj. | koszt ${s.cost_usd:.4f}")
    typer.echo(f"Koszt API dnia: ${result.day_cost_usd:.4f} z limitu ${settings.budget.max_daily_usd:.2f}")
    for w in s.warnings:
        typer.echo(f"OSTRZEŻENIE: {w}", err=True)
    return result


@app.command()
def report(
    day: Optional[str] = DayOpt,
    out_dir: Optional[Path] = OutDir,
    config_dir: Path = ConfigDir,
    db_path: Optional[Path] = DbPath,
) -> None:
    """Zbuduj raport dzienny: metryki, pakiet danych, synteza LLM, walidacja, Markdown."""
    settings, conn = _open_db(config_dir, db_path)
    result = _run_report(conn, settings, config_dir, _parse_day(day), out_dir)
    conn.close()
    if not result.complete:
        raise typer.Exit(code=1)


@app.command()
def board(
    event_file: Path = typer.Argument(..., exists=True, dir_okay=False, help="Plik YAML zdarzenia (events/*.yaml)."),
    out_dir: Path = typer.Option(Path("data/boards"), "--out-dir", "-o", help="Katalog wyjściowy."),
    png: bool = typer.Option(True, "--png/--no-png", help="Zrzut PNG 1080×1920 przez przeglądarkę headless."),
    config_dir: Path = ConfigDir,
    db_path: Optional[Path] = DbPath,
) -> None:
    """Plansza „Paralaksa zdarzeń”: nagłówki o jednym zdarzeniu z wielu krajów, bez komentarza."""
    from paralaksa.board.render import BoardError, collect_board, find_browser, render_html, screenshot
    from paralaksa.board.spec import load_event

    spec = load_event(event_file)
    _, conn = _open_db(config_dir, db_path)
    try:
        b = collect_board(conn, spec)
    except BoardError as e:
        typer.echo(f"BŁĄD: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        conn.close()
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{spec.id}.html"
    html_path.write_text(render_html(b), encoding="utf-8")
    typer.echo(f"{spec.id}: {len(b.groups)} krajów, {b.n_headlines} nagłówków: {html_path}")
    if png:
        browser = find_browser()
        if not browser:
            typer.echo("OSTRZEŻENIE: brak Chromium/Chrome/Edge (ustaw PLX_BROWSER); pominięto PNG", err=True)
            return
        png_path = out_dir / f"{spec.id}.png"
        screenshot(html_path, png_path, browser)
        typer.echo(f"PNG: {png_path}")


@app.command()
def site(
    out_dir: Path = typer.Option(Path("data/site"), "--out-dir", "-o", help="Katalog strony (nadpisywany w całości)."),
    events_dir: Path = typer.Option(Path("events"), "--events", help="Katalog kart zdarzeń."),
    reports_dir: Path = typer.Option(Path("reports"), "--reports", help="Katalog raportów dziennych (JSON)."),
    make_zip: bool = typer.Option(False, "--zip", help="Dodatkowo spakuj stronę do .zip (do przesłania)."),
    publish_site: bool = typer.Option(False, "--publikuj",
                                      help="Wypchnij stronę do prywatnego repo SITE_REPO (Render, pod hasłem)."),
    publish_hf: bool = typer.Option(False, "--publikuj-hf",
                                    help="Wypchnij stronę do Space na Hugging Face (HF_SPACE i HF_TOKEN w .env); zapasowy hosting."),
    no_stories: bool = typer.Option(False, "--bez-historii",
                                    help="Nie wywołuj modelu: historie dnia i tłumaczenia nagłówków tylko z zapisanych."),
    stories_dir: Path = typer.Option(Path("data/stories"), "--historie-dir", help="Zapisane historie dnia (JSON)."),
    titles_dir: Path = typer.Option(Path("data/tytuly"), "--tytuly-dir", help="Zapisane tłumaczenia nagłówków (JSON)."),
    with_tv: bool = typer.Option(False, "--z-tv", help="Z zakładką Telewizja (raporty TV GDELT, tłumaczenia i historie, "
                                 "ok. 0,2 $ dziennie). Domyślnie bez (decyzja 2026-10-01: skupiamy się na prasie)."),
    tv_days: int = typer.Option(7, "--tv-dni", min=1, max=31, help="Ile ostatnich dni w zakładce Telewizja."),
    config_dir: Path = ConfigDir,
    db_path: Optional[Path] = DbPath,
) -> None:
    """Strona wewnętrzna: interaktywne karty zdarzeń i dziennik z bazy. Statyczne pliki HTML.

    --publikuj: jeden commit do prywatnego repo z SITE_REPO (właściciel/nazwa, w .env); Render wydaje stronę pod hasłem.
    Publiczne repo jest odrzucane.

    Historie dnia (wydarzenia opisywane w wielu krajach): jedno wywołanie modelu ekstrakcji na dzień, wynik zapisany
    w --historie-dir i używany przy kolejnych budowach. Tłumaczenia wszystkich nagłówków dnia na polski: porcje po 120,
    zapis w --tytuly-dir, przy kolejnych budowach tylko nowe artykuły. Daily ich nie liczy."""
    from paralaksa.config import load_themes
    from paralaksa.events.check import open_db_readonly
    import sqlite3

    from paralaksa.extract.llm_client import build_client
    from paralaksa.site import stories, titles
    from paralaksa.site.build import build_site, zip_site

    settings = load_settings(config_dir)
    path = db_path or settings.resolved_db_path()
    conn = open_db_readonly(path)
    if conn is None:
        typer.echo(f"OSTRZEŻENIE: brak bazy {path}; strona bez dziennika i bez odnośników do bazy", err=True)
    else:
        conn.row_factory = sqlite3.Row

    model = settings.models.site_model()
    client = None
    spent = 0.0

    def stories_for(day: str, eligible: set[int]) -> dict | None:
        nonlocal client, spent
        items = stories.story_items(conn, day, eligible)
        cached = stories.load_cached(stories_dir, day, items)
        if cached is not None or no_stories:
            return cached
        try:
            client = client or build_client(model, settings.pricing, settings.extract.batch_poll_interval_s,
                                            settings.extract.batch_timeout_h)
            out = stories.generate(client, model, day, items, stories_dir)
        except RuntimeError as e:
            typer.echo(f"OSTRZEŻENIE: {e}; strona bez historii dnia {day}", err=True)
            return None
        spent += out["cost_usd"]
        typer.echo(f"Historie dnia {day}: {len(out['historie'])} ({out['input_tokens']} + {out['output_tokens']} tokenów, "
                   f"{out['cost_usd']:.3f} $)")
        return out

    def titles_for(day: str, ids: set[int]) -> dict[int, str]:
        nonlocal client, spent
        if no_stories:
            return titles.cached(titles_dir, day)
        items = titles.title_items(conn, ids)
        known = titles.cached(titles_dir, day)
        if all(i["id"] in known for i in items):
            return known
        try:
            client = client or build_client(model, settings.pricing, settings.extract.batch_poll_interval_s,
                                            settings.extract.batch_timeout_h)
            out = titles.translate(client, model, day, items, titles_dir)
        except RuntimeError as e:
            typer.echo(f"OSTRZEŻENIE: {e}; nagłówki dnia {day} bez tłumaczenia", err=True)
            return known
        spent += out["run_cost"]
        for err in out["errors"]:
            typer.echo(f"OSTRZEŻENIE: tłumaczenia {day}: {err}", err=True)
        typer.echo(f"Tłumaczenia nagłówków {day}: {out['translated']} nowych, bez tłumaczenia {out['missing']} "
                   f"({out['run_cost']:.3f} $)")
        return out["tytuly"]

    import threading

    from paralaksa.gdelt import tv as tvmod, tv_pl, tv_stories

    tv_cache = Path("data/gdelt/tv")
    tv_client = None
    tv_clients: dict = {}
    if with_tv and not no_stories:
        try:
            tv_client = build_client(tv_pl.MODEL, settings.pricing, settings.extract.batch_poll_interval_s,
                                     settings.extract.batch_timeout_h)
        except RuntimeError as e:
            typer.echo(f"OSTRZEŻENIE: {e}; Telewizja bez nowych tłumaczeń", err=True)
        try:
            tv_clients = {m: build_client(m, settings.pricing, settings.extract.batch_poll_interval_s,
                                          settings.extract.batch_timeout_h) for m in tv_stories.MODELS}
        except RuntimeError as e:
            typer.echo(f"OSTRZEŻENIE: {e}; Telewizja bez nowych historii", err=True)
    tv_spent: dict[str, float] = {}
    tv_lock = threading.Lock()

    def tv_pl_for(day: str, report) -> dict | None:   # wołane równolegle z tv_views.build
        nonlocal spent
        known = tv_pl.cached(tv_cache, day, report.code, len(tvmod.sentences(report.text)))
        if known is not None or tv_client is None:
            return known
        try:
            out = tv_pl.translate(tv_client, tv_pl.MODEL, day, report, tv_cache)
        except RuntimeError as e:
            typer.echo(f"OSTRZEŻENIE: tłumaczenie TV {day} {report.code}: {e}", err=True)
            return None
        for err in out["errors"]:
            typer.echo(f"OSTRZEŻENIE: tłumaczenie TV {day} {report.code}: {err}", err=True)
        with tv_lock:
            spent += out["cost_usd"]
            tv_spent[day] = tv_spent.get(day, 0.0) + out["cost_usd"]
        return out

    def tv_stories_for(day: str, reports, pl) -> list[dict] | None:
        nonlocal spent
        if not tv_clients:
            return tv_stories.cached(tv_cache, day, reports)
        try:
            out = tv_stories.generate(tv_clients.__getitem__, day, reports, pl, tv_cache)
        except RuntimeError as e:
            typer.echo(f"OSTRZEŻENIE: historie TV {day}: {e}", err=True)
            return None
        for err in out["errors"] + out.get("warnings", []):
            typer.echo(f"OSTRZEŻENIE: historie TV {day}: {err}", err=True)
        if out["cost_usd"]:
            spent += out["cost_usd"]
            typer.echo(f"Historie TV {day}: {len(out['historie'])} ({out['cost_usd']:.3f} $)")
        return out["historie"] if not out["errors"] else None

    tv_payload = _tv_payload(tv_days, None, tv_cache, config_dir, pl_for=tv_pl_for,
                             stories_for=tv_stories_for) if with_tv else None
    for day, usd in sorted(tv_spent.items()):
        typer.echo(f"Tłumaczenia TV {day}: {usd:.3f} $")
    try:
        res = build_site(out_dir, events_dir, reports_dir, conn, {t.id: t.name_pl for t in load_themes(config_dir)},
                         stories_for, titles_for, tv_payload, v2_dir=out_dir.parent / "widok")
    finally:
        if conn is not None:
            conn.close()
    for err in res.errors:
        typer.echo(f"OSTRZEŻENIE: {err}", err=True)
    if spent:
        typer.echo(f"Koszt modelu (historie dnia, tłumaczenia nagłówków, raporty i historie TV): {spent:.3f} $")
    typer.echo(f"Zdarzenia: {len(res.events)}, dni dziennika: {len(res.days)}, dni telewizji: {len(tv_payload['days']) if tv_payload else 'bez zakładki'}. "
               f"Start: {out_dir / 'index.html'}")
    if make_zip:
        typer.echo(f"Paczka: {zip_site(out_dir)}")
    if publish_site:
        from paralaksa.site.publish import publish

        repo = os.environ.get("SITE_REPO", "")
        if not repo:
            typer.echo("BŁĄD: brak SITE_REPO w .env (np. kraxtere/paralaksa-strona)", err=True)
            raise typer.Exit(1)
        try:
            typer.echo(f"Opublikowano w {repo}: {publish(out_dir, repo)}")
        except RuntimeError as e:
            typer.echo(f"BŁĄD publikacji: {e}", err=True)
            raise typer.Exit(1)
    if publish_hf:
        from paralaksa.site.publish import publish_hf as _publish_hf

        space = os.environ.get("HF_SPACE", "")
        if not space:
            typer.echo("BŁĄD: brak HF_SPACE w .env (użytkownik/nazwa Space)", err=True)
            raise typer.Exit(1)
        try:
            typer.echo(f"Opublikowano w Space {space}: {_publish_hf(out_dir, space, os.environ.get('HF_TOKEN', ''))}")
        except RuntimeError as e:
            typer.echo(f"BŁĄD publikacji HF: {e}", err=True)
            raise typer.Exit(1)


events_app = typer.Typer(help="Karty zdarzeń (events/*.md).", no_args_is_help=True)
app.add_typer(events_app, name="events")


@events_app.command("check")
def events_check(
    cards: list[Path] = typer.Argument(..., exists=True, help="Karty events/*.md albo katalog z kartami."),
    out_dir: Path = typer.Option(Path("data/checks"), "--out-dir", "-o", help="Katalog raportów."),
    days: int = typer.Option(2, "--dni", min=1, max=14, help="Ile dni (UTC) od dnia publikacji przeszukać w archiwum."),
    max_fetch: int = typer.Option(12, "--max-fetch", min=1, max=50, help="Ile kopii pobrać na relację (równo rozłożonych)."),
    config_dir: Path = ConfigDir,
    db_path: Optional[Path] = DbPath,
) -> None:
    """Podpowiedzi do karty: kopie Wayback, metadane stron, zmiany nagłówków, nasza baza. Karty nie zmienia."""
    from paralaksa.events.check import CardError, card_paths, check_card, open_db_readonly, render_check

    settings = load_settings(config_dir)
    cfg = settings.ingest
    conn = open_db_readonly(db_path or settings.resolved_db_path())
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    try:
        with PoliteClient(cfg.user_agent, cfg.per_domain_delay_s, 60.0) as client:
            for path in card_paths(cards):
                try:
                    cc = check_card(path, client, conn, days, max_fetch)
                except CardError as e:
                    typer.echo(f"BŁĄD: {e}", err=True)
                    failed = True
                    continue
                report_path = out_dir / f"{cc.card['id']}.md"
                report_path.write_text(render_check(cc), encoding="utf-8")
                n_hints = sum(len(r.hints) for r in cc.relations)
                typer.echo(f"{cc.card['id']}: {len(cc.relations)} relacji, {n_hints} podpowiedzi: {report_path}")
                for r in cc.relations:
                    for h in r.hints:
                        typer.echo(f"  {r.rid} {r.kto}: {h}")
    finally:
        if conn is not None:
            conn.close()
    if failed:
        raise typer.Exit(code=1)


@events_app.command("archive")
def events_archive(
    cards: list[Path] = typer.Argument(..., exists=True, help="Karty events/*.md albo katalog z kartami."),
    dry_run: bool = typer.Option(False, "--na-sucho", help="Tylko pokaż, co byłoby zrobione (bez nowych kopii i zapisu)."),
    no_write: bool = typer.Option(False, "--bez-wpisu", help="Rób kopie, ale nie wpisuj ich do karty."),
    config_dir: Path = ConfigDir,
) -> None:
    """Uzupełnia puste `archiwum` w kartach: istniejąca kopia Wayback albo nowa (Save Page Now).

    Nowa kopia wymaga konta archive.org (IA_ACCESS_KEY, IA_SECRET_KEY w .env). Nie nadpisuje
    wpisanych archiwów, nie zmienia `sprawdzil` ani innych pól.
    """
    from paralaksa.events.archive import archive_card, ia_auth_from_env
    from paralaksa.events.check import CardError, card_paths

    cfg = load_settings(config_dir).ingest
    auth = ia_auth_from_env()
    if not auth and not dry_run:
        typer.echo("Uwaga: brak IA_ACCESS_KEY/IA_SECRET_KEY, więc tylko istniejące kopie (bez Save Page Now).")
    failed = False
    with PoliteClient(cfg.user_agent, cfg.per_domain_delay_s, 60.0) as client:
        for path in card_paths(cards):
            try:
                ca = archive_card(path, client, auth, write=not no_write, dry_run=dry_run)
            except CardError as e:
                typer.echo(f"BŁĄD: {e}", err=True)
                failed = True
                continue
            typer.echo(f"{ca.card_id}: wpisano {ca.written} archiwów")
            for ra in ca.relations:
                if ra.action != "jest":
                    typer.echo(f"  {ra.rid} {ra.kto}: {ra.message}")
                failed |= ra.action == "błąd"
    if failed:
        raise typer.Exit(code=1)


gdelt_app = typer.Typer(help="GDELT: kandydaci na karty i brakujące relacje (BigQuery), raporty telewizyjne "
                        "(lokalnie, poza daily).",
                        no_args_is_help=True)
app.add_typer(gdelt_app, name="gdelt")
GdeltOut = typer.Option(Path("data/gdelt"), "--out-dir", "-o", help="Katalog wyników (Markdown i JSON).")
GdeltProject = typer.Option(None, "--projekt", help="Projekt Google Cloud (domyślnie GCP_PROJECT z .env).")
GdeltMaxGb = typer.Option(5.0, "--max-gb", help="Twardy limit przeszukanych danych na jedno zapytanie (GB).")


def _gdelt_tools(config_dir: Path, project: Optional[str], max_gb: float):
    from paralaksa.extract.llm_client import build_client
    from paralaksa.gdelt.bq import BigQueryRunner

    settings = load_settings(config_dir)
    try:
        runner = BigQueryRunner(project, max_gb)
    except RuntimeError as e:
        typer.echo(f"BŁĄD: {e}", err=True)
        raise typer.Exit(code=1)
    client = build_client(settings.models.extract, settings.pricing, settings.extract.batch_poll_interval_s,
                          settings.extract.batch_timeout_h)
    return runner, client, settings.models.extract


@gdelt_app.command("rezonans")
def gdelt_rezonans(
    day: Optional[str] = typer.Option(None, "--dzien", help="Dzień UTC RRRR-MM-DD (domyślnie wczoraj)."),
    out_dir: Path = GdeltOut, project: Optional[str] = GdeltProject, max_gb: float = GdeltMaxGb,
    config_dir: Path = ConfigDir,
) -> None:
    """Kandydaci na karty: wydarzenia, o których danego dnia pisało wyraźnie więcej redakcji w wielu językach niż zwykle.

    Osobno podane powody (redakcje, języki, wzrost względem tygodnia) i nagłówki z różnych krajów z tłumaczeniem."""
    from datetime import datetime, timedelta, timezone

    from paralaksa.gdelt import rezonans

    day = day or (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    runner, client, model = _gdelt_tools(config_dir, project, max_gb)
    try:
        out = rezonans.find(runner, client, model, day)
    except RuntimeError as e:
        typer.echo(f"BŁĄD: {e}", err=True)
        raise typer.Exit(code=1)
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"rezonans-{day}.md"
    md.write_text(rezonans.render(out), encoding="utf-8")
    md.with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for n, ev in enumerate(out["wydarzenia"], 1):
        p = ev["powody"]
        typer.echo(f"{n}. {ev['tytul']} ({p['redakcje']} redakcji, {p['jezyki']} języków, ×{p['wzrost']:g})")
    typer.echo(f"BigQuery {out['gb']} GB, model {out['cost_usd']:.3f} $. Wynik: {md}")


@gdelt_app.command("szukaj")
def gdelt_szukaj(
    card_path: Path = typer.Argument(..., exists=True, dir_okay=False, help="Karta events/<id>.md."),
    phrases: Optional[list[str]] = typer.Option(None, "--fraza", help="Własne frazy zamiast podpowiedzi modelu "
                                                "(można wiele; części połączone ' & ' muszą wystąpić razem)."),
    days_after: int = typer.Option(3, "--dni-po", min=0, max=14, help="Ile dni po dniu karty przeszukać."),
    no_check: bool = typer.Option(False, "--bez-sprawdzenia", help="Bez sprawdzania nagłówków modelem (więcej szumu)."),
    out_dir: Path = GdeltOut, project: Optional[str] = GdeltProject, max_gb: float = GdeltMaxGb,
    config_dir: Path = ConfigDir,
) -> None:
    """Brakujące relacje do karty: nagłówki z GDELT o tym zdarzeniu z redakcji, których w karcie jeszcze nie ma.

    Karty nie zmienia. Wynik to podpowiedzi do otwarcia i sprawdzenia."""
    from paralaksa.events.check import CardError, load_card
    from paralaksa.gdelt import szukaj

    try:
        card = load_card(card_path)
    except CardError as e:
        typer.echo(f"BŁĄD: {e}", err=True)
        raise typer.Exit(code=1)
    runner, client, model = _gdelt_tools(config_dir, project, max_gb)
    try:
        out = szukaj.search(runner, client, model, card, days_after, phrases, not no_check)
    except RuntimeError as e:
        typer.echo(f"BŁĄD: {e}", err=True)
        raise typer.Exit(code=1)
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"szukaj-{card['id']}.md"
    md.write_text(szukaj.render(out), encoding="utf-8")
    md.with_suffix(".json").write_text(szukaj.dump(out), encoding="utf-8")
    langs = sorted({f["lang"] for f in out["nowe"]})
    typer.echo(f"{card['id']}: {len(out['nowe'])} relacji spoza karty w {len(langs)} językach ({', '.join(langs)}); "
               f"{len(out['w_karcie'])} z redakcji już w karcie")
    typer.echo(f"BigQuery {out['gb']} GB, model {out['cost_usd']:.3f} $. Wynik: {md}")


@gdelt_app.command("tv")
def gdelt_tv(
    day: Optional[str] = typer.Option(None, "--dzien", help="Dzień RRRR-MM-DD (domyślnie wczoraj; raporty wychodzą dzień później)."),
    channels: Optional[list[str]] = typer.Option(None, "--kanal", help="Kod kanału GDELT (można wiele; domyślnie stała lista)."),
    phrases: Optional[list[str]] = typer.Option(None, "--fraza", help="Pokaż zdanie z każdej stacji o tej frazie (można wiele)."),
    min_channels: int = typer.Option(3, "--min-kanalow", min=2, help="Nazwa musi paść w co najmniej tylu stacjach."),
    out_dir: Path = GdeltOut, config_dir: Path = ConfigDir,
) -> None:
    """Telewizja: raporty GDELT „Today's Media Trends” (streszczenia dnia per kanał) i nazwy, które pojawiły się
    naraz w kilku stacjach, ze zdaniem z każdej. Bez modelu i bez kosztów; transkrypcje tylko w Visual Explorer."""
    from datetime import datetime, timedelta, timezone

    import httpx

    from paralaksa.gdelt import tv

    day = day or (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    try:
        date.fromisoformat(day)
    except ValueError:
        typer.echo(f"BŁĄD: zła data {day!r}", err=True)
        raise typer.Exit(code=1)
    codes = [c.upper() for c in channels] if channels else list(tv.CHANNELS)
    cfg = load_settings(config_dir).ingest
    cache = out_dir / "tv"
    with PoliteClient(cfg.user_agent, cfg.per_domain_delay_s, 60.0) as client:
        def fetch(url: str) -> bytes | None:
            try:
                return client.get(url).content
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
        try:
            today = tv.load(day, codes, cache, fetch)
            before_day = tv.previous_day(day)
            before = tv.load(before_day, codes, cache, fetch) if today else {}
        except (httpx.HTTPError, ImportError) as e:
            typer.echo(f"BŁĄD: {e}", err=True)
            raise typer.Exit(code=1)
    if not today:
        typer.echo(f"Raportów za {day} jeszcze nie ma (wychodzą dzień później).", err=True)
        raise typer.Exit(code=1)
    groups = tv.trends(today, before, min_channels)
    found = {p: tv.phrase_snippets(today, p) for p in phrases or []}
    missing = [c for c in codes if c not in today]
    md = out_dir / f"tv-{day}.md"
    md.write_text(tv.render(day, today, before_day, before, groups, found, missing), encoding="utf-8")
    md.with_suffix(".json").write_text(json.dumps({"dzien": day, "grupy": groups, "frazy": found, "brak": missing},
                                                  ensure_ascii=False, indent=1), encoding="utf-8")
    for p, snips in found.items():
        typer.echo(f"fraza {p!r}: {len(snips)} kanałów ({', '.join(snips)})")
    for n, g in enumerate(groups, 1):
        typer.echo(f"{n}. {g['label']}: {len(g['channels'])} kanałów ({', '.join(g['channels'])}), "
                   f"dzień wcześniej {g['before']}")
    typer.echo(f"Kanały: {len(today)}/{len(codes)}, porównanie z {before_day}: {len(before)}. Wynik: {md}")


def _tv_payload(days: int, last: Optional[str], cache: Path, config_dir: Path, download: bool = True,
                pl_for=None, stories_for=None) -> dict:
    """Data of the Telewizja views for `days` days up to `last` (default yesterday); missing reports are downloaded
    unless `download` is off. A network error only warns: the views use what is cached."""
    from datetime import datetime, timedelta, timezone

    import httpx

    from paralaksa.gdelt import tv, tv_views

    end = date.fromisoformat(last) if last else datetime.now(timezone.utc).date() - timedelta(days=1)
    wanted = [(end - timedelta(days=n)).isoformat() for n in range(days, -1, -1)]   # plus dzień przed pierwszym
    if download:
        cfg = load_settings(config_dir).ingest
        with PoliteClient(cfg.user_agent, cfg.per_domain_delay_s, 60.0) as client:
            def fetch(url: str) -> bytes | None:
                try:
                    return client.get(url).content
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        return None
                    raise
            try:
                for d in wanted:
                    tv.load(d, tv.CHANNELS, cache, fetch)
            except (httpx.HTTPError, ImportError) as e:
                typer.echo(f"OSTRZEŻENIE: raporty TV: {e}; widoki z zapisanych", err=True)
    if pl_for is None:   # bez modelu: tylko zapisane tłumaczenia
        from paralaksa.gdelt import tv_pl

        def pl_for(day, report):
            return tv_pl.cached(cache, day, report.code, len(tv.sentences(report.text)))
    return tv_views.build(wanted[1:], cache, pl_for, stories_for)


@gdelt_app.command("tv-widoki")
def gdelt_tv_views(
    days: int = typer.Option(7, "--dni", min=1, max=31, help="Ile dni wstecz (brakujące raporty są pobierane)."),
    last: Optional[str] = typer.Option(None, "--do", help="Ostatni dzień RRRR-MM-DD (domyślnie wczoraj)."),
    out_dir: Path = GdeltOut, config_dir: Path = ConfigDir,
) -> None:
    """Robocze widoki tylko z telewizji (tablica dnia, jeden temat, dwie stacje, kanał w czasie, szukanie frazy) jako
    osobny plik HTML. Na stronie wewnętrznej to zakładka Telewizja (plx site)."""
    from paralaksa.gdelt import tv_views

    payload = _tv_payload(days, last, out_dir / "tv", config_dir)
    if not payload["days"]:
        typer.echo("Brak raportów w tym zakresie.", err=True)
        raise typer.Exit(code=1)
    out = out_dir / "tv-widoki.html"
    out.write_text(tv_views.render(payload), encoding="utf-8")
    typer.echo(f"Dni: {', '.join(sorted(payload['days']))}. Wynik: {out}")


@gdelt_app.command("tv-historie")
def gdelt_tv_stories(
    days: int = typer.Option(1, "--dni", min=1, max=31, help="Ile dni wstecz (tylko zapisane raporty)."),
    last: Optional[str] = typer.Option(None, "--do", help="Ostatni dzień RRRR-MM-DD (domyślnie wczoraj)."),
    out_dir: Path = GdeltOut, config_dir: Path = ConfigDir,
) -> None:
    """Historie dnia z telewizji: do 3 zdarzeń, w których streszczenia stacji podają różne wersje (model tani,
    ok. kilku centów dziennie; ponowna budowa za darmo). Na stronie: zakładka Telewizja → Historie dnia."""
    from datetime import datetime, timedelta, timezone

    from paralaksa.extract.llm_client import build_client
    from paralaksa.gdelt import tv, tv_pl, tv_stories

    settings = load_settings(config_dir)
    clients = {m: build_client(m, settings.pricing, settings.extract.batch_poll_interval_s, settings.extract.batch_timeout_h)
               for m in tv_stories.MODELS}
    cache = out_dir / "tv"
    end = date.fromisoformat(last) if last else datetime.now(timezone.utc).date() - timedelta(days=1)
    total = 0.0
    for n in range(days - 1, -1, -1):
        day = (end - timedelta(days=n)).isoformat()
        reports = tv.load(day, tv.CHANNELS, cache, lambda url: None)
        if not reports:
            typer.echo(f"{day}: brak zapisanych raportów")
            continue
        pl = {c: tv_pl.cached(cache, day, c, len(tv.sentences(r.text))) for c, r in reports.items()}
        res = tv_stories.generate(clients.__getitem__, day, reports, pl, cache)
        total += res["cost_usd"]
        for err in res["errors"] + res.get("warnings", []):
            typer.echo(f"OSTRZEŻENIE: {day}: {err}", err=True)
        typer.echo(f"{day}: historii {len(res['historie'])} (kandydatów {res.get('kandydaci', 0)}, "
                   f"odrzuconych {res.get('odrzucone', 0)}, w tym niesprawdzonych {res.get('niesprawdzone', 0)}), "
                   f"{res['cost_usd']:.3f} $")
        for s in res["historie"]:
            typer.echo(f"  {s['sila']} [{s['typ']}] {s['tytul']}: {s['roznica']}")
    typer.echo(f"Koszt: {total:.3f} $")


@app.command("run-daily")
def run_daily(
    no_fulltext: bool = typer.Option(False, "--no-fulltext", help="Nie pobieraj pełnych tekstów."),
    skip_ingest: bool = typer.Option(False, "--skip-ingest", help="Bez pobierania (tylko ekstrakcja i raport)."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Maks. liczba artykułów do ekstrakcji."),
    no_report: bool = typer.Option(False, "--bez-raportu",
                                   help="Bez syntezy: tylko metryki i status dnia (Actions od 2026-10-01; raport lokalnie)."),
    out_dir: Optional[Path] = OutDir,
    config_dir: Path = ConfigDir,
    db_path: Optional[Path] = DbPath,
) -> None:
    """Pełny przebieg dzienny: ingest → extract → aggregate → report."""
    settings, conn = _open_db(config_dir, db_path)
    all_sources = load_sources(config_dir)
    db.upsert_sources(conn, all_sources)
    themes = load_themes(config_dir)
    d = db.utc_now().date().isoformat()
    if not skip_ingest:
        typer.echo("== ingest")
        _run_ingest(conn, settings, [s for s in all_sources if s.active], fulltext=not no_fulltext)
    typer.echo("== extract")
    _run_extract(conn, settings, themes, limit, use_batch=True)
    if no_report:
        from paralaksa.report.pipeline import material_status

        typer.echo("== aggregate (bez raportu)")
        status = material_status(conn, settings, all_sources, themes, d, out_dir or settings.report.resolved_output_dir())
        conn.close()
        typer.echo(f"Sygnały dnia: {status['n_signals']} | koszt API dnia: ${status['cost_usd']:.4f}")
        for w in status["warnings"]:
            typer.echo(f"OSTRZEŻENIE: {w}", err=True)
        if not status["complete"]:
            raise typer.Exit(code=1)
        return
    typer.echo("== aggregate + report")
    result = _run_report(conn, settings, config_dir, d, out_dir)
    conn.close()
    if not result.complete:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
