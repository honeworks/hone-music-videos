"""Tiny media files for tests, examples and demos: a silent WAV song, a one-colour PNG, a synthetic sheet,
a one-colour video."""

from __future__ import annotations

import struct
import wave
import zlib
from pathlib import Path

from PIL import Image, ImageDraw

from hone_music_video._video import ffmpeg


def make_song(path: str | Path, duration_ms: int = 30_000, *, sample_rate: int = 8000) -> Path:
    """A silent mono WAV of `duration_ms`, for tests, examples and demos."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = duration_ms * sample_rate // 1000
    with wave.open(str(path), "wb") as song:
        song.setnchannels(1)
        song.setsampwidth(2)
        song.setframerate(sample_rate)
        song.writeframes(b"\x00\x00" * frames)
    return path


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _png(width: int, height: int, rows: bytes) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    body = zlib.compress(rows)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", body) + _chunk(b"IEND", b"")


def png_bytes(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """A valid PNG of one colour."""
    row = b"\x00" + bytes(rgb) * width
    return _png(width, height, row * height)


def gradient_png_bytes(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """A valid PNG whose rows step one level each away from `rgb` (row 0 is `rgb`): not one colour."""
    rows = bytearray()
    for r in range(height):
        pixel = bytes(c + r if c < 128 else c - r for c in rgb)
        rows += b"\x00" + pixel * width
    return _png(width, height, bytes(rows))


def make_picture(path: str | Path, rgb: tuple[int, int, int] = (180, 150, 120), size: int = 16) -> Path:
    """A small one-colour PNG (a stand-in for a given sheet)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_bytes(size, size, rgb))
    return path


FIGURE_COLOURS = ((40, 40, 40), (120, 20, 20), (20, 120, 20), (20, 20, 120), (120, 120, 20))


def make_sheet(path: str | Path, widths: tuple[float, ...] = (1, 1, 1, 1), height: int = 200) -> Path:
    """A synthetic turnaround sheet: one figure per width (a head over a body that wide, in its own colour,
    left to right) on a light-grey backdrop; the bodies touch at the bottom, the heads stand apart."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    slot = height
    sheet = Image.new("RGB", (slot * len(widths), height), (200, 200, 200))
    draw = ImageDraw.Draw(sheet)
    for n, width in enumerate(widths):
        middle, colour = slot * n + slot // 2, FIGURE_COLOURS[n % len(FIGURE_COLOURS)]
        half = round(slot * 0.2 * width)
        draw.ellipse((middle - 12, height * 0.1, middle + 12, height * 0.24), fill=colour)  # the head
        draw.rectangle((middle - half, height * 0.26, middle + half, height * 0.85), fill=colour)
        draw.rectangle((slot * n, height * 0.85, slot * (n + 1), height * 0.9), fill=colour)  # the floor line
    sheet.save(path)
    return path


FAST_X264 = ("-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-threads", "1")


def _colour(rgb: tuple[int, int, int]) -> str:
    return "0x{:02x}{:02x}{:02x}".format(*rgb)


def _box(rgb: tuple[int, int, int]) -> str:
    inverted = (255 - rgb[0], 255 - rgb[1], 255 - rgb[2])
    return f"drawbox=x=iw/2:y=ih/2:w=iw/2:h=ih/2:c={_colour(inverted)}:t=fill"


def make_clip(
    path: str | Path,
    frames: int,
    fps: int,
    rgb: tuple[int, int, int] = (90, 60, 30),
    size: str = "64x36",
    *,
    box: bool = False,
) -> Path:
    """A small real H.264 video of one colour, `frames` frames at `fps` (made with ffmpeg)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    source = f"color=c={_colour(rgb)}:s={size}:r={fps}"
    drawn = ("-vf", _box(rgb)) if box else ()
    ffmpeg("-f", "lavfi", "-i", source, *drawn, "-frames:v", str(frames), *FAST_X264, path)
    return path


def make_interpolated(
    path: str | Path, video: Path, fps: int, rgb: tuple[int, int, int], *, box: bool = False
) -> Path:
    """`video` at a higher `fps` (each frame repeated, as many frames as an interpolation makes), its
    size kept, painted one colour."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    vf = f"fps={fps},drawbox=c={_colour(rgb)}:t=fill"
    if box:
        vf += "," + _box(rgb)
    ffmpeg("-i", video, "-vf", vf, "-an", *FAST_X264, path)
    return path
