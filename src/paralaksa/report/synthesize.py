"""Synthesis (SPEC §9.4): data package -> LLM -> validated ReportOutput.

One call per day; on validation errors one retry with the error list, then the report is
sanitized (claims without valid references dropped) and marked with warnings instead of failing.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from paralaksa import db
from paralaksa.config import PROJECT_ROOT, Settings
from paralaksa.extract.llm_client import LLMRequest, LLMResult, model_extra_params
from paralaksa.extract.signals import CHARS_PER_TOKEN, RETRY_INSTRUCTION
from paralaksa.report.schema import SCHEMA_EXAMPLE, ReportOutput, parse_report
from paralaksa.report.validate import sanitize_report, validate_report

log = logging.getLogger(__name__)

DEFAULT_PROMPT = PROJECT_ROOT / "prompts" / "synthesize_report.md"


@dataclass
class SynthStats:
    model: str
    prompt_version: str
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    retried: bool = False
    first_pass_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0

    @property
    def clean(self) -> bool:
        return not self.warnings


def load_prompt(path: Path = DEFAULT_PROMPT) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    return text, "synthesize_report@" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def render_prompt(template: str, package: dict, settings: Settings) -> str:
    th = settings.thresholds
    values = {
        "date": package["data"],
        "min_countries": str(th.min_countries),
        "min_sources": str(th.min_sources_per_country),
        "schema": SCHEMA_EXAMPLE,
        "payload": json.dumps(package, ensure_ascii=False, separators=(",", ":")),
    }
    for key, value in values.items():  # nie str.format(): szablon i dane zawierają klamry JSON-a
        template = template.replace("{" + key + "}", value)
    return template


def estimate_cost(prompt: str, settings: Settings) -> float:
    return settings.pricing.cost(settings.models.synthesize, int(len(prompt) / CHARS_PER_TOKEN),
                                 settings.report.est_output_tokens)


def run_synthesis(
    conn: sqlite3.Connection,
    llm,
    settings: Settings,
    package: dict,
    known_ids: set[int],
    now: datetime | None = None,
    prompt_path: Path = DEFAULT_PROMPT,
) -> tuple[ReportOutput, SynthStats]:
    now = now or db.utc_now()
    model = settings.models.synthesize
    template, version = load_prompt(prompt_path)
    stats = SynthStats(model=model, prompt_version=version)
    prompt = render_prompt(template, package, settings)

    spent = db.spent_on(conn, now.date().isoformat())
    if spent + estimate_cost(prompt, settings) > settings.budget.max_daily_usd:
        stats.warnings.append(f"synteza pominięta: dzienny limit kosztów (wydano ${spent:.2f} "
                              f"z ${settings.budget.max_daily_usd:.2f})")
        return ReportOutput(), stats

    cfg = settings.report
    req = LLMRequest(custom_id=f"report-{package['data']}", model=model, max_tokens=cfg.max_tokens,
                     messages=[{"role": "user", "content": prompt}],
                     extra=model_extra_params(model, cfg.thinking, cfg.effort))
    started = time.monotonic()

    def call(r: LLMRequest) -> LLMResult:
        res = llm.complete(r)
        if not res.ok and res.retryable:
            log.warning("Synteza: błąd przejściowy (%s), ponawiam", res.error)
            res = llm.complete(r)
        stats.calls += 1
        if res.input_tokens or res.output_tokens:
            db.record_usage(conn, res.model, res.mode, "synthesize", res.input_tokens, res.output_tokens,
                            res.cost_usd, now=now)
            conn.commit()
            stats.cost_usd += res.cost_usd
            stats.input_tokens += res.input_tokens
            stats.output_tokens += res.output_tokens
        return res

    def evaluate(res: LLMResult) -> tuple[ReportOutput | None, list[str]]:
        if not res.ok:
            return None, [f"wywołanie nieudane: {res.error}"]
        report, errors = parse_report(res.text or "")
        if report is None:
            return None, errors
        return report, validate_report(report, package, known_ids)

    first = call(req)
    report, errors = evaluate(first)
    stats.first_pass_errors = list(errors)
    if errors and (first.ok or first.text):
        log.info("Synteza: ponowienie, błędy walidacji: %s", "; ".join(errors[:10]))
        stats.retried = True
        retry_req = LLMRequest(
            custom_id=req.custom_id + "-retry", model=model, max_tokens=req.max_tokens, extra=req.extra,
            messages=req.messages + [
                {"role": "assistant", "content": first.text or "(pusta odpowiedź)"},
                {"role": "user", "content": RETRY_INSTRUCTION.format(errors="\n".join(f"- {e}" for e in errors))},
            ],
        )
        second_report, second_errors = evaluate(call(retry_req))
        if second_report is not None:
            report, errors = second_report, second_errors
        else:
            errors = errors if report is not None else second_errors

    stats.elapsed_s = time.monotonic() - started
    if report is None:
        stats.warnings.append("synteza nieudana (brak poprawnego JSON po ponowieniu): " + "; ".join(errors[:5]))
        return ReportOutput(), stats
    if errors:
        stats.warnings.append(f"walidacja po ponowieniu: {len(errors)} błędów; usunięto twierdzenia bez "
                              f"poprawnych odnośników. Błędy: " + "; ".join(errors[:5]))
        report = sanitize_report(report, package, known_ids)
    return report, stats
