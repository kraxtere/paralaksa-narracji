from datetime import datetime, timezone
from types import SimpleNamespace

import anthropic
import pytest

from fake_llm import FakeAnthropic, FakeOpenAI, api_error, connection_error, message, openai_error
from paralaksa.config import Pricing, is_deepseek_peak
from paralaksa.extract.llm_client import DeepSeekClient, LLMClient, LLMRequest, build_client, model_extra_params

PRICING = Pricing()


def req(i=1, model="claude-sonnet-5", extra=None) -> LLMRequest:
    return LLMRequest(f"article-{i}", model, 4000, [{"role": "user", "content": f"Tytuł: A{i}"}], extra or {})


def client(responder=None, **kw) -> tuple[LLMClient, FakeAnthropic]:
    fake = FakeAnthropic(responder or (lambda p: message("{}", 1_000_000, 100_000)), **kw)
    return LLMClient(PRICING, client=fake, poll_interval_s=0, sleep=lambda s: None), fake


def test_pricing_cost():
    assert PRICING.cost("claude-sonnet-5", 1_000_000, 100_000) == pytest.approx(3.0)
    assert PRICING.cost("claude-sonnet-5", 1_000_000, 100_000, batch=True) == pytest.approx(1.5)
    assert PRICING.cost("claude-haiku-4-5-20251001", 1_000_000, 0) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="cennika"):
        PRICING.cost("claude-unknown", 1, 1)


FRIDAY_PEAK = datetime(2026, 9, 25, 2, 0, tzinfo=timezone.utc)       # pt. 02:00 UTC -> szczyt
FRIDAY_OFF_PEAK = datetime(2026, 9, 25, 5, 0, tzinfo=timezone.utc)   # pt. 05:00 UTC -> poza szczytem
SATURDAY_PEAK_HOUR = datetime(2026, 9, 26, 2, 0, tzinfo=timezone.utc)  # sobota: zawsze poza szczytem


def test_deepseek_peak_windows():
    assert is_deepseek_peak(FRIDAY_PEAK)
    assert not is_deepseek_peak(FRIDAY_OFF_PEAK)
    assert not is_deepseek_peak(SATURDAY_PEAK_HOUR)


def test_deepseek_cost_peak_vs_off_peak_and_cache():
    p = PRICING.deepseek
    peak = p.cost("deepseek-v4-pro", 1_000_000, 1_000_000, at=FRIDAY_PEAK)
    off_peak = p.cost("deepseek-v4-pro", 1_000_000, 1_000_000, at=FRIDAY_OFF_PEAK)
    assert peak == pytest.approx(1.32 + 3.96)
    assert off_peak == pytest.approx(0.66 + 1.98)
    assert off_peak == pytest.approx(peak / 2)
    with_cache = p.cost("deepseek-v4-pro", 1_000_000, 0, cache_hit_tokens=1_000_000, at=FRIDAY_OFF_PEAK)
    assert with_cache == pytest.approx(0.022)  # 100% trafień w cache
    with pytest.raises(ValueError, match="cennika"):
        p.cost("deepseek-unknown", 1, 1)


def test_pricing_cost_dispatches_to_deepseek():
    assert PRICING.cost("deepseek-flash", 1_000_000, 0, at=FRIDAY_OFF_PEAK) == pytest.approx(0.15)
    assert PRICING.cost("deepseek-flash", 1_000_000, 0) == pytest.approx(0.30)  # brak `at`: zakładamy szczyt


def test_complete_success_and_cost():
    llm, fake = client()
    res = llm.complete(req())
    assert res.ok and res.mode == "direct"
    assert res.input_tokens == 1_000_000 and res.cost_usd == pytest.approx(3.0)
    assert fake.messages.calls[0]["model"] == "claude-sonnet-5"


def test_extra_params_passed():
    llm, fake = client()
    llm.complete(req(extra={"thinking": {"type": "disabled"}}))
    assert fake.messages.calls[0]["thinking"] == {"type": "disabled"}


def test_model_extra_params():
    assert model_extra_params("claude-haiku-4-5-20251001", "adaptive", "low") == {}
    assert model_extra_params("claude-sonnet-5", "disabled", None) == {"thinking": {"type": "disabled"}}
    assert model_extra_params("claude-sonnet-5", "adaptive", "low") == {
        "thinking": {"type": "adaptive"}, "output_config": {"effort": "low"}}


@pytest.mark.parametrize("exc,retryable", [
    (api_error(400), False),
    (api_error(429), True),
    (api_error(529, anthropic.InternalServerError), True),
    (api_error(500), True),
    (connection_error(), True),
])
def test_error_mapping(exc, retryable):
    llm, _ = client(lambda p: exc)
    res = llm.complete(req())
    assert not res.ok and res.retryable is retryable and res.cost_usd == 0


def test_auth_error_propagates():
    llm, _ = client(lambda p: api_error(401, anthropic.AuthenticationError))
    with pytest.raises(anthropic.AuthenticationError):
        llm.complete(req())


def test_refusal_is_error():
    llm, _ = client(lambda p: message("", 100, 0, stop_reason="refusal"))
    res = llm.complete(req())
    assert not res.ok and "refusal" in res.error


