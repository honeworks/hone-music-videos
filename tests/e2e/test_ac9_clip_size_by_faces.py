"""AC-9: clips use the larger size exactly when `faces` is true and the clip has at most 110 frames
(design §11.1, §14, D-082).

Runs on fake models whose shot plan mixes shots with and without faces; every call to the clip model is
checked for its size (16:9: 832x480, with faces 960x544; the other aspect ratios likewise, D-030) and its
length (one frame more than the shot at 16 fps). Public API only."""

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.testing import FakeModels, make_song
from hone_music_video.testing.frame_answers import shots_answer as planned
from tests.conftest import drive

pytestmark = pytest.mark.e2e

FACES = {"S001": False, "S002": True, "S003": False, "S004": True}
SIZES = {"16:9": ("832x480", "960x544"), "9:16": ("480x832", "544x960")}


def shots_answer(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """The fake planner's tiling (it passes `check_shots`), with faces on S002 and S004."""
    tiled = planned(data)["shots"]
    assert [s["id"] for s in tiled] == list(FACES)
    shots = [
        shot | {"framing": "close-up" if FACES[shot["id"]] else "wide", "faces": FACES[shot["id"]],
                "cast": [], "objects": [], "takes": "one"}
        for shot in tiled
    ]  # fmt: skip
    return {"shots": shots}


@pytest.mark.parametrize("ratio", SIZES)
def test_the_larger_size_exactly_for_faces(tmp_path: Path, ratio: str) -> None:
    song = make_song(tmp_path / "song.wav", 18_000)
    project = hmv.create_project(
        tmp_path / "projects",
        "Faces",
        song,
        settings={"aspect_ratio": ratio, "max_shot_ms": 6000},  # four shots
    )
    models = FakeModels(answers={"ShotList": shots_answer})
    assert drive(project, models).status == "completed"

    clips = [c for c in models.calls_of("generate") if c.model == project.settings.models.clips]
    by_shot = {c.out.parents[1].name: c.inputs for c in clips if c.out}  # current/shots/<id>/versions/
    assert sorted(by_shot) == sorted(FACES)
    small, large = SIZES[ratio]
    for shot, faces in FACES.items():
        assert by_shot[shot]["size"] == (large if faces else small), shot
    frames = {s: round(i["duration_s"] * 16 + 1) for s, i in by_shot.items()}  # as the registry entry does
    shots = hmv.Shots.model_validate_json((project.current / "shots.json").read_bytes()).shots
    expected = {s.id: min(129, max(33, math.ceil((s.end_ms - s.start_ms) * 16 / 1000) + 1)) for s in shots}
    assert frames == expected and len(set(frames.values())) > 1


def long_first_shot(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Two shots of a 12 s song, the cut moved to 7.5 s: S001 a face shot of 121 frames, S002 without."""
    first, second = planned(data)["shots"]
    one = {"cast": [], "objects": [], "takes": "one"}
    return {
        "shots": [
            first | one | {"end_ms": 7500, "faces": True, "framing": "close-up"},
            second | one | {"start_ms": 7500, "faces": False, "framing": "wide"},
        ]
    }


@pytest.mark.parametrize("ratio", SIZES)
def test_a_long_face_clip_is_made_at_the_smaller_size(tmp_path: Path, ratio: str) -> None:
    """D-082: a face shot longer than 110 frames would not fit the 8 GB card at the larger size."""
    song = make_song(tmp_path / "song.wav", 12_000)
    project = hmv.create_project(
        tmp_path / "projects", "Long face", song, settings={"aspect_ratio": ratio, "max_shot_ms": 8000}
    )
    models = FakeModels(answers={"ShotList": long_first_shot})
    assert drive(project, models).status == "completed"

    clips = [c for c in models.calls_of("generate") if c.model == project.settings.models.clips]
    made = {
        c.out.parents[1].name: (round(c.inputs["duration_s"] * 16 + 1), c.inputs["size"])
        for c in clips
        if c.out
    }
    assert made == {"S001": (121, SIZES[ratio][0]), "S002": (73, SIZES[ratio][0])}
