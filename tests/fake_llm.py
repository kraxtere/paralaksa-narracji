"""Fake Anthropic client for offline tests (mimics the parts of the SDK we use)."""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Callable

import anthropic
import httpx2

_REQ = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def api_error(status: int, cls=None) -> anthropic.APIStatusError:
    cls = cls or {400: anthropic.BadRequestError, 429: anthropic.RateLimitError}.get(status, anthropic.InternalServerError)
    return cls(f"error {status}", response=httpx2.Response(status, request=_REQ), body=None)


def connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=_REQ)


def message(text: str, input_tokens: int = 1000, output_tokens: int = 200, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens,
                              cache_read_input_tokens=0, cache_creation_input_tokens=0),
        stop_reason=stop_reason,
    )


def prompt_title(params: dict) -> str:
    return re.search(r"Tytuł: (.*)", params["messages"][0]["content"]).group(1).strip()


def valid_json_for(params: dict, n: int = 1, theme: str = "ukraine_war") -> str:
    """A valid answer whose evidence_span is the article title (always verbatim)."""
    title = prompt_title(params)
    signal = {
        "theme_id": theme, "subject_actor": "UA", "frame": "rama testowa", "stance": "neutralny",
        "intensity": 3, "signal_type": "fakt", "summary_pl": "Streszczenie testowe.",
        "evidence_span": " ".join(title.split()[:10]),
    }
    return json.dumps({"signals": [signal] * n}, ensure_ascii=False)


def default_responder(params: dict):
    return message(valid_json_for(params))


class FakeBatches:
    def __init__(self, owner: "FakeMessages", polls_until_end: int = 2, result_override: Callable | None = None):
        self.owner = owner
        self.polls_until_end = polls_until_end
        self.result_override = result_override
        self.created: list[list] = []
        self.polls = 0

    def create(self, requests):
        self.created.append(list(requests))
        return SimpleNamespace(id=f"batch_{len(self.created)}", processing_status="in_progress")

    def retrieve(self, batch_id):
        self.polls += 1
        status = "ended" if self.polls >= self.polls_until_end else "in_progress"
        return SimpleNamespace(id=batch_id, processing_status=status,
                               request_counts=SimpleNamespace(processing=1))

    def results(self, batch_id):
        requests = self.created[int(batch_id.split("_")[1]) - 1]
        out = []
        for req in reversed(requests):  # celowo w innej kolejności niż żądania
            if self.result_override:
                res = self.result_override(req)
                if res is None:
                    continue
            else:
                res = SimpleNamespace(type="succeeded", message=self.owner.responder(req["params"]))
            out.append(SimpleNamespace(custom_id=req["custom_id"], result=res))
        return out


class FakeMessages:
    def __init__(self, responder: Callable = default_responder, **batch_kw):
        self.responder = responder
        self.calls: list[dict] = []
        self.batches = FakeBatches(self, **batch_kw)

    def create(self, **params):
        self.calls.append(params)
        result = self.responder(params)
        if isinstance(result, Exception):
            raise result
        return result


class FakeAnthropic:
    def __init__(self, responder: Callable = default_responder, **batch_kw):
        self.messages = FakeMessages(responder, **batch_kw)


# ------------------------------------------------------------ DeepSeek (openai SDK, chat.completions)

import openai  # noqa: E402

_OAI_REQ = httpx2.Request("POST", "https://api.deepseek.com/chat/completions")


def openai_error(status: int, cls=None) -> openai.APIStatusError:
    cls = cls or {400: openai.BadRequestError, 429: openai.RateLimitError}.get(status, openai.InternalServerError)
    return cls(f"error {status}", response=httpx2.Response(status, request=_OAI_REQ), body=None)


def openai_connection_error() -> openai.APIConnectionError:
    return openai.APIConnectionError(request=_OAI_REQ)


def chat_completion(text: str, prompt_tokens: int = 1000, completion_tokens: int = 200,
                    cache_hit_tokens: int = 0, finish_reason: str = "stop"):
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=finish_reason, message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                              prompt_cache_hit_tokens=cache_hit_tokens),
    )


def default_chat_responder(params: dict):
    return chat_completion(valid_json_for(params))


class FakeChatCompletions:
    def __init__(self, responder: Callable):
        self.responder = responder
        self.calls: list[dict] = []

    def create(self, **params):
        self.calls.append(params)
        result = self.responder(params)
        if isinstance(result, Exception):
            raise result
        return result


class FakeOpenAI:
    """Fake `openai.OpenAI` client, only the `chat.completions.create` surface we use."""

    def __init__(self, responder: Callable = default_chat_responder):
        self.chat = SimpleNamespace(completions=FakeChatCompletions(responder))
