"""Fakes for tests, examples and demos: `FakeModels` (no models, no GPU, no network), the port's
contract checker, tiny media files, and `settle_scenes`: the owner's accepts, picks and Run at
`review_scenes` (0027)."""

from hone_music_video.testing.contract import (
    check_generate,
    check_models,
    check_plan,
    check_separate,
    check_transcribe,
)
from hone_music_video.testing.fake_models import Call, FakeModels
from hone_music_video.testing.media import make_clip, make_picture, make_sheet, make_song
from hone_music_video.testing.scenes import settle_scenes

__all__ = [
    "Call",
    "FakeModels",
    "check_generate",
    "check_models",
    "check_plan",
    "check_separate",
    "check_transcribe",
    "make_clip",
    "make_picture",
    "make_sheet",
    "make_song",
    "settle_scenes",
]
