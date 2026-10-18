"""Real vocal isolation (D-041, D-045): Demucs `htdemucs` on the CPU through `HoneModels`, on a song.

Skipped by default (marker `separate`); needs the `separate` extra. The first run downloads the weights
(about 80 MB) to the Hugging Face cache. Run it with `uv run pytest -m separate tests/separate`."""

import wave
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video.testing import make_song

pytestmark = [pytest.mark.separate, pytest.mark.timeout(600)]


def test_demucs_isolates_the_vocals_of_a_song_on_the_cpu(tmp_path: Path) -> None:
    pytest.importorskip("demucs.api", reason="needs the separate extra: uv sync --extra separate")
    song = make_song(tmp_path / "song.wav", 4000, sample_rate=44100)  # mono: demucs makes it stereo
    vocals = hmv.HoneModels().separate_vocals(hmv.ModelRoles().vocals, song, out=tmp_path / "vocals.wav")
    with wave.open(str(vocals), "rb") as audio:
        assert (audio.getnchannels(), audio.getframerate()) == (2, 44100)
        assert abs(audio.getnframes() - 4 * 44100) <= 441  # the song's length, within 10 ms