def test_batch_results_keyed_by_custom_id():
    llm, fake = client(lambda p: message(p["messages"][0]["content"], 1_000_000, 0))
    outcome = llm.run_batch([req(i) for i in range(1, 4)])
    assert outcome.batch_id == "batch_1"
    assert fake.messages.batches.polls == 2
    for i in range(1, 4):
        r = outcome.results[f"article-{i}"]
        assert r.text == f"Tytuł: A{i}" and r.mode == "batch" and r.batch_id == "batch_1"
        assert r.cost_usd == pytest.approx(1.0)  # 50% z $2


def test_batch_errored_expired_and_missing():
    def override(request):
        cid = request["custom_id"]
        if cid == "article-1":
            return SimpleNamespace(type="errored", error=SimpleNamespace(
                error=SimpleNamespace(type="invalid_request_error")))
        if cid == "article-2":
            return SimpleNamespace(type="errored", error=SimpleNamespace(error=SimpleNamespace(type="api_error")))
        if cid == "article-3":
            return SimpleNamespace(type="expired")
        return None  # article-4: brak wyniku

    llm, _ = client(result_override=override)
    res = llm.run_batch([req(i) for i in range(1, 5)]).results
    assert not res["article-1"].retryable
    assert res["article-2"].retryable
    assert res["article-3"].retryable and "expired" in res["article-3"].error
    assert res["article-4"].retryable and "brak wyniku" in res["article-4"].error


def test_batch_timeout():
    llm, _ = client(polls_until_end=10**6)
    llm.batch_timeout_s = 0
    with pytest.raises(TimeoutError):
        llm.run_batch([req()])


# ------------------------------------------------------------ DeepSeek

def ds_req(i=1, model="deepseek-v4-pro", extra=None) -> LLMRequest:
    return LLMRequest(f"article-{i}", model, 4000, [{"role": "user", "content": f"Tytuł: A{i}"}], extra or {})


def ds_client(responder=None) -> tuple[DeepSeekClient, FakeOpenAI]:
    from fake_llm import FakeOpenAI as _FakeOpenAI
    fake = _FakeOpenAI(responder) if responder else _FakeOpenAI()
    return DeepSeekClient(PRICING, client=fake, clock=lambda: FRIDAY_OFF_PEAK), fake


def test_deepseek_complete_success_and_cost():
    from fake_llm import chat_completion
    llm, fake = ds_client(lambda p: chat_completion("{}", 1_000_000, 1_000_000))
    res = llm.complete(ds_req())
    assert res.ok and res.mode == "direct"
    assert res.input_tokens == 1_000_000 and res.output_tokens == 1_000_000
    assert res.cost_usd == pytest.approx(0.66 + 1.98)  # off-peak, brak trafień w cache
    assert fake.chat.completions.calls[0]["model"] == "deepseek-v4-pro"


def test_deepseek_cache_hit_lowers_cost():
    from fake_llm import chat_completion
    llm, _ = ds_client(lambda p: chat_completion("{}", 1_000_000, 0, cache_hit_tokens=1_000_000))
    res = llm.complete(ds_req())
    assert res.cost_usd == pytest.approx(0.022)


def test_deepseek_extra_params_passed():
    llm, fake = ds_client()
    llm.complete(ds_req(extra={"extra_body": {"thinking": {"type": "enabled"}}, "reasoning_effort": "low"}))
    call = fake.chat.completions.calls[0]
    assert call["extra_body"] == {"thinking": {"type": "enabled"}}
    assert call["reasoning_effort"] == "low"


def test_deepseek_model_extra_params():
    assert model_extra_params("deepseek-v4-pro", "disabled", None) == {"extra_body": {"thinking": {"type": "disabled"}}}
    assert model_extra_params("deepseek-v4-pro", "enabled", "low") == {
        "extra_body": {"thinking": {"type": "enabled"}}, "reasoning_effort": "low"}


@pytest.mark.parametrize("exc,retryable", [
    (openai_error(400), False),
    (openai_error(429), True),
    (openai_error(500), True),
])
def test_deepseek_error_mapping(exc, retryable):
    llm, _ = ds_client(lambda p: exc)
    res = llm.complete(ds_req())
    assert not res.ok and res.retryable is retryable and res.cost_usd == 0


def test_deepseek_auth_error_propagates():
    llm, _ = ds_client(lambda p: openai_error(401, __import__("openai").AuthenticationError))
    with pytest.raises(__import__("openai").AuthenticationError):
        llm.complete(ds_req())


def test_deepseek_length_finish_reason_is_error():
    from fake_llm import chat_completion
    llm, _ = ds_client(lambda p: chat_completion("obcięta odpo", finish_reason="length"))
    res = llm.complete(ds_req())
    assert not res.ok and "max_tokens" in res.error


def test_deepseek_content_filter_is_error():
    from fake_llm import chat_completion
    llm, _ = ds_client(lambda p: chat_completion("", finish_reason="content_filter"))
    res = llm.complete(ds_req())
    assert not res.ok and "content_filter" in res.error


# ------------------------------------------------------------ build_client


def test_build_client_returns_llm_client_for_claude_model():
    llm = build_client("claude-sonnet-5", PRICING, poll_interval_s=1, batch_timeout_h=2)
    assert isinstance(llm, LLMClient)


def test_build_client_returns_deepseek_client_with_env_key(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    llm = build_client("deepseek-v4-pro", PRICING, poll_interval_s=1, batch_timeout_h=2)
    assert isinstance(llm, DeepSeekClient)


def test_build_client_missing_deepseek_key_raises(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        build_client("deepseek-v4-pro", PRICING, poll_interval_s=1, batch_timeout_h=2)
