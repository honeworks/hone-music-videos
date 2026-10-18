"""A project's progress read from its run (0003): the units, versions and current unit of the clip stages
from the progress log (D-050), and the folders for a run from before those events (D-053). The scenes'
progress is the frame run's own (its estimates, 0027)."""

import shutil
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video import _run_progress, runs
from hone_music_video._run_progress import project_progress
from hone_music_video.events import EventLog
from hone_music_video.testing import Call, FakeModels
from tests.conftest import new_project, settle_scenes

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
NOW = 4_000_000_000_000  # a fixed clock, in ms


@pytest.fixture
def project(tmp_path: Path) -> hmv.Project:
    return new_project(tmp_path)


def to_clips(project: hmv.Project, models: FakeModels) -> None:
    """Run to the scenes, settle and approve them; the next resume makes the clips."""
    state = hmv.start(project, models)
    while state.waiting != "review_scenes":
        hmv.approve(project)
        state = hmv.resume(project, models)
    settle_scenes(project, models)
    hmv.approve(project)


def test_the_clips_stage_counts_its_clips_as_they_are_made(project: hmv.Project) -> None:
    to_clips(project, FakeModels())
    seen: list[dict[str, Any]] = []

    def note(call: Call) -> None:
        if call.kind == "generate" and call.out is not None and call.out.name.startswith("clips-"):
            seen.append(project_progress(project, runs.status(project), NOW)["stages"]["clips"])

    hmv.resume(project, FakeModels(on_call=note))
    shots = len(seen)
    assert shots >= 2
    assert [(s["done"], s["total"]) for s in seen] == [(n, shots) for n in range(shots)]
    assert seen[0]["current"]["kind"] == "raw_clip" and seen[0]["current"]["subject"] == "S001"


def test_a_resumed_clips_stage_counts_what_was_made_before(project: hmv.Project) -> None:
    to_clips(project, FakeModels())
    calls: list[str] = []

    def fail_second(call: Call) -> None:
        if call.kind == "generate" and call.out is not None and call.out.name.startswith("clips-"):
            calls.append(call.out.name)
            if len(calls) == 2:
                raise hmv.ModelFailure("out of memory")

    hmv.resume(project, FakeModels(on_call=fail_second))
    hmv.resume(project, FakeModels())
    counts = [
        e for e in EventLog(project.events_file).read()[0] if e["event"] == "units" and e["stage"] == "clips"
    ]
    assert counts[0]["made"] == {"raw_clip": 0}
    assert counts[1]["made"] == {"raw_clip": 1}


def test_a_run_from_before_the_progress_events_is_counted_from_its_folders(project: hmv.Project) -> None:
    to_clips(project, FakeModels())
    hmv.resume(project, FakeModels())
    shots = _run_progress._shots(project)  # pyright: ignore[reportPrivateUsage]
    assert shots is not None
    work = _run_progress._work(project, "clips", [], shots, "done")  # pyright: ignore[reportPrivateUsage]
    assert work.source == "files" and work.made == {"raw_clip": len(shots.shots)}
