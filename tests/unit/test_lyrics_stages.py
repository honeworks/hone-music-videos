"""Stages 2 and 3 on their own (design §6, §7.1): the transcription prompt, and the lyrics editor's one
call, sent back once when its reply cannot be timed."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video import stages_plan
from hone_music_video._jobs import Job
from hone_music_video.events import EventLog
from hone_music_video.testing import FakeModels
from hone_music_video.timed_lyrics import PROMPT_CHARS

WORDS = hmv.Words(
    words=[hmv.Word(text=t, start_ms=1000 * n, end_ms=1000 * n + 500) for n, t in enumerate("abc", 1)]
)
SONG = hmv.Song(duration_ms=5000, sample_rate=44100, channels=2)


def job(project: hmv.Project, models: FakeModels) -> Job:
    return Job(project, models, project.settings, EventLog(project.events_file))


def reply(*ranges: tuple[int, int]) -> dict[str, Any]:
    return {
        "sections": [{"id": "v", "kind": "verse"}],
        "lines": [{"section": "v", "text": "a b", "heard_first": a, "heard_last": b} for a, b in ranges],
    }


def test_the_prompt_is_the_opening_of_the_sung_lines(project: hmv.Project) -> None:
    models = FakeModels()
    song = project.root / "input" / "song.wav"
    lines = [f"line {n} " + "word " * 10 for n in range(1, 40)]
    lyrics = "[Intro: thunder]\n\n«she waits»\n[Verse 1]\n" + "\n".join(lines)

    def prompts() -> list[str]:  # the calls on the whole song's vocals (the lines past the prompt get slices)
        whole = project.vocals_dir
        return [c.prompt for c in models.calls_of("transcribe") if c.images[0].parent == whole]

    stages_plan.transcribe(job(project, models), song, SONG, lyrics)
    prompt = prompts()[0]
    assert prompt.startswith("«she waits» line 1 word") and prompt.endswith("word")
    assert len(prompt) <= PROMPT_CHARS < len(prompt) + len(lines[0]) + 1  # whole lines, as many as fit
    stages_plan.transcribe(job(project, models), song, SONG, "[only notes]")
    assert prompts()[-1] == ""  # no prompt sent
    stages_plan.transcribe(job(project, models), song, SONG, "la " * 300)
    assert len(prompts()[-1]) <= PROMPT_CHARS  # one long line, cut at a word


class LateWords(FakeModels):
    """Hears a word running past the song's end, then two after it (one of them without length)."""

    def transcribe(
        self, model_id: str, audio: Path, *, language: str | None, prompt: str | None
    ) -> hmv.Words:
        times = [("a", 1000, 1500), ("b", 4800, 5300), ("c", 5000, 5000), ("d", 5100, 5400)]
        return hmv.Words(words=[hmv.Word(text=t, start_ms=a, end_ms=b) for t, a, b in times])


def test_heard_words_are_kept_inside_the_song(project: hmv.Project) -> None:
    heard = stages_plan.transcribe(job(project, LateWords()), project.root / "input" / "song.wav", SONG, None)
    assert [(w.text, w.start_ms, w.end_ms) for w in heard.words] == [("a", 1000, 1500), ("b", 4800, 5000)]


def test_a_reply_that_cannot_be_timed_is_sent_back_once(project: hmv.Project) -> None:
    answers = iter([reply((1, 2), (0, 0)), reply((0, 1), (2, 2))])

    def editor(_data: Mapping[str, Any]) -> dict[str, Any]:
        return next(answers)

    models = FakeModels(answers={"LyricsEdit": editor})
    timed = stages_plan.lyrics(job(project, models), SONG, WORDS, "a b")
    first, second = models.calls_of("plan")
    assert "problems" not in first.data
    assert second.data["problems"] == ["line 2: starts at heard word 0, inside the line before it"]
    assert [(ln.start_ms, ln.end_ms) for ln in timed.lines] == [(1000, 2500), (3000, 3500)]


def test_two_replies_that_cannot_be_timed_fail_the_stage(project: hmv.Project) -> None:
    models = FakeModels(answers={"LyricsEdit": lambda _data: reply((0, 7))})
    with pytest.raises(
        hmv.ModelFailure, match=r"twice gave lyrics that cannot be timed: line 1: heard words 0\.\.7"
    ):
        stages_plan.lyrics(job(project, models), SONG, WORDS, None)
    assert len(models.calls_of("plan")) == 2


def test_the_owner_note_and_the_previous_lines_go_to_the_editor(project: hmv.Project) -> None:
    models = FakeModels(answers={"LyricsEdit": lambda _data: reply((0, 2))})
    previous = stages_plan.lyrics(job(project, models), SONG, WORDS, None)
    stages_plan.lyrics(job(project, models), SONG, WORDS, None, note="one line, please", previous=previous)
    sent = models.calls_of("plan")[1].data
    assert sent["review_note"] == "one line, please"
    assert sent["previous_lines"] == [{"id": "L001", "section": "v", "text": "a b", "heard": [0, 2]}]
    assert [w["i"] for w in sent["heard_words"]] == [0, 1, 2]
