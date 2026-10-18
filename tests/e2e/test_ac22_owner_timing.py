"""AC-22: the owner's timing saved at the lyrics gate is checked (order, overlaps, inside the song), kept
as a version, and is the timeline every later stage uses; a line's words move with it (design §6, §14;
0018). Through the public API and the CLI only."""

import json
from collections.abc import Mapping
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.cli import main
from hone_music_video.testing import FakeModels
from hone_music_video.testing.answers import lyrics_answer
from tests.conftest import drive

pytestmark = pytest.mark.e2e


def events(project: hmv.Project, kind: str) -> list[dict[str, Any]]:
    found = map(json.loads, project.events_file.read_text().splitlines())
    return [e for e in found if e["event"] == kind]


def lines_seen(data: Mapping[str, Any]) -> dict[str, tuple[int, int]]:
    return {ln["id"]: (ln["start_ms"], ln["end_ms"]) for ln in data["timeline"]["lines"]}


def test_ac22_the_owners_timing_is_checked_kept_and_used_by_every_later_stage(project: hmv.Project) -> None:
    models = FakeModels()
    assert hmv.start(project, models).waiting == "review_lyrics"  # L001 2000-7750, L002 8000-13750, L003 ...

    bad = {"L002": {"start_ms": 7000, "end_ms": 13600}, "L007": None, "L009": {"start_ms": 1, "end_ms": 2}}
    with pytest.raises(hmv.InvalidInput) as refused:
        hmv.lyrics_timing(project, bad)
    assert refused.value.problems == [
        "L009: there is no line L009 now",
        "L002 starts 750 ms before L001 ends",
    ]
    assert not (project.current / "lyrics").exists()  # a refused save changes nothing
    assert events(project, "lyrics_timed") == []

    hmv.lyrics_timing(project, {"L002": {"start_ms": 8100, "end_ms": 13700}, "L003": None})
    versions = sorted((project.current / "lyrics").glob("timeline-*.json"))
    earlier = versions[0].read_bytes()

    saved = hmv.lyrics_timing(project, {"L002": {"start_ms": 8200, "end_ms": 13600}})
    assert (saved.kept, saved.dropped, saved.report.errors) == (["L002"], {}, [])
    line = saved.timeline.lines[1]
    assert (line.start_ms, line.end_ms) == (8200, 13600)
    assert (line.words[0].start_ms, line.words[-1].end_ms) == (8200, 13600)  # its words moved with it
    record = json.loads((project.current / "lyrics" / "owner-timing.json").read_text())
    assert record["edits"] == {"L002": {"start_ms": 8200, "end_ms": 13600}}
    kept = hmv.Timeline.model_validate_json(project.path(record["timeline"]).read_text())
    assert kept == saved.timeline and kept.owner_timed == ["L002"]
    assert saved.measured == {"L002": [8000, 13750]}  # the times it was made with
    versions = sorted((project.current / "lyrics").glob("timeline-*.json"))
    assert len(versions) == 2 and earlier in [v.read_bytes() for v in versions]  # never overwritten
    hmv.lyrics_timing(project, {"L002": {"start_ms": 8200, "end_ms": 13600}})  # the same again: no new file
    assert len(list((project.current / "lyrics").glob("timeline-*.json"))) == 2
    assert [e["lines"] for e in events(project, "lyrics_timed")] == [["L002"], ["L002"], ["L002"]]

    taken_back = hmv.lyrics_timing(project, {"L003": {"start_ms": 14000, "end_ms": 17000}})
    taken_back = hmv.lyrics_timing(project, {"L003": None})  # takes the edit back
    assert taken_back.kept == ["L002"] and taken_back.timeline.lines[2].end_ms == 17750
    assert taken_back.timeline.owner_timed == ["L002"]

    with pytest.raises(hmv.InvalidInput, match="keeps no note"):  # an edited gate keeps no note
        hmv.approve(project, note="fine")
    assert events(project, "gate_approved") == []

    assert hmv.approve(project) == "review_lyrics"
    assert events(project, "gate_approved")[-1]["timing_kept"] == ["L002"]
    record = json.loads((project.current / "lyrics" / "owner-timing.json").read_text())
    assert record["decided"] is True  # the record of the gate, never applied again
    drive(project, models)
    (shots_call,) = (c for c in models.calls_of("plan") if c.schema == "ShotList")
    assert lines_seen(shots_call.data)["L002"] == (8200, 13600)  # the shot list reads the owner's times
    assert hmv.Timeline.model_validate_json((project.current / "timeline.json").read_text()) == kept


