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
    results = {tuple(s.cmd): s.result for s in dzien.phase1(day)}

    def make_result(cmd):                                             # krok z kodem 0 zostawia swój plik wynikowy
        r = results.get(tuple(cmd))
        if r is not None:
            r.parent.mkdir(parents=True, exist_ok=True)
            r.write_text("{}")

    def fake(cmd, env):
        ran.append(cmd[-1] if len(cmd) < 3 else cmd[2])
        assert env["DZIEN"] == day
        if len(ran) == 4:
            return 1                                                  # czwarty uruchomiony krok pada
        make_result(cmd)
        return 0

    assert not dzien.run_steps(dzien.phase1(day), day, state, fake)
    assert len(ran) == 4 and "site" not in state.done and state.done == ["kategorie", "report", "dzien_prasy"][: len(state.done)]
    first_failed = [s.name for s in dzien.phase1(day)][4]
    assert first_failed not in state.done
    ran.clear()
    assert dzien.run_steps(dzien.phase1(day), day, dzien.State(day), lambda c, e: make_result(c) or 0)   # wznowienie: nic nie pada
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
    monkeypatch.setattr(dzien, "phase2", lambda d, timings=None: called.append(d) or True)
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

def test_phase1_graph_has_no_cycle_and_osdzien_waits_for_stories_marker():
    steps = {s.name: s for s in dzien.phase1("2026-10-12")}
    assert steps["os-dzien"].after == () and steps["os-dzien"].wait_files == (Path("data/stories/2026-10-12.json"),)
    assert set(steps["kraje-D"].after) == {"site", "os-dzien"}            # kraje.py czyta data/tytuly/D.json, więc czeka na cały site
    assert steps["os-ciag"].after == ("os-dzien",) and steps["kraje-ciag"].after == ("kraje-D",)
    done, left = set(), list(steps)
    while left:                                                            # każdy krok ma wszystkie `after` wcześniej: brak cyklu
        ready_now = [n for n in left if all(a in done for a in steps[n].after)]
        assert ready_now, f"cykl: {left}"
        done |= set(ready_now)
        left = [n for n in left if n not in done]


def test_step_starts_when_marker_file_is_ready_while_other_step_still_runs(tmp_path, monkeypatch):
    import threading
    import time
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dzien, "POLL_S", 0.05)
    day, order, lock = "2026-10-12", [], threading.Lock()
    marker = Path("marker.json")

    def fake(cmd, env):
        name = cmd[-1]
        with lock:
            order.append(("start", name))
        if name == "site":
            time.sleep(0.2)
            marker.write_text("{", encoding="utf-8")             # niekompletny JSON: jeszcze nie gotowy
            time.sleep(0.1)
            marker.write_text("{}", encoding="utf-8")
            time.sleep(1.5)
        with lock:
            order.append(("end", name))
        return 0

    steps = [dzien.Step("site", ["site"]), dzien.Step("os", ["os"], wait_files=(marker,))]
    assert dzien.run_parallel(steps, day, dzien.State(day), fake)
    pos = {e: i for i, e in enumerate(order)}
    assert pos[("start", "os")] < pos[("end", "site")]                    # nie czekał na koniec site
    assert marker.read_text(encoding="utf-8") == "{}"


def test_step_with_marker_that_never_appears_is_left_pending(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    steps = [dzien.Step("site", ["site"]), dzien.Step("os", ["os"], wait_files=(Path("brak.json"),))]
    assert not dzien.run_parallel(steps, "2026-10-12", dzien.State("2026-10-12"), lambda c, e: 0)
    assert "nie ruszyły: os (brak markera: brak.json)" in capsys.readouterr().out


def test_main_exits_nonzero_when_marker_never_appears(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dzien, "phase1", lambda day: [dzien.Step("site", ["site"]),
                                                      dzien.Step("os", ["os"], wait_files=(Path("brak.json"),))])
    monkeypatch.setattr(dzien, "shell", lambda c, e: 0)
    assert dzien.main(["2026-10-12", "--faza", "1"]) != 0


def test_timings_keep_earlier_phases_and_record_start_end(tmp_path, monkeypatch):
    import json
    monkeypatch.chdir(tmp_path)
    first = dzien.Timings("2026-10-12")
    first.step("site", 10.0)
    first.phase("faza1", 12.0)
    first.save()
    second = dzien.Timings("2026-10-12")                                  # kolejny proces (faza 2) nie nadpisuje
    second.step("obraz:x", 3.0)
    second.phase("faza2", 4.0)
    second.save()
    data = json.loads(Path("data/widok/2026-10-12/_czasy.json").read_text(encoding="utf-8"))
    assert data["fazy"] == {"faza1": 12.0, "faza2": 4.0} and set(data["kroki"]) == {"site", "obraz:x"}
    assert [r["krok"] for r in data["przebiegi"]] == ["site", "obraz:x"]
    assert set(data["przebiegi"][0]) == {"krok", "start", "koniec", "s"}


def test_step_exit_zero_without_result_file_fails_and_is_not_marked_done(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = dzien.State("2026-10-12")
    steps = [dzien.Step("site", ["site"], Path("stories.json")),
             dzien.Step("os", ["os"], wait_files=(Path("stories.json"),))]
    assert not dzien.run_parallel(steps, "2026-10-12", state, lambda c, e: 0)
    assert not state.has("site")
    assert not dzien.run_steps(steps[:1], "2026-10-12", state, lambda c, e: 0)
