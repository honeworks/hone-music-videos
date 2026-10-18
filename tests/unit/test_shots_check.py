"""`check_shots` (design §5.2): every error and warning, each with the shot, the rule and by how much."""

import itertools
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

import hone_music_video as hmv
from hone_music_video.pace import shot_range
from hone_music_video.prompt_words import words_of_speech
from hone_music_video.shots_check import MOTION_PROMPT_CHARS, STILL_PROMPT_CHARS

SETTINGS = hmv.Settings()  # shots of 2000 to 8000 ms


def words(*spans: tuple[str, int, int]) -> list[dict[str, Any]]:
    return [{"text": t, "start_ms": a, "end_ms": b} for t, a, b in spans]


TIMELINE = hmv.Timeline.model_validate(
    {
        "duration_ms": 20_000,
        "sections": [{"id": "verse-1", "kind": "verse", "start_ms": 2000, "end_ms": 9000}],
        "lines": [
            {"id": "L001", "section": "verse-1", "text": "she waits upon", "start_ms": 2000, "end_ms": 5000,
             "words": words(("she", 2000, 2500), ("waits", 2600, 3200), ("upon", 3300, 5000))},
            {"id": "L002", "section": "verse-1", "text": "the wind", "start_ms": 6000, "end_ms": 9000,
             "words": words(("the", 6000, 6400), ("wind", 6500, 9000))},
        ],
        "instrumental": [{"start_ms": 0, "end_ms": 2000, "kind": "intro"},
                         {"start_ms": 9000, "end_ms": 20_000, "kind": "outro"}],
    }
)  # fmt: skip
CAST = ["celina", "darvin"]  # the characters of the plan (0027)


def shot(n: int, start: int, end: int, **more: Any) -> dict[str, Any]:
    cast = more.get("cast", [])
    return {
        "id": f"S{n:03d}",
        "start_ms": start,
        "end_ms": end,
        "lines": [],
        "beat": "a beat",
        "framing": "medium" if cast else "wide",
        "faces": bool(cast),
        "cast": cast,
        "location": "a balcony",
        "camera": "static camera",
        "still_prompt": " and ".join(f"the {c} from image {n}" for n, c in enumerate(cast, 1))
        or "An empty balcony at dusk.",
        "motion_prompt": "Static camera. The veil lifts in the wind.",
    } | more


GOOD = [
    shot(1, 0, 2000, framing="extreme-wide"),
    shot(2, 2000, 6000, lines=["L001"], cast=["celina"], framing="close-up"),
    shot(3, 6000, 9000, lines=["L002"], cast=["celina", "darvin"]),
    shot(4, 9000, 15_000, cast=["celina"], framing="wide", faces=False),
    shot(5, 15_000, 20_000, cast=["darvin"], framing="extreme-wide", faces=False),
]


def check(plan: list[dict[str, Any]], settings: hmv.Settings = SETTINGS) -> hmv.Report:
    return hmv.check_shots(hmv.Shots.model_validate({"shots": plan}), TIMELINE, CAST, settings)


def found(problems: list[hmv.Problem]) -> dict[tuple[str, str], str]:
    return {(p.rule, p.where): p.message for p in problems}


def test_a_plan_that_tiles_the_song_passes() -> None:
    report = check(GOOD)
    assert report.errors == []
    assert found(report.warnings) == {
        ("far-cut", "S005"): "the cut at 0:15.000 is 5000 ms from the nearest line start or end, section "
        "start, instrumental edge or end of the song (0:20.000); at most 120 ms is preferred",
    }


def test_gaps_overlaps_and_the_ends_of_the_song_are_errors() -> None:
    plan = [shot(1, 100, 2000), shot(2, 2300, 6000, lines=["L001"]), shot(3, 5500, 9000, lines=["L002"])]
    plan += [shot(4, 9000, 15_000), shot(5, 15_000, 19_000)]
    errors = found(check(plan).errors)
    assert errors[("song-start", "S001")] == "starts at 0:00.100, not at 0:00.000 (100 ms late)"
    assert errors[("gap", "S002")] == "starts 300 ms after S001 ends (0:02.000): a gap"
    assert errors[("overlap", "S003")] == "starts 500 ms before S002 ends (0:06.000): an overlap"
    assert errors[("song-end", "S005")] == "ends at 0:19.000, 1000 ms before the song ends (0:20.000)"


