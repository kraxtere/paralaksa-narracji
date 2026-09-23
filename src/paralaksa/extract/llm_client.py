"""Thin wrappers over provider SDKs: direct calls, Message Batches (Anthropic only), cost accounting.

Retries of transient errors (429, 5xx, connection) are done by the SDK itself (max_retries).
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

from paralaksa.config import Pricing

log = logging.getLogger(__name__)


@dataclass
class LLMRequest:
    custom_id: str
    model: str
    max_tokens: int
    messages: list[dict[str, Any]]
    extra: dict[str, Any] = field(default_factory=dict)   # np. thinking, output_config

    def params(self) -> dict[str, Any]:
        return {"model": self.model, "max_tokens": self.max_tokens, "messages": self.messages, **self.extra}


def model_extra_params(model: str, thinking: str, effort: str | None) -> dict[str, Any]:
    """Model/provider-specific request params.

    Haiku 4.5 supports neither adaptive thinking nor effort. DeepSeek (chat.completions,
    OpenAI-compatible) takes thinking via `extra_body` and effort via a top-level `reasoning_effort`,
    unlike Anthropic's `thinking` + `output_config.effort`.
    """
    if model.startswith("deepseek"):
        params: dict[str, Any] = {"extra_body": {"thinking": {"type": thinking}}}
        if effort:
            params["reasoning_effort"] = effort
        return params
    if model.startswith("claude-haiku-4-5"):
        return {}
    extra: dict[str, Any] = {"thinking": {"type": thinking}}
    if effort:
        extra["output_config"] = {"effort": effort}
    return extra


@dataclass
class LLMResult:
    custom_id: str
    model: str
    mode: str                       # direct | batch
    text: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    stop_reason: str | None = None
    error: str | None = None
    retryable: bool = False         # błąd przejściowy: artykuł wraca do kolejki
    batch_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.text is not None


@dataclass
class BatchOutcome:
    batch_id: str
    results: dict[str, LLMResult] = field(default_factory=dict)


def _message_text(message) -> str:
    return "".join(b.text for b in message.content if b.type == "text")


class LLMClient:
    def __init__(
        self,
        pricing: Pricing,
        client: Any | None = None,
        poll_interval_s: float = 30.0,
        batch_timeout_h: float = 24.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.pricing = pricing
        self._client = client if client is not None else anthropic.Anthropic(max_retries=4)
        self.poll_interval_s = poll_interval_s
        self.batch_timeout_s = batch_timeout_h * 3600
        self._sleep = sleep

    # ------------------------------------------------------------ direct

    def complete(self, req: LLMRequest) -> LLMResult:
        result = LLMResult(custom_id=req.custom_id, model=req.model, mode="direct")
        try:
            message = self._client.messages.create(**req.params())
        except anthropic.BadRequestError as e:
            result.error = f"błąd żądania: {e.message}"
            return result
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError, anthropic.NotFoundError):
            raise  # błąd konfiguracji: przerywamy cały przebieg
        except anthropic.RateLimitError as e:
            result.error, result.retryable = f"limit zapytań: {e.message}", True
            return result
        except anthropic.APIStatusError as e:
            result.error, result.retryable = f"błąd API {e.status_code}: {e.message}", e.status_code >= 500
            return result
        except anthropic.APIConnectionError as e:
            result.error, result.retryable = f"błąd połączenia: {e}", True
            return result
        self._fill(result, message, batch=False)
        return result

    # ------------------------------------------------------------ batch

    def submit_batch(self, reqs: list[LLMRequest]) -> str:
        batch = self._client.messages.batches.create(
            requests=[
                Request(custom_id=r.custom_id, params=MessageCreateParamsNonStreaming(**r.params()))
                for r in reqs
            ]
        )
        log.info("Utworzono batch %s (%d żądań)", batch.id, len(reqs))
        return batch.id

    def wait_batch(self, batch_id: str) -> None:
        waited = 0.0
        while True:
            batch = self._client.messages.batches.retrieve(batch_id)
            if batch.processing_status == "ended":
                return
            if waited >= self.batch_timeout_s:
                raise TimeoutError(f"batch {batch_id} nie zakończył się w {self.batch_timeout_s / 3600:.0f} h")
            log.info("Batch %s: %s, w toku: %s", batch_id, batch.processing_status,
                     getattr(batch.request_counts, "processing", "?"))
            self._sleep(self.poll_interval_s)
            waited += self.poll_interval_s

    def batch_results(self, batch_id: str, models: dict[str, str]) -> dict[str, LLMResult]:
        """Results keyed by custom_id (the API returns them in arbitrary order)."""
        out: dict[str, LLMResult] = {}
        for item in self._client.messages.batches.results(batch_id):
            res = LLMResult(custom_id=item.custom_id, model=models.get(item.custom_id, ""),
                            mode="batch", batch_id=batch_id)
            kind = item.result.type
            if kind == "succeeded":
                self._fill(res, item.result.message, batch=True)
            elif kind == "errored":
                err = item.result.error
                err_type = getattr(getattr(err, "error", err), "type", "unknown")
                res.error = f"batch errored: {err_type}"
                res.retryable = err_type != "invalid_request_error" and err_type != "invalid_request"
            else:  # canceled | expired
                res.error, res.retryable = f"batch {kind}", True
            out[item.custom_id] = res
        return out

    def run_batch(self, reqs: list[LLMRequest]) -> BatchOutcome:
        batch_id = self.submit_batch(reqs)
        self.wait_batch(batch_id)
        results = self.batch_results(batch_id, {r.custom_id: r.model for r in reqs})
        for r in reqs:  # brak wyniku dla żądania: traktujemy jak przejściowy błąd
            results.setdefault(r.custom_id, LLMResult(r.custom_id, r.model, "batch", error="brak wyniku w batchu",
                                                      retryable=True, batch_id=batch_id))
        return BatchOutcome(batch_id, results)

    # ------------------------------------------------------------ helpers

    def _fill(self, result: LLMResult, message, batch: bool) -> None:
        usage = message.usage
        result.text = _message_text(message)
        result.stop_reason = message.stop_reason
        result.input_tokens = (usage.input_tokens or 0) + (getattr(usage, "cache_read_input_tokens", 0) or 0) \
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
        result.output_tokens = usage.output_tokens or 0
        result.cost_usd = self.pricing.cost(result.model, result.input_tokens, result.output_tokens, batch=batch)
        if message.stop_reason == "refusal":
            result.error = "model odmówił (refusal)"


class DeepSeekClient:
    """Direct calls only (DeepSeek nie ma Message Batches API). Duck-type kompatybilny z LLMClient.complete()."""

    def __init__(
        self,
        pricing: Pricing,
        client: Any | None = None,
        api_key: str | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.pricing = pricing
        self._clock = clock
        if client is not None:
            self._client = client
        else:
            import openai  # zależność opcjonalna, tylko dla tego dostawcy
            self._client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com", max_retries=4)

    def complete(self, req: LLMRequest) -> LLMResult:
        result = LLMResult(custom_id=req.custom_id, model=req.model, mode="direct")
        import openai
        try:
            resp = self._client.chat.completions.create(
                model=req.model, max_tokens=req.max_tokens, messages=req.messages, **req.extra
            )
        except openai.BadRequestError as e:
            result.error = f"błąd żądania: {e}"
            return result
        except (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError):
            raise  # błąd konfiguracji: przerywamy cały przebieg
        except openai.RateLimitError as e:
            result.error, result.retryable = f"limit zapytań: {e}", True
            return result
        except openai.APIStatusError as e:
            result.error, result.retryable = f"błąd API {e.status_code}: {e}", e.status_code >= 500
            return result
        except openai.APIConnectionError as e:
            result.error, result.retryable = f"błąd połączenia: {e}", True
            return result
        choice = resp.choices[0]
        result.text = choice.message.content
        result.stop_reason = choice.finish_reason
        usage = resp.usage
        cache_hit = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
        result.input_tokens = usage.prompt_tokens or 0
        result.output_tokens = usage.completion_tokens or 0   # tokeny myślenia liczą się jako wyjście
        result.cost_usd = self.pricing.deepseek.cost(
            req.model, result.input_tokens, result.output_tokens, cache_hit_tokens=cache_hit, at=self._clock()
        )
        if choice.finish_reason == "content_filter":
            result.error = "model odmówił (content_filter)"
        elif choice.finish_reason == "length":
            result.error = "odpowiedź obcięta przez max_tokens"
            result.retryable = False
        return result


def build_client(
    model: str, pricing: Pricing, poll_interval_s: float, batch_timeout_h: float
) -> LLMClient | DeepSeekClient:
    """Wybór klienta po prefiksie modelu. DeepSeek: klucz z DEEPSEEK_API_KEY (brak Batches API)."""
    if model.startswith("deepseek"):
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError(
                f"model '{model}' wymaga zmiennej środowiskowej DEEPSEEK_API_KEY (ustaw w .env)"
            )
        return DeepSeekClient(pricing, api_key=api_key)
    return LLMClient(pricing, poll_interval_s=poll_interval_s, batch_timeout_h=batch_timeout_h)
