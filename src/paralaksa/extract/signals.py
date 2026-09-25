"""Signal extraction pipeline: pending articles -> LLM -> validation -> signals table."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from paralaksa import db
from paralaksa.config import PROJECT_ROOT, Settings, Theme
from paralaksa.extract.llm_client import LLMClient, LLMRequest, LLMResult, model_extra_params
from paralaksa.extract.schema import ParseOutcome, Signal, parse_extraction

log = logging.getLogger(__name__)

DEFAULT_PROMPT = PROJECT_ROOT / "prompts" / "extract_signals.md"
# Kalibracja 2026-09-23 na 20 artykułach: średnio 2,14 znaku/token (pl 1,94, de 1,97, uk 2,07, en 2,32).
# Wartość zaniżona celowo, żeby szacunek budżetu (jedyny hamulec w trybie batch) był z zapasem.
CHARS_PER_TOKEN = 1.9

MATERIAL_NOTES = {
    "fulltext": "pełny tekst artykułu (może być obcięty do limitu słów).",
    "lead_only": (
        "TYLKO tytuł i lead; pełny tekst niedostępny (paywall). Wydobywaj wyłącznie to, co wprost "
        "wynika z tego materiału. Zwykle 0–2 sygnały, intensity ostrożnie, nie zgaduj ramy całego artykułu."
    ),
}

RETRY_INSTRUCTION = (
    "Twoja odpowiedź nie przeszła walidacji:\n{errors}\n"
    "Zwróć poprawiony JSON wyłącznie w wymaganym formacie, bez komentarzy."
)


@dataclass
class ArticleForExtraction:
    id: int
    source_id: str
    country: str
    source_type: str
    title: str
    lead: str | None
    fulltext: str | None

    @property
    def source_depth(self) -> str:
        return "fulltext" if self.fulltext else "lead_only"


@dataclass
class ExtractStats:
    pending: int = 0
    mode: str = "direct"
    batch_id: str | None = None
    done: int = 0
    signals: int = 0
    failed: int = 0          # trwały błąd (extracted=2)
    deferred: int = 0        # błąd przejściowy lub budżet: zostaje extracted=0
    skipped: int = 0         # poza oknem publikacji (extracted=3), bez kosztu
    retries: int = 0
    repairs: int = 0         # obcięte evidence_span (bez kosztu)
    dropped: int = 0         # sygnały odrzucone po ponowieniu
    cost_usd: float = 0.0
    budget_stopped: bool = False


# ------------------------------------------------------------------ prompt

def load_prompt(path: Path = DEFAULT_PROMPT) -> tuple[str, str]:
    """Template text and its version (short hash of the file content)."""
    text = path.read_text(encoding="utf-8")
    return text, "extract_signals@" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def format_themes(themes: list[Theme]) -> str:
    return "\n".join(f"- {t.id}: {t.name_pl} – {t.description}" for t in themes)


def render_prompt(template: str, art: ArticleForExtraction, themes_text: str, max_words: int) -> str:
    text = " ".join(art.fulltext.split()[:max_words]) if art.fulltext else "(niedostępny – patrz MATERIAŁ)"
    values = {
        "country": art.country,
        "source_type": art.source_type,
        "material_note": MATERIAL_NOTES[art.source_depth],
        "themes": themes_text,
        "title": art.title,
        "lead": art.lead or "(brak)",
        "text": text,
    }
    # Zwykłe zastępowanie: szablon zawiera klamry przykładowego JSON-a, więc nie str.format().
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


# ------------------------------------------------------------------ db

def pending_articles(conn: sqlite3.Connection, limit: int | None = None) -> list[ArticleForExtraction]:
    sql = """
        SELECT a.id, a.source_id, s.country, s.type, a.title, a.lead, a.fulltext
        FROM articles a JOIN sources s ON s.id = a.source_id
        WHERE a.extracted = 0
        ORDER BY ROW_NUMBER() OVER (PARTITION BY s.country,a.source_id ORDER BY a.fetched_at DESC,a.published_at DESC,a.id),
                 s.country,a.source_id
    """
    params: tuple = ()
    if limit is not None:
        if limit < 1:
            raise ValueError("limit musi być dodatni")
        sql += " LIMIT ?"
        params = (limit,)
    return [ArticleForExtraction(*row) for row in conn.execute(sql, params).fetchall()]


SKIPPED_OUT_OF_WINDOW = 3  # articles.extracted: poza oknem publikacji, bez wywołania modelu
SKIP_NOTE = "pominięty: publikacja poza oknem D-1..D (nie wchodzi do porównań)"


def out_of_window_ids(conn: sqlite3.Connection) -> list[int]:
    """Pending articles that no report will compare (late, future or undated outside the initial run)."""
    from paralaksa.aggregate.sample import publication_meta

    days = [r[0] for r in conn.execute(
        "SELECT DISTINCT substr(fetched_at, 1, 10) FROM articles WHERE extracted = 0")]
    skip: list[int] = []
    for day in days:
        eligible = set(publication_meta(conn, day)["eligible_ids"])
        skip += [r[0] for r in conn.execute(
            "SELECT id FROM articles WHERE extracted = 0 AND substr(fetched_at, 1, 10) = ?", (day,))
            if r[0] not in eligible]
    return skip


def skip_out_of_window(conn: sqlite3.Connection) -> int:
    ids = out_of_window_ids(conn)
    conn.executemany("UPDATE articles SET extracted = ?, extract_error = ? WHERE id = ?",
                     [(SKIPPED_OUT_OF_WINDOW, SKIP_NOTE, i) for i in ids])
    conn.commit()
    return len(ids)


def save_signals(
    conn: sqlite3.Connection, art: ArticleForExtraction, signals: list[Signal],
    model: str, prompt_version: str, now: datetime, note: str | None = None,
) -> None:
    created = db.to_iso(now)
    conn.executemany(
        """
        INSERT INTO signals (article_id, theme_id, subject_actor, frame, stance, intensity, signal_type,
                             summary_pl, evidence_span, model, created_at, source_depth, prompt_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (art.id, s.theme_id, s.subject_actor, s.frame, s.stance, s.intensity, s.signal_type,
             s.summary_pl, s.evidence_span, model, created, art.source_depth, prompt_version)
            for s in signals
        ],
    )
    conn.execute("UPDATE articles SET extracted = 1, extract_error = ? WHERE id = ?",
                 (note[:1000] if note else None, art.id))


