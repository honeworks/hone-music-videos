"""What a video cost (design §13.5, D-062): the hosted calls' recorded prices and every stage's time, from
what is already recorded, never estimated here.

- **Time:** every attempt of every stage in every run of the project, from hone-flow's step records
  (a stage a fork copied is not counted again), in integer ms, by where the stage runs (GPU, CPU, hosted).
- **Transcription:** each `transcribe` attempt's `words.json` (`HostedCall.cost_usd` of the call and of
  every listen again, D-002), a retired attempt's from `attempts/<n>/output/`; a failed attempt is one
  unknown call.
- **Planners:** the `hone.models.chat` spans of hone-models' store within the project's time. A span
  naming one of the project's runs is that run's stage's (D-061); the time only picks the attempt (none
  matches: the stage's latest). A run that no span names (made before 0007) gets the spans without a
  run that started during an attempt of its planner stages. A planner attempt with no call found (no
  store, or no span) counts one unknown call.
- **Pictures:** made on local models only since 0027 (the frame run): their time is the scenes stage's.
- **Parts:** an attempt is the `first` pass, a `rerun` (an attempt after a rejected gate or a failure)
  or a `redo` (in a fork of the run: a redone shot, assembling again)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import hone_flow as fk
import hone_models as mk
from pydantic import BaseModel, ConfigDict, ValidationError

from hone_music_video._files import write_json
from hone_music_video.project import Project
from hone_music_video.records import Version, Words
from hone_music_video.workflow import ITEM, NAME, STAGES

# the planners: their calls are hone-models' chat spans (the frame plan's many calls, 0026)
CHAT_STAGES = ("lyrics", "plan")
HOSTED = ("transcribe", *CHAT_STAGES)  # where each stage runs (design §3.1)
GPU = ("scenes", "clips", "finish")
WHERE = {s: "hosted" if s in HOSTED else "gpu" if s in GPU else "cpu" for s in map(str, STAGES)}
MARGIN = timedelta(minutes=1)  # spans read around the project's attempts (clocks, rounding)
STRICT = ConfigDict(extra="forbid")


class Part(BaseModel):
    """A stage's first pass, its reruns or its redos: time, and the hosted calls with their price."""

    model_config = STRICT
    time_ms: int = 0
    calls: int = 0
    cost_usd: float = 0.0  # the calls whose price is recorded
    unknown_calls: int = 0  # the calls without a recorded price


class StageCost(BaseModel):
    """One stage of design §3.1: where it runs, and its parts."""

    model_config = STRICT
    stage: str
    where: str  # gpu, cpu or hosted
    first: Part
    reruns: Part
    redos: Part


class Costs(BaseModel):
    """`current/costs.json`: what the project's video cost so far, by stage, with the totals."""

    model_config = STRICT
    format_version: Version = "1"

    project: str
    hosted_usd: float  # every hosted call with a recorded price
    unknown_calls: int  # hosted calls without one: the cost is at least `hosted_usd`
    gpu_ms: int
    cpu_ms: int
    hosted_ms: int  # time waiting for hosted models
    added_usd: float  # what reruns and redos added
    added_ms: int
    stages: list[StageCost]
    store: str  # hone-models' span store read for the planners' calls
    store_found: bool  # False: no records there, every planner attempt is unknown


@dataclass(frozen=True)
class Attempt:
    run_id: str
    stage: str
    number: int
    part: str
    start: datetime
    end: datetime
    called: bool = True  # False: the attempt made no hosted call (a start-frame check that was off)


@dataclass(frozen=True)
class Call:
    """A planner call hone-models recorded: when it started, the run and stage it names, its price."""

    at: datetime
    run_id: str | None
    stage: str | None
    cost_usd: float | None
    kind: str = "chat"  # "image": a hosted picture's span (0020)


Priced = tuple[Attempt, float | None]  # a hosted call of an attempt, and its price (None: unknown)


