import json
from datetime import datetime, timezone

import pytest

from fake_llm import FakeAnthropic, api_error, message, prompt_title, valid_json_for
from paralaksa import db
from paralaksa.config import load_themes
from paralaksa.extract.llm_client import LLMClient
from paralaksa.extract.signals import extract_pending, load_prompt, pending_articles

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
THEMES = load_themes()
FULLTEXT = ("Rosyjskie drony zaatakowały infrastrukturę energetyczną w obwodzie charkowskim. "
            "Władze poinformowały o przerwach w dostawach prądu. ") * 20


@pytest.fixture
def seeded(conn, make_source):
    db.upsert_sources(conn, [
        make_source("full", country="UK", language="en", fulltext=True),
        make_source("lead", country="PL", language="pl", type="private"),
    ])

    def add(n: int, source_id: str = "full", start: int = 0):
        for i in range(start, start + n):
            db.insert_article(conn, db.ArticleRow(
                source_id=source_id, url=f"https://ex.com/{source_id}/{i}", url_hash=f"{source_id}-{i}",
                title=f"Artykuł numer {i} o ataku na infrastrukturę energetyczną Ukrainy",
                lead=f"Lead artykułu {i}.", language="en", published_at="2026-09-23T06:00:00+00:00",
                fetched_at="2026-09-23T07:00:00+00:00",
                fulltext=FULLTEXT if source_id == "full" else None,
            ))
        conn.commit()
    return add


def run(conn, settings, responder=None, **kw):
    fake = FakeAnthropic(responder) if responder else FakeAnthropic()
    llm = LLMClient(settings.pricing, client=fake, poll_interval_s=0, sleep=lambda s: None)
    stats = extract_pending(conn, llm, settings, THEMES, now=NOW, **kw)
    return stats, fake


def statuses(conn) -> list[int]:
    return [r[0] for r in conn.execute("SELECT extracted FROM articles ORDER BY id")]


# ------------------------------------------------------------------ end-to-end

def test_end_to_end_20_articles(conn, settings, seeded):
    seeded(14, "full")
    seeded(6, "lead")
    stats, fake = run(conn, settings)

    assert stats.mode == "direct" and stats.pending == 20
    assert stats.done == 20 and stats.signals == 20 and stats.failed == stats.deferred == 0
    assert statuses(conn) == [1] * 20
    _, version = load_prompt()
    rows = conn.execute("SELECT source_depth, prompt_version, model, COUNT(*) n FROM signals GROUP BY 1, 2, 3").fetchall()
    assert {(r["source_depth"], r["n"]) for r in rows} == {("fulltext", 14), ("lead_only", 6)}
    assert {r["prompt_version"] for r in rows} == {version}
    assert {r["model"] for r in rows} == {settings.models.extract}
    usage = conn.execute("SELECT COUNT(*), SUM(cost_usd), MIN(date), MIN(purpose) FROM api_usage").fetchone()
    assert usage[0] == 20 and usage[1] == pytest.approx(stats.cost_usd)
    assert usage[2] == "2026-09-23" and usage[3] == "extract"
    assert db.spent_on(conn, "2026-09-23") == pytest.approx(stats.cost_usd)
    assert fake.messages.calls[0]["thinking"] == {"type": "disabled"}  # Sonnet 5: jawnie wyłączone
    assert pending_articles(conn) == []


def test_source_depth_and_material_note(conn, settings, seeded):
    seeded(1, "full")
    seeded(1, "lead")
    _, fake = run(conn, settings)
    prompts = [c["messages"][0]["content"] for c in fake.messages.calls]
    full_prompt, lead_prompt = sorted(prompts, key=lambda p: "TYLKO tytuł i lead" in p)
    assert "pełny tekst artykułu" in full_prompt and "Rosyjskie drony" in full_prompt
    assert "TYLKO tytuł i lead" in lead_prompt and "(niedostępny" in lead_prompt
    depth = dict(conn.execute(
        "SELECT a.source_id, s.source_depth FROM signals s JOIN articles a ON a.id = s.article_id").fetchall())
    assert depth == {"full": "fulltext", "lead": "lead_only"}


# ------------------------------------------------------------------ retry / validation

def test_retry_with_error_list_then_success(conn, settings, seeded):
    seeded(1)

    def responder(params):
        if len(params["messages"]) == 1:
            return message("to nie jest JSON")
        assert "nie przeszła walidacji" in params["messages"][2]["content"]
        return message(valid_json_for(params))

    stats, fake = run(conn, settings, responder)
    assert stats.retries == 1 and stats.done == 1 and stats.signals == 1
    assert len(fake.messages.calls) == 2
    assert conn.execute("SELECT COUNT(*) FROM api_usage").fetchone()[0] == 2


def test_invalid_signal_dropped_with_note(conn, settings, seeded):
    seeded(1)

    def responder(params):
        good = json.loads(valid_json_for(params))["signals"][0]
        return message(json.dumps({"signals": [good, {**good, "stance": "zły"}]}, ensure_ascii=False))

    stats, _ = run(conn, settings, responder)
    assert stats.retries == 1 and stats.done == 1 and stats.signals == 1 and stats.dropped == 1
    status, error = conn.execute("SELECT extracted, extract_error FROM articles").fetchone()
    assert status == 1 and error.startswith("odrzucono 1")


