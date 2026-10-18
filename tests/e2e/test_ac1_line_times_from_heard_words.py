"""AC-1: a song with given lyrics yields a timeline whose line times come only from measured words: the
given lyrics aligned to the vocals (change 0005), or the heard words when they are not aligned (design
§5.1, §6, §14; D-003, D-016). The transcriber mishears; the lyrics editor corrects the words from the
given lyrics, regroups the lines and marks the instrumental spans, and can never move a time. The last
given line is not heard at first: the second listen hears it in its slice of the song (D-040)."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video import runs
from hone_music_video.testing import FakeModels
from tests.conftest import LYRICS, new_project  # the project's given lyrics

pytestmark = pytest.mark.e2e
# what the transcriber heard: misheard words, a cough nobody sang, times in ms
HEARD = [
    ("she", 3010, 3290),
    ("weights", 3320, 3700),
    ("upon", 3760, 4020),
    ("the", 4050, 4130),
    ("balcony", 4170, 4980),
    ("cough", 6000, 6100),
    ("the", 9040, 9200),
    ("win", 9230, 9610),
    ("is", 9650, 9800),
    ("inner", 9820, 10200),
    ("hair", 10240, 11050),
]
# what the second listen heard in its slice (10 550 to 20 000 ms: the gap after "hair", with a margin)
SLICE = [("and", 1000, 1300), ("the", 1350, 1500), ("night", 1550, 2100), ("comes", 2200, 2600)]
SLICE += [("down", 2700, 3400)]


class Models(FakeModels):
    """Fake models whose transcriber hears `HEARD` in the song and `SLICE` in a slice of it, and whose
    lyrics editor corrects it."""

    def transcribe(
        self, model_id: str, audio: Path, *, language: str | None, prompt: str | None
    ) -> hmv.Words:
        super().transcribe(model_id, audio, language=language, prompt=prompt)
        heard = SLICE if audio.name.startswith("slice-") else HEARD
        return hmv.Words(words=[hmv.Word(text=t, start_ms=a, end_ms=b) for t, a, b in heard])


def editor(data: Mapping[str, Any]) -> dict[str, Any]:
    assert [w["i"] for w in data["heard_words"]] == list(range(len(HEARD) + len(SLICE)))
    assert data["lyrics"] == LYRICS
    return {
        "language": "en",
        "sections": [{"id": "verse-1", "kind": "verse"}, {"id": "chorus-1", "kind": "chorus"}],
        "lines": [
            {"section": "verse-1", "text": "she waits upon the balcony", "heard_first": 0, "heard_last": 4},
            {"section": "chorus-1", "text": "the wind is in her hair", "heard_first": 6, "heard_last": 10},
            {"section": "chorus-1", "text": "and the night comes down", "heard_first": 11, "heard_last": 15},
        ],
        "instrumental": [
            {"after_line": 0, "kind": "intro"},
            {"after_line": 1, "kind": "break"},
            {"after_line": 3, "kind": "outro"},
        ],
    }


def test_line_and_word_times_come_only_from_heard_words(tmp_path: Path) -> None:
    project = new_project(tmp_path, {"models": {"align": None}})  # the lyrics not aligned (0005)
    models = Models(answers={"LyricsEdit": editor})
    state = hmv.start(project, models)
    assert state.waiting == "review_lyrics"
    first, second = models.calls_of("transcribe")
    assert first.prompt.startswith("she waits upon the balcony the wind")
    assert second.prompt == "and the night comes down"  # the line not heard, in its slice
    assert second.images[0].name == "slice-10550-20000.wav"
    stored: hmv.Words = runs.stage_outputs(project, "transcribe")["transcribe"]
    assert [
        (n.lines, n.start_ms, n.end_ms, n.gap_start_ms, n.gap_end_ms, n.heard) for n in stored.listened_again
    ] == [(["and the night comes down"], 10550, 20000, 11050, 20000, 5)]
    hmv.approve(project)  # refused if check_lyrics had found an error (D-015)
    hmv.resume(project, models)  # plan_cast keeps the approved timeline in current/
    timeline = hmv.Timeline.model_validate(json.loads((project.current / "timeline.json").read_text()))

    starts = {a for _, a, _ in HEARD} | {a + 10550 for _, a, _ in SLICE}  # slice times in song time
    ends = {b for _, _, b in HEARD} | {b + 10550 for _, _, b in SLICE}
    assert [(ln.text, ln.start_ms, ln.end_ms) for ln in timeline.lines] == [
        ("she waits upon the balcony", 3010, 4980),
        ("the wind is in her hair", 9040, 11050),
        ("and the night comes down", 11550, 13950),
    ]
    for line in timeline.lines:
        assert line.words, line.id
        assert all(w.start_ms in starts and w.end_ms in ends for w in line.words)
    # corrected words keep the times of what was heard there
    words = {w.text: (w.start_ms, w.end_ms) for ln in timeline.lines for w in ln.words}
    assert words["waits"] == (3320, 3700) and words["hair"] == (10240, 11050)
    assert [(i.kind, i.start_ms, i.end_ms) for i in timeline.instrumental] == [
        ("intro", 0, 3010),
        ("break", 4980, 9040),
        ("outro", 13950, 20000),
    ]
    assert [(s.id, s.start_ms, s.end_ms) for s in timeline.sections] == [
        ("verse-1", 3010, 4980),
        ("chorus-1", 9040, 13950),
    ]


# where the aligner places the given words, and the editor that splits them into the given lines
ALIGNED = [
    [("she", 3060, 3290), ("waits", 3330, 3700), ("upon", 3760, 4020), ("the", 4050, 4130)],
    [("balcony", 4170, 4980)],
    [("the", 9060, 9200), ("wind", 9230, 9610), ("is", 9650, 9800), ("in", 9820, 9900), ("her", 9950, 10200)],
    [("hair", 10240, 11050)],
    [("and", 12000, 12300), ("the", 12350, 12500), ("night", 12550, 13100), ("comes", 13200, 13600)],
    [("down", 13700, 14400)],
]
GIVEN = ["she waits upon the balcony", "the wind is in her hair", "and the night comes down"]


class Aligner(Models):
    def align(self, model_id: str, audio: Path, lines: Sequence[str]) -> list[list[hmv.AlignedWord]]:
        super().align(model_id, audio, lines)
        assert list(lines) == GIVEN
        pairs = [ALIGNED[0] + ALIGNED[1], ALIGNED[2] + ALIGNED[3], ALIGNED[4] + ALIGNED[5]]
        return [
            [hmv.AlignedWord(text=t, start_ms=a, end_ms=b, score=0.9) for t, a, b in line] for line in pairs
        ]


def splitter(data: Mapping[str, Any]) -> dict[str, Any]:
    assert data["aligned"] is True and [w["text"] for w in data["heard_words"]] == " ".join(GIVEN).split()
    return {
        "language": "en",
        "sections": [{"id": "verse-1", "kind": "verse"}],
        "lines": [
            {"section": "verse-1", "text": text, "heard_first": first, "heard_last": last}
            for text, (first, last) in zip(GIVEN, [(0, 4), (5, 10), (11, 15)], strict=True)
        ],
        "instrumental": [{"after_line": 0, "kind": "intro"}, {"after_line": 3, "kind": "outro"}],
    }


def test_given_lyrics_are_timed_from_the_aligned_words(project: hmv.Project) -> None:
    models = Aligner(answers={"LyricsEdit": splitter})
    state = hmv.start(project, models)
    assert state.waiting == "review_lyrics"
    (aligned,) = models.calls_of("align")
    assert aligned.images[0].parent == project.vocals_dir  # aligned to the isolated vocals
    hmv.approve(project)  # refused if check_lyrics had found an error (D-015)
    hmv.resume(project, models)
    timeline = hmv.Timeline.model_validate(json.loads((project.current / "timeline.json").read_text()))
    assert [(ln.text, ln.start_ms, ln.end_ms) for ln in timeline.lines] == [
        ("she waits upon the balcony", 3060, 4980),
        ("the wind is in her hair", 9060, 11050),
        ("and the night comes down", 12000, 14400),  # not heard at first: aligned all the same
    ]
    placed = {(t, a, b) for line in ALIGNED for t, a, b in line}
    assert all((w.text, w.start_ms, w.end_ms) in placed for ln in timeline.lines for w in ln.words)
