"""AC-11: a run killed during any stage resumes without redoing finished work (design §3.1, §14).

A subprocess runs a project on fake models and is SIGKILLed during one stage; this process resumes it.
Every stage that finished before the kill is not started again, no finished shot or sheet take is made
again, and the model calls of both processes together are those of an uninterrupted run (plus, in a
stage that makes several files, the one in flight when the process died, in a model session opened
again)."""

import json
import signal
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video.testing import FakeModels
from tests.conftest import drive, new_project

pytestmark = pytest.mark.e2e
KILLER = Path(__file__).with_name("killed_run.py")
PER_SHOT = ("clips", "finish")
Calls = Counter[tuple[str, str, str]]


def events(project: hmv.Project) -> list[dict[str, object]]:
    return [json.loads(line) for line in project.events_file.read_text().splitlines()]


def calls_of(models: FakeModels) -> list[tuple[str, str, str]]:
    return [(c.kind, c.model, c.prompt) for c in models.calls]


def clean_run(project: hmv.Project) -> Calls:
    models = FakeModels()
    assert drive(project, models).status == "completed"
    return Counter(calls_of(models))


@pytest.fixture(scope="module")
def clean_calls(tmp_path_factory: pytest.TempPathFactory) -> Calls:
    """The model calls of an uninterrupted run of the same project."""
    return clean_run(new_project(tmp_path_factory.mktemp("clean")))


def kill_and_resume(project: hmv.Project, log: Path, stage: str, mode: str) -> Calls:
    """Kill a run in `stage`, resume it here to the end; the model calls of both processes."""
    command = [sys.executable, str(KILLER), str(project.root), stage, str(log), mode]
    killed = subprocess.run(command, capture_output=True, timeout=60)
    assert killed.returncode == -signal.SIGKILL, killed.stderr.decode()
    assert hmv.status(project).status == "interrupted"
    models = FakeModels()
    assert drive(project, models).status == "completed"
    started = Counter(e["step"] for e in events(project) if e["event"] == "step_started")
    for name in {*hmv.STAGES, stage}:
        assert started[name] == (2 if name == stage else 1), f"{name} started {started[name]} times"
    lines = log.read_text().splitlines() if log.exists() else []
    return Counter(tuple(json.loads(line).values()) for line in lines) + Counter(calls_of(models))


def assert_redone_only_in_flight(together: Calls, clean: Calls, in_flight: str = "") -> None:
    """`in_flight`: "clip" (a clip in flight, in a model session opened again) or "picture" (a frame
    picture in flight, in its model's session too, 0027)."""
    assert clean - together == Counter(), "a call of the clean run is missing"
    extra = sorted(kind for kind, _, _ in (together - clean).elements())
    expected = {"clip": ["generate", "session"], "picture": ["generate", "session"], "": []}[in_flight]
    assert extra == expected, extra


# killed as the step starts: a gate, a planning stage and the assembly; killed in the middle: the stages
# that make a file per shot (the other stages are steps like these, so they resume the same way)
KILLED_IN = ("review_plan", "plan", "scenes", *PER_SHOT, "assemble")


@pytest.mark.parametrize("stage", KILLED_IN)
def test_a_killed_run_resumes_without_redoing_finished_work(
    project: hmv.Project, tmp_path: Path, stage: str, clean_calls: Calls
) -> None:
    mode = "second-call" if stage in (*PER_SHOT, "scenes") else "start"
    together = kill_and_resume(project, tmp_path / "killed-calls.jsonl", stage, mode)
    shots = Counter(e["file"] for e in events(project) if e["event"] == "version_made" and "shot" in e)
    assert set(shots.values()) <= {1}, "a finished file was made again"  # a shot's takes are files
    flight = "clip" if stage in PER_SHOT else "picture" if stage == "scenes" else ""
    assert_redone_only_in_flight(together, clean_calls, flight)


def test_an_assembly_killed_midway_leaves_no_partial_video(
    project: hmv.Project, tmp_path: Path, clean_calls: Calls
) -> None:
    """Killed once the first cut is being written: no `video.mp4` (never a partial one); the resumed
    assembly clears the dead one's work folder and makes the whole video."""
    command = [
        sys.executable,
        str(KILLER),
        str(project.root),
        "assemble",
        str(tmp_path / "calls.jsonl"),
        "first-cut",
    ]
    killed = subprocess.run(command, capture_output=True, timeout=60)
    assert killed.returncode == -signal.SIGKILL, killed.stderr.decode()
    assert not (project.current / "video.mp4").exists()
    assert list(project.root.glob(".assemble-*"))  # the dead assembly's work
    assert drive(project, FakeModels()).status == "completed"
    assert list(project.root.glob(".assemble-*")) == []
    edl = hmv.Assembly.model_validate_json((project.current / "edl.json").read_bytes())
    assert edl.video == "current/video.mp4" and (project.current / "video.mp4").stat().st_size > 0
