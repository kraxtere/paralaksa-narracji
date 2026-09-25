"""Command-line interface: plx."""

from __future__ import annotations

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


@app.command("run-daily")
def run_daily(
    no_fulltext: bool = typer.Option(False, "--no-fulltext", help="Nie pobieraj pełnych tekstów."),
    skip_ingest: bool = typer.Option(False, "--skip-ingest", help="Bez pobierania (tylko ekstrakcja i raport)."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Maks. liczba artykułów do ekstrakcji."),
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
    typer.echo("== aggregate + report")
    result = _run_report(conn, settings, config_dir, d, out_dir)
    conn.close()
    if not result.complete:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
