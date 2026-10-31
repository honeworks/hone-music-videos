"""The five focuses of a shot (0035 §1): what each holds, the views they set, an older shot's focus."""

from __future__ import annotations

from typing import Any

import pytest

from hone_music_video.frame_focus import focus_of, focus_problems, with_focus_views
from hone_music_video.frame_items import normalized, scene_refs
from hone_music_video.records import Framing
from hone_music_video.records_frame import CastUse, FrameShot, PlaceUse
from tests.unit.test_frame_items import bible

DARVIN, EMBER = CastUse(character="darvin"), CastUse(character="ember")


def shot(framing: Framing, cast: list[CastUse], **more: Any) -> FrameShot:
    fields: dict[str, Any] = {
        "id": "S001", "start_ms": 0, "end_ms": 3000, "beat": "b", "framing": framing, "faces": False,
        "camera": "static camera", "light": "moonlight", "cast": cast, "place": PlaceUse(place="oasis"),
    }  # fmt: skip
    return FrameShot.model_validate(fields | more)


@pytest.mark.parametrize(
    ("focus", "framing", "cast", "wrong"),
    [
        ("face", "close-up", [DARVIN], ""),
        ("face", "close-up", [DARVIN, EMBER], "2 characters"),
        ("face", "wide", [DARVIN], "a wide"),
        ("figure", "wide", [DARVIN], ""),
        ("figure", "medium", [], "0 characters"),
        ("pair", "medium", [DARVIN, EMBER], ""),
        ("pair", "close-up", [DARVIN, EMBER], "a close-up"),
        ("place", "extreme-wide", [], ""),
        ("place", "wide", [DARVIN], "1 characters"),
        ("detail", "insert", [], ""),
        ("detail", "insert", [DARVIN, EMBER, DARVIN], "3 characters"),
    ],
)
def test_each_focus_holds_its_characters_and_framings(
    focus: str, framing: Framing, cast: list[CastUse], wrong: str
) -> None:
    found = " ".join(focus_problems(shot(framing, cast, focus=focus)))
    assert (wrong in found) if wrong else found == ""


def test_a_shot_without_a_focus_is_sent_back_and_faces_need_a_person() -> None:
    assert "no `focus`" in " ".join(focus_problems(shot("medium", [DARVIN])))
    assert "faces" in " ".join(focus_problems(shot("wide", [], focus="place", faces=True)))
    hand = shot("insert", [CastUse(character="darvin", view="detail")], focus="detail")
    assert "`part`" in " ".join(focus_problems(hand))


def test_the_focus_sets_the_view_and_the_references_follow() -> None:
    b = normalized(bible())
    face = shot("close-up", [CastUse(character="darvin", view="side", pose="lying")], focus="face")
    hand = shot("insert", [CastUse(character="darvin", part="his hand")], focus="detail")
    face, hand = with_focus_views([face, hand])
    assert (face.cast[0].view, face.cast[0].pose) == ("close", "")
    assert hand.cast[0].view == "detail"
    assert scene_refs(b, face) == ["oasis.wide", "darvin.close"]
    assert scene_refs(b, hand) == ["oasis.wide", "darvin.detail-his-hand"]


@pytest.mark.parametrize(
    ("framing", "cast", "focus"),
    [
        ("insert", [], "detail"),
        ("wide", [], "place"),
        ("medium", [DARVIN, EMBER], "pair"),
        ("close-up", [DARVIN], "face"),
        ("medium", [CastUse(character="darvin", view="close")], "face"),
        ("wide", [DARVIN], "figure"),
        ("extreme-close-up", [CastUse(character="darvin", view="detail", part="eye")], "detail"),
    ],
)
def test_an_older_shot_has_the_focus_its_framing_and_cast_imply(
    framing: Framing, cast: list[CastUse], focus: str
) -> None:
    assert focus_of(shot(framing, cast)) == focus
