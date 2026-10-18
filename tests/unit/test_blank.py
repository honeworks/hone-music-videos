"""A blank picture or clip is one colour; a gradient or a corner box is not (0025 §4, D-159)."""

from pathlib import Path

from hone_music_video._blank import _flat, blank_clip, blank_picture
from hone_music_video.testing.media import make_clip, png_bytes


def test_flat_rgb_is_one_colour_within_two_levels() -> None:
    assert _flat(bytes([0, 0, 0, 2, 0, 0]))
    assert not _flat(bytes([0, 0, 0, 3, 0, 0]))


def test_blank_picture_and_clip(tmp_path: Path) -> None:
    black = tmp_path / "black.png"
    black.write_bytes(png_bytes(32, 18, (0, 0, 0)))
    assert blank_picture(black)
    near = tmp_path / "near.png"
    near.write_bytes(png_bytes(8, 8, (0, 0, 1)))
    assert blank_picture(near)
    clip = make_clip(tmp_path / "plain.mp4", 17, 16, (0, 0, 0))
    assert blank_clip(clip)
    boxed = make_clip(tmp_path / "boxed.mp4", 17, 16, (0, 0, 0), box=True)
    assert not blank_clip(boxed)
