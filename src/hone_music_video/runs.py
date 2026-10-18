"""Start, resume, approve, reject and read a project's run (design §3.1). One run per project.

Every call returns or reads the state from the run folder, so a CLI, a dashboard and a test in other
processes all see the same thing."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from typing import Any

import hone_flow as fk

from hone_music_video import frame_stages, pause
from hone_music_video import owner_timing as timing
from hone_music_video._auto_approve import approved_unattended, scenes_ready
from hone_music_video._gates import OnEvent, decide, gate_waiting, pass_on_its_own, resume_or_fork
from hone_music_video._shot_jobs import CHOSEN
from hone_music_video.errors import InvalidInput, NotFound, RunStateError
from hone_music_video.events import EventLog
from hone_music_video.ports import Models
from hone_music_video.project import Project, set_prepare
from hone_music_video.records import Report, Song
from hone_music_video.video_costs import write_costs
from hone_music_video.workflow import GATES, ITEM, NAME, STAGES, build_workflow, song_item

# gates whose stage reads the owner's note when run again (D-015)
RERUNNABLE = ("review_lyrics", "review_plan")
# gates that are not approved while their check reports errors: the check, what to say (D-015)
CHECKED = {
    "review_lyrics": ("check_lyrics", "the timed lyrics have {n} errors", "run the lyrics stage again"),
    "review_plan": ("check_plan", "the shot list has {n} errors", "plan the scenes again"),
}
PER_SHOT = ("clips", "finish")


@dataclass(frozen=True)
class Stage:
    """One stage of design §3.1 as the dashboard shows it."""

    number: int
    name: str
    status: str  # not_started, pending, running, done, failed, paused, blocked, interrupted, awaiting_review
    gate: str | None = None  # the owner's gate after this stage, if any
    duration_ms: int | None = None
    started_at: str | None = None  # ISO-8601 UTC, so the dashboard can show how long a stage has run
    error: str | None = None
    shots_done: int | None = None  # stages 8 and 9: shots finished so far
    shots_total: int | None = None
    gate_auto: bool = False  # its gate was approved unattended (0004)


@dataclass(frozen=True)
class RunState:
    """Where a project's run stands: `status` is hone-flow's run status, or `not_started`."""

    project: str
    status: str
    run_id: str | None = None
    waiting: str | None = None  # the gate waiting for the owner
    stages: list[Stage] = field(default_factory=list[Stage])
    pausing: str | None = None  # "pause" or "stop": asked while it runs (0022)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _history(project: Project) -> fk.RunHistory:
    return fk.open_runs(project.runs_dir, NAME)


def latest_run(project: Project) -> fk.Run | None:
    """The project's run: the newest, or after a redo the newest fork (D-031). A run is a fork of the one
    before it, so the run no other run forks from is the latest; ids alone sort only to the second."""
    history = _history(project)
    folder = project.runs_dir / NAME / "runs"
    ids = history.run_ids() if folder.is_dir() else []
    # a run being created has its folder before its manifest (written atomically): leave it out until then
    found = [history.open_run(i) for i in ids if (folder / i / "manifest.json").is_file()]
    forked = {fork.run_id for r in found if (fork := r.read_manifest().fork_of) is not None}
    return next((r for r in found if r.run_id not in forked), None)


def _require_run(project: Project) -> fk.Run:
    run = latest_run(project)
    if run is None:
        raise RunStateError(f"{project.id} has no run yet; start it (`hone-music-video run`)")
    return run


def logger(project: Project, on_event: OnEvent | None) -> OnEvent:
    log = EventLog(project.events_file)

    def record(event: dict[str, Any]) -> None:
        log.record(event)
        if on_event is not None:
            on_event(event)

    return record


def start(project: Project, models: Models, *, on_event: OnEvent | None = None) -> RunState:
    """Start the project's run; it goes until the first gate (or a failure) and returns its state."""
    if latest_run(project) is not None:
        raise RunStateError(f"{project.id} has a run already; resume it (`hone-music-video resume`)")
    wf = build_workflow(project, models)
    settings = project.settings.model_dump(mode="json")
    log = logger(project, on_event)
    run = wf.run(
        [song_item(project)], params={"settings": settings}, label=project.record().name, on_event=log
    )
    pass_on_its_own(project, wf, run.run_id, log)
    write_costs(project)  # current/costs.json follows the run (design §13.5)
    return status(project)


def prepared(project: Project, state: RunState | None = None) -> bool:
    """The run stopped before its first local stage, every hosted call made (0028 §6)."""
    if not project.record().prepare:
        return False
    found = state or status(project)
    return found.status == "paused" and any(s.name == "scenes" and s.status == "paused" for s in found.stages)


