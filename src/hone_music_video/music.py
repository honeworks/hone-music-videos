"""The song's shape, measured (0028 §1): what the music does in each part, from the audio alone.

Every section and every instrumental span (a "part", in time order) gets its loudness against the whole
song's, its change from the part before, the loudness of the voice (the isolated vocals of the first
listen, when kept) and the words sung per second, with the lyrics' notes for it. A drop, a quiet break,
a whisper or a rushed verse shows here even when the owner gave no lyrics and no notes. No model is
called: ffmpeg decodes the audio, numpy measures it."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from hone_music_video.errors import InvalidInput
from hone_music_video.records import Timeline

RATE = 8000  # samples per second: plenty for a loudness
FLOOR_DB = -60.0  # silence reads as this much below the song


def decode(audio: Path) -> np.ndarray:
    """The audio as mono float samples at `RATE` (ffmpeg)."""
    command = ["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"]
    try:
        done = subprocess.run(command, capture_output=True, check=True)  # noqa: S603 - fixed arguments
    except (OSError, subprocess.CalledProcessError) as error:
        raise InvalidInput(f"cannot read {audio.name} to measure the song: {error}") from None
    return np.frombuffer(done.stdout, dtype=np.float32)  # pyright: ignore[reportUnknownMemberType] - numpy's stub


def _rms(samples: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float64)))) if samples.size else 0.0


def level_db(samples: np.ndarray, start_ms: int, end_ms: int, reference: float) -> float:
    """The loudness of a span against `reference` (an RMS), in dB, never below `FLOOR_DB`."""
    span = samples[start_ms * RATE // 1000 : end_ms * RATE // 1000]
    rms = _rms(span)
    if rms <= 0 or reference <= 0:
        return FLOOR_DB
    return max(FLOOR_DB, round(20 * math.log10(rms / reference), 1))


def parts(timeline: Timeline) -> list[dict[str, Any]]:
    """The sections and the instrumental spans (`instrumental-1`, ...) in time order, with their notes."""
    found = [
        {"part": s.id, "kind": s.kind, "start_ms": s.start_ms, "end_ms": s.end_ms, "notes": s.notes}
        for s in timeline.sections
    ]
    found += [
        {"part": f"instrumental-{n}", "kind": f"instrumental {i.kind}", "start_ms": i.start_ms,
         "end_ms": i.end_ms, "notes": i.notes}
        for n, i in enumerate(timeline.instrumental, 1)
    ]  # fmt: skip
    return sorted(found, key=lambda p: (p["start_ms"], p["end_ms"]))


def _words_per_s(timeline: Timeline, start_ms: int, end_ms: int) -> float:
    words = sum(1 for ln in timeline.lines for w in ln.words if start_ms <= w.start_ms < end_ms)
    return round(words * 1000 / max(1, end_ms - start_ms), 1)


def shape(timeline: Timeline, song: Path, vocals: Path | None = None) -> list[dict[str, Any]]:
    """Every part with `loudness_db` (against the song), `change_db` (against the part before; null for
    the first), `voice_db` (the vocals against their own average; null without vocals) and
    `words_per_s`."""
    mix = decode(song)
    voice = decode(vocals) if vocals is not None and vocals.is_file() else None
    mix_ref, voice_ref = _rms(mix), _rms(voice) if voice is not None else 0.0
    found: list[dict[str, Any]] = []
    for part in parts(timeline):
        a, b = part["start_ms"], part["end_ms"]
        loud = level_db(mix, a, b, mix_ref)
        before = found[-1]["loudness_db"] if found else None
        found.append(
            part
            | {
                "loudness_db": loud,
                "change_db": None if before is None else round(loud - before, 1),
                "voice_db": None if voice is None else level_db(voice, a, b, voice_ref),
                "words_per_s": _words_per_s(timeline, a, b),
            }
        )
    return found
