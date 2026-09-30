import base64
import subprocess
from pathlib import Path

import pytest

from paralaksa.extract import codex_client as C
from paralaksa.extract.llm_client import LLMRequest, build_client, model_extra_params


def fake_run(answer="{\"ok\": 1}", code=0, seen=None):
    def run(args, input, capture_output, timeout):
        if seen is not None:
            seen.update(args=args, prompt=input.decode("utf-8"),
                        images=[Path(a).read_bytes() for a, prev in zip(args[1:], args) if prev == "-i"])
        if code == 0:
            Path(args[args.index("-o") + 1]).write_text(answer, encoding="utf-8")
        return subprocess.CompletedProcess(args, code, b"", b"blad")
    return run


def req(content, model="codex"):
    return LLMRequest(custom_id="t", model=model, max_tokens=100, messages=[{"role": "user", "content": content}])


def test_answer_text_images_and_read_only_sandbox(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    seen = {}
    client = C.CodexClient(exe="codex.exe", run=fake_run(seen=seen))
    png = base64.b64encode(b"PNG").decode()
    res = client.complete(req([{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": png}},
                               {"type": "text", "text": "Przepisz tekst."}], model="codex:low"))
    assert res.ok and res.text == '{"ok": 1}' and res.cost_usd == 0
    assert seen["args"][seen["args"].index("--sandbox") + 1] == "read-only" and "--ephemeral" in seen["args"]
    assert 'model_reasoning_effort="low"' in seen["args"] and seen["images"] == [b"PNG"]
    assert seen["prompt"].endswith("Przepisz tekst.")


def test_failure_is_retryable_error(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    res = C.CodexClient(exe="codex.exe", run=fake_run(code=1)).complete(req("x"))
    assert not res.ok and res.retryable and "kod 1" in res.error


def test_refuses_ci_and_ultra(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(RuntimeError):
        C.CodexClient(exe="codex.exe")
    with pytest.raises(ValueError):
        C.effort_of("codex:ultra")


def test_build_client_routes_codex(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("PLX_CODEX", "codex.exe")
    assert isinstance(build_client("codex:medium", None, 1, 1), C.CodexClient)
    assert model_extra_params("codex", "disabled", None) == {}