def test_a_plan_past_the_song_or_without_shots_is_an_error() -> None:
    late = check([*GOOD[:4], shot(5, 15_000, 20_500)]).errors
    assert found(late)[("song-end", "S005")] == "ends at 0:20.500, 500 ms after the song ends (0:20.000)"
    empty = [(p.rule, p.where) for p in check([]).errors]
    assert empty == [("song-end", "plan"), ("line-unlisted", "L001"), ("line-unlisted", "L002")]


def test_shots_outside_the_length_limits_are_errors() -> None:
    plan = [shot(1, 0, 1500), shot(2, 1500, 2000), *GOOD[1:3], shot(4, 9000, 20_000)]
    errors = found(check(plan).errors)
    assert errors[("length", "S001")] == "lasts 1500 ms, 500 ms shorter than the shortest shot (2000 ms)"
    assert errors[("length", "S004")] == "lasts 11000 ms, 3000 ms longer than the longest shot (8000 ms)"
    zero = found(check([shot(1, 0, 0), *GOOD]).errors)
    assert zero[("length", "S001")] == "lasts 0 ms, 2000 ms shorter than the shortest shot (2000 ms)"


def test_a_cut_inside_a_sung_word_is_an_error() -> None:
    plan = [GOOD[0], shot(2, 2000, 6200, lines=["L001", "L002"]), shot(3, 6200, 9000, lines=["L002"])]
    errors = found(check([*plan, *GOOD[3:]]).errors)
    assert errors == {
        ("cut-in-word", "S003"): "starts at 0:06.200, inside the sung word 'the' of L002 "
        "(0:06.000-0:06.400), 200 ms after it starts and 200 ms before it ends"
    }
    between = [GOOD[0], shot(2, 2000, 6450, lines=["L001", "L002"]), shot(3, 6450, 9000, lines=["L002"])]
    assert check([*between, *GOOD[3:]]).errors == []  # between two words of a line is a fine cut


def test_lines_and_shots_must_overlap_both_ways() -> None:
    plan = [shot(1, 0, 2000, lines=["L002", "L404"]), shot(2, 2000, 6000), *GOOD[2:]]
    report = check(plan)
    errors = found(report.errors)
    assert (
        errors[("line-outside", "S001")]
        == "lists L002 (0:06.000-0:09.000), which is sung 4000 ms after the shot ends"
    )
    assert errors[("unknown-line", "S001")] == "lists L404, which is not a line of the timeline"
    assert (
        errors[("line-unlisted", "S002")]
        == "L001 (0:02.000-0:05.000) is sung during S002 but no shot lists it"
    )


def test_an_unknown_cast_is_an_error() -> None:
    plan = [*GOOD[:3], shot(4, 9000, 15_000, cast=["loren"], framing="wide", faces=False), GOOD[4]]
    errors = found(check(plan).errors)
    assert errors == {("unknown-cast", "S004"): "names loren, who is not a character (celina, darvin)"}


@pytest.mark.parametrize("framing", ["extreme-wide", "wide", "insert"])
def test_recognisable_faces_need_a_medium_shot_or_closer(framing: str) -> None:
    plan = [*GOOD[:3], GOOD[3] | {"framing": framing, "faces": True}, GOOD[4]]
    assert found(check(plan).errors) == {
        ("faces", "S004"): f"faces is true on a {framing} shot; a recognisable face needs a medium shot, "
        "close-up or extreme close-up"
    }


def test_prompts_must_be_written_and_fit_their_model() -> None:
    plan = [GOOD[0] | {"still_prompt": "  "}, GOOD[1] | {"motion_prompt": "m" * (MOTION_PROMPT_CHARS + 1)}]
    plan += [GOOD[2] | {"still_prompt": "{celina} " + "s" * STILL_PROMPT_CHARS}, *GOOD[3:]]
    errors = found(check(plan).errors)
    assert errors[("empty-prompt", "S001")] == "the still prompt is empty"
    over = MOTION_PROMPT_CHARS + 1
    assert errors[("prompt-length", "S002")] == (
        f"the motion prompt has {over} characters, 1 over the limit of {MOTION_PROMPT_CHARS}"
    )
    assert errors[("prompt-length", "S003")].startswith(
        f"the still prompt has {STILL_PROMPT_CHARS + 9} characters"
    )


