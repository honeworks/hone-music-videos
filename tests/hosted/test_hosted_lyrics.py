"""Real hosted check of milestone M2 (costs a little: about 0.03 USD of Whisper and 0.16 USD of the lyrics
editor for a five-minute song): measure, transcribe, lyrics and check_lyrics on a real song, on the gateway.

Skipped by default (marker `hosted`). Run it with
`HONE_TEST_HOSTED_SONG=<folder with song.* and lyrics.txt> HONE_TEST_PROJECTS=<folder on the real disk>
HONE_ENV_FILE=<.env with OPENAI_COMPATIBLE_API_KEY> uv run pytest -m hosted tests/hosted`."""

import os
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import runs
from hone_music_video.timed_lyrics import sung_lines

pytestmark = pytest.mark.hosted


def _folders() -> tuple[Path, Path]:
    song, projects = os.environ.get("HONE_TEST_HOSTED_SONG"), os.environ.get("HONE_TEST_PROJECTS")
    if not song or not projects:
        pytest.skip("set HONE_TEST_HOSTED_SONG and HONE_TEST_PROJECTS (and OPENAI_COMPATIBLE_API_KEY) to run")
    return Path(song), Path(projects)


def test_a_real_song_is_timed_from_heard_words() -> None:
    sample, projects = _folders()
    lyrics = (sample / "lyrics.txt").read_text(encoding="utf-8")
    song = next(p for p in sample.glob("song.*"))
    project = hmv.create_project(projects, "M2 hosted check", song, hmv.Material(lyrics=lyrics))
    state = hmv.start(project, hmv.HoneModels())
    assert state.waiting == "review_lyrics", state
    out = runs.stage_outputs(project, "transcribe", "lyrics", "check_lyrics")
    words, timeline, report = out["transcribe"], out["lyrics"], out["check_lyrics"]
    assert report.errors == []
    assert words.call is not None and words.call.cost_usd
    assert len(timeline.lines) >= len(sung_lines(lyrics)) // 2
    for line in timeline.lines:
        assert line.start_ms == words.words[line.heard_first].start_ms
        assert line.end_ms == words.words[line.heard_last].end_ms
    key = os.environ["OPENAI_COMPATIBLE_API_KEY"].encode()  # set by now (the environment or .env)
    assert [p for p in project.root.rglob("*") if p.is_file() and key in p.read_bytes()] == []
