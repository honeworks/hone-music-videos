"""`check_lyrics` (design §5.1): every error and warning, with where, the rule and by how much."""

from typing import Any

import hone_music_video as hmv

HEARD = hmv.Words(
    words=[
        hmv.Word(text=t, start_ms=a, end_ms=b)
        for t, a, b in [("she", 1000, 1400), ("waits", 1500, 1900), ("um", 2000, 2100), ("wind", 3000, 3500)]
    ]
)


def line(n: int, start: int, end: int, first: int | None, last: int | None, **more: Any) -> dict[str, Any]:
    words = more.pop("words", [{"text": "w", "start_ms": start, "end_ms": end}])
    base = {"id": f"L{n:03d}", "section": "verse-1", "text": more.pop("text", "w"), "words": words}
    return base | {"start_ms": start, "end_ms": end, "heard_first": first, "heard_last": last} | more


def timeline(lines: list[dict[str, Any]], **more: Any) -> hmv.Timeline:
    data = {
        "duration_ms": 4000,
        "sections": [{"id": "verse-1", "kind": "verse", "start_ms": 1000, "end_ms": 3500}],
        "lines": lines,
        "instrumental": [],
    }
    return hmv.Timeline.model_validate(data | more)


def rules(report: hmv.Report) -> list[tuple[str, str]]:
    return [(p.rule, p.where) for p in report.errors]


GOOD = [line(1, 1000, 1900, 0, 1, text="she waits"), line(2, 3000, 3500, 3, 3, text="wind")]


def test_a_timeline_from_heard_words_passes() -> None:
    report = hmv.check_lyrics(timeline(GOOD), HEARD, "she waits\nthe wind")
    assert report.errors == []
    assert [(p.rule, p.where, p.message) for p in report.warnings] == [
        ("heard-unused", "heard words 2..2", "'um' at 0:02.000 is in no line"),
        ("lyrics-not-found", "given lyrics", "'the wind' was not found in the audio"),
    ]


def test_moved_lines_are_rejected_beyond_150_ms() -> None:
    near = [line(1, 1150, 1750, 0, 1, words=[]), GOOD[1]]
    assert hmv.check_lyrics(timeline(near), HEARD).errors == []
    moved = [line(1, 1151, 1900, 0, 1, words=[]), line(2, 3000, 3700, 3, 3, words=[])]
    errors = hmv.check_lyrics(timeline(moved, duration_ms=4000), HEARD).errors
    assert [(p.rule, p.where) for p in errors] == [
        ("moved", "L001"),
        ("moved", "L002"),
        ("section-cover", "L002"),
    ]
    assert "start 0:01.151 is 151 ms from heard word 0 ('she' at 0:01.000)" in errors[0].message
    assert "end 0:03.700 is 200 ms from heard word 3" in errors[1].message


def test_lines_must_come_from_heard_words() -> None:
    errors = hmv.check_lyrics(
        timeline([line(1, 1000, 1900, None, None), line(2, 3000, 3500, 3, 9)]), HEARD
    ).errors
    assert rules(hmv.Report(errors=errors)) == [("not-heard", "L001"), ("not-heard", "L002")]


def test_overlaps_and_times_outside_the_song_are_rejected() -> None:
    lines = [line(1, 1000, 1900, 0, 1), line(2, 1500, 1500, 1, 1), line(3, 3000, 4100, 3, 3)]
    report = hmv.check_lyrics(timeline(lines), HEARD)
    found = {(p.rule, p.where): p.message for p in report.errors}
    assert found[("overlap", "L002")] == "starts 400 ms before L001 ends"
    assert found[("no-length", "L002")] == "starts at 0:01.500, not before its end 0:01.500"
    assert found[("outside-song", "L003")] == "ends at 0:04.100, 100 ms after the song ends (0:04.000)"


def test_words_lie_inside_their_line_in_order() -> None:
    words = [{"text": "b", "start_ms": 1500, "end_ms": 1900}, {"text": "a", "start_ms": 900, "end_ms": 1400}]
    report = hmv.check_lyrics(timeline([line(1, 1000, 1900, 0, 1, words=words)]), HEARD)
    assert rules(report) == [("word-outside-line", "L001 word 2 (a)"), ("word-order", "L001 word 2 (a)")]
    assert report.errors[1].message == "starts 600 ms before the word before it"


def test_sections_cover_the_lines_and_instrumental_spans_avoid_them() -> None:
    lines = [line(1, 1000, 1900, 0, 1, section="chorus"), GOOD[1]]
    spans = [
        {"start_ms": 0, "end_ms": 1200, "kind": "intro"},
        {"start_ms": 3500, "end_ms": 4000, "kind": "outro"},
    ]
    sections = [{"id": "verse-1", "kind": "verse", "start_ms": 3200, "end_ms": 3500}]
    report = hmv.check_lyrics(timeline(lines, instrumental=spans, sections=sections), HEARD)
    assert rules(report) == [
        ("no-section", "L001"),
        ("section-cover", "L002"),
        ("instrumental-overlap", "instrumental 1 (intro)"),
    ]
    assert report.errors[2].message == "overlaps sung line L001 by 200 ms"


def test_overlapping_sections_are_rejected() -> None:
    sections = [
        {"id": "verse-1", "kind": "verse", "start_ms": 1000, "end_ms": 1900},
        {"id": "chorus-1", "kind": "chorus", "start_ms": 1800, "end_ms": 3500},
    ]
    report = hmv.check_lyrics(timeline(GOOD, sections=sections), HEARD)
    assert [(p.rule, p.where, p.message) for p in report.errors] == [
        ("section-cover", "L002", "lies outside its section verse-1 (0:01.000-0:01.900)"),
        ("section-overlap", "chorus-1", "starts 100 ms before section verse-1 ends"),
    ]
