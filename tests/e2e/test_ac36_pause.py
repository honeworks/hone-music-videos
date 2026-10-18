"""AC-36 to AC-40: Pause and Stop a running video (0022); the frame run's own pause is AC-64 (0027).

A fake model asks for the pause while it makes a file; the run then stops before its next model call,
reports `paused`, and Resume makes the rest, no file twice. Stop also ends the call being made: a local
one through ComfyUI's interrupt (the fake fails as an interrupted job does), a hosted one by no longer
waiting for it."""

import threading
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import pause, runs_pause
from hone_music_video.testing import Call, FakeModels, make_sheet, make_song
from tests.conftest import drive

pytestmark = pytest.mark.e2e


def video(tmp_path: Path) -> hmv.Project:
    """A 30 s song with Darvin's sheet: six shots."""
    material = hmv.Material(
        sheets=(hmv.GivenSheet("Darvin", make_sheet(tmp_path / "darvin.png"), "the hero"),)
    )
    return hmv.create_project(
        tmp_path / "projects", "Pause", make_song(tmp_path / "song.wav", 30_000), material
    )


def files_made(models: FakeModels) -> Counter[tuple[str, str]]:
    return Counter((c.out.parent.parent.name, c.out.name) for c in models.calls_of("generate") if c.out)


def drafts(models: FakeModels) -> int:
    """The clips begun (0027: the start frames are the frame run's, whose pause is AC-64)."""
    return sum(1 for c in models.calls_of("generate") if c.out and c.out.name.startswith("clips-"))


class Asker:
    """A fake model hook: once `when(call)` holds, `act(call)` runs (it asks for the pause)."""

    def __init__(self, when: Callable[[Call], bool], act: Callable[[Call], object]) -> None:
        self.when, self.act, self.done = when, act, False
        self.models = FakeModels(on_call=self)

    def __call__(self, call: Call) -> None:
        if not self.done and self.when(call):
            self.done = True
            self.act(call)


@pytest.fixture
def baseline(tmp_path: Path) -> Counter[tuple[str, str]]:
    models = FakeModels()
    assert drive(video(tmp_path / "clean"), models).status == "completed"
    return files_made(models)


def third_clip(models: FakeModels) -> Callable[[Call], bool]:
    return lambda call: call.kind == "generate" and drafts(models) == 3


def test_ac36_pause_finishes_the_file_being_made_then_resume_makes_the_rest(
    tmp_path: Path, baseline: Counter[tuple[str, str]]
) -> None:
    project, seen = video(tmp_path / "paused"), {}
    asker = Asker(lambda _: False, lambda _: None)

    def ask(_: Call) -> None:
        seen["state"] = runs_pause.pause(project)

    asker.when, asker.act = third_clip(asker.models), ask
    state = drive(project, asker.models)
    assert seen["state"].status == "running" and seen["state"].pausing == "pause"
    assert state.status == "paused" and drafts(asker.models) == 3  # the third is kept, no fourth begun
    assert {s.name: s.status for s in state.stages}["clips"] == "paused"
    assert '"run_paused"' in project.events_file.read_text()

    assert drive(project, asker.models).status == "completed"
    assert files_made(asker.models) == baseline  # every file once, the same as a run never paused
    assert pause.asked(project) is None  # Resume took the request away


def test_ac37_stop_now_interrupts_the_local_job_and_resume_draws_it_again(
    tmp_path: Path, baseline: Counter[tuple[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    project, interrupted = video(tmp_path / "stopped"), []
    monkeypatch.setattr(pause, "interrupt", lambda: interrupted.append(True))
    asker = Asker(lambda _: False, lambda _: None)

    def stop(_: Call) -> None:
        runs_pause.pause(project, now=True)
        raise RuntimeError("ComfyUI: execution interrupted")  # what the interrupted job gives back

    asker.when, asker.act = third_clip(asker.models), stop
    state = drive(project, asker.models)
    assert interrupted == [True]
    assert state.status == "paused"  # the pause, not the model's error
    third = [c.out for c in asker.models.calls_of("generate") if c.out and c.out.name.startswith("clips-")][2]
    assert third is not None and not third.exists()  # nothing of the interrupted picture is kept

    assert drive(project, asker.models).status == "completed"
    made = files_made(asker.models)
    assert made[(third.parent.parent.name, third.name)] == 2  # asked twice: interrupted, then drawn
    assert set(made) == set(baseline)


def test_ac38_stop_now_stops_waiting_for_a_hosted_call(tmp_path: Path) -> None:
    project, release = video(tmp_path), threading.Event()
    asker = Asker(lambda call: call.kind == "plan", lambda _: None)

    def stop(_: Call) -> None:
        runs_pause.pause(project, now=True)
        release.wait(10)  # the planner's long answer

    asker.act = stop
    began = time.monotonic()
    state = hmv.start(project, asker.models)
    assert state.status == "paused" and time.monotonic() - began < 5  # it did not wait for the answer
    release.set()


def test_ac38_a_pause_during_a_hosted_call_takes_effect_when_it_answers(tmp_path: Path) -> None:
    """Every planner is followed by its gate: the run stops there, and the request does not outlive it."""
    project = video(tmp_path)
    asker = Asker(lambda call: call.kind == "plan", lambda _: runs_pause.pause(project))
    state = hmv.start(project, asker.models)
    assert state.waiting == "review_lyrics"
    assert asker.models.calls[-1].kind == "plan"  # the call answered, and no model call after it
    with pytest.raises(hmv.RunStateError, match="not running"):
        runs_pause.pause(project)
    assert drive(project, asker.models).status == "completed"  # the next resume is not paused by it


def test_ac40_a_pause_request_left_from_before_the_run_does_not_stop_it(tmp_path: Path) -> None:
    project = video(tmp_path)
    pause.request(project, now=False)
    (project.current / pause.PAUSE_FILE).write_text('{"now": false, "at": 1.0}')
    assert drive(project, FakeModels()).status == "completed"
    assert pause.asked(project) is None
