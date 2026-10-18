"""How far a stage is and when the run should end (0003): pure functions over what a stage has to make
and the units it has made, each with its measured time (D-051, D-052).

A unit is one model-made file. The time left is the remaining units at the time per unit measured in
this run; a kind this run has not measured yet takes the reference machine's time (design §15) and the
result is marked as an estimate. Nothing here reads a file or the clock."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Design §15, the reference machine (RTX 4060 Laptop 8 GB), per unit: used only until this run has
# measured the kind (D-052).
DEFAULT_MS = {
    "raw_clip": 222_000,  # a 5 s clip at 832x480 (318 s at 960x544: see `clip_default`)
    "clip": 84_000,  # finishing a 5 s clip, 73 to 95 s
    "assembly": 77_000,  # 60 shots of 5 s; scaled by the shot count
}
MIN_TIMED = 2  # units of this run before a stage's time left is shown ("estimating" until then)


@dataclass(frozen=True)
class Timed:
    """A unit this run made: its kind, its measured time, and whether it was its model session's first
    (which includes loading the model)."""

    kind: str
    took_ms: int
    first: bool = False


@dataclass(frozen=True)
class Current:
    """The unit being made: its kind, shot or character, its number in the stage, and when it began."""

    kind: str
    subject: str
    n: int
    started_ms: int


@dataclass(frozen=True)
class Work:
    """What a stage has to make (`totals` per kind), what is made (`made`), the units this run of the
    stage made in order (`timed`), when it started, and the unit being made."""

    stage: str
    totals: dict[str, int]
    made: dict[str, int]
    timed: list[Timed] = field(default_factory=list[Timed])
    started_ms: int | None = None
    current: Current | None = None
    defaults: dict[str, int] = field(default_factory=dict[str, int])  # per kind, over DEFAULT_MS
    source: str = "events"  # or "files": a run from before 0003 (D-053)
    running: bool = True  # a failed or interrupted stage spends no more time on its current unit


@dataclass(frozen=True)
class StageProgress:
    """A stage's bar: done of total, elapsed, time left (None while estimating) and how it was got."""

    stage: str
    done: int
    total: int
    elapsed_ms: int | None
    left_ms: int | None
    estimate: bool  # a §15 time went into `left_ms`
    per_unit_ms: dict[str, int]
    load_ms: int | None  # the model load, when the first unit and others are measured
    current: Current | None
    source: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Overall:
    """The long local part of the run: the time left, the share done (by time) and its stages."""

    left_ms: int
    fraction: float
    estimate: bool
    stages: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def averages(timed: list[Timed]) -> dict[str, int]:
    """The measured time per unit of each kind: the mean of the units that loaded no model, or of all
    when only first units are measured."""
    found: dict[str, int] = {}
    for kind in dict.fromkeys(t.kind for t in timed):
        same = [t.took_ms for t in timed if t.kind == kind]
        warm = [t.took_ms for t in timed if t.kind == kind and not t.first] or same
        found[kind] = round(sum(warm) / len(warm))
    return found


def load_ms(timed: list[Timed]) -> int | None:
    """What the first units took over their kind's warm average: the model loads, when known."""
    warm = averages([t for t in timed if not t.first])
    extra = [max(0, t.took_ms - warm[t.kind]) for t in timed if t.first and t.kind in warm]
    return sum(extra) if extra else None


def _each(work: Work, kind: str, measured: dict[str, int]) -> int:
    """One unit's time: measured in this run, else the stage's default, else §15's."""
    return measured.get(kind, work.defaults.get(kind, DEFAULT_MS.get(kind, 0)))


def _left(work: Work, measured: dict[str, int], now_ms: int) -> tuple[int, bool]:
    """The remaining units at the measured times (the defaults where none is measured), less the time
    already spent on the unit being made while the stage runs; and whether a default was used."""
    left, estimate = 0, False
    for kind, total in work.totals.items():
        remaining = max(0, total - work.made.get(kind, 0))
        if remaining and kind not in measured:
            estimate = True
        left += remaining * _each(work, kind, measured)
    if work.current is not None and work.running:
        spent = max(0, now_ms - work.current.started_ms)
        left -= min(_each(work, work.current.kind, measured), spent)
    return max(0, left), estimate


def stage_progress(work: Work, now_ms: int) -> StageProgress:
    """A stage's numbers: the time left only once `MIN_TIMED` units of this run are measured."""
    measured = averages(work.timed)
    left, estimate = _left(work, measured, now_ms)
    shown = len(work.timed) >= MIN_TIMED
    return StageProgress(
        stage=work.stage,
        done=sum(work.made.values()),
        total=sum(work.totals.values()),
        elapsed_ms=now_ms - work.started_ms if work.started_ms is not None else None,
        left_ms=left if shown else None,
        estimate=estimate and shown,
        per_unit_ms=measured,
        load_ms=load_ms(work.timed),
        current=work.current,
        source=work.source,
    )


def overall(works: list[Work], now_ms: int) -> Overall | None:
    """The stages still to finish together: each one's remaining units at the time this run measured
    for the kind (in any stage), else the §15 time (an estimate); the share done weighs units by time."""
    if not works:
        return None
    measured = averages([t for w in works for t in w.timed])
    left, done, estimate = 0, 0, False
    for work in works:
        stage_left, defaulted = _left(work, measured, now_ms)
        left, estimate = left + stage_left, estimate or defaulted
        for kind, made in work.made.items():
            done += made * _each(work, kind, measured)
    whole = done + left
    return Overall(left, done / whole if whole else 1.0, estimate, [w.stage for w in works])


def clip_default(faces: int, plain: int) -> int:
    """§15's time for a raw clip, weighed by how many shots have faces (the larger size)."""
    count = faces + plain
    return round((faces * 318_000 + plain * DEFAULT_MS["raw_clip"]) / count) if count else 0