def test_the_same_framing_three_times_in_a_row_is_a_warning() -> None:
    medium = {"framing": "medium", "faces": True}
    plan = [GOOD[0] | {"framing": "wide"}, GOOD[1] | medium, GOOD[2], GOOD[3] | medium, GOOD[4]]
    warnings = found(check(plan).warnings)
    assert warnings[("same-framing", "S002")] == "S002 to S004 are all medium shots (3 in a row)"


def test_a_character_missing_for_a_third_of_the_song_is_a_warning() -> None:
    plan = [*GOOD[:4], GOOD[4] | {"cast": [], "still_prompt": "Dust on an empty plain."}]
    warnings = found(check(plan).warnings)
    assert warnings[("character-missing", "S004")] == (
        "darvin is not seen from 0:09.000 to 0:20.000 (11000 ms, more than a third of the song)"
    )


# ------------------------------------------------------------------------------ properties (guarantee 6)


# times outside every sung word of TIMELINE: any of them is a fine cut
FREE = (2000, 2500, 2600, 3200, 3300, 5000, 6000, 6400, 6500, 9000, 12_000, 15_000, 18_000)
LOOSE = hmv.Settings(min_shot_ms=1, max_shot_ms=20_000)  # only the times are judged


@st.composite
def plans(draw: st.DrawFn) -> tuple[list[tuple[int, int]], bool]:
    """A tiling of the song cut at free times, and whether one time was then moved: the first start, a
    cut (the start of a later shot) or the last end."""
    cuts = sorted(draw(st.sets(st.sampled_from(FREE), max_size=8)))
    starts, ends = [0, *cuts], [*cuts, 20_000]
    where = draw(st.sampled_from(["none", "start", "cut", "end"]))
    by = draw(st.integers(-300, 300).filter(bool))
    if where == "start":
        starts[0] = max(0, by)
    elif where == "cut" and len(starts) > 1:
        starts[draw(st.integers(1, len(starts) - 1))] += by
    elif where == "end":
        ends[-1] += by
    moved = (starts, ends) != ([0, *cuts], [*cuts, 20_000])
    return list(zip(starts, ends, strict=True)), moved


@given(plans())
def test_a_plan_passes_exactly_when_it_tiles_the_song(drawn: tuple[list[tuple[int, int]], bool]) -> None:
    spans, moved = drawn
    plan = [shot(n, a, b) for n, (a, b) in enumerate(spans, 1)]
    for row in plan:  # list every line the shot overlaps, so only the times are judged
        row["lines"] = [
            ln.id for ln in TIMELINE.lines if ln.start_ms < row["end_ms"] and ln.end_ms > row["start_ms"]
        ]
    errors = check(plan, LOOSE).errors
    tiles = plan[0]["start_ms"] == 0 and plan[-1]["end_ms"] == TIMELINE.duration_ms
    tiles = tiles and all(a["end_ms"] == b["start_ms"] for a, b in itertools.pairwise(plan))
    assert tiles != moved
    assert (errors == []) == tiles, errors


@pytest.mark.parametrize(("start", "end", "amount"), [(0, 1999, "1 ms shorter"), (0, 8001, "1 ms longer")])
def test_one_millisecond_outside_the_length_limits_is_an_error(start: int, end: int, amount: str) -> None:
    errors = check([shot(1, start, end), shot(2, end, 20_000)]).errors
    assert any(p.rule == "length" and p.where == "S001" and amount in p.message for p in errors)


def test_a_shot_of_exactly_the_longest_length_passes() -> None:
    plan = [GOOD[0], GOOD[1] | {"end_ms": 10_000}, shot(3, 10_000, 18_000), shot(4, 18_000, 20_000)]
    assert [p for p in check(plan).errors if p.rule == "length"] == []  # S002 and S003 last 8000 ms


