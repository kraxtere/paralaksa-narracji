"""Command-line interface: plx."""

from __future__ import annotations

import logging
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
        selected = [s for s in all_sources if s.id in source and s.feeds]
    else:
        selected = [s for s in all_sources if s.active]
    if not selected:
        typer.echo("Brak źródeł do pobrania.", err=True)
        raise typer.Exit(code=1)

    cfg = settings.ingest
    with PoliteClient(cfg.user_agent, cfg.per_domain_delay_s, cfg.timeout_s) as client:
        results = ingest_sources(conn, client, selected, settings, fulltext=not no_fulltext)

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
    conn.close()


@app.command()
def extract(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Maks. liczba artykułów."),
    no_batch: bool = typer.Option(False, "--no-batch", help="Zawsze wywołania bezpośrednie (bez Batches API)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Tylko szacunek kosztu, bez wywołań API."),
    config_dir: Path = ConfigDir,
    db_path: Optional[Path] = DbPath,
) -> None:
    """Wydobądź sygnały narracyjne z nieprzetworzonych artykułów (LLM)."""
    from paralaksa.extract.llm_client import build_client
    from paralaksa.extract.signals import estimate_pending, extract_pending

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

    cfg = settings.extract
    llm = build_client(settings.models.extract, settings.pricing, cfg.batch_poll_interval_s, cfg.batch_timeout_h)
    stats = extract_pending(conn, llm, settings, themes, limit, use_batch=not no_batch)

    typer.echo(f"Tryb: {stats.mode}" + (f" (batch {stats.batch_id})" if stats.batch_id else ""))
    typer.echo(
        f"Artykuły: {stats.pending} | przetworzone: {stats.done} | sygnały: {stats.signals} | "
        f"ponowienia: {stats.retries} | błędy trwałe: {stats.failed} | odłożone: {stats.deferred}"
    )
    typer.echo(f"Naprawione evidence_span: {stats.repairs} | odrzucone sygnały: {stats.dropped}")
    total = db.spent_on(conn, db.utc_now().date().isoformat())
    typer.echo(f"Koszt przebiegu: ${stats.cost_usd:.4f} | wydano dziś: ${total:.4f} z limitu ${budget:.2f}")
    if stats.budget_stopped:
        typer.echo("OSTRZEŻENIE: osiągnięto dzienny limit kosztów – część artykułów czeka na kolejny przebieg.", err=True)
    conn.close()
    if stats.failed and not stats.done:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
