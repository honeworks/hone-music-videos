"""A blank picture or clip, refused before it is kept (0025 §4): a model that failed silently (Qwen-Image-Edit
on a SageAttention server returns black) must not leave a version in use."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from hone_music_video._video import frame_rgb, probe
from hone_music_video.errors import ModelFailure

SIZE = (64, 36)  # read small: a blank picture is blank at any size
SPREAD = 2  # levels a channel may vary and still be one colour
PICTURES = {".png", ".jpg", ".jpeg", ".webp"}


def _flat(pixels: bytes) -> bool:
    """Whether RGB bytes are one colour: each channel within `SPREAD` levels."""
    return all(max(pixels[c::3]) - min(pixels[c::3]) <= SPREAD for c in range(3))


def blank_picture(path: Path) -> bool:
    with Image.open(path) as picture:
        return _flat(picture.convert("RGB").resize(SIZE, Image.Resampling.BOX).tobytes())


def blank_clip(path: Path) -> bool:
    """Its first, middle and last frames all blank."""
    frames = probe(path).frames
    return all(_flat(frame_rgb(path, n, SIZE)) for n in sorted({0, frames // 2, max(frames - 1, 0)}))


def refuse_blank(model: str, path: Path) -> None:
    """Delete a blank file and raise `ModelFailure`; anything else is left as it is."""
    suffix = path.suffix.lower()
    if suffix in PICTURES and blank_picture(path):
        what = "picture"
    elif suffix == ".mp4" and blank_clip(path):
        what = "clip"
    else:
        return
    path.unlink(missing_ok=True)
    raise ModelFailure(f"{model} returned a blank {what}")