@pytest.mark.parametrize(
    ("cut", "inside"),
    [
        (6001, "1 ms after it starts and 399 ms before it ends"),
        (6399, "399 ms after it starts and 1 ms before it ends"),
        (6000, None),
        (6400, None),
    ],
)
def test_a_cut_one_millisecond_inside_a_word_is_an_error(cut: int, inside: str | None) -> None:
    plan = [
        GOOD[0],
        shot(2, 2000, cut, lines=["L001", "L002"]),
        shot(3, cut, 9000, lines=["L002"]),
        *GOOD[3:],
    ]
    found = [p.message for p in check(plan).errors if p.rule == "cut-in-word"]
    if inside is None:
        assert found == []  # the word's own edge is a fine cut
    else:
        assert found == [
            f"starts at 0:06.{cut % 1000:03d}, inside the sung word 'the' of L002 (0:06.000-0:06.400), "
            f"{inside}"
        ]


def test_a_cut_at_a_line_end_is_near_enough() -> None:
    plan = [
        GOOD[0],
        shot(2, 2000, 5000, lines=["L001"], cast=["celina"]),
        shot(3, 5000, 9000, lines=["L002"]),
    ]
    plan += [shot(4, 9000, 15_000, cast=["celina", "darvin"]), GOOD[4]]
    assert ("far-cut", "S003") not in found(check(plan).warnings)  # L001 ends at 0:05.000


def test_shot_ids_are_unique_and_numbered() -> None:
    plan = [GOOD[0], GOOD[1] | {"id": "S001"}, GOOD[2] | {"id": "shot-3"}, *GOOD[3:]]
    errors = found(check(plan).errors)
    assert errors[("shot-id", "S001")] == "the id S001 is used by 2 shots"
    assert errors[("shot-id", "shot-3")] == "the id shot-3 is not S followed by three or more digits (S001)"
    with pytest.raises(ValueError, match="String should match pattern"):
        hmv.Shot.model_validate(GOOD[0] | {"id": "../etc"})  # never a folder path


def test_a_recognisable_face_without_a_cast_is_a_warning() -> None:
    plan = [
        *GOOD[:3],
        GOOD[3] | {"cast": [], "framing": "medium", "faces": True, "still_prompt": "A boy."},
        GOOD[4],
    ]
    warnings = found(check(plan).warnings)
    assert warnings[("faces-without-cast", "S004")] == (
        "faces is true but the shot has no cast: nobody's reference pictures keep that face the same"
    )


def test_quality_errors_can_be_accepted_and_structural_ones_cannot() -> None:
    wide = {"id": "S004", "framing": "wide"}
    plan = [
        shot(1, 0, 1500),
        shot(2, 1500, 2000),
        GOOD[1] | {"id": "S003"},
        GOOD[2] | wide,
        shot(5, 9000, 20_000),
    ]
    plan[1] = plan[1] | {"motion_prompt": "m" * (MOTION_PROMPT_CHARS + 1)}
    report = check(plan)
    assert {p.rule for p in report.errors if p.acceptable} == {"length", "prompt-length", "faces"}
    late = check([GOOD[0], GOOD[1] | {"start_ms": 2100}, *GOOD[2:]])
    assert {p.rule: p.acceptable for p in late.errors} == {"gap": False, "cut-in-word": False}


def test_a_word_longer_than_the_longest_shot_is_named() -> None:
    settings = hmv.Settings(min_shot_ms=500, max_shot_ms=1500)
    errors = check(GOOD, settings).errors
    word = next(p for p in errors if p.rule == "word-longer-than-max-shot")
    assert word.where == "S002" and word.acceptable
    assert word.message.startswith(
        "the sung word 'upon' of L001 (0:03.300-0:05.000) lasts 1700 ms, longer than"
    )


@pytest.mark.parametrize(
    ("prompt", "words"),
    [
        ("She whispers the line to the night.", "'whispers'"),
        ("He sings.", "'sings'"),
        ("She mouths the words; her lips move.", "'mouths the words', 'lips move'"),
        ("SPEAKING softly, he calls out to her and she says his name.", "'speaking', 'calls out', 'says'"),
        ("The priests chant; he recites a prayer; they talk.", "'chant', 'recites', 'talk'"),
    ],
)
def test_a_word_of_speech_is_a_warning(prompt: str, words: str) -> None:
    """No one speaks or sings on screen (0014, D-078): a warning naming the words, never an error."""
    plan = [*GOOD[:3], GOOD[3] | {"motion_prompt": prompt}, GOOD[4] | {"still_prompt": prompt}]
    report = check(plan)
    assert not report.errors
    warnings = found(report.warnings)
    said = f"has {words}: no one speaks or sings (no lip sync); show it in the face"
    assert warnings[("speech", "S005")] == f"the still prompt {said}"
    assert warnings[("speech", "S004")] == (
        f"the motion prompt {said} through what moves (eyes, tears, a turn of the head) and say the face "
        "stays still"
    )


