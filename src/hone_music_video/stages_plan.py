"""Stages 1 to 3 (design §3.1): measure, transcribe, time the lyrics; the check of stage 4 is
`lyrics_check.py`. The frame plan (stage 5) is `frame_plan.py` (0026, 0027).

Plain functions over records; `workflow.py` makes them hone-flow steps."""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib import resources
from pathlib import Path
from typing import Any

from hone_music_video._files import write_json
from hone_music_video._jobs import Job
from hone_music_video.aligned_lyrics import align_lyrics
from hone_music_video.errors import InvalidInput, ModelFailure, ToolMissing
from hone_music_video.first_listen import first_listen
from hone_music_video.records import (
    Song,
    Timeline,
    Words,
)
from hone_music_video.second_listen import listen_again
from hone_music_video.timed_lyrics import (
    LyricsEdit,
    build_timeline,
    edit_problems,
)


def system_prompt(*names: str) -> str:
    """The planner's system prompt, from the versioned files in `data/prompts/` (design §7.1)."""
    folder = resources.files("hone_music_video") / "data" / "prompts"
    return "\n\n".join((folder / f"{name}.md").read_text(encoding="utf-8").strip() for name in names)


def accept(job: Job, name: str, record: Timeline) -> None:
    """Keep an approved plan in `current/` for the dashboard and for people (design §4)."""
    write_json(job.project.current / name, record)


# ------------------------------------------------------------------------------ 1-4: timed lyrics


def measure(song: Path) -> Song:
    """Stage 1: the song's length, sample rate and channels, measured with ffprobe (design §2.1)."""
    if shutil.which("ffprobe") is None:
        raise ToolMissing("ffprobe is not installed; install ffmpeg (it brings ffprobe) and resume the run")
    found = subprocess.run(  # noqa: S603 - a fixed program and a path we made
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(song)],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        probe = json.loads(found.stdout)
        audio = next(s for s in probe["streams"] if s.get("codec_type") == "audio")
        duration_ms = round(float(probe["format"]["duration"]) * 1000)
        rate, channels = int(audio["sample_rate"]), int(audio["channels"])
    except (ValueError, KeyError, StopIteration, TypeError):
        why = found.stderr.strip() or "no audio stream found"
        raise InvalidInput(
            f"{song.name} is not a song ffprobe can read ({why}); give a WAV, FLAC, MP3, M4A or OGG"
        ) from None
    return Song(duration_ms=duration_ms, sample_rate=rate, channels=channels)


def transcribe(job: Job, song: Path, measured: Song, lyrics: str | None) -> Words:
    """Stage 2: every heard word with its times, tidied and inside the song (D-017): the song's isolated
    vocals heard with the opening of the given lyrics' sung lines as the prompt (design §6, D-045; made
    again once when too few lines are found, D-047); a given line not heard is listened for again in its
    slices of the song (D-040, D-046). Given lyrics are then aligned to the vocals, and the lines are
    timed from the aligned words (0005)."""
    heard, vocals = first_listen(job, song, measured, lyrics)
    words = listen_again(job, song, measured, lyrics, heard, vocals=vocals)
    return align_lyrics(job, vocals or song, measured, lyrics, words)


def _edit(job: Job, data: dict[str, Any], heard: int) -> LyricsEdit:
    """The editor's one call; a reply that cannot be timed is sent back once with what is wrong (§7.1)."""
    system, model = system_prompt("lyrics"), job.settings.models.lyrics
    edit = job.models.plan(model, system=system, data=data, images=[], schema=LyricsEdit)
    problems = edit_problems(edit, heard)
    if problems:
        retry = data | {"problems": problems}
        edit = job.models.plan(model, system=system, data=retry, images=[], schema=LyricsEdit)
        problems = edit_problems(edit, heard)
    if problems:
        raise ModelFailure(f"{model} twice gave lyrics that cannot be timed: {'; '.join(problems)}")
    return edit


def _previous_lines(previous: Timeline | None) -> list[dict[str, Any]]:
    """The lines of the timeline the owner's note is about, as the editor sees them."""
    lines = previous.lines if previous is not None else []
    return [
        {"id": ln.id, "section": ln.section, "text": ln.text, "heard": [ln.heard_first, ln.heard_last]}
        for ln in lines
    ]


def lyrics(
    job: Job,
    song: Song,
    words: Words,
    given: str | None,
    *,
    note: str | None = None,
    previous: Timeline | None = None,
) -> Timeline:
    """Stage 3: one call to the lyrics editor; the code takes every time from the words: the aligned
    words when the given lyrics were aligned (0005, D-059), else the heard words (design §6, D-003,
    D-016). `note` is the owner's note when the stage is run again (D-015), with the lines of the
    `previous` timeline it is about."""
    timing = words.timing()
    data: dict[str, Any] = {
        "duration_ms": song.duration_ms,
        "language": job.settings.language or words.language,
        "heard_words": [{"i": i} | w.model_dump() for i, w in enumerate(timing)],
        "lyrics": given,
    }
    if words.aligned is not None:
        data["aligned"] = True
    if note:
        data["review_note"] = note
        data["previous_lines"] = _previous_lines(previous)
    edit = _edit(job, data, len(timing))
    return build_timeline(edit, words, song.duration_ms, job.settings.language)


# ------------------------------------------------------------------------------ the frame planner reads


def timeline_data(timeline: Timeline) -> dict[str, Any]:
    """The timeline as the shot planner reads it: sections, lines with every word as
    `[start_ms, end_ms, text]` (a cut may fall between two words), instrumental spans."""
    lines = [
        line.model_dump(include={"id", "section", "text", "start_ms", "end_ms"})
        | {"words": [[w.start_ms, w.end_ms, w.text] for w in line.words]}
        for line in timeline.lines
    ]
    return {
        "duration_ms": timeline.duration_ms,
        "sections": [s.model_dump() for s in timeline.sections],
        "lines": lines,
        "instrumental": [i.model_dump() for i in timeline.instrumental],
    }
