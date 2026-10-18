"""The run of a project: start, the three gates, approve, resume, status, failures (design §3.1)."""

from collections.abc import Callable, Mapping
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video import frame_stages
from hone_music_video.testing import FakeModels
from hone_music_video.testing.answers import lyrics_answer
from tests.conftest import drive, settle_scenes


def test_a_new_project_has_not_started(project: hmv.Project) -> None:
    state = hmv.status(project)
    assert state.status == "not_started" and state.run_id is None and state.waiting is None
    assert [s.name for s in state.stages] == list(hmv.STAGES)
    assert [s.gate for s in state.stages if s.gate] == list(hmv.GATES.values())


def test_the_run_stops_at_each_gate_in_order(project: hmv.Project) -> None:
    models = FakeModels()
    state = hmv.start(project, models)
    seen: list[str] = []
    while state.waiting:
        seen.append(state.waiting)
        reviewed = {s.name: s.status for s in state.stages}
        assert "awaiting_review" in reviewed.values()
        if state.waiting == "review_scenes":
            settle_scenes(project, models)
        assert hmv.approve(project) == state.waiting
        state = hmv.resume(project, models)
    assert seen == ["review_lyrics", "review_plan", "review_scenes"]
    assert state.status == "completed"
    assert all(s.status == "done" for s in state.stages)
    shots = len(frame_stages.read_shots(project).shots)
    assert {s.shots_total for s in state.stages if s.name in ("clips", "finish")} == {shots}


def test_every_stage_writes_its_records(project: hmv.Project) -> None:
    drive(project, FakeModels())
    current = project.current
    for name in ("timeline.json", "edl.json", "video.mp4"):
        assert (current / name).is_file(), name
    assert (project.root / "frame" / "shots.json").is_file()
    for shot in frame_stages.read_shots(project).shots:
        for name in ("still.png", "clip-raw.mp4", "clip.mp4"):
            assert (current / "shots" / shot.scene / name).is_file()


def test_planner_calls_are_small_calls(project: hmv.Project) -> None:
    models = FakeModels()
    drive(project, models)
    schemas = [c.schema for c in models.calls_of("plan")]
    assert schemas[:4] == ["LyricsEdit", "Bible", "ShotList", "ShotReview"]  # the review reads the list
    assert set(schemas[4:]) == {"ItemPrompts", "ScenePrompts"}  # one per subject, one per six shots
    review = models.calls_of("plan")[3]
    assert review.model == "claude-haiku-5-5"  # a check, not a planner (0028)


def test_wrong_states_say_what_to_do(project: hmv.Project) -> None:
    with pytest.raises(hmv.RunStateError, match="start it"):
        hmv.approve(project)
    with pytest.raises(hmv.RunStateError, match="start it"):
        hmv.resume(project, FakeModels())
    hmv.start(project, FakeModels())
    with pytest.raises(hmv.RunStateError, match="resume it"):
        hmv.start(project, FakeModels())
    with pytest.raises(hmv.RunStateError, match="waiting: review_lyrics"):
        hmv.approve(project, "review_plan")
    with pytest.raises(hmv.NotFound, match="no gate 'lunch'"):
        hmv.approve(project, "lunch")


def test_a_failed_stage_shows_its_error_and_resumes(project: hmv.Project) -> None:
    def broken(_data: Mapping[str, Any]) -> Mapping[str, Any]:
        raise hmv.ModelFailure("the planner is down")

    state = hmv.start(project, FakeModels(answers={"LyricsEdit": broken}))
    assert state.status == "failed"
    lyrics = next(s for s in state.stages if s.name == "lyrics")
    assert lyrics.status == "failed" and "the planner is down" in (lyrics.error or "")
    assert drive(project, FakeModels()).status == "completed"


def test_a_failed_stage_being_made_again_shows_running(project: hmv.Project) -> None:
    """hone-flow keeps a failed step's record until its next attempt ends; while a resume makes it again
    the stage shows `running`, not `failed` (the dashboard showed every new clip as failed)."""

    def broken(_data: Mapping[str, Any]) -> Mapping[str, Any]:
        raise hmv.ModelFailure("the planner is down")

    seen: list[tuple[str, str | None, str | None]] = []

    def watched(data: Mapping[str, Any]) -> Mapping[str, Any]:
        lyrics = next(s for s in hmv.status(project).stages if s.name == "lyrics")
        seen.append((lyrics.status, lyrics.error, lyrics.started_at))
        return lyrics_answer(data)

    assert hmv.start(project, FakeModels(answers={"LyricsEdit": broken})).status == "failed"
    hmv.resume(project, FakeModels(answers={"LyricsEdit": watched}))
    assert seen == [("running", None, None)]  # not the failed attempt's error or start (review)


def test_a_stage_that_fails_again_on_resume_shows_its_new_error(project: hmv.Project) -> None:
    """D-083 applies only while the run is live: once the resumed attempt fails, the stage reads failed."""

    def broken(note: str) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
        def answer(_data: Mapping[str, Any]) -> Mapping[str, Any]:
            raise hmv.ModelFailure(note)

        return answer

    hmv.start(project, FakeModels(answers={"LyricsEdit": broken("down")}))
    state = hmv.resume(project, FakeModels(answers={"LyricsEdit": broken("still down")}))
    lyrics = next(s for s in state.stages if s.name == "lyrics")
    assert state.status == "failed" and lyrics.status == "failed" and "still down" in (lyrics.error or "")
