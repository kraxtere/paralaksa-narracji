from datetime import datetime, timezone

import pytest

from fake_llm import FakeAnthropic, FakeOpenAI, chat_completion, message
from paralaksa import db
from paralaksa.aggregate.package import build_data_package, known_article_ids
from paralaksa.config import load_themes
from paralaksa.extract.llm_client import DeepSeekClient, LLMClient
from paralaksa.report.synthesize import run_synthesis
from report_fixtures import as_text, mutate, valid_report
from seed import DAY, seed_alarm_convergence, seed_sources

THEMES = load_themes()
NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def data(conn, settings):
    seed_sources(conn)
    ids = seed_alarm_convergence(conn)
    return ids, build_data_package(conn, DAY, settings, THEMES), known_article_ids(conn, DAY)


def responder_seq(*texts):
    answers = list(texts)
    return lambda params: message(answers.pop(0), 30_000, 3_000)


def synth(conn, settings, data, *texts):
    _, package, known = data
    fake = FakeAnthropic(responder_seq(*texts))
    llm = LLMClient(settings.pricing, client=fake)
    report, stats = run_synthesis(conn, llm, settings, package, known, now=NOW)
    return report, stats, fake


def test_success_first_pass(conn, settings, data):
    ids = data[0]
    report, stats, fake = synth(conn, settings, data, as_text(valid_report(ids)))
    assert stats.calls == 1 and not stats.retried and stats.clean
    assert report.wzorce_zbieznosci[0].temat == "security_defense"
    call = fake.messages.calls[0]
    prompt = call["messages"][0]["content"]
    assert "z dnia 2026-09-23" in prompt and '"zbieznosc_kandydaci"' in prompt and "{payload}" not in prompt
    assert "https://" not in prompt                       # payload bez URL-i i bez pełnych tekstów
    assert call["model"] == settings.models.synthesize and call["max_tokens"] == settings.report.max_tokens
    assert call["thinking"] == {"type": "disabled"}
    row = conn.execute("SELECT purpose, input_tokens, cost_usd FROM api_usage").fetchone()
    assert row["purpose"] == "synthesize" and row["input_tokens"] == 30_000
    assert stats.cost_usd == pytest.approx(row["cost_usd"]) and stats.prompt_version.startswith("synthesize_report@")


def test_retry_after_validation_error(conn, settings, data):
    ids = data[0]
    bad = mutate(valid_report(ids), lambda r: r["w_skrocie"][0].update(article_ids=[]))
    report, stats, fake = synth(conn, settings, data, as_text(bad), as_text(valid_report(ids)))
    assert stats.calls == 2 and stats.retried and stats.clean
    assert any("twierdzenie bez odnośnika" in e for e in stats.first_pass_errors)
    retry_msgs = fake.messages.calls[1]["messages"]
    assert [m["role"] for m in retry_msgs] == ["user", "assistant", "user"]
    assert "w_skrocie.0: twierdzenie bez odnośnika" in retry_msgs[2]["content"]
    assert report.w_skrocie[0].article_ids


def test_invalid_after_retry_is_sanitized_with_warning(conn, settings, data):
    ids = data[0]
    bad = mutate(valid_report(ids), lambda r: r["slabe_sygnaly"][0].update(article_ids=[999_999]))
    report, stats, _ = synth(conn, settings, data, as_text(bad), as_text(bad))
    assert stats.calls == 2 and not stats.clean
    assert "walidacja po ponowieniu" in stats.warnings[0]
    assert report.slabe_sygnaly == [] and report.wzorce_zbieznosci        # reszta raportu zostaje


def test_unparseable_twice_gives_empty_report(conn, settings, data):
    report, stats, _ = synth(conn, settings, data, "nie JSON", "nadal nie JSON")
    assert report.w_skrocie == [] and "synteza nieudana" in stats.warnings[0]


def test_unparseable_retry_keeps_first_parsed_answer(conn, settings, data):
    ids = data[0]
    bad = mutate(valid_report(ids), lambda r: r["slabe_sygnaly"][0].update(article_ids=[999_999]))
    report, stats, _ = synth(conn, settings, data, as_text(bad), "urwany {")
    assert report.wzorce_zbieznosci and report.slabe_sygnaly == [] and stats.warnings


def test_budget_exceeded_skips_call(conn, settings, data):
    db.record_usage(conn, "deepseek-v4-pro", "direct", "extract", 0, 0, settings.budget.max_daily_usd, now=NOW)
    report, stats, fake = synth(conn, settings, data)
    assert fake.messages.calls == [] and stats.calls == 0
    assert "dzienny limit" in stats.warnings[0] and report.w_skrocie == []


def test_deepseek_with_thinking(conn, settings, data):
    ids, package, known = data
    settings = settings.model_copy(update={
        "models": settings.models.model_copy(update={"synthesize": "deepseek-v4-pro"}),
        "report": settings.report.model_copy(update={"thinking": "enabled", "effort": "high"}),
    })
    fake = FakeOpenAI(lambda p: chat_completion(as_text(valid_report(ids)), 30_000, 8_000))
    llm = DeepSeekClient(settings.pricing, client=fake, clock=lambda: NOW)
    report, stats = run_synthesis(conn, llm, settings, package, known, now=NOW)
    assert stats.clean and stats.model == "deepseek-v4-pro"
    call = fake.chat.completions.calls[0]
    assert call["extra_body"] == {"thinking": {"type": "enabled"}} and call["reasoning_effort"] == "high"


def test_truncated_deepseek_answer_is_retried(conn, settings, data):
    ids, package, known = data
    settings = settings.model_copy(update={
        "models": settings.models.model_copy(update={"synthesize": "deepseek-v4-pro"})})
    answers = [chat_completion('{"w_skrocie": [', finish_reason="length"),
               chat_completion(as_text(valid_report(ids)))]
    fake = FakeOpenAI(lambda p: answers.pop(0))
    llm = DeepSeekClient(settings.pricing, client=fake, clock=lambda: NOW)
    report, stats = run_synthesis(conn, llm, settings, package, known, now=NOW)
    assert stats.retried and stats.clean and "max_tokens" in stats.first_pass_errors[0]
