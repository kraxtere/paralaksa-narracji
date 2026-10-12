import json
import threading
import time

import pytest

from paralaksa.extract import call_log
from paralaksa.extract.llm_client import LLMRequest, LLMResult
from paralaksa.site import stories


def test_parallel_map_keeps_input_order_and_first_error_in_order():
    def slow_first(n):
        time.sleep(0.2 if n == 0 else 0.0)
        return n * 10

    assert stories.parallel_map(slow_first, [0, 1, 2, 3]) == [0, 10, 20, 30]      # wolny pierwszy, wynik dalej na pierwszym miejscu
    assert stories.parallel_map(lambda n: n, []) == [] and stories.parallel_map(lambda n: n + 1, [1]) == [2]

    def boom(n):
        if n in (1, 2):
            raise RuntimeError(f"błąd {n}")
        return n

    with pytest.raises(RuntimeError, match="błąd 1"):
        stories.parallel_map(boom, [0, 1, 2])


def test_generate_verifies_chunks_in_parallel_with_same_order_of_texts(tmp_path, monkeypatch):
    monkeypatch.setattr(stories, "VERIFY_CHUNK", 2)
    seen = {}

    def fake_parse_stories(cands, texts, items, **kw):
        seen["texts"] = list(texts)
        return []

    monkeypatch.setattr(stories, "parse_candidates", lambda text, items: [{"ids": [1, 2, 3, 4, 5]}])
    monkeypatch.setattr(stories, "build_verify_prompt", lambda cands, items, ids: ",".join(map(str, ids)))
    monkeypatch.setattr(stories, "parse_stories", fake_parse_stories)
    started = []

    class Client:
        def complete(self, req: LLMRequest) -> LLMResult:
            if req.custom_id.startswith("historie-weryfikacja"):
                started.append(req.custom_id)
                time.sleep(0.3 if req.custom_id.endswith("-1") else 0.0)       # pierwsza porcja kończy się ostatnia
            return LLMResult(custom_id=req.custom_id, model="m", mode="direct", text=req.messages[0]["content"], stop_reason="end")

    out = stories.generate(Client(), "m", "2026-10-12", [], tmp_path)
    assert seen["texts"] == ["1,2", "3,4", "5"] and len(started) == 3
    assert json.loads((tmp_path / "2026-10-12.json").read_text(encoding="utf-8"))["day"] == out["day"]
    assert not list(tmp_path.glob("*.tmp"))


def test_call_log_writes_only_with_day_and_counts_attempts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DZIEN", raising=False)
    call_log.log_call("a", 10, 1.0, True)
    assert not (tmp_path / "data").exists()
    monkeypatch.setenv("DZIEN", "2026-10-12")
    call_log._attempts.clear()
    call_log.log_call("a", 10, 1.234, False, "codex")
    call_log.log_call("a", 12, 2.0, True, "codex")
    rows = [json.loads(l) for l in (tmp_path / "data/widok/2026-10-12/_wywolania.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["proba"] for r in rows] == [1, 2] and rows[0]["s"] == 1.2 and rows[0]["ok"] is False and rows[1]["znaki"] == 12
    assert {"id", "start", "s", "znaki", "ok", "proba", "model", "pid"} <= set(rows[0])


def test_codex_client_logs_each_call(tmp_path, monkeypatch):
    import subprocess

    from paralaksa.extract.codex_client import CodexClient
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DZIEN", "2026-10-12")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    call_log._attempts.clear()

    def run(args, input=None, capture_output=None, timeout=None):
        out = args[args.index("-o") + 1]
        open(out, "w", encoding="utf-8").write("odpowiedź")
        return subprocess.CompletedProcess(args, 0, b"", b"")

    client = CodexClient(exe="codex.exe", run=run)
    res = client.complete(LLMRequest(custom_id="x-1", model="codex", max_tokens=10, messages=[{"role": "user", "content": "treść"}]))
    assert res.ok and res.text == "odpowiedź"
    row = json.loads((tmp_path / "data/widok/2026-10-12/_wywolania.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["id"] == "x-1" and row["ok"] is True and row["znaki"] == 5