@pytest.mark.parametrize(
    "prompt",
    [
        "She smiles, then laughs.",
        "He shouts a battle cry; a roar; she gasps and cries.",
        "Her eyes glisten, a single tear runs down her cheek; her face stays still.",
    ],
)
def test_expressions_are_not_speech(prompt: str) -> None:
    plan = [*GOOD[:4], GOOD[4] | {"motion_prompt": prompt, "still_prompt": prompt}]
    assert not [p for p in check(plan).warnings if p.rule == "speech"]


@pytest.mark.parametrize(
    ("prompt", "words"),
    [
        (
            "Slow push-in on her face. She keeps her lips closed; her breath trembling. She does not speak.",
            "'lips', 'breath', 'speak'",
        ),
        ("A clenched jaw, teeth bared; his mouth opens without a word.", "'jaw', 'teeth', 'mouth', 'word'"),
        ("He breathes slowly, his voice gone.", "'breathes', 'voice'"),
    ],
)
def test_a_motion_prompt_never_names_the_mouth_not_even_negated(prompt: str, words: str) -> None:
    """D-088: Wan runs at cfg 1, so a negation does nothing and naming the mouth moves it; in a still
    prompt the same words are no warning (the still is drawn, not animated)."""
    plan = [*GOOD[:3], GOOD[3] | {"motion_prompt": prompt}, GOOD[4] | {"still_prompt": prompt}]
    warnings = found(check(plan).warnings)
    assert warnings[("speech", "S004")].startswith(f"the motion prompt has {words}:")
    assert (("speech", "S005") in warnings) == bool(words_of_speech(prompt, motion=False))  # 'speak' only
    assert words_of_speech("Her lips slightly apart at rest.", motion=False) == []


def test_parts_of_other_words_are_not_speech() -> None:
    prompt = "The singer's essay; a talkative crowd; enchanting lamps; the sayings carved in stone."
    plan = [*GOOD[:4], GOOD[4] | {"still_prompt": prompt}]
    assert not [p for p in check(plan).warnings if p.rule == "speech"]


def test_a_calm_pace_warns_on_short_shots_and_an_energetic_one_on_long_shots() -> None:
    """0009, D-084: the pace's shot length, inside the limits, is a warning (never an error); the last
    shot ends with the song and is not warned; a balanced pace warns nothing."""
    calm = found(check(GOOD, hmv.Settings(pace="calm")).warnings)
    assert {where for rule, where in calm if rule == "pace"} == {"S001", "S002", "S003", "S004"}
    assert calm[("pace", "S001")] == "lasts 2000 ms, 4500 ms shorter than the calm pace's 6500-8000 ms"
    assert ("pace", "S004") in calm  # 6000 ms
    energetic = found(check(GOOD, hmv.Settings(pace="energetic")).warnings)
    assert {where for rule, where in energetic if rule == "pace"} == {"S004"}
    assert (
        energetic[("pace", "S004")] == "lasts 6000 ms, 1500 ms longer than the energetic pace's 2000-4500 ms"
    )
    assert not [p for p in check(GOOD).warnings if p.rule == "pace"]
    assert not check(GOOD, hmv.Settings(pace="calm")).errors


def test_the_pace_range_stays_inside_the_shot_limits() -> None:
    assert shot_range(hmv.Settings(pace="calm", max_shot_ms=7000)) == (6500, 7000)
    assert shot_range(hmv.Settings(pace="calm", max_shot_ms=6000)) is None  # the limits win: no pace
    assert not [
        p for p in check(GOOD, hmv.Settings(pace="calm", max_shot_ms=6000)).warnings if p.rule == "pace"
    ]
    assert shot_range(hmv.Settings(pace="energetic", min_shot_ms=3000)) == (3000, 4500)
    assert shot_range(hmv.Settings()) is None
