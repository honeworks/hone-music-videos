"""AC-74, AC-75, AC-77 and AC-78 (change 0034): scene references designed for an edit model. The place is
image 1, a wide shot without faces too; every setup opens on a master; size words are sent back and a
subject prompt is repaired twice."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video import frame_stages
from hone_music_video.testing import FakeModels, make_song
from hone_music_video.testing.frame_answers import FRAME_ANSWERS, bible_answer, shots_answer
from tests.conftest import LYRICS

pytestmark = pytest.mark.e2e


@pytest.fixture
def project(tmp_path: Path) -> hmv.Project:
    return hmv.create_project(
        tmp_path / "projects", "Walk", make_song(tmp_path / "song.wav", 40_000), hmv.Material(lyrics=LYRICS)
    )


def to_plan(project: hmv.Project, models: FakeModels) -> dict[str, Any]:
    state = hmv.start(project, models)
    while state.waiting != "review_plan":
        assert state.waiting is not None, state
        hmv.approve(project)
        state = hmv.resume(project, models)
    ws = frame_stages.workspace(project, FakeModels())
    return tomllib.loads(frame_stages.frame_project(ws).text())


def scene_data(models: FakeModels) -> dict[str, dict[str, Any]]:
    return {
        s["id"]: s for c in models.calls_of("plan") if c.schema == "ScenePrompts" for s in c.data["shots"]
    }


def test_ac74_the_place_is_image_1(project: hmv.Project) -> None:
    models = FakeModels()
    plan = to_plan(project, models)
    face = plan["scenes"]["S001"]  # a medium face shot: the street, then the woman's close-up
    assert face["refs"] == ["street.wide", "singer.close"]
    sent = scene_data(models)["S001"]["refs"]
    assert [(r["image"], r["id"]) for r in sent] == [(1, "street.wide"), (2, "singer.close")]


def test_ac75_a_wide_shot_without_faces_keeps_its_character_pictures(project: hmv.Project) -> None:
    models = FakeModels()
    plan = to_plan(project, models)
    wide = plan["scenes"]["S002"]  # wide, faces false: the street at night, then the woman, then the lamp
    assert wide["refs"] == ["street.night", "singer.back", "lamp.hero"]
    words = scene_data(models)["S002"]["in_words"]
    assert not [w for w in words if w["what"].startswith("Mara")]


def test_ac77_every_setup_opens_on_a_master(project: hmv.Project) -> None:
    def close_master(data: Mapping[str, Any]) -> dict[str, Any]:
        answer = shots_answer(data)
        answer["setups"] = [{"id": "doorway", "layout": "she stands at the door, the lamp on her left"}]
        answer["shots"][0] |= {"setup": "doorway", "framing": "close-up"}
        return answer

    models = FakeModels(answers=FRAME_ANSWERS | {"ShotList": close_master})
    to_plan(project, models)
    asked = [c.data for c in models.calls_of("plan") if c.schema == "ShotList"]
    assert any("master" in p["message"] for p in asked[1]["problems"])


def test_ac78_size_words_are_sent_back_and_subjects_repaired_twice(project: hmv.Project) -> None:
    def sized(data: Mapping[str, Any]) -> dict[str, Any]:
        answer = bible_answer(data)
        answer["demo"] = [f"{answer['kind']} In a 16:9 frame, a woman. {answer['finish']}"] * 3
        return answer

    def too_long(data: Mapping[str, Any]) -> dict[str, Any]:
        return {"items": [{"id": i["id"], "prompt": "x" * 1600} for i in data["items"]]}

    models = FakeModels(answers=FRAME_ANSWERS | {"Bible": sized, "ItemPrompts": too_long})
    to_plan(project, models)
    bibles = [c.data for c in models.calls_of("plan") if c.schema == "Bible"]
    assert any("16:9" in p["message"] for p in bibles[1]["problems"])
    lamp = [
        c for c in models.calls_of("plan") if c.schema == "ItemPrompts" and c.data["subject"]["id"] == "lamp"
    ]
    assert len(lamp) == 3  # the call and two repairs
