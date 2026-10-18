"""The lyrics gate (D-015): timed lyrics with errors cannot be approved; `reject` runs the lyrics stage
again with the owner's note, which reaches the lyrics editor; every other refusal says why."""

import json
from collections.abc import Mapping
from typing import Any

import hone_flow as fk
import pytest

import hone_music_video as hmv
from hone_music_video import runs, workflow
from hone_music_video.cli import main
from hone_music_video.lyrics_check import check_lyrics
from hone_music_video.testing import FakeModels
from tests.conftest import drive


def events(project: hmv.Project, kind: str) -> list[dict[str, Any]]:
    found = map(json.loads, project.events_file.read_text().splitlines())
    return [e for e in found if e["event"] == kind]


@pytest.fixture
def one_error(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """`check_lyrics` reports one error the first time only (the code never builds such a timeline)."""
    calls: list[int] = []

    def checked(timeline: hmv.Timeline, words: hmv.Words, given: str | None) -> hmv.Report:
        calls.append(1)
        report = check_lyrics(timeline, words, given)
        problem = hmv.Problem(rule="overlap", where="L002", message="starts 20 ms before L001 ends")
        return report.model_copy(update={"errors": [problem]}) if len(calls) == 1 else report

    monkeypatch.setattr(workflow, "check_lyrics_of", checked)
    return calls


def test_errors_block_the_gate_until_the_lyrics_run_again_with_a_note(
    project: hmv.Project, one_error: list[int], capsys: pytest.CaptureFixture[str]
) -> None:
    def editor(data: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "sections": [{"id": "v", "kind": "verse"}],
            "lines": [{"section": "v", "text": "x", "heard_first": 0, "heard_last": 1}],
        }

    models = FakeModels(answers={"LyricsEdit": editor})
    state = hmv.start(project, models)
    assert state.waiting == "review_lyrics", [s.error for s in state.stages if s.error]
    with pytest.raises(hmv.RunStateError, match="the timed lyrics have 1 errors"):
        hmv.approve(project)
    assert main(["approve", str(project.root)]) == 1
    assert "1 errors (check_lyrics)" in capsys.readouterr().err
    with pytest.raises(SystemExit):  # --note is required
        main(["reject", str(project.root)])
    with pytest.raises(hmv.InvalidInput, match="say what should change"):
        hmv.reject(project, note="  ")

    assert main(["reject", str(project.root), "--note", "sing the first two words as one line"]) == 0
    assert hmv.resume(project, models).waiting == "review_lyrics"
    first, second = models.calls_of("plan")
    assert "review_note" not in first.data
    assert second.data["review_note"] == "sing the first two words as one line"
    assert second.data["previous_lines"] == [{"id": "L001", "section": "v", "text": "x", "heard": [0, 1]}]
    assert len(one_error) == 2
    assert hmv.approve(project, note="good now") == "review_lyrics"
    assert [e["note"] for e in events(project, "gate_rejected")] == ["sing the first two words as one line"]
    assert [e["note"] for e in events(project, "gate_approved")] == ["good now"]


def test_the_owners_timing_clears_a_blocking_check(
    project: hmv.Project, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The lyrics stage's check blocks the gate; once the owner times the line it is about, `approve`
    goes by the check of the edited timeline (0018, D-115)."""

    def blocked(timeline: hmv.Timeline, words: hmv.Words, given: str | None) -> hmv.Report:
        problem = hmv.Problem(rule="moved", where="L002", message="its start is 400 ms from its word")
        return check_lyrics(timeline, words, given).model_copy(update={"errors": [problem]})

    monkeypatch.setattr(workflow, "check_lyrics_of", blocked)
    hmv.start(project, FakeModels())
    with pytest.raises(hmv.RunStateError, match="the timed lyrics have 1 errors"):
        hmv.approve(project)
    assert main(["lyrics-timing", str(project.root), "L002=8400-13750"]) == 0
    assert "0 errors" in capsys.readouterr().out
    assert hmv.approve(project) == "review_lyrics"
    approved: hmv.Timeline = runs.stage_outputs(project, "review_lyrics")["review_lyrics"]
    assert approved.owner_timed == ["L002"] and approved.lines[1].start_ms == 8400


def test_only_gates_whose_stage_reads_the_note_can_be_rejected(project: hmv.Project) -> None:
    with pytest.raises(hmv.RunStateError, match="has no run yet"):
        hmv.reject(project, note="again")
    models = FakeModels()
    hmv.start(project, models)
    with pytest.raises(hmv.RunStateError, match="review_plan is not waiting"):
        hmv.reject(project, "review_plan", note="again")
    with pytest.raises(hmv.NotFound, match="no gate 'lunch'"):
        hmv.reject(project, "lunch", note="again")
    hmv.approve(project)
    assert hmv.resume(project, models).waiting == "review_plan"
    assert hmv.reject(project, note="Darvin rides a black horse") == "review_plan"  # the planner reads it
    assert hmv.resume(project, models).waiting == "review_plan"
    noted = [
        c.schema for c in models.calls_of("plan") if c.data.get("review_note") == "Darvin rides a black horse"
    ]
    assert noted[:2] == ["Bible", "ShotList"]  # the bible and the shot list read the owner's note
    hmv.approve(project)
    assert hmv.resume(project, models).waiting == "review_scenes"
    with pytest.raises(hmv.RunStateError, match="review_scenes cannot be run again with a note"):
        hmv.reject(project, note="again")
    assert drive(project, models).status == "completed"


def test_a_locked_run_refuses_the_rejection(project: hmv.Project, monkeypatch: pytest.MonkeyPatch) -> None:
    hmv.start(project, FakeModels())

    def locked(*_args: object, **_kwargs: object) -> None:
        raise fk.RunLocked("held by another process")

    monkeypatch.setattr(fk.Run, "reject", locked)
    with pytest.raises(hmv.RunStateError, match="running in another process"):
        hmv.reject(project, note="again")