def test_fatal_twice_marks_failed(conn, settings, seeded):
    seeded(1)
    stats, _ = run(conn, settings, lambda p: message("nie wiem"))
    assert stats.failed == 1 and stats.done == 0
    status, error = conn.execute("SELECT extracted, extract_error FROM articles").fetchone()
    assert status == 2 and "walidacja po ponowieniu" in error
    assert pending_articles(conn) == []  # nie wraca w kolejnych przebiegach


def test_transient_error_leaves_article_pending(conn, settings, seeded):
    seeded(1)
    stats, _ = run(conn, settings, lambda p: api_error(429))
    assert stats.deferred == 1 and stats.failed == 0
    status, error = conn.execute("SELECT extracted, extract_error FROM articles").fetchone()
    assert status == 0 and "limit" in error
    assert len(pending_articles(conn)) == 1


def test_permanent_api_error_marks_failed(conn, settings, seeded):
    seeded(1)
    stats, _ = run(conn, settings, lambda p: api_error(400))
    assert stats.failed == 1 and statuses(conn) == [2]


# ------------------------------------------------------------------ budget

def test_budget_stops_direct_run(conn, settings, seeded):
    seeded(10)
    settings.budget.max_daily_usd = 0.02
    settings.extract.max_concurrency = 1
    stats, _ = run(conn, settings)
    assert stats.budget_stopped
    assert 0 < stats.done < 10 and stats.done + stats.deferred == 10
    assert statuses(conn).count(0) == stats.deferred
    assert db.spent_on(conn, "2026-09-23") <= 0.02


def test_budget_counts_earlier_spending_today(conn, settings, seeded):
    seeded(3)
    settings.budget.max_daily_usd = 1.0
    db.record_usage(conn, "claude-sonnet-5", "direct", "extract", 0, 0, 0.999, now=NOW)
    stats, fake = run(conn, settings)
    assert stats.budget_stopped and stats.done == 0 and stats.deferred == 3
    assert fake.messages.calls == []


def test_budget_trims_batch(conn, settings, seeded):
    seeded(60)
    settings.budget.max_daily_usd = 0.1
    stats, fake = run(conn, settings)
    submitted = len(fake.messages.batches.created[0])
    assert stats.mode == "batch" and stats.budget_stopped
    assert 0 < submitted < 60 and stats.done == submitted and stats.deferred == 60 - submitted
    assert db.spent_on(conn, "2026-09-23") <= 0.1


# ------------------------------------------------------------------ batch threshold (SPEC: batch, gdy > 50)

def test_threshold_50_is_direct(conn, settings, seeded):
    seeded(50)
    stats, fake = run(conn, settings)
    assert stats.mode == "direct" and fake.messages.batches.created == []
    assert len(fake.messages.calls) == 50 and stats.done == 50


def test_threshold_51_is_batch(conn, settings, seeded):
    seeded(51)
    stats, fake = run(conn, settings)
    assert stats.mode == "batch" and stats.batch_id == "batch_1"
    assert len(fake.messages.batches.created[0]) == 51 and fake.messages.calls == []
    assert stats.done == 51
    assert conn.execute("SELECT DISTINCT mode FROM api_usage").fetchall()[0][0] == "batch"


def test_limit_50_of_51_is_direct(conn, settings, seeded):
    seeded(51)
    stats, fake = run(conn, settings, limit=50)
    assert stats.mode == "direct" and stats.done == 50 and len(pending_articles(conn)) == 1


def test_deepseek_always_direct_above_threshold(conn, settings, seeded):
    """DeepSeek nie ma Batches API: nawet 51 artykułów idzie bezpośrednio, przez DeepSeekClient.complete()."""
    from fake_llm import FakeOpenAI, chat_completion
    from paralaksa.extract.llm_client import DeepSeekClient

    seeded(51)
    settings.models.extract = "deepseek-v4-pro"
    fake = FakeOpenAI(lambda p: chat_completion(valid_json_for(p)))
    llm = DeepSeekClient(settings.pricing, client=fake)
    stats = extract_pending(conn, llm, settings, THEMES, now=NOW)
    assert stats.mode == "direct" and stats.done == 51
    assert len(fake.chat.completions.calls) == 51
    assert conn.execute("SELECT DISTINCT mode FROM api_usage").fetchall()[0][0] == "direct"
    assert conn.execute("SELECT DISTINCT model FROM signals").fetchone()[0] == "deepseek-v4-pro"


def test_no_batch_flag_with_51(conn, settings, seeded):
    seeded(51)
    stats, fake = run(conn, settings, use_batch=False)
    assert stats.mode == "direct" and fake.messages.batches.created == [] and stats.done == 51


def test_batch_validation_retry_is_direct(conn, settings, seeded):
    seeded(51)

    def responder(params):
        if len(params["messages"]) == 1 and "numer 7 " in params["messages"][0]["content"]:
            return message("zepsute")
        return message(valid_json_for(params))

    stats, fake = run(conn, settings, responder)
    assert stats.mode == "batch" and stats.retries == 1 and stats.done == 51
    assert len(fake.messages.calls) == 1  # tylko ponowienie poza batchem