def resume(project: Project, models: Models, *, on_event: OnEvent | None = None) -> RunState:
    """Continue the run: finish interrupted, failed and pending stages, up to the next gate. A run made
    by an earlier version with other stages is continued as a fork of it (`run_forked_for_new_version`).
    A prepared run goes on through the local stages (0028 §6)."""
    if prepared(project):
        set_prepare(project, False)
    run, wf, log = _require_run(project), build_workflow(project, models), logger(project, on_event)
    pass_on_its_own(project, wf, resume_or_fork(project, wf, run.run_id, log), log)
    write_costs(project)  # current/costs.json follows the run (design §13.5)
    return status(project)


def _gate(project: Project, gate: str | None) -> tuple[fk.Run, str]:
    """The run and its gate waiting for the owner (`gate`, when named, must be the one waiting)."""
    run = _require_run(project)
    if _run_status(run) == "running":  # the gate is decided once the run lets go of it (D-012)
        raise RunStateError(f"{project.id} is still running; decide once it stops at the gate")
    waiting = gate_waiting(run)
    if gate is not None and gate not in GATES.values():
        raise NotFound(f"there is no gate {gate!r}; the gates are {', '.join(GATES.values())}")
    if waiting is None or (gate is not None and gate != waiting):
        raise RunStateError(f"{gate or 'no gate'} is not waiting for approval (waiting: {waiting or 'none'})")
    return run, waiting


def waiting_gate(project: Project) -> tuple[fk.Run, str]:
    """The run and the gate waiting for the owner, whichever it is (`RunStateError` when none waits)."""
    return _gate(project, None)


def _accepted(project: Project, gate: str, accept_errors: bool, report: Report | None = None) -> list[str]:
    """The errors the owner accepts by approving (`"<where> <rule>"`). The lyrics and shot gates are not
    approved while their check (`report`, else the check stage's) reports errors (design §5, D-015),
    except the shot list's `acceptable` ones when the owner says so (D-027)."""
    if gate not in CHECKED:
        return []
    check, found, again = CHECKED[gate]
    report = report or stage_outputs(project, check)[check]
    errors = report.errors if report is not None else []
    blocking = sum(not p.acceptable for p in errors)
    if not errors or (accept_errors and not blocking):
        return [f"{p.where} {p.rule}" for p in errors]
    if blocking == len(errors):
        why = ""
    elif blocking:
        why = f"{blocking} of them cannot be accepted; "
    else:
        why = "approve with accept_errors (`approve --accept-errors`) to keep them, or "
    raise RunStateError(
        f"{found.format(n=len(errors))} ({check}); {why}"
        f"{again} with a note (`hone-music-video reject --note ...`)"
    )


def _note_kept(run: fk.Run, gate: str) -> str:
    """The note of the gate's last decision as hone-flow kept it (secrets stripped)."""
    reviews = run.steps(gate, ITEM)[0].reviews
    return str(reviews[-1].get("note") or "") if reviews else ""


def approve(project: Project, gate: str | None = None, *, note: str = "", accept_errors: bool = False) -> str:
    """Approve the gate waiting for the owner (or the named one); `resume` then continues the run.
    `accept_errors` approves a shot list whose errors are all `acceptable`; the acceptance is kept in the
    gate's note and its event (D-027). At `review_lyrics` with the owner's saved timing, the gate's output
    becomes the edited timeline, checked again (0018)."""
    run, waiting = _gate(project, gate)
    timed = timing.under_review(project, run) if waiting == "review_lyrics" else None
    if timed and timed.kept and note.strip():  # hone-flow's edit keeps no note (D-113)
        raise InvalidInput("an approval with your timing keeps no note (it is an edit); approve without one")
    accepted = _accepted(project, waiting, accept_errors, timed.report if timed else None)
    if accepted:
        note = f"{note} (accepted {len(accepted)} errors: {', '.join(accepted)})".strip()
    if waiting == "review_scenes":  # the scenes as they are now: the pictures picked since (0027 §5)
        scenes = scenes_ready(project)
        decide(project, lambda: run.edit(waiting, ITEM, value=scenes))
    elif timed and timed.kept:  # the gate's output becomes the owner's timeline (0018, D-113)
        decide(project, lambda: run.edit(waiting, ITEM, value=timed.timeline))
    else:
        decide(project, lambda: run.approve(waiting, ITEM, note=note))
    if timed:
        timing.decided(project)
    extra = {"accepted_errors": accepted} if accepted else {}
    extra |= {"timing_kept": timed.kept, "timing_dropped": timed.dropped} if timed else {}
    EventLog(project.events_file).write("gate_approved", gate=waiting, note=_note_kept(run, waiting), **extra)
    return waiting


