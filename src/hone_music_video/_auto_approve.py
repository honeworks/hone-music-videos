"""Unattended runs (0004): every gate of a project that runs with `approve: "auto"` is approved as it is
reached, unless its check reports errors (D-075, D-076). `_gates.pass_on_its_own` asks here."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import hone_flow as fk

from hone_music_video import frame_stages
from hone_music_video.errors import RunStateError
from hone_music_video.events import EventLog
from hone_music_video.frame.runner import ACTIVE
from hone_music_video.project import Project
from hone_music_video.records import Report
from hone_music_video.records_frame import Scenes
from hone_music_video.workflow import ITEM

AUTO = "auto"  # the actor of a gate approved unattended
CHECKS = {"review_lyrics": "check_lyrics", "review_plan": "check_plan"}  # the gates with a check
# the events that decide a gate (after which an earlier stop no longer stands)
DECIDED = (
    "gate_approved",
    "gate_auto_approved",
    "gate_rejected",
)
Decide = Callable[[Callable[[], object]], None]  # runs' decision wrapper (another process: RunStateError)


def scenes_ready(project: Project) -> Scenes:
    """The scenes as they are, for `review_scenes` (0027 §5): refused while the frame run is going, an
    item is marked, or a scene has no picture in use (made and accepted or picked)."""
    fp = frame_stages.frame_project(frame_stages.workspace(project))
    if fp.run().status in ACTIVE:
        raise RunStateError("the scenes are being made: wait for the frame run to end, or pause it")
    marked = [i.id for i in fp.marked()]
    if marked:
        raise RunStateError(f"marked and not made yet: {', '.join(marked[:5])}; run them or unmark them")
    found = frame_stages.scenes_now(project)
    if found.shots is None:
        raise RunStateError(f"the scenes are not ready: {found.reason}")
    return found


def stop_reason(run: fk.Run, gate: str) -> str | None:
    """Why an unattended run stops at this gate: its check reports errors, which only the owner can
    accept, acceptable ones too (D-076); None when it may pass."""
    check = CHECKS.get(gate)
    if check is None or run.manifest["state"].get(f"{check}/{ITEM}") != "done":
        return None
    report: Report = run.output(check, ITEM)
    n = len(report.errors)
    return f"{check} reports {n} errors; auto-approval never accepts errors" if n else None


def stopped_here(events: Sequence[Mapping[str, Any]], gate: str) -> bool:
    """The newest `auto_stopped` names this gate and nothing decided it since (so it is not written on
    every resume at the same gate)."""
    for event in reversed(events):
        if event.get("gate") == gate and event.get("event") in DECIDED:
            return False
        if event.get("event") == "auto_stopped":
            return event.get("gate") == gate
    return False


def approved_unattended(reviews: Sequence[Mapping[str, Any]]) -> bool:
    """The gate's last decision was an approval (or the scenes' edit, 0027) by the actor `auto`."""
    if not reviews:
        return False
    last = reviews[-1]
    return last.get("actor") == AUTO and last.get("decision") in ("approved", "edited")


def approve_unattended(project: Project, run: fk.Run, gate: str, decide: Decide) -> bool:
    """Approve the gate unattended, or stop: its check reports errors, or someone decided it first."""
    log = EventLog(project.events_file)
    reason = stop_reason(run, gate)
    scenes: Scenes | None = None
    if reason is None and gate == "review_scenes":
        try:
            scenes = scenes_ready(project)
        except RunStateError as why:
            reason = str(why)
    if reason is not None:
        if not stopped_here(log.read()[0], gate):
            log.write("auto_stopped", gate=gate, reason=reason)
        return False
    note = "approved unattended: the project runs without stopping for approval"
    try:
        if scenes is not None:  # the scenes as they are now (0027 §5)
            decide(lambda: run.edit(gate, ITEM, value=scenes, actor=AUTO, automated=True))
        else:
            decide(lambda: run.approve(gate, ITEM, note=note, actor=AUTO, automated=True))
    except fk.ReviewError:  # the owner (or another process) decided it first: theirs stands
        return False
    log.write("gate_auto_approved", gate=gate)
    return True
