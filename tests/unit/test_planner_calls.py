"""A planner call is kept with what was sent and the problems the code found in its reply (0030 §2)."""

import json
from collections.abc import Mapping
from typing import Any

import hone_music_video as hmv
from hone_music_video._jobs import Job
from hone_music_video.events import EventLog
from hone_music_video.frame_calls import Planner
from hone_music_video.records import Problem
from hone_music_video.records_frame import ShotReview
from hone_music_video.testing import FakeModels


def test_a_call_and_its_repair_keep_the_request_and_the_problems(project: hmv.Project) -> None:
    replies = iter([{"notes": []}, {"notes": [{"where": "S001", "problem": "p"}]}])

    def review(_data: Mapping[str, Any]) -> dict[str, Any]:
        return next(replies)

    job = Job(
        project, FakeModels(answers={"ShotReview": review}), project.settings, EventLog(project.events_file)
    )
    planner = Planner(job, "planner", project.root / "frame" / "calls")

    def check(reply: ShotReview) -> list[Problem]:
        return [] if reply.notes else [Problem(rule="r", where="S001", message="write a note")]

    reply, problems = planner.call("review", "# Role\nrules", {"a": 1}, ShotReview, check=check)
    assert reply.notes and problems == []
    first, repair = (json.loads(p.read_text()) for p in sorted(planner.folder.glob("review-*.json")))
    if first["label"] != "review":
        first, repair = repair, first
    assert first["problems"] == [{"where": "S001", "message": "write a note"}] and repair["problems"] == []
    assert first["request"]["data"] == {"a": 1} and first["request"]["schema"] == "ShotReview"
    assert repair["request"]["data"]["problems"] == [{"where": "S001", "message": "write a note"}]
    system = planner.folder / first["request"]["system"]
    assert system.read_text() == "# Role\nrules" and first["at"]
    assert len(list(planner.folder.glob("system-*.md"))) == 1  # kept once
