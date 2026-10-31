"""AC-80 to AC-84 (change 0035): simple scenes. Every shot has one of five focuses, checked by code; the
scene and review calls are given it; the instructions name the focuses and not the retired rules."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.stages_plan import system_prompt
from hone_music_video.testing import FakeModels, make_song
from hone_music_video.testing.frame_answers import FRAME_ANSWERS, shots_answer
from tests.conftest import LYRICS
from tests.e2e.test_ac74_scene_references import scene_data, to_plan

pytestmark = pytest.mark.e2e
FOCUSES = ("face", "figure", "pair", "place", "detail")


@pytest.fixture
def project(tmp_path: Path) -> hmv.Project:
    return hmv.create_project(
        tmp_path / "projects", "Walk", make_song(tmp_path / "song.wav", 40_000), hmv.Material(lyrics=LYRICS)
    )


def test_ac80_every_shot_has_a_focus_its_shot_list_keeps(project: hmv.Project) -> None:
    def crowded(data: Mapping[str, Any]) -> dict[str, Any]:
        answer = shots_answer(data)
        answer["shots"][0]["focus"] = "place"  # a place with a character in it
        return answer

    models = FakeModels(answers=FRAME_ANSWERS | {"ShotList": crowded})
    to_plan(project, models)
    asked = [c.data for c in models.calls_of("plan") if c.schema == "ShotList"]
    assert any("is a place with 1 characters" in p["message"] for p in asked[1]["problems"])


def test_ac82_the_scene_and_review_calls_are_given_the_focus(project: hmv.Project) -> None:
    models = FakeModels()
    to_plan(project, models)
    scenes = scene_data(models)
    assert {s["focus"] for s in scenes.values()} == {"face", "figure"}
    face = next(s for s in scenes.values() if s["focus"] == "face")
    assert [r["id"] for r in face["refs"]][1] == "singer.close"  # the focus gave it the close-up (AC-81)
    review = next(c.data for c in models.calls_of("plan") if c.schema == "ShotReview")
    assert all(s["focus"] in FOCUSES for s in review["shots"])


def test_ac84_the_instructions_name_the_focuses_not_the_retired_rules() -> None:
    shots, review, scenes = (system_prompt(n) for n in ("frame_shots", "frame_review", "frame_scenes"))
    for text in (shots, review, scenes):
        assert all(f"`{f}`" in text for f in FOCUSES)
    for retired in ("`place_in_words`", "Mark every hard moment", '`"prompts"`', "at most three"):
        assert retired not in shots
