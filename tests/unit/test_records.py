"""The records of design §4: the examples of §4.1 and §4.3 and the frame's sidecar (0027) validate; times
are integer milliseconds; unknown keys and closed choices are refused."""

import pytest
from pydantic import ValidationError

import hone_music_video as hmv

TIMELINE = {
    "format_version": "1",
    "duration_ms": 214380,
    "language": "en",
    "sections": [{"id": "verse-1", "kind": "verse", "start_ms": 12040, "end_ms": 41210, "notes": ""}],
    "lines": [
        {
            "id": "L001",
            "section": "verse-1",
            "text": "She waits upon the balcony",
            "start_ms": 12040,
            "end_ms": 15385,
            "words": [{"text": "She", "start_ms": 12040, "end_ms": 12310}],
            "heard_first": 0,
            "heard_last": 4,
        }
    ],
    "instrumental": [{"start_ms": 0, "end_ms": 12040, "kind": "intro", "notes": "[Intro: soft piano]"}],
    "owner_timed": [],
}
SHOTS = {
    "format_version": "1",
    "shots": [
        {
            "id": "S001",
            "start_ms": 0,
            "end_ms": 6210,
            "lines": [],
            "beat": "establishing: the palace at dusk before the first line",
            "framing": "wide",
            "faces": False,
            "cast": ["celina"],
            "location": "palace balcony",
            "camera": "slow push-in",
            "still_prompt": "A still from an epic film. The queen from image 1 stands at the balustrade.",
            "motion_prompt": "Slow push-in. Her veil lifts in the wind; torch flames flicker; mist drifts.",
            "clip_seed": 0,
        }
    ],
}
SCENE_SHOTS = {
    "format_version": "1",
    "shots": [
        {
            "scene": "S001",
            "start_ms": 0,
            "end_ms": 6210,
            "lines": [],
            "beat": "the palace at dusk",
            "framing": "wide",
            "faces": False,
            "cast": ["celina"],
            "location": "palace",
            "camera": "slow push-in",
            "motion_prompt": "Slow push-in. Mist drifts.",
            "clip_seed": 0,
            "feel": "the calm before the loss",
            "evidence": "the palace small under a huge sky, nothing moves but the mist",
        }
    ],
}


@pytest.mark.parametrize(
    ("model", "example"), [(hmv.Timeline, TIMELINE), (hmv.Shots, SHOTS), (hmv.SceneShots, SCENE_SHOTS)]
)
def test_the_design_examples_round_trip(model: type[hmv.Timeline], example: dict[str, object]) -> None:
    assert model.model_validate(example).model_dump(mode="json") == example


@pytest.mark.parametrize("bad", [1.5, -1, "100"])
def test_times_are_integer_milliseconds(bad: object) -> None:
    shot = SHOTS["shots"][0]  # type: ignore[index]
    with pytest.raises(ValidationError):
        hmv.Shots.model_validate({"shots": [shot | {"start_ms": bad}]})


def test_closed_choices_and_unknown_keys() -> None:
    shot = SHOTS["shots"][0]  # type: ignore[index]
    with pytest.raises(ValidationError):
        hmv.Shots.model_validate({"shots": [shot | {"framing": "two-shot"}]})
    with pytest.raises(ValidationError):
        hmv.Shots.model_validate(SHOTS | {"format_version": "2"})
    with pytest.raises(ValidationError):
        hmv.Shots.model_validate(SHOTS | {"comment": "no"})
    with pytest.raises(ValidationError):
        hmv.SceneShots.model_validate({"shots": [SCENE_SHOTS["shots"][0] | {"refs": []}]})  # type: ignore[index]


def test_a_shot_without_a_clip_seed_reads_zero() -> None:
    shot = {k: v for k, v in SHOTS["shots"][0].items() if k != "clip_seed"}  # type: ignore[union-attr]
    assert hmv.Shots.model_validate({"shots": [shot]}).shots[0].clip_seed == 0
