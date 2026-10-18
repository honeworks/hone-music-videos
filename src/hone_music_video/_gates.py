"""What `runs` and `runs_redo` share about a run's gates and decisions: the gate waiting, a decision made
while another process may hold the run, every gate of an unattended project (0004, `_auto_approve`), and
a run made by an earlier version continued as a fork (0006)."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

import hone_flow as fk

from hone_music_video._auto_approve import AUTO, approve_unattended
from hone_music_video.errors import RunStateError
from hone_music_video.events import EventLog
from hone_music_video.project import Project
from hone_music_video.workflow import ITEM

OnEvent = Callable[[dict[str, Any]], None]


def busy(project: Project, error: fk.RunLocked) -> RunStateError:
    return RunStateError(
        f"{project.id} is running in another process ({error}); wait for it to stop at a gate or end, "
        "or stop that process, then try again"
    )


def decide(project: Project, decision: Callable[[], object]) -> None:
    """Make a decision or resume the run; another process holding the run is a `RunStateError`."""
    try:
        decision()
    except fk.RunLocked as error:
        raise busy(project, error) from None


def gate_waiting(run: fk.Run) -> str | None:
    """The gate waiting for the owner, if any."""
    return next((s.step for s in run.steps(item=ITEM) if s.status == "awaiting_review"), None)


def _passed(project: Project, run: fk.Run, gate: str) -> bool:
    """Pass the gate waiting when the project runs unattended (never over errors); False when the owner
    must decide."""
    return project.record().approve == AUTO and approve_unattended(
        project, run, gate, partial(decide, project)
    )


def pass_on_its_own(project: Project, wf: fk.Workflow, run_id: str, log: OnEvent) -> None:
    """Pass each gate the run stops at that needs no decision from the owner, and go on after it."""
    while True:
        run = wf.open_run(run_id)
        gate = gate_waiting(run)
        if gate is None or not _passed(project, run, gate):
            return
        decide(project, partial(wf.open_run(run_id).resume, on_event=log))  # opened again: it was decided


def resume_or_fork(project: Project, wf: fk.Workflow, run_id: str, log: OnEvent) -> str:
    """Resume the run; a run this version cannot resume (made with other stages, before 0006) is forked
    instead: the fork reuses every finished stage and runs the rest with this version. The run's id
    afterwards (the fork's is the project's run from then on)."""
    run = wf.open_run(run_id)
    try:
        decide(project, partial(run.resume, on_event=log))
        return run_id
    except fk.IncompatibleRun as why:
        EventLog(project.events_file).write("run_forked_for_new_version", run=run_id, reason=str(why))
        forked: list[fk.Run] = []
        decide(project, lambda: forked.append(run.fork(label=project.record().name, on_event=log)))
        return forked[0].run_id