def joined(data: Mapping[str, Any]) -> dict[str, Any]:
    """The lyrics editor; after a note it sings the last two lines as one, so L003 is gone."""
    answer = lyrics_answer(data)
    if data.get("review_note"):
        *first, a, b = answer["lines"]
        answer["lines"] = [*first, a | {"text": f"{a['text']} {b['text']}", "heard_last": b["heard_last"]}]
        answer["instrumental"][-1]["after_line"] = len(answer["lines"])
    return answer


def test_ac22_running_the_lyrics_again_keeps_the_edits_whose_lines_remain(
    project: hmv.Project, capsys: pytest.CaptureFixture[str]
) -> None:
    models = FakeModels(answers={"LyricsEdit": joined})
    hmv.start(project, models)
    assert main(["lyrics-timing", str(project.root), "L001=1900-7750", "L003=14100-17500"]) == 0
    assert main(["lyrics-timing", str(project.root), "L003=-", "L002=99-1"]) == 1  # refused whole
    assert main(["lyrics-timing", str(project.root), "L003"]) == 1
    assert json.loads((project.current / "lyrics" / "owner-timing.json").read_text())["edits"] == {
        "L001": {"start_ms": 1900, "end_ms": 7750},
        "L003": {"start_ms": 14100, "end_ms": 17500},
    }

    hmv.reject(project, note="L002 and L003 are one line")
    assert hmv.resume(project, models).waiting == "review_lyrics"
    sent = models.calls_of("plan")[-1].data["review_note"]
    assert sent.startswith("L002 and L003 are one line")
    assert "times of L001, L003 by hand" in sent and "Change the text only" in sent

    capsys.readouterr()
    assert main(["lyrics-timing", str(project.root), "L002=8100-17750"]) == 0  # a save after the rerun
    assert "dropped  L003: L003: there is no line L003 now" in capsys.readouterr().out
    record = json.loads((project.current / "lyrics" / "owner-timing.json").read_text())
    assert sorted(record["edits"]) == ["L001", "L002"]  # only the edits that still apply

    assert hmv.approve(project) == "review_lyrics"
    approved = events(project, "gate_approved")[-1]
    assert approved["timing_kept"] == ["L001", "L002"]
    assert approved["timing_dropped"] == {}
    drive(project, models)
    timeline = hmv.Timeline.model_validate_json((project.current / "timeline.json").read_text())
    assert [(ln.id, ln.start_ms) for ln in timeline.lines] == [("L001", 1900), ("L002", 8100)]
    assert timeline.owner_timed == ["L001", "L002"]


def test_ac22_edits_that_no_longer_apply_leave_the_gate_as_made(project: hmv.Project) -> None:
    models = FakeModels(answers={"LyricsEdit": joined})
    hmv.start(project, models)
    hmv.lyrics_timing(project, {"L003": {"start_ms": 14100, "end_ms": 17500}})
    hmv.reject(project, note="L002 and L003 are one line")
    hmv.resume(project, models)
    assert hmv.approve(project, note="as heard") == "review_lyrics"  # nothing kept: a plain approval
    approved = events(project, "gate_approved")[-1]
    assert (approved["note"], approved["timing_kept"]) == ("as heard", [])
    assert approved["timing_dropped"] == {"L003": "L003: there is no line L003 now"}
    drive(project, models)
    assert hmv.Timeline.model_validate_json((project.current / "timeline.json").read_text()).owner_timed == []