def mark_article(conn: sqlite3.Connection, article_id: int, status: int, error: str | None) -> None:
    conn.execute("UPDATE articles SET extracted = ?, extract_error = ? WHERE id = ?",
                 (status, error[:1000] if error else None, article_id))


# ------------------------------------------------------------------ pipeline

class _Run:
    def __init__(self, conn, llm: LLMClient, settings: Settings, themes: list[Theme],
                 prompt_path: Path, now: datetime) -> None:
        self.conn, self.llm, self.settings, self.now = conn, llm, settings, now
        self.template, self.prompt_version = load_prompt(prompt_path)
        self.themes_text = format_themes(themes)
        self.theme_ids = {t.id for t in themes}
        self.model = settings.models.extract
        self.max_daily = settings.budget.max_daily_usd
        self.day = now.date().isoformat()
        self.stats = ExtractStats()
        self.deadline = time.monotonic() + settings.extract.max_runtime_s

    # --- budżet

    def spent(self) -> float:
        return db.spent_on(self.conn, self.day)

    def estimate(self, prompt: str, batch: bool, reserve: bool = False) -> float:
        in_tokens = int(len(prompt) / CHARS_PER_TOKEN)
        return self.settings.pricing.cost(self.model, in_tokens,
            self.settings.extract.max_tokens if reserve else self.settings.extract.est_output_tokens, batch)

    def fits(self, extra_usd: float) -> bool:
        return self.spent() + extra_usd <= self.max_daily

    # --- żądania

    def request(self, art: ArticleForExtraction) -> LLMRequest:
        prompt = render_prompt(self.template, art, self.themes_text, self.settings.ingest.max_fulltext_words)
        cfg = self.settings.extract
        return LLMRequest(
            custom_id=f"article-{art.id}", model=self.model, max_tokens=cfg.max_tokens,
            messages=[{"role": "user", "content": prompt}],
            extra=model_extra_params(self.model, cfg.thinking, cfg.effort),
        )

    def record(self, res: LLMResult, article_id: int) -> None:
        if res.input_tokens or res.output_tokens:
            db.record_usage(self.conn, res.model, res.mode, "extract", res.input_tokens, res.output_tokens,
                            res.cost_usd, article_id=article_id, batch_id=res.batch_id, now=self.now)
            self.stats.cost_usd += res.cost_usd

    def handle(self, art: ArticleForExtraction, req: LLMRequest, res: LLMResult, recorded=False) -> None:
        if not recorded:
            self.record(res, art.id)
        if not res.ok:
            self._fail(art, res.error or "nieznany błąd", res.retryable)
            return
        first = parse_extraction(res.text or "", self.theme_ids, self.source_text(art))
        self.stats.repairs += first.repairs
        final = first
        if not first.clean:
            errors = [first.fatal] if first.fatal else first.errors
            log.info("Artykuł %s: ponowienie, błędy walidacji: %s", art.id, "; ".join(errors))
            second = self.retry(art, req, res.text or "", errors)
            if second is not None:
                self.stats.repairs += second.repairs
            if second is not None and second.fatal is None:
                final = second
            elif first.fatal is not None:
                reason = second.fatal if second is not None else "ponowienie nieudane"
                self._fail(art, f"walidacja po ponowieniu: {reason}", retryable=False)
                return
        note = None
        if final.errors:
            note = f"odrzucono {len(final.errors)} błędnych sygnałów: " + "; ".join(final.errors)
            self.stats.dropped += len(final.errors)
            log.warning("Artykuł %s: %s", art.id, note)
        save_signals(self.conn, art, final.signals, self.model, self.prompt_version, self.now, note)
        self.conn.commit()
        self.stats.done += 1
        self.stats.signals += len(final.signals)

    def retry(self, art, req: LLMRequest, bad_text: str, errors: list[str]) -> ParseOutcome | None:
        retry_req = LLMRequest(
            custom_id=req.custom_id + "-retry", model=req.model, max_tokens=req.max_tokens, extra=req.extra,
            messages=req.messages + [
                {"role": "assistant", "content": bad_text or "(pusta odpowiedź)"},
                {"role": "user", "content": RETRY_INSTRUCTION.format(errors="\n".join(f"- {e}" for e in errors))},
            ],
        )
        if not self.fits(self.estimate(str(retry_req.messages), batch=False, reserve=True)):
            self.stats.budget_stopped = True
            log.warning("Artykuł %s: pominięto ponowienie (dzienny limit kosztów)", art.id)
            return None
        self.stats.retries += 1
        res = self.llm.complete(retry_req)
        self.record(res, art.id)
        if not res.ok:
            log.warning("Artykuł %s: ponowienie nieudane: %s", art.id, res.error)
            return None
        return parse_extraction(res.text or "", self.theme_ids, self.source_text(art))

    def source_text(self, art: ArticleForExtraction) -> str:
        """Everything the model saw of the article (for the verbatim evidence check)."""
        text = " ".join(art.fulltext.split()[: self.settings.ingest.max_fulltext_words]) if art.fulltext else ""
        return "\n".join([art.title, art.lead or "", text])

    def _fail(self, art: ArticleForExtraction, error: str, retryable: bool) -> None:
        if retryable:
            mark_article(self.conn, art.id, 0, error)
            self.stats.deferred += 1
        else:
            mark_article(self.conn, art.id, 2, error)
            self.stats.failed += 1
        self.conn.commit()
        log.warning("Artykuł %s: %s", art.id, error)

    # --- tryby

    def within_budget(self, items: list[tuple[ArticleForExtraction, LLMRequest]], batch: bool):
        """Longest prefix whose estimated cost fits in the remaining daily budget."""
        remaining = self.max_daily - self.spent()
        selected, total = [], 0.0
        for art, req in items:
            est = self.estimate(req.messages[0]["content"], batch, reserve=True)
            if total + est > remaining:
                self.stats.budget_stopped = True
                break
            selected.append((art, req))
            total += est
        return selected

    def run_batch(self, items) -> None:
        self.stats.mode = "batch"
        selected = self.within_budget(items, batch=True)
        self.stats.deferred += len(items) - len(selected)
        if not selected:
            return
        outcome = self.llm.run_batch([req for _, req in selected])
        self.stats.batch_id = outcome.batch_id
        for art, req in selected:
            self.record(outcome.results[req.custom_id], art.id)
        self.conn.commit()
        for art, req in selected:
            self.handle(art, req, outcome.results[req.custom_id], recorded=True)

    def run_direct(self, items) -> None:
        self.stats.mode = "direct"
        chunk_size = self.settings.extract.max_concurrency
        with ThreadPoolExecutor(max_workers=chunk_size) as pool:
            for i in range(0, len(items), chunk_size):
                if time.monotonic() >= self.deadline:
                    self.stats.deferred += len(items) - i
                    log.warning("Limit czasu ekstrakcji; pozostałe artykuły zachowano do kolejnego przebiegu")
                    return
                chunk = items[i : i + chunk_size]
                chunk_est = sum(self.estimate(req.messages[0]["content"], False, reserve=True) for _, req in chunk)
                if not self.fits(chunk_est):
                    chunk = self.within_budget(chunk, batch=False)
                    self.stats.budget_stopped = True
                results = list(pool.map(lambda item: self.llm.complete(item[1]), chunk))
                for (art, req), res in zip(chunk, results):
                    self.record(res, art.id)
                self.conn.commit()
                for (art, req), res in zip(chunk, results):
                    self.handle(art, req, res, recorded=True)
                if self.stats.budget_stopped:
                    self.stats.deferred += len(items) - i - len(chunk)
                    return


