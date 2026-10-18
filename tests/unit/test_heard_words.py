"""`heard_words`: hone-models' transcript as integer milliseconds, tidied (D-017)."""

import hone_models as mk

from hone_music_video.adapters import hone_models as adapter


def test_heard_words_never_overlap_and_always_have_length() -> None:
    times = [("a", 1.0, 1.62), ("b", 1.6, 1.6), ("c", 1.6, 2.0), ("d", 2.5, 2.4)]
    transcript = mk.Transcript(
        text="",
        language="fa",
        duration_s=3.0,
        segments=[],
        model="whisper-1",
        span_id="",
        words=[mk.Word(t, a, b) for t, a, b in times],
    )
    words = adapter.heard_words(transcript)
    assert [(w.start_ms, w.end_ms) for w in words.words] == [
        (1000, 1600),
        (1600, 1601),
        (1601, 2000),
        (2500, 2501),
    ]
    assert words.language == "fa" and words.call is None
