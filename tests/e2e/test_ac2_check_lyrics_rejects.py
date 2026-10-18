"""AC-2: `check_lyrics` rejects overlapping lines, times outside the song and moved lines (design §5.1,
§14; D-003). What a run does with the errors (the gate refuses approval, D-015) is in
`tests/unit/test_reject.py`."""

import pytest

import hone_music_video as hmv

pytestmark = pytest.mark.e2e
HEARD = hmv.Words(
    words=[
        hmv.Word(text=t, start_ms=a, end_ms=b)
        for t, a, b in [("she", 1000, 1600), ("waits", 1500, 2000), ("wind", 3000, 3500)]
    ]
)


def timeline(*lines: tuple[int, int, int, int], duration_ms: int = 4000) -> hmv.Timeline:
    return hmv.Timeline.model_validate(
        {
            "duration_ms": duration_ms,
            "sections": [{"id": "v", "kind": "verse", "start_ms": 0, "end_ms": duration_ms}],
            "lines": [
                {
                    "id": f"L{n:03d}",
                    "section": "v",
                    "text": "x",
                    "start_ms": a,
                    "end_ms": b,
                    "words": [],
                    "heard_first": first,
                    "heard_last": last,
                }
                for n, (a, b, first, last) in enumerate(lines, 1)
            ],
        }
    )


def errors(report: hmv.Report) -> list[tuple[str, str]]:
    return [(p.rule, p.where) for p in report.errors]


def test_a_timeline_from_its_heard_words_passes() -> None:
    assert hmv.check_lyrics(timeline((1000, 1600, 0, 0), (3000, 3500, 2, 2)), HEARD).errors == []


def test_overlapping_lines_are_rejected() -> None:
    report = hmv.check_lyrics(timeline((1000, 1600, 0, 0), (1500, 2000, 1, 1)), HEARD)
    assert errors(report) == [("overlap", "L002")]
    assert report.errors[0].message == "starts 100 ms before L001 ends"


def test_times_outside_the_song_are_rejected() -> None:
    report = hmv.check_lyrics(timeline((1000, 1600, 0, 0), (3000, 3500, 2, 2), duration_ms=3400), HEARD)
    assert ("outside-song", "L002") in errors(report)


@pytest.mark.parametrize(("shift", "rejected"), [(150, False), (151, True), (-400, True)])
def test_moved_lines_are_rejected(shift: int, rejected: bool) -> None:
    report = hmv.check_lyrics(timeline((1000 + shift, 1600 + shift, 0, 0)), HEARD)
    assert (("moved", "L001") in errors(report)) is rejected