def extract_pending(
    conn: sqlite3.Connection,
    llm: LLMClient,
    settings: Settings,
    themes: list[Theme],
    limit: int | None = None,
    use_batch: bool = True,
    prompt_path: Path = DEFAULT_PROMPT,
    now: datetime | None = None,
) -> ExtractStats:
    run = _Run(conn, llm, settings, themes, prompt_path, now or db.utc_now())
    run.stats.skipped = skip_out_of_window(conn)
    articles = pending_articles(conn, limit)
    run.stats.pending = conn.execute("SELECT COUNT(*) FROM articles WHERE extracted=0").fetchone()[0]
    run.stats.deferred = run.stats.pending - len(articles)
    if not articles:
        return run.stats
    items = [(art, run.request(art)) for art in articles]
    # Batches API istnieje tylko u Anthropic; inni dostawcy (np. deepseek-*) zawsze idą bezpośrednio.
    batch_capable = settings.models.extract.startswith("claude") and hasattr(llm, "run_batch")
    if use_batch and batch_capable and len(items) > settings.extract.batch_threshold:
        run.run_batch(items)
    else:
        run.run_direct(items)
    return run.stats


def estimate_pending(conn: sqlite3.Connection, settings: Settings, themes: list[Theme],
                     limit: int | None = None, use_batch: bool = True,
                     prompt_path: Path = DEFAULT_PROMPT) -> tuple[int, int, float, str]:
    """(articles, estimated input tokens, estimated cost USD, mode) without calling the API."""
    run = _Run(conn, None, settings, themes, prompt_path, db.utc_now())  # type: ignore[arg-type]
    skip = set(out_of_window_ids(conn))
    articles = [a for a in pending_articles(conn) if a.id not in skip][:limit]
    batch_capable = settings.models.extract.startswith("claude")
    batch = use_batch and batch_capable and len(articles) > settings.extract.batch_threshold
    prompts = [run.request(a).messages[0]["content"] for a in articles]
    tokens = sum(int(len(p) / CHARS_PER_TOKEN) for p in prompts)
    cost = sum(run.estimate(p, batch) for p in prompts)
    return len(articles), tokens, cost, "batch" if batch else "direct"
