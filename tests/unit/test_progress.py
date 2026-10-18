"""The progress function (0003, D-051, D-052): units done of total, the current unit, the time left from
this run's measured times ("estimating" until two units), the model load, and the overall estimate."""

import pytest

from hone_music_video.progress import (
    DEFAULT_MS,
    Current,
    Timed,
    Work,
    averages,
    clip_default,
    load_ms,
    overall,
    stage_progress,
)

STILLS = {"raw_clip": 3, "clip": 4}  # a stage of two kinds of unit


def test_a_stage_is_estimating_until_two_units_of_this_run_are_measured() -> None:
    one = Work("stills", STILLS, {"raw_clip": 1}, [Timed("raw_clip", 130_000, first=True)], started_ms=0)
    found = stage_progress(one, now_ms=150_000)
    assert (found.done, found.total, found.elapsed_ms) == (1, 7, 150_000)
    assert found.left_ms is None and not found.estimate  # "estimating…"
    assert found.per_unit_ms == {"raw_clip": 130_000}


def test_the_time_left_is_the_remaining_units_at_this_runs_measured_times() -> None:
    """Two drafts of 100 s (the first also loaded the model for 30 s): one draft left at 100 s, and the
    four stills at §15's time, so the result is an estimate."""
    timed = [Timed("raw_clip", 130_000, first=True), Timed("raw_clip", 100_000)]
    work = Work("stills", STILLS, {"raw_clip": 2}, timed, started_ms=0)
    found = stage_progress(work, now_ms=230_000)
    assert found.left_ms == 100_000 + 4 * DEFAULT_MS["clip"]
    assert found.estimate
    assert found.load_ms == 30_000
    assert found.per_unit_ms == {"raw_clip": 100_000}


def test_a_stage_whose_every_kind_is_measured_is_not_an_estimate() -> None:
    timed = [Timed("raw_clip", 200_000, first=True), Timed("raw_clip", 180_000), Timed("raw_clip", 220_000)]
    work = Work("clips", {"raw_clip": 5}, {"raw_clip": 3}, timed, started_ms=0)
    found = stage_progress(work, now_ms=600_000)
    assert (found.left_ms, found.estimate) == (2 * 200_000, False)
    assert found.load_ms == 0  # the first clip was no slower than the others


def test_the_time_spent_on_the_current_unit_is_taken_off() -> None:
    timed = [Timed("clip", 80_000, first=True), Timed("clip", 80_000)]
    current = Current("clip", "S003", 3, started_ms=500_000)
    work = Work("finish", {"clip": 4}, {"clip": 2}, timed, started_ms=0, current=current)
    assert stage_progress(work, now_ms=530_000).left_ms == 2 * 80_000 - 30_000
    late = stage_progress(work, now_ms=700_000)  # slower than the average: never less than the rest
    assert late.left_ms == 80_000
    assert late.current == current


def test_a_stopped_stage_spends_no_time_on_its_current_unit() -> None:
    """A failed or interrupted stage still names the unit it stopped on, but its time is not running."""
    timed = [Timed("clip", 80_000, first=True), Timed("clip", 80_000)]
    current = Current("clip", "S003", 3, started_ms=500_000)
    work = Work("finish", {"clip": 4}, {"clip": 2}, timed, started_ms=0, current=current, running=False)
    found = stage_progress(work, now_ms=530_000)
    assert found.left_ms == 2 * 80_000 and found.current == current
    assert overall([work], now_ms=530_000).left_ms == 2 * 80_000  # type: ignore[union-attr]


def test_averages_leave_out_model_loads_when_warm_units_exist() -> None:
    timed = [Timed("raw_clip", 150_000, True), Timed("clip", 40_000, True), Timed("raw_clip", 100_000)]
    assert averages(timed) == {"raw_clip": 100_000, "clip": 40_000}
    assert load_ms(timed) == 50_000  # the still's load is not known: it has no warm unit
    assert load_ms([Timed("clip", 40_000, True)]) is None


def test_overall_uses_measured_times_and_marks_defaults_as_an_estimate() -> None:
    """The clips are measured (100 s each, two of four made); finish and assembly take §15's times."""
    timed = [Timed("raw_clip", 100_000), Timed("raw_clip", 100_000)]
    clips = Work("clips", {"raw_clip": 4}, {"raw_clip": 2}, timed, started_ms=0)
    finish = Work("finish", {"clip": 4}, {})
    assemble = Work("assemble", {"assembly": 1}, {}, defaults={"assembly": 5_000})
    found = overall([clips, finish, assemble], now_ms=0)
    assert found is not None
    left = 2 * 100_000 + 4 * DEFAULT_MS["clip"] + 5_000
    assert found.left_ms == left and found.estimate
    done = 2 * 100_000
    assert found.fraction == pytest.approx(done / (done + left))
    assert found.stages == ["clips", "finish", "assemble"]


def test_overall_with_everything_measured_is_not_an_estimate() -> None:
    timed = [Timed("clip", 90_000), Timed("clip", 90_000)]
    finish = Work("finish", {"clip": 3}, {"clip": 2}, timed)
    found = overall([finish], now_ms=0)
    assert found is not None and (found.left_ms, found.estimate) == (90_000, False)
    assert overall([], now_ms=0) is None


def test_a_clips_default_weighs_the_shots_with_faces() -> None:
    assert clip_default(faces=1, plain=1) == (318_000 + DEFAULT_MS["raw_clip"]) // 2
    assert clip_default(0, 0) == 0
