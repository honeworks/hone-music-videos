"""A project's progress as the dashboard shows it (0003): each unit stage's work read from the progress
log (`units`, `version_started`, `version_made`, D-050), or from its folders for a run made before them
(D-053), turned into numbers by `progress.py`."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from hone_music_video import frame_stages, runs
from hone_music_video.events import EventLog
from hone_music_video.progress import DEFAULT_MS, Current, Timed, Work, clip_default, overall, stage_progress
from hone_music_video.project import Project
from hone_music_video.records import Shots

UNIT_STAGES = ("clips", "finish")  # the scenes' progress is the frame run's own (its estimates, 0027)
LONG_PART = ("clips", "finish", "assemble")  # the overall estimate, once the shots are planned
SHOWN = ("running", "failed", "interrupted")
Event = dict[str, Any]
Found = list[tuple[str, Path | None]]  # (kind, the file when made) for every unit of a stage


def _ms(at: str) -> int:
    return round(datetime.fromisoformat(at).timestamp() * 1000)


def _this_run(events: Sequence[Event], stage: str) -> tuple[int | None, list[Event]]:
    """When the stage's latest run started, and the events since."""
    starts = [n for n, e in enumerate(events) if e.get("event") == "step_started" and e.get("step") == stage]
    if not starts:
        return None, []
    return _ms(events[starts[-1]]["at"]), list(events[starts[-1] + 1 :])


def _from_events(stage: str, since: list[Event], started: int | None) -> Work | None:
    """The stage's work from its last `units` event and the versions made after it."""
    mine = [e for e in since if e.get("stage") == stage]
    counts = [n for n, e in enumerate(mine) if e["event"] == "units"]
    if not counts:
        return None
    after = mine[counts[-1] :]
    made, timed = dict(after[0]["made"]), list[Timed]()
    for e in after:
        if e["event"] == "version_made":
            made[e["kind"]] = made.get(e["kind"], 0) + 1
            timed.append(Timed(e["kind"], int(e["took_ms"]), bool(e.get("first"))))
    last = [e for e in after if e["event"] in ("version_started", "version_made")]
    current = None
    if last and last[-1]["event"] == "version_started":
        e = last[-1]
        current = Current(e["kind"], e.get("shot") or e.get("character") or "", e["n"], _ms(e["at"]))
    return Work(stage, dict(after[0]["totals"]), made, timed, started, current)


def _found(project: Project, stage: str, shots: Shots | None) -> Found:
    """Every unit of the stage with its file when made, from the folders (D-053)."""
    folder = project.current / "shots"
    kind, name = ("raw_clip", "clip-raw.mp4") if stage == "clips" else ("clip", "clip.mp4")
    rows = shots.shots if shots else []
    return [(kind, folder / s.id / name if (folder / s.id / name).is_file() else None) for s in rows]


def _from_files(stage: str, found: Found, started: int | None) -> Work:
    """Counts from the folders; this run's times per unit are the gaps between the files made since the
    stage started, the first of each kind holding its model's load."""
    totals: dict[str, int] = {}
    made: dict[str, int] = {}
    for kind, file in found:
        totals[kind] = totals.get(kind, 0) + 1
        made[kind] = made.get(kind, 0) + (file is not None)
    times = sorted((f.stat().st_mtime_ns // 1_000_000, kind) for kind, f in found if f is not None)
    timed: list[Timed] = []
    previous, seen = started, set[str]()
    for at, kind in times:
        if started is not None and previous is not None and at >= started:
            timed.append(Timed(kind, at - previous, kind not in seen))
            seen.add(kind)
            previous = at
    return Work(stage, totals, made, timed, started, source="files")


def _defaults(stage: str, shots: Shots | None) -> dict[str, int]:
    rows = shots.shots if shots else []
    if stage == "clips":
        faces = sum(s.faces for s in rows)
        return {"raw_clip": clip_default(faces, len(rows) - faces)}
    if stage == "assemble":
        return {"assembly": DEFAULT_MS["assembly"] * len(rows) // 60}
    return {}


def _work(project: Project, stage: str, events: Sequence[Event], shots: Shots | None, status: str) -> Work:
    started, since = _this_run(events, stage)
    defaults = _defaults(stage, shots)
    if stage == "assemble":
        return Work(stage, {"assembly": 1}, {}, started_ms=started, defaults=defaults)
    found = _from_events(stage, since, started)
    if found is None:
        found = _from_files(stage, _found(project, stage, shots), started)
    return replace(found, defaults=defaults, running=status == "running")


def _shots(project: Project) -> Shots | None:
    """The shot list of the frame plan, once there is one."""
    return frame_stages.as_shots(frame_stages.read_shots(project)) if frame_stages.has_plan(project) else None


def project_progress(project: Project, state: runs.RunState, now_ms: int) -> dict[str, Any]:
    """Each running (or stopped) unit stage's bar, and the overall estimate of the long local part once
    the shots are planned (`ends_ms`: when it should end)."""
    events, _ = EventLog(project.events_file).read()
    shots = _shots(project)
    status = {s.name: s.status for s in state.stages}
    stages = {
        name: stage_progress(_work(project, name, events, shots, status[name]), now_ms).as_dict()
        for name in UNIT_STAGES
        if status[name] in SHOWN
    }
    whole = None
    if shots is not None and status.get("scenes") == "done":  # the overall once the scenes are made
        works = [_work(project, n, events, shots, status[n]) for n in LONG_PART if status[n] != "done"]
        found = overall(works, now_ms)
        whole = found.as_dict() | {"ends_ms": now_ms + found.left_ms} if found else None
    return {"stages": stages, "overall": whole, "now_ms": now_ms}
