"""Real forced alignment (change 0005, D-055): torchaudio's `MMS_FA` on the CPU through `HoneModels`.

Skipped by default (marker `align`); needs the `align` extra. The first run downloads the weights (about
1.2 GB) to torch's cache. Run it with `uv run pytest -m align tests/align`. With
`HONE_TEST_ALIGN_VOCALS` (a song's isolated vocals) and `HONE_TEST_ALIGN_LYRICS` (its lyrics file), it
also aligns that song and checks every given line is placed, in order."""

import itertools
import os
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video.testing import make_song
from hone_music_video.timed_lyrics import sung_lines

pytestmark = [pytest.mark.align, pytest.mark.timeout(900)]


def test_the_mms_aligner_places_every_word_in_order_on_the_cpu(tmp_path: Path) -> None:
    pytest.importorskip("torchaudio", reason="needs the align extra: uv sync --extra align")
    song = make_song(tmp_path / "song.wav", 4000)
    timed = hmv.HoneModels().align(hmv.ModelRoles().align or "", song, ["la la", "Kaa-ra-van!", "—"])
    assert [[w.text for w in line] for line in timed] == [["la", "la"], ["Kaa-ra-van!"], []]
    words = [w for line in timed for w in line]
    assert all(0 <= w.start_ms < w.end_ms <= 4000 for w in words)
    assert all(a.end_ms <= b.start_ms for a, b in itertools.pairwise(words))


def test_a_songs_given_lines_are_all_placed() -> None:
    vocals, lyrics = os.environ.get("HONE_TEST_ALIGN_VOCALS"), os.environ.get("HONE_TEST_ALIGN_LYRICS")
    if not (vocals and lyrics):
        pytest.skip("set HONE_TEST_ALIGN_VOCALS and HONE_TEST_ALIGN_LYRICS to align a real song")
    lines = sung_lines(Path(lyrics).read_text(encoding="utf-8"))
    timed = hmv.HoneModels().align("MMS_FA", Path(vocals), lines)
    assert all(timed), [text for text, own in zip(lines, timed, strict=True) if not own]
    starts = [own[0].start_ms for own in timed]
    assert starts == sorted(starts)
