"""Unattended runs (0004, D-075, D-076): a project in "auto" mode approves each gate the moment it is
reached, never over errors; an existing project can be switched to it and back."""

import json
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video import _auto_approve, runs, workflow
from hone_music_video.lyrics_check import check_lyrics
from hone_music_video.testing import FakeModels, make_song
from hone_music_video.testing.frame_answers import shots_answer

GATES = ["review_lyrics", "review_plan", "review_scenes"]  # 0027


def events(project: hmv.Project, *kinds: str) -> list[dict[str, Any]]:
    found = map(json.loads, project.events_file.read_text().splitlines())
    return [e for e in found if e["event"] in kinds]


def solo(root: Path, **kwargs: Any) -> hmv.Project:
    """A project of a 20 s song; every gate is reached."""
    settings = kwargs.pop("settings", {})
    return hmv.create_project(
        root / "projects", "Solo", make_song(root / "song.wav", 20_000), settings=settings, **kwargs
    )


def test_a_project_is_made_asking_unless_told(tmp_path: Path) -> None:
    assert solo(tmp_path).record().approve == "ask"
    assert solo(tmp_path, approve="auto").record().approve == "auto"
    with pytest.raises(hmv.InvalidInput, match="approve"):
        solo(tmp_path, approve="sometimes")  # type: ignore[arg-type]


def test_an_auto_project_runs_to_the_end_with_no_approval(tmp_path: Path) -> None:
    project = solo(tmp_path, approve="auto")
    state = hmv.start(project, FakeModels())
    assert state.status == "completed" and state.waiting is None
    passed = events(project, "gate_auto_approved", "gate_approved")
    assert [(e["event"], e["gate"]) for e in passed] == [("gate_auto_approved", g) for g in GATES]
    assert {s.gate: s.gate_auto for s in state.stages if s.gate} == dict.fromkeys(GATES, True)
    scenes = runs.stage_outputs(project, "review_scenes")["review_scenes"]
    assert scenes.shots is not None  # the scenes as they were when it passed (0027 §5)


def test_an_asking_project_shows_no_gate_as_automatic(project: hmv.Project) -> None:
    state = hmv.start(project, FakeModels())
    assert state.waiting == "review_lyrics"
    assert not any(s.gate_auto for s in state.stages)
    assert events(project, "gate_auto_approved") == []


def test_auto_stops_at_a_gate_whose_check_has_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def one_error(timeline: hmv.Timeline, words: hmv.Words, given: str | None) -> hmv.Report:
        problem = hmv.Problem(rule="overlap", where="L002", message="starts 20 ms before L001 ends")
        return check_lyrics(timeline, words, given).model_copy(update={"errors": [problem]})

    monkeypatch.setattr(workflow, "check_lyrics_of", one_error)
    project = solo(tmp_path, approve="auto")
    state = hmv.start(project, FakeModels())
    assert (state.status, state.waiting) == ("awaiting_review", "review_lyrics")
    (stopped,) = events(project, "auto_stopped")
    assert stopped["gate"] == "review_lyrics" and "1 errors" in stopped["reason"]
    assert events(project, "gate_auto_approved") == []
    assert hmv.resume(project, FakeModels()).waiting == "review_lyrics"
    assert len(events(project, "auto_stopped")) == 1  # not written again at the same gate


def too_long(data: Any) -> dict[str, Any]:
    """One shot longer than the longest: an acceptable error (D-027)."""
    first, second, *rest = shots_answer(data)["shots"]
    return {"shots": [first | {"end_ms": second["end_ms"], "lines": first["lines"] + second["lines"]}, *rest]}


def test_acceptable_shot_errors_are_not_accepted_automatically(tmp_path: Path) -> None:
    project = solo(tmp_path, approve="auto", settings={"max_shot_ms": 6000})
    state = hmv.start(project, FakeModels(answers={"ShotList": too_long}))
    assert state.waiting == "review_plan"
    assert [e["gate"] for e in events(project, "gate_auto_approved")] == GATES[:1]
    assert [e["gate"] for e in events(project, "auto_stopped")] == ["review_plan"]


def test_a_waiting_project_switched_to_auto_continues(tmp_path: Path) -> None:
    project, models = solo(tmp_path), FakeModels()
    assert hmv.start(project, models).waiting == "review_lyrics"
    hmv.set_approve_mode(project, "auto")
    assert project.record().approve == "auto"
    state = hmv.resume(project, models)
    assert state.status == "completed"
    assert [e["gate"] for e in events(project, "gate_auto_approved")] == GATES


def test_switching_back_to_ask_stops_at_the_next_gate(tmp_path: Path) -> None:
    project, models = solo(tmp_path, approve="auto"), FakeModels()
    hmv.set_approve_mode(project, "ask")
    assert hmv.start(project, models).waiting == "review_lyrics"
    with pytest.raises(hmv.InvalidInput, match="ask or auto"):
        hmv.set_approve_mode(project, "never")  # type: ignore[arg-type]


def test_only_auto_is_written_so_asking_projects_stay_readable(tmp_path: Path) -> None:
    """`project.json` holds `approve` only for "auto": a project that asks is what a version from before
    0004 wrote, and one without the key reads as asking (D-075)."""
    project = solo(tmp_path)
    assert "approve" not in json.loads((project.root / "project.json").read_text())
    assert project.record().approve == "ask"
    hmv.set_approve_mode(project, "auto")
    assert json.loads((project.root / "project.json").read_text())["approve"] == "auto"
    hmv.set_approve_mode(project, "ask")
    assert "approve" not in json.loads((project.root / "project.json").read_text())


def test_a_gate_the_owner_approved_first_is_left_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The owner approves the gate between the run stopping and the unattended approval: hone-flow
    refuses the second decision, the run stops quietly and the owner's approval stands."""
    project = solo(tmp_path, approve="auto")
    first = _auto_approve.stop_reason

    def owner_first(run: Any, gate: str) -> str | None:
        if gate == "review_lyrics":
            hmv.approve(project, gate)
        return first(run, gate)

    monkeypatch.setattr(_auto_approve, "stop_reason", owner_first)
    state = hmv.start(project, FakeModels())
    assert state.waiting is None and state.status != "running"
    assert [e["gate"] for e in events(project, "gate_approved")] == ["review_lyrics"]
    assert events(project, "gate_auto_approved") == []
    monkeypatch.setattr(_auto_approve, "stop_reason", first)
    assert hmv.resume(project, FakeModels()).status == "completed"