def _time(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _part(attempt: int, forked: bool) -> str:
    if forked:
        return "redos"
    return "first" if attempt == 1 else "reruns"


def _attempts(run_id: str, record: fk.StepRecord, forked: bool) -> list[Attempt]:
    """Every attempt of a stage this run made itself (not one a fork copied), with its part."""
    if record.reused_from is not None or record.step not in WHERE:
        return []
    tried = [(a.get("attempt", 1), a.get("started_at"), a.get("ended_at")) for a in record.attempts]
    if record.status in ("done", "failed"):
        tried.append((record.attempt, record.started_at, record.ended_at))
    return [
        Attempt(run_id, record.step, n, _part(n, forked), _time(s), _time(e)) for n, s, e in tried if s and e
    ]


def _heard(run: Path, attempt: Attempt, current: bool) -> list[Priced]:
    """A `transcribe` attempt's calls from its `words.json`; one unknown call when it has none (failed)."""
    step = run / "transcribe" / f"item_{ITEM}"
    output = step / "output" if current else step / "attempts" / str(attempt.number) / "output"
    try:
        words = Words.model_validate_json((output / "transcribe.json").read_bytes())
    except (OSError, ValidationError):
        return [(attempt, None)]
    calls = [words.call, *(listen.call for listen in words.listened_again)]
    return [(attempt, c.cost_usd) for c in calls if c is not None]


def from_runs(project: Project) -> tuple[list[Attempt], list[Priced], dict[str, bool]]:
    """Every attempt of every run of the project, the transcription calls, and which runs are forks."""
    folder = project.runs_dir / NAME / "runs"
    if not folder.is_dir():
        return [], [], {}
    history = fk.open_runs(project.runs_dir, NAME)
    attempts: list[Attempt] = []
    heard: list[Priced] = []
    forks: dict[str, bool] = {}
    for run_id in history.run_ids():
        if not (folder / run_id / "manifest.json").is_file():  # a run being created
            continue
        run = history.open_run(run_id)
        forks[run_id] = run.read_manifest().fork_of is not None
        for record in run.steps(item=ITEM):
            made = [a for a in _attempts(run_id, record, forks[run_id]) if a.stage in STAGES]  # 0027: not old
            attempts += made
            if record.step == "transcribe":
                done = record.status == "done"
                for a in made:
                    heard += _heard(folder / run_id, a, done and a.number == record.attempt)
    return attempts, heard, forks


def from_store(path: Path, attempts: list[Attempt]) -> list[Call] | None:
    """The `hone.models.chat` spans of hone-models' store within the project's time (None: no store)."""
    if not path.is_file():
        return None
    if not attempts:
        return []
    start, end = min(a.start for a in attempts) - MARGIN, max(a.end for a in attempts) + MARGIN
    query = (
        "SELECT start_time, attributes, name FROM spans WHERE name IN (?, ?) AND start_time BETWEEN ? AND ?"
    )
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            rows = db.execute(
                query, ("hone.models.chat", "hone.models.image", _iso(start), _iso(end))
            ).fetchall()
        finally:
            db.close()
    except sqlite3.Error:
        return None
    calls: list[Call] = []
    for at, text, name in rows:
        attrs = json.loads(text)
        cost = attrs.get("hone.models.cost_usd")
        kind = "image" if name == "hone.models.image" else "chat"
        calls.append(Call(_time(at), attrs.get("hone.run_id"), attrs.get("hone.step"), cost, kind))
    return calls


def _named(call: Call, attempts: list[Attempt]) -> Attempt | None:
    """The attempt of the run and stage a span names: the one running when it started, else the latest."""
    ours = [a for a in attempts if (a.run_id, a.stage) == (call.run_id, call.stage)]
    during = [a for a in ours if a.start <= call.at <= a.end]
    return (during or ours[-1:] or [None])[0]


def planner_calls(calls: list[Call] | None, attempts: list[Attempt], forks: dict[str, bool]) -> list[Priced]:
    """Each planner call with its attempt; a planner attempt without one is an unknown call (unless its
    record says it made none)."""
    planners = [a for a in attempts if a.stage in CHAT_STAGES]
    calls = [c for c in calls or [] if c.kind == "chat"]
    named = {c.run_id for c in calls if c.run_id in forks}
    found: list[Priced] = []
    for call in calls:
        if call.run_id in forks and call.stage in CHAT_STAGES:
            owner = _named(call, planners)
        elif call.run_id is None:  # made before 0007: by time, only for a run no span names
            during = (a for a in planners if a.run_id not in named and a.start <= call.at <= a.end)
            owner = next(during, None)
        else:  # another run, another tool's stage
            owner = None
        if owner is not None:
            found.append((owner, call.cost_usd))
    called = {a for a, _ in found}
    return found + [(a, None) for a in planners if a not in called and a.called]


def summary(
    project: Project, attempts: list[Attempt], priced: list[Priced], store: Path, found: bool
) -> Costs:
    """The parts of every stage and the totals."""
    parts = {(s, p): Part() for s in STAGES for p in ("first", "reruns", "redos")}
    for attempt in attempts:
        parts[attempt.stage, attempt.part].time_ms += round(
            (attempt.end - attempt.start).total_seconds() * 1000
        )
    for attempt, cost in priced:
        part = parts[attempt.stage, attempt.part]
        part.calls += 1
        part.unknown_calls += cost is None
        part.cost_usd = round(part.cost_usd + (cost or 0.0), 6)
    stages = [
        StageCost(
            stage=s,
            where=WHERE[s],
            first=parts[s, "first"],
            reruns=parts[s, "reruns"],
            redos=parts[s, "redos"],
        )
        for s in STAGES
    ]
    rows = [(s.where, p) for s in stages for p in (s.first, s.reruns, s.redos)]
    added = [p for s in stages for p in (s.reruns, s.redos)]
    return Costs(
        project=project.id,
        hosted_usd=round(sum(p.cost_usd for _, p in rows), 6),
        unknown_calls=sum(p.unknown_calls for _, p in rows),
        gpu_ms=sum(p.time_ms for where, p in rows if where == "gpu"),
        cpu_ms=sum(p.time_ms for where, p in rows if where == "cpu"),
        hosted_ms=sum(p.time_ms for where, p in rows if where == "hosted"),
        added_usd=round(sum(p.cost_usd for p in added), 6),
        added_ms=sum(p.time_ms for p in added),
        stages=stages,
        store=str(store),
        store_found=found,
    )


def costs(project: Project, store: Path | None = None) -> Costs:
    """What the project's video cost so far (design §13.5, D-062); reads only. `store`: hone-models' span
    store, by default the one this process records to (`${HONE_HOME:-.hone}/models/spans.db`)."""
    path = store or mk.records.default_store()
    attempts, heard, forks = from_runs(project)
    calls = from_store(path, attempts)
    priced = heard + planner_calls(calls, attempts, forks)
    return summary(project, attempts, priced, path, calls is not None)


def write_costs(project: Project) -> Costs:
    """`costs` written to `current/costs.json`: after every start, resume and fork of the run."""
    found = costs(project)
    write_json(project.current / "costs.json", found)
    return found
