"""The prompt guideline for the still models (0029): scene replies write their facts first and the code
checks the prompt against them; the shot list is planned around the six limits no prompt fixes (rules in
the prompts, warnings from the beat's words, the warnings read by the review); an extreme camera or a
creature fight gets no place picture, only its words; a creature's size is drawn in its reference."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.frame_items import scene_refs
from hone_music_video.frame_prompts import Context, _shot_data, scene_problems, scene_warnings
from hone_music_video.records_frame import Bible, CastUse, FrameShot, PlaceUse, ScenePrompt
from hone_music_video.shots_check import model_limits
from hone_music_video.stages_plan import system_prompt
from hone_music_video.testing import FakeModels
from hone_music_video.testing.frame_answers import shots_answer
from tests.conftest import drive

LIMITS, SHOTS, SCENES, ASSETS, BIBLE, REVIEW = (
    " ".join(system_prompt(n).split())
    for n in ("limits", "frame_shots", "frame_scenes", "frame_assets", "frame_bible", "frame_review")
)
KIND = "A frame from a film."


def bible() -> Bible:
    return Bible.model_validate(
        {
            "story": "s", "kind": KIND, "finish": "Grain.", "world": "w", "reference_light": "l",
            "demo": ["a", "b", "c"],
            "characters": [
                {"id": "ember", "name": "Ember", "kind": "animal", "noun": "the horse", "look": "a horse"},
                {"id": "dragon", "name": "Dragon", "kind": "creature", "noun": "the dragon", "look": "huge"},
            ],
            "places": [{"id": "pass", "name": "the mountain pass", "look": "a narrow pass of grey rock",
                        "light": "low sun from the left", "states": [{"id": "dusk", "look": "red sky"}]}],
        }
    )  # fmt: skip


def shot(**more: Any) -> FrameShot:
    fields: dict[str, Any] = {
        "id": "S001", "start_ms": 0, "end_ms": 3000, "beat": "b", "framing": "wide", "faces": False,
        "camera": "static camera", "light": "l",
        "cast": [CastUse(character="ember", view="side"), CastUse(character="dragon", view="side")],
        "place": PlaceUse(place="pass", state="dusk"),
    }  # fmt: skip
    return FrameShot(**fields | more)


FACTS = {
    "things": [{"what": "horse", "count": 1, "image": 1}, {"what": "dragon", "count": 1, "image": 2}],
    "links": [{"sentence": "The horse's hooves strike the dragon's neck.",
               "ends": ["the horse's hooves", "the dragon's neck"]}],
    "visible": ["both hooves and the neck they strike"],
    "moment": "the hooves an inch from the scales",
}  # fmt: skip
PROMPT = (
    f"{KIND} The horse from image 1 rears above the dragon from image 2 in the pass from image 3; "
    "the horse's hooves strike the dragon's neck. Wide shot, 35mm lens. Low sun from the left. Grain."
)


def scene(prompt: str = PROMPT, **facts: Any) -> ScenePrompt:
    reply = {"id": "S001", "prompts": [prompt], "motion_prompt": "Static camera.", "facts": FACTS | facts}
    return ScenePrompt.model_validate(reply)


# ------------------------------------------------------------------------------ §1 facts first


def test_the_scene_call_writes_the_facts_before_the_prompt() -> None:
    assert (
        "fill `facts` before you write its prompt" in SCENES and "`things`" in SCENES and "`links`" in SCENES
    )
    assert "`visible`" in SCENES and "`moment`" in SCENES
    assert "only as the left or right of the picture" in SCENES
    assert "inside the frame and lit" in SCENES and "never a size word" in SCENES


def test_a_scene_with_its_facts_and_both_ends_of_each_link_passes() -> None:
    assert scene_problems(bible(), shot(), scene()) == []


def test_a_scene_without_facts_is_sent_back() -> None:
    bare = scene().model_copy(update={"facts": None})
    assert [p.message for p in scene_problems(bible(), shot(), bare)] == [
        "has no `facts`: write the things, links, visible and moment first, then the prompt from them"
    ]


def test_a_link_whose_end_the_prompt_does_not_name_is_sent_back() -> None:
    prompt = PROMPT.replace("the horse's hooves strike the dragon's neck", "the horse strikes")
    found = [p.message for p in scene_problems(bible(), shot(), scene(prompt))]
    assert found == [
        "the link \"The horse's hooves strike the dragon's neck.\" has ends the prompt does not name: "
        '"the horse\'s hooves", "the dragon\'s neck"; name both ends in the prompt as the link does'
    ]


def test_ends_are_matched_without_their_article_or_case() -> None:
    links = [{"sentence": "s", "ends": ["The Horse", "a dragon"]}]
    assert scene_problems(bible(), shot(), scene(links=links)) == []


def test_more_than_three_of_a_kind_is_a_warning_not_a_repair() -> None:
    wolves = [{"what": "grey wolves", "count": 5, "image": 0}]
    assert scene_problems(bible(), shot(), scene(things=wolves)) == []
    found = scene_warnings(scene(things=wolves))
    assert [(p.rule, p.where, p.message) for p in found] == [
        ("model-limit", "S001", "counts 5 'grey wolves': more than three of a kind are seldom drawn exactly")
    ]
    assert scene_warnings(scene()) == []


# ------------------------------------------------------------------------------ §2 the six limits


def test_the_shot_list_is_planned_around_the_six_limits() -> None:
    for words in ("A body's own side", "A grip or a bite between two bodies", "More than three of a kind",
                  "A tear, a cut or a swollen eye", "Eyes meeting", "A movement state"):  # fmt: skip
        assert words in LIMITS, words
    assert "the moment just before or after" in LIMITS
    assert "The models' limits" in REVIEW and "`code_found`" in REVIEW


@pytest.mark.parametrize(
    ("beat", "framing", "rule_words"),
    [
        ("He grips the sword in his LEFT hand.", "medium", "'LEFT hand'"),
        ("Seven candles burn on the table.", "wide", "'Seven candles'"),
        ("12 guests sit at the feast.", "wide", "'12 guests'"),
    ],
)
def test_the_beats_words_warn_of_a_limit(beat: str, framing: str, rule_words: str) -> None:
    found = model_limits("S003", beat, framing)
    assert len(found) == 1 and found[0].rule == "model-limit" and rule_words in found[0].message


@pytest.mark.parametrize(
    ("beat", "framing"),
    [
        ("Her left hand rests on the snake's scales.", "close-up"),  # the close-up is the fix
        ("Three wolves circle the moose.", "wide"),
        ("He stands on the left side of the road.", "wide"),
        ("Hundreds of bees rise from the hive.", "wide"),
    ],
)
def test_what_the_models_can_draw_does_not_warn(beat: str, framing: str) -> None:
    assert model_limits("S003", beat, framing) == []


def test_the_limits_found_in_the_beats_go_to_the_review(project: hmv.Project) -> None:
    reviewed: list[dict[str, Any]] = []

    def shots(data: Mapping[str, Any]) -> dict[str, Any]:
        answer = shots_answer(data)
        answer["shots"][1]["beat"] = "She holds the lamp in her RIGHT hand, five moths around it."
        return answer

    def review(data: Mapping[str, Any]) -> dict[str, Any]:
        reviewed.append(dict(data))
        return {"notes": []}

    drive(project, FakeModels(answers={"ShotReview": review, "ShotList": shots}))
    found = reviewed[0]["code_found"]
    assert [f["where"] for f in found] == ["S002", "S002"]
    assert "'RIGHT hand'" in found[0]["message"] and "'five moths'" in found[1]["message"]


# ------------------------------------------------------------------------------ §3 the place in words


def test_an_extreme_camera_or_a_creature_fight_gets_the_place_in_words() -> None:
    plain, in_words = shot(), shot(place_in_words=True)
    assert scene_refs(bible(), plain) == ["ember.hero", "dragon.hero", "pass.dusk"]
    assert scene_refs(bible(), in_words) == ["ember.hero", "dragon.hero"]
    data = _shot_data(bible(), [in_words], 0, Context(lines={}))
    assert [r["id"] for r in data["refs"]] == ["ember.hero", "dragon.hero"]
    assert data["in_words"] == [
        {"what": "the mountain pass", "look": "a narrow pass of grey rock Low sun from the left. red sky"}
    ]
    assert "`place_in_words`" in SHOTS and "straight down" in SHOTS


# ------------------------------------------------------------------------------ §4 a creature's size


def test_a_creatures_size_is_drawn_in_its_reference() -> None:
    assert "for scale" in ASSETS and "A scene can't change the size its reference shows" in ASSETS
    assert "its size against a person" in BIBLE
