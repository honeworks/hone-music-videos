"""The owner's timing at the lyrics gate (0018, D-113 to D-116): edits applied by line id, words scaled
within their line, sections and instrumental spans adjusted, every problem refused by name, edits that no
longer fit dropped with why, and `check_lyrics` not holding an owner-timed line to its words."""

from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.owner_timing import LineTimes, apply_timing, parse_changes, parse_spec
from hone_music_video.records import Instrumental


def words(start: int, *texts: str) -> list[dict[str, Any]]:
    return [
        {"text": t, "start_ms": start + 1000 * n, "end_ms": start + 1000 * n + 750}
        for n, t in enumerate(texts)
    ]


BASE = hmv.Timeline.model_validate(
    {
        "duration_ms": 20_000,
        "sections": [
            {"id": "verse-1", "kind": "verse", "start_ms": 2000, "end_ms": 7750},
            {"id": "chorus-1", "kind": "chorus", "start_ms": 8000, "end_ms": 17750},
        ],
        "lines": [
            {"id": "L001", "section": "verse-1", "text": "a b c d e f", "start_ms": 2000, "end_ms": 7750,
             "words": words(2000, *"abcdef"), "heard_first": 0, "heard_last": 5},
            {"id": "L002", "section": "chorus-1", "text": "g h i j k l", "start_ms": 8000, "end_ms": 13750,
             "words": words(8000, *"ghijkl"), "heard_first": 6, "heard_last": 11},
            {"id": "L003", "section": "chorus-1", "text": "m n o p", "start_ms": 14000, "end_ms": 17750,
             "words": words(14000, *"mnop"), "heard_first": 12, "heard_last": 15},
        ],
        "instrumental": [
            {"start_ms": 0, "end_ms": 2000, "kind": "intro"},
            {"start_ms": 17750, "end_ms": 20000, "kind": "outro"},
        ],
    }
)  # fmt: skip


def times(start: int, end: int) -> LineTimes:
    return LineTimes(start_ms=start, end_ms=end)


def test_a_lines_words_move_with_it_scaled_within_it() -> None:
    timeline, kept, dropped = apply_timing(BASE, {"L002": times(8500, 13000)})
    assert (kept, dropped) == (["L002"], {})
    line = timeline.lines[1]
    assert (line.start_ms, line.end_ms) == (8500, 13000)
    # 5750 ms become 4500: each time from the line's start scaled by 4500 / 5750
    assert [(w.start_ms, w.end_ms) for w in line.words][:2] == [(8500, 9087), (9283, 9870)]
    assert (line.words[-1].start_ms, line.words[-1].end_ms) == (12413, 13000)
    assert [w.text for w in line.words] == list("ghijkl")
    assert timeline.lines[0] == BASE.lines[0] and timeline.lines[2] == BASE.lines[2]  # the others as made
    assert timeline.owner_timed == ["L002"]
    assert timeline.sections[1].model_dump() == {
        "id": "chorus-1",
        "kind": "chorus",
        "start_ms": 8500,
        "end_ms": 17750,
        "notes": "",
    }
    assert timeline.sections[0] == BASE.sections[0]
    assert hmv.check_lyrics(timeline, words_of(BASE)).errors == []


def words_of(timeline: hmv.Timeline) -> hmv.Words:
    """The words the lines were timed from (each line's words, as heard)."""
    return hmv.Words(words=[w for line in timeline.lines for w in line.words])


def test_the_instrumental_spans_next_to_an_edited_line_fill_the_new_gap() -> None:
    timeline, _, _ = apply_timing(BASE, {"L001": times(1500, 7700), "L003": times(14000, 17000)})
    assert [(s.kind, s.start_ms, s.end_ms) for s in timeline.instrumental] == [
        ("intro", 0, 1500),
        ("outro", 17000, 20000),
    ]
    assert (timeline.sections[0].start_ms, timeline.sections[0].end_ms) == (1500, 7700)
    assert (timeline.sections[1].start_ms, timeline.sections[1].end_ms) == (8000, 17000)
    covered, _, _ = apply_timing(BASE, {"L001": times(0, 7750)})
    assert [s.kind for s in covered.instrumental] == ["outro"]  # no gap is left before the first line


