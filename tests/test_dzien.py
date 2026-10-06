import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "v2"))
import dzien  # noqa: E402


def test_steps_skip_done_and_resume(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    day = "2026-10-05"
    Path("data/stories").mkdir(parents=True)
    Path(f"data/stories/{day}.json").write_text("{}")                 # wynik pierwszego kroku istnieje
    ran, state = [], dzien.State(day)

    def fake(cmd, env):
        ran.append(cmd[-1] if len(cmd) < 3 else cmd[2])
        assert env["DZIEN"] == day
        return 1 if len(ran) == 4 else 0                              # czwarty uruchomiony krok pada

    assert not dzien.run_steps(dzien.phase1(day), day, state, fake)
    assert len(ran) == 4 and "site" not in state.done and state.done == ["kategorie", "report", "dzien_prasy"][: len(state.done)]
    first_failed = [s.name for s in dzien.phase1(day)][4]
    assert first_failed not in state.done
    ran.clear()
    assert dzien.run_steps(dzien.phase1(day), day, dzien.State(day), lambda c, e: 0)   # wznowienie: nic nie pada
    assert dzien.State(day).done[-1] == "kraje-ciag"


def test_dry_run_runs_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    called = []
    assert dzien.run_steps(dzien.phase1("2026-10-05"), "2026-10-05", dzien.State("2026-10-05"),
                           lambda c, e: called.append(c) or 0, dry=True)
    assert not called


def test_phase3_pages_always_rebuilt_and_publish_optional(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    day = "2026-10-05"
    state = dzien.State(day)
    state.add("strona-dnia")
    ran = []
    dzien.run_steps(dzien.phase3(day, False), day, state, lambda c, e: ran.append(c) or 0)
    assert len(ran) == 7 and not any("--publikuj" in c for c in ran)
    assert any("--publikuj" in s.cmd for s in dzien.phase3(day, True))


def test_phase2_single_queue_and_failure(monkeypatch):
    seen = {}

    def fake_run_all(jobs):
        seen["labels"] = [label for label, _ in jobs]
        return {"a": "ok", "b": "429"}
    import paski
    monkeypatch.setattr(paski, "run_all", fake_run_all)
    monkeypatch.delenv("PASKI_PROCESY", raising=False)
    assert not dzien.phase2("2026-10-05", build=lambda d: [("a", lambda: "ok"), ("b", lambda: "429")])
    assert seen["labels"] == ["a", "b"]
    import os
    assert os.environ["PASKI_PROCESY"] == "100"
    monkeypatch.delenv("PASKI_PROCESY")
    assert dzien.phase2("2026-10-05", build=lambda d: [])                # nic do zrobienia


def test_main_stops_after_failed_phase(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dzien, "shell", lambda c, e: 1)
    called = []
    monkeypatch.setattr(dzien, "phase2", lambda d: called.append(d) or True)
    assert dzien.main(["2026-10-05"]) == 1 and not called


def test_parallel_respects_after_and_stops_on_failure(tmp_path, monkeypatch):
    import threading
    import time
    monkeypatch.chdir(tmp_path)
    day, order, lock = "2026-10-05", [], threading.Lock()
    tm = dzien.Timings(day)

    def fake(cmd, env):
        name = cmd[-1]
        with lock:
            order.append(("start", name))
        time.sleep(0.05)
        with lock:
            order.append(("end", name))
        return 0

    mk = lambda n, *a: dzien.Step(n, [n], after=a)  # noqa: E731
    steps = [mk("a"), mk("b"), mk("c", "a"), mk("d", "b", "c")]
    assert dzien.run_parallel(steps, day, dzien.State(day), fake, timings=tm)
    pos = {e: i for i, e in enumerate(order)}
    assert pos[("start", "b")] < pos[("end", "a")]                       # niezależne ruszyły razem
    assert pos[("end", "a")] < pos[("start", "c")] and pos[("end", "c")] < pos[("start", "d")]
    assert set(tm.steps) == {"a", "b", "c", "d"}

    state = dzien.State("2026-10-06")
    assert not dzien.run_parallel(steps, "2026-10-06", state, lambda c, e: 1 if c[-1] == "a" else 0)
    assert "c" not in state.done and "d" not in state.done
