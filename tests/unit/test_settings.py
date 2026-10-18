"""Settings (design §2.3) and the model per role (design §3.2); settings stored before 0027 are read
with the scene pipeline's retired keys dropped."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import hone_music_video as hmv
from hone_music_video.settings import RETIRED_0027, stored
from hone_music_video.testing import make_song


def test_defaults_are_the_design_table() -> None:
    settings = hmv.Settings()
    assert settings.style == "photoreal live-action film, 35mm film look, natural film grain"
    assert (settings.aspect_ratio, settings.resolution, settings.fps) == ("16:9", 1080, 32)
    assert (settings.min_shot_ms, settings.max_shot_ms, settings.language) == (2000, 8000, None)
    roles = settings.models
    assert roles.speech == "scribe_v2"  # D-049
    assert {roles.lyrics, roles.planner} == {"claude-opus-5-5"}
    assert roles.frame == ("qwen-image-2.1-turbo",)  # the frame's image models (0027)
    assert (roles.clips, roles.finish) == ("wan2.2-i2v-14b", "esrgan-rife-x2")
    assert roles.vocals == "htdemucs"  # the third listen's Demucs model (D-041)
    assert roles.align == "MMS_FA"  # Meta's MMS forced aligner (0005)
    assert hmv.parse_settings({"models": {"align": None}}).models.align is None  # alignment off
    assert (settings.pace, settings.mood) == ("balanced", "")  # 0009
    several = hmv.parse_settings({"models": {"frame": ["qwen-image-2.1-turbo", "z-image-turbo"]}})
    assert several.models.frame == ("qwen-image-2.1-turbo", "z-image-turbo")


OLD = {"models": {"upscale": "real-esrgan-x2", "interpolation": "rife", "clips": "wan2.2-i2v-14b"}}


def test_the_two_retired_finishing_roles_are_refused_in_new_settings() -> None:
    """Guarantee 13: new settings with `upscale` or `interpolation` say what replaced them (D-032)."""
    with pytest.raises(hmv.InvalidInput) as refused:
        hmv.parse_settings(OLD)
    assert refused.value.problems == [
        "models.upscale: replaced by models.finish in 0.1 (D-032)",
        "models.interpolation: replaced by models.finish in 0.1 (D-032)",
    ]
    with pytest.raises(ValidationError, match="upscale"):
        hmv.Settings.model_validate(OLD)


def test_retired_roles_and_settings_still_load_from_stored_data(tmp_path: Path) -> None:
    """Projects and runs made before M5 hold the finishing roles, before 0027 the scene pipeline's
    settings: reading stored settings drops them (D-032, 0027 §8)."""
    assert hmv.Settings.model_validate(stored(OLD)).models == hmv.ModelRoles(align=None)
    assert stored("not a dict") == "not a dict"
    old = dict.fromkeys(RETIRED_0027, "x") | {
        "style": "ink",
        "models": {"shots": "a", "stills": "b", "polish": "c"},
    }
    settings = hmv.Settings.model_validate(stored(old))
    assert (settings.style, settings.models.planner, settings.models.frame) == ("ink", "a", ("b",))
    project = hmv.create_project(tmp_path / "projects", "Old", make_song(tmp_path / "song.wav", 2000))
    record = json.loads((project.root / "project.json").read_text())
    record["settings"] |= dict.fromkeys(RETIRED_0027, 1)
    (project.root / "project.json").write_text(json.dumps(record))
    assert project.settings == hmv.Settings()


def test_a_project_made_before_alignment_keeps_its_timing(tmp_path: Path) -> None:
    """Stored settings without `models.align` (before 0005) mean it off, and keep their speech model
    (D-059); a new project aligns."""
    project = hmv.create_project(tmp_path / "projects", "Old", make_song(tmp_path / "song.wav", 2000))
    assert project.settings.models.align == "MMS_FA"
    record = json.loads((project.root / "project.json").read_text())
    del record["settings"]["models"]["align"]
    record["settings"]["models"]["speech"] = "whisper-1"  # as the owner's project stores it
    (project.root / "project.json").write_text(json.dumps(record))
    assert (project.settings.models.speech, project.settings.models.align) == ("whisper-1", None)
    assert stored({"models": {"align": "MMS_FA"}}) == {"models": {"align": "MMS_FA"}}


@pytest.mark.parametrize(
    ("data", "named"),
    [
        ({"colour": "red"}, "colour"),
        ({"models": {"singer": "x"}}, "models.singer"),
        ({"aspect_ratio": "21:9"}, "aspect_ratio"),
        ({"min_shot_ms": 2000.5}, "min_shot_ms"),
        ({"max_shot_ms": "8000"}, "max_shot_ms"),
        ({"fps": 24}, "fps"),
        ({"min_shot_ms": 9000, "max_shot_ms": 8000}, "min_shot_ms (9000) is larger"),
        ({"pace": "slow"}, "pace"),
        ({"mood": 3}, "mood"),
        ({"take_clips": "some"}, "take_clips"),
        ({"polish": "on"}, "polish"),  # retired by 0027: refused in new settings
        ({"models": {"frame": []}}, "models.frame"),
    ],
)
def test_bad_settings_are_refused_with_the_field_named(data: dict[str, object], named: str) -> None:
    with pytest.raises(hmv.InvalidInput) as caught:
        hmv.parse_settings(data)
    assert named in str(caught.value)
    assert caught.value.problems


def test_planners_get_everything_but_the_model_ids() -> None:
    data = hmv.parse_settings({"style": "ink drawing", "aspect_ratio": "9:16"}).for_planner()
    assert data["style"] == "ink drawing" and data["aspect_ratio"] == "9:16"
    assert "models" not in data and data["max_shot_ms"] == 8000
    assert "take_clips" not in data  # which takes get clips is not the planner's (0031)
    assert (data["pace"], data["mood"]) == ("balanced", "")  # the project's options are (0009)
    mood = "dark, دلهره‌آور (dread)"  # any language
    assert hmv.parse_settings({"pace": "calm", "mood": mood}).mood == mood


def test_settings_are_frozen() -> None:
    with pytest.raises(ValueError, match="frozen"):
        hmv.Settings().style = "other"  # type: ignore[misc]


def test_only_the_picked_takes_get_clips_unless_asked() -> None:
    """0031: a new project and one stored before 0031 make clips of the takes in use only."""
    assert hmv.Settings().take_clips == "picked"
    assert hmv.Settings.model_validate(stored({"pace": "calm"})).take_clips == "picked"
    assert hmv.parse_settings({"take_clips": "all"}).take_clips == "all"