def test_edits_that_do_not_fit_are_dropped_with_why() -> None:
    edits = {
        "L009": times(1, 2),
        "L001": times(3000, 3000),
        "L002": times(8000, 14500),  # into L003, which was not edited
        "L003": times(19000, 21000),
    }
    timeline, kept, dropped = apply_timing(BASE, edits)
    assert kept == [] and timeline.lines == BASE.lines and timeline.owner_timed == []
    assert dropped == {
        "L009": "L009: there is no line L009 now",
        "L001": "L001: starts at 0:03.000, not before its end 0:03.000",
        "L002": "L003 starts 500 ms before L002 ends",
        "L003": "L003: ends at 0:21.000, after the song ends (0:20.000)",
    }


def test_two_edits_that_fit_together_are_both_kept() -> None:
    moved = {"L002": times(8000, 14500), "L003": times(14500, 18000)}
    timeline, kept, dropped = apply_timing(BASE, moved)
    assert (kept, dropped) == (["L002", "L003"], {})
    assert [s.kind for s in timeline.instrumental] == ["intro", "outro"]
    assert timeline.instrumental[1].start_ms == 18000


def test_an_owner_timed_line_is_not_held_to_its_words() -> None:
    timeline, _, _ = apply_timing(BASE, {"L002": times(8600, 13000)})
    heard = words_of(BASE)
    assert hmv.check_lyrics(timeline, heard).errors == []
    unmarked = timeline.model_copy(update={"owner_timed": []})
    assert [(p.rule, p.where) for p in hmv.check_lyrics(unmarked, heard).errors] == [
        ("moved", "L002"),
        ("moved", "L002"),
    ]


def test_an_older_timeline_has_no_owner_times() -> None:
    data = BASE.model_dump(mode="json")
    del data["owner_timed"]
    assert hmv.Timeline.model_validate(data).owner_timed == []


def test_the_changes_are_read_strictly() -> None:
    assert parse_changes({"L001": {"start_ms": 1, "end_ms": 2}, "L002": None}) == {
        "L001": times(1, 2),
        "L002": None,
    }
    for bad in ({"L001": {"start_ms": 1.5, "end_ms": 2}}, {"L001": {"start_ms": "1", "end_ms": 2}},
                {"L001": {"start_ms": True, "end_ms": 2}}, {"L001": {"start_ms": -1, "end_ms": 2}},
                {"L001": {"start_ms": 1}}, {"L001": {"start_ms": 1, "end_ms": 2, "x": 3}}):  # fmt: skip
        with pytest.raises(hmv.InvalidInput, match="L001: give start_ms and end_ms as whole milliseconds"):
            parse_changes(bad)
    for empty in ({}, [], None, "L001"):
        with pytest.raises(hmv.InvalidInput, match="send the timing as"):
            parse_changes(empty)


def test_the_cli_spec() -> None:
    assert parse_spec(["L012=77300-81200", "L013=-"]) == {
        "L012": {"start_ms": 77300, "end_ms": 81200},
        "L013": None,
    }
    for bad in ("L012", "L012=77.3-81.2", "L012=81200", "=1-2", "L012=-1-2"):
        with pytest.raises(hmv.InvalidInput, match="write LINE=START-END in milliseconds"):
            parse_spec([bad])


def test_a_span_between_two_edited_lines_fills_their_gap_or_goes() -> None:
    middle = BASE.model_copy(
        update={"instrumental": [*BASE.instrumental, Instrumental(start_ms=7750, end_ms=8000, kind="break")]}
    )
    timeline, _, _ = apply_timing(middle, {"L001": times(2000, 7000), "L002": times(9000, 13750)})
    assert [(s.kind, s.start_ms, s.end_ms) for s in timeline.instrumental][2] == ("break", 7000, 9000)
    closed, kept, _ = apply_timing(middle, {"L001": times(2000, 8000)})
    assert kept == ["L001"] and [s.kind for s in closed.instrumental] == ["intro", "outro"]


def test_a_line_shorter_than_its_words_keeps_them_in_order_inside_it() -> None:
    timeline, _, _ = apply_timing(BASE, {"L002": times(8000, 8004)})
    spans = [(w.start_ms, w.end_ms) for w in timeline.lines[1].words]
    assert all(8000 <= a < b <= 8004 for a, b in spans)
    assert [a for a, _ in spans] == sorted(a for a, _ in spans)