def reject(project: Project, gate: str | None = None, *, note: str) -> str:
    """Send the gate's stage back to run again with the owner's note (hone-flow's reject-and-revise,
    D-015): `resume` runs it again, and its planner reads the note. Only at gates whose stage reads it."""
    if not note.strip():
        raise InvalidInput("say what should change: the note goes to the planner that runs again")
    run, waiting = _gate(project, gate)
    if waiting not in RERUNNABLE:
        raise RunStateError(
            f"{waiting} cannot be run again with a note (only {', '.join(RERUNNABLE)}); approve it or wait"
        )
    sent = timing.rerun_note(project, note) if waiting == "review_lyrics" else note  # D-116
    decide(project, lambda: run.reject(waiting, ITEM, note=sent))
    EventLog(project.events_file).write("gate_rejected", gate=waiting, note=_note_kept(run, waiting))
    return waiting


def lyrics_timing(project: Project, changes: Mapping[str, Any]) -> timing.Reviewed:
    """At `review_lyrics`: save the owner's start and end of lines (`{line id: {start_ms, end_ms}}`, None
    takes an edit back) on top of those saved before, checked, kept as a version and checked again with
    `check_lyrics`; `approve` then decides the gate with them (0018, D-113)."""
    run, _ = _gate(project, "review_lyrics")
    found = timing.save(project, run, timing.parse_changes(dict(changes)))
    EventLog(project.events_file).write("lyrics_timed", lines=found.kept, dropped=found.dropped)
    return found


def duration_ms(project: Project) -> int | None:
    """The song's length once `measure` has run."""
    song: Song | None = stage_outputs(project, "measure")["measure"]
    return song.duration_ms if song else None


def stage_outputs(project: Project, *stages: str) -> dict[str, Any]:
    """Each finished stage's output record (`Timeline`, `Cast`, `Shots`...); None for one not done yet."""
    run = latest_run(project)
    state: dict[str, str] = run.manifest["state"] if run else {}
    return {s: run.output(s, ITEM) if run and state.get(f"{s}/{ITEM}") == "done" else None for s in stages}


def _shot_progress(project: Project, stage: str) -> tuple[int, int] | None:
    if not (project.root / frame_stages.FOLDER / frame_stages.SHOTS).is_file():
        return None
    ids = [s.scene for s in frame_stages.read_shots(project).shots]
    done = sum((project.current / "shots" / i / CHOSEN[stage]).is_file() for i in ids)  # the chosen files
    return done, len(ids)


def _stage(project: Project, number: int, name: str, steps: dict[str, fk.StepRecord]) -> Stage:
    record, gate = steps.get(name), GATES.get(name)
    status = record.status if record else "not_started"
    if gate and status == "done" and gate in steps and steps[gate].status == "awaiting_review":
        status = "awaiting_review"
    progress = _shot_progress(project, name) if name in PER_SHOT and status != "pending" else None
    return Stage(
        number=number,
        name=name,
        status=status,
        gate=gate,
        duration_ms=record.duration_ms if record else None,
        started_at=record.started_at if record else None,
        error=(record.error or {}).get("message") if record else None,
        shots_done=progress[0] if progress else None,
        shots_total=progress[1] if progress else None,
        gate_auto=approved_unattended(steps[gate].reviews) if gate in steps else False,
    )


def _run_status(run: fk.Run) -> str:
    """hone-flow's status, except that a run whose process died shows `interrupted` before a resume."""
    lease = run.lease()
    if lease is not None:
        return "running" if lease.live else "interrupted"
    return "interrupted" if run.status == "running" else run.status


def status(project: Project) -> RunState:
    """The run's status, the gate waiting and every stage, read from the run folder."""
    run = latest_run(project)
    if run is None:
        stages = [Stage(n, s, "not_started", GATES.get(s)) for n, s in enumerate(STAGES, 1)]
        return RunState(project=project.id, status="not_started", stages=stages)
    steps = {s.step: s for s in run.steps(item=ITEM)}
    stages = [_stage(project, n, s, steps) for n, s in enumerate(STAGES, 1)]
    status = _run_status(run)
    if status == "running":  # a failed step keeps its record until the resume's attempt ends: it runs again
        stages = [
            replace(s, status="running", error=None, started_at=None, duration_ms=None)
            if s.status == "failed"
            else s
            for s in stages
        ]
    if status == "failed" and any(_paused(s) for s in stages):  # the owner's pause ended the step (0022)
        status, stages = (
            "paused",
            [replace(s, status="paused", error=None) if _paused(s) else s for s in stages],
        )
    waiting = None if status == "running" else gate_waiting(run)  # a gate can be decided once the run lets go
    asked = pause.asked(project) if status == "running" else None
    pausing = None if asked is None else "stop" if asked.now else "pause"
    return RunState(project.id, status, run.run_id, waiting, stages, pausing)


def _paused(stage: Stage) -> bool:
    return stage.status == "failed" and pause.MESSAGE in (stage.error or "")
