"""Timed lyrics (design §6, D-016): the editor's reply is checked, then every time comes from heard words."""

import pytest

import hone_music_video as hmv
from hone_music_video.timed_lyrics import (
    EditedSection,
    LyricsEdit,
    build_timeline,
    edit_problems,
    line_words,
    plain,
    sung_lines,
    tidy,
)


def heard(*texts: str, start: int = 1000, step: int = 500) -> list[hmv.Word]:
    return [
        hmv.Word(text=t, start_ms=start + n * step, end_ms=start + n * step + 400)
        for n, t in enumerate(texts)
    ]


def edit(lines: list[tuple[str, int, int]], breaks: list[int] | None = None) -> LyricsEdit:
    return LyricsEdit.model_validate(
        {
            "language": "en",
            "sections": [{"id": "verse-1", "kind": "verse"}],
            "lines": [
                {"section": "verse-1", "text": t, "heard_first": a, "heard_last": b} for t, a, b in lines
            ],
            "instrumental": [{"after_line": n, "kind": "break"} for n in breaks or []],
        }
    )


def test_given_lyrics_without_notes_and_blank_lines() -> None:
    text = "[Intro: thunder]\n\n«she waits»\n  the wind  \n[Chorus]\n"
    assert sung_lines(text) == ["«she waits»", "the wind"]
    assert sung_lines(None) == []


def test_plain_text_drops_marks_case_and_spaces() -> None:
    assert plain("«She WAITS…»") == "shewaits"
    assert plain("مَن Celina هَستَم") == plain("من celina هستم")


def test_matching_words_take_their_heard_times() -> None:
    words = line_words("she waits upon", heard("she", "waits", "upon"))
    assert [(w.text, w.start_ms, w.end_ms) for w in words] == [
        ("she", 1000, 1400),
        ("waits", 1500, 1900),
        ("upon", 2000, 2400),
    ]


def test_corrected_words_share_the_heard_words_between_their_neighbours() -> None:
    sung = heard("she", "wait", "sup", "on", "the", "balcony")
    words = line_words("She waits upon the balcony", sung)
    assert [w.text for w in words] == ["She", "waits", "upon", "the", "balcony"]
    assert (words[1].start_ms, words[2].end_ms) == (1500, 2900)  # "waits upon" over "wait sup on"
    starts = {w.start_ms for w in sung}
    ends = {w.end_ms for w in sung}
    assert all(w.start_ms in starts and w.end_ms in ends for w in words)


def test_a_written_word_nobody_heard_takes_a_neighbour_and_extra_heard_words_are_skipped() -> None:
    words = line_words("oh the night", heard("the", "uh", "night"))
    assert [(w.text, w.start_ms) for w in words] == [("oh", 1000), ("the", 1000), ("night", 2000)]
    assert line_words("", heard("x")) == []


def test_problems_with_the_reply_are_named() -> None:
    bad = edit([("a", 0, 2), ("b", 2, 3), ("c", 5, 9)], breaks=[4])
    bad.lines[0].section = "chorus-9"
    assert edit_problems(bad, 6) == [
        "line 1: section 'chorus-9' is not in sections",
        "line 2: starts at heard word 2, inside the line before it",
        "line 3: heard words 5..9 are not a range of 0..5",
        "instrumental span 1: after_line 4 is not 0..3",
    ]
    twice = edit([("a", 0, 0)])
    twice.sections.append(twice.sections[0])
    assert edit_problems(twice, 1) == ["section ids repeat; give every section its own id"]


def test_the_timeline_takes_every_time_from_heard_words() -> None:
    sung = hmv.Words(words=heard("she", "waits", "the", "wind", start=4000))
    timed = build_timeline(
        edit([("she waits", 0, 1), ("the wind", 2, 3)], breaks=[0, 1, 2]), sung, 9000, None
    )
    assert [(ln.id, ln.start_ms, ln.end_ms, ln.heard_first, ln.heard_last) for ln in timed.lines] == [
        ("L001", 4000, 4900, 0, 1),
        ("L002", 5000, 5900, 2, 3),
    ]
    assert [(s.id, s.start_ms, s.end_ms) for s in timed.sections] == [("verse-1", 4000, 5900)]
    spans = [(i.start_ms, i.end_ms) for i in timed.instrumental]
    assert spans == [(0, 4000), (4900, 5000), (5900, 9000)]
    assert timed.language == "en" and timed.duration_ms == 9000


@pytest.mark.parametrize("after", [0, 1, 2])
def test_an_instrumental_span_without_room_is_left_out(after: int) -> None:
    sung = hmv.Words(
        words=[hmv.Word(text="a", start_ms=0, end_ms=500), hmv.Word(text="b", start_ms=500, end_ms=900)]
    )
    timed = build_timeline(edit([("a", 0, 0), ("b", 1, 1)], breaks=[after]), sung, 900, "fa")
    assert timed.instrumental == [] and timed.language == "fa"


def test_more_written_words_than_heard_share_them_in_order() -> None:
    words = line_words("one two three four five", heard("uno", "dos"))
    assert [(w.text, w.start_ms, w.end_ms) for w in words] == [
        ("one", 1000, 1400),
        ("two", 1000, 1400),
        ("three", 1000, 1400),
        ("four", 1500, 1900),
        ("five", 1500, 1900),
    ]


def test_each_section_is_one_run_of_lines_in_order() -> None:
    reply = edit([("a", 0, 0), ("b", 1, 1), ("c", 2, 2)])
    reply.sections.append(EditedSection(id="chorus-1", kind="chorus"))
    reply.lines[1].section = "chorus-1"
    assert edit_problems(reply, 3) == ["section 'verse-1': its lines are not one run; keep them together"]
    reply.lines[2].section = "chorus-1"
    reply.sections.reverse()
    assert edit_problems(reply, 3) == [
        "the lines' sections come in the order ['verse-1', 'chorus-1'], not the order of sections"
    ]


def test_heard_words_are_tidied() -> None:
    times = [(1000, 1620), (1600, 1600), (1600, 2000), (4990, 4990)]
    words = [hmv.Word(text="w", start_ms=a, end_ms=b) for a, b in times]
    assert [(w.start_ms, w.end_ms) for w in tidy(words)] == [
        (1000, 1600),
        (1600, 1601),
        (1601, 2000),
        (4990, 4991),
    ]
    late = [*words, hmv.Word(text="x", start_ms=5000, end_ms=5000)]
    assert [(w.start_ms, w.end_ms) for w in tidy(late, 4995)] == [
        (1000, 1600),
        (1600, 1601),
        (1601, 2000),
        (4990, 4991),
    ]
    assert [(w.start_ms, w.end_ms) for w in tidy(words, 4991)][-1] == (4990, 4991)
