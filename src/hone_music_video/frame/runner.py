"""`Runner`: runs projects one at a time (design §8). A run repeatedly makes the topmost marked item;
it stops when an item waits for the owner, fails, is paused or stopped, or nothing is marked.

hone-flow keeps the execution record: each run (or resume) is one hone-flow run whose items are the steps
it made, with spans, timings and errors (decisions D-043). `state.json` decides what exists.

Hone Frame: ported from `src/hone_frame/runner.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, NamedTuple

import hone_flow as fk

from hone_music_video.frame import actions
from hone_music_video.frame._files import now, project_lock, running, running_elsewhere
from hone_music_video.frame.errors import RunStateError
from hone_music_video.frame.making import make, next_up, rest_of
from hone_music_video.frame.notifications import notify
from hone_music_video.frame.project import Project
from hone_music_video.frame.records import RunRecord, RunStatus
from hone_music_video.frame.workspace import Workspace

ACTIVE = ("queued", "running", "pausing")
RUN_EVENT = {"waiting": "run_waiting", "paused": "run_paused", "stopped": "run_stopped", "done": "run_done"}
LOG = logging.getLogger("hone_music_video.frame.runner")


class RunEnd(NamedTuple):
    """How a run ended: its status, the reason shown to the owner, and the item it is about."""

    status: RunStatus
    reason: str
    item: str | None = None


@dataclass
class _FlowRun:
    """One hone-flow run of a run: `end` is set when the run ends inside it."""

    end: RunEnd | None = None


class Runner:
    """One queue for the workspace: one run at a time, in the order they were started (design §8.5).

    `drain()` runs the queue in the calling thread (the CLI, tests); `start()` runs it in a background
    thread (the dashboard). Control methods may be called from any thread."""

    def __init__(self, ws: Workspace) -> None:
        self.ws = ws
        self._queue: list[str] = []
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._halt: str | None = None  # "pause" or "stop", asked for the current run
        self._current: str | None = None
        self._wake = threading.Event()
        self._closed = threading.Event()
        self._thread: threading.Thread | None = None

    # control ---------------------------------------------------------------------------------------

    def run(self, project_id: str) -> None:
        """Queue a new run of the project: it starts when no other project is running."""
        project = self.ws.project(project_id)
        project.sync()  # items added to the file by hand are marked
        if project.run().status in ACTIVE:
            raise RunStateError(f"{project_id} is already {project.run().status}: pause or stop it first")
        if not project.marked():
            raise RunStateError(f"nothing in {project_id} is marked to run: mark an item first")
        self._enqueue(project, RunRecord(started_at=now()))

    def resume(self, project_id: str) -> None:
        """Continue a paused run from the topmost marked item."""
        project = self.ws.project(project_id)
        record = project.run()
        if record.status != "paused":
            raise RunStateError(f"{project_id} is {record.status}, not paused: use run")
        self._enqueue(project, record)

    def pause(self, project_id: str) -> None:
        """Cancel the current image now and pause; the item stays marked (design §8.3)."""
        self._halt_run(project_id, "pause")

    def stop(self, project_id: str) -> None:
        """Cancel the current image now and end the run."""
        self._halt_run(project_id, "stop")

    def accept(self, project_id: str, item_id: str, version: int | None = None) -> None:
        """Accept (or pick a version of) a waiting item; a run waiting for it continues by itself."""
        actions.accept(self.ws.project(project_id), item_id, version)
        self.settle(project_id)

    def settle(self, project_id: str) -> None:
        """A run waiting for an item continues by itself once that item no longer waits: accepted, picked,
        a version used, replaced, marked again or removed (decisions D-074)."""
        project = self.ws.project(project_id)
        record = project.run()
        if record.status != "waiting":
            return
        waited = project.state().items.get(record.item or "")
        held = waited is not None and waited.status == "waiting" and not waited.marked
        if held and project.spec().item(record.item or "").hold:
            return  # a hold stops the whole run until it is accepted
        if next_up(project)[0]:
            self._enqueue(project, record.model_copy(update={"item": None}))
            return
        end = _rest(project)
        if end.status == "done":
            self._finish(project, end)
        else:  # still picks to make: say which, without ringing again
            project.update_run(reason=end.reason, item=end.item)

    @property
    def background(self) -> bool:
        """Whether `start()` runs the queue in a thread (Hone Frame: not public there; stage 6 of the
        video's run waits for such a runner, and drains one that is not, 0027)."""
        return self._thread is not None and self._thread.is_alive()

    def queue(self) -> list[str]:
        """Every project id: the running one, the queued ones in order, then the others."""
        with self._lock:
            order = ([self._current] if self._current else []) + self._queue
        projects = {p.id for p in self.ws.projects()}
        return [i for i in order if i in projects] + sorted(projects - set(order))

    def recover(self, project_ids: list[str] | None = None) -> list[str]:
        """Runs a process left queued or running when it ended are stopped, with the reason; an item it
        was making goes back to `done` (it has a current version) or `todo`, still marked. Only these
        projects when given (the CLI's `run`); never one this runner has, or that another process is
        running now (decisions D-069). Returns the projects whose run was stopped."""
        found: list[str] = []
        for project in self.ws.projects():
            mine = project.id in self._queue or project.id == self._current
            if mine or (project_ids is not None and project.id not in project_ids):
                continue
            if running_elsewhere(project.root):
                continue
            status = project.run().status
            if status in ACTIVE:
                reason = f"Hone Frame stopped while this run was {status}: run it again"
                project.update_run(status="stopped", reason=reason, current=None)
                found.append(project.id)
            project.reset_running()
        return found

    def _enqueue(self, project: Project, record: RunRecord) -> None:
        with self._lock:
            busy = self._current
            if project.id not in self._queue:
                self._queue.append(project.id)
        reason = f"queued behind {busy}" if busy else ""
        project.save_run(record.model_copy(update={"status": "queued", "reason": reason, "item": None}))
        self._wake.set()

    def _halt_run(self, project_id: str, how: str) -> None:
        project = self.ws.project(project_id)
        with self._lock:
            record = project.run()  # read under the lock: the run cannot end meanwhile (D-058)
            if project_id == self._current:
                if how == "pause":  # written before the cancel, so the run's own writes come after (D-068)
                    project.update_run(when=ACTIVE, status="pausing", reason="pausing")
                self._halt = how
                self._cancel.set()
                return
            queued = project_id in self._queue
            if queued:
                self._queue.remove(project_id)
        allowed = ("queued",) if how == "pause" else ("queued", "paused", "waiting")
        if not queued and record.status not in allowed:
            raise RunStateError(f"{project_id} is {record.status}: there is no run to {how}")
        status = "paused" if how == "pause" else "stopped"
        project.update_run(status=status, reason=f"{status} by you")
        project.log(RUN_EVENT[status], None, f"{status} by you")

    # execution -------------------------------------------------------------------------------------

    def drain(self, *, once: bool = False) -> None:
        """Run the queued projects in this thread until the queue is empty (`once`: one item each). A run
        that raises ends `failed` with the error; the others still run (decisions D-059)."""
        while True:
            with self._lock:
                if not self._queue:
                    return
                current = self._current = self._queue.pop(0)
                self._halt = None
                self._cancel.clear()
            try:
                project = self.ws.project(current)
                with running(project.root):
                    end = self._execute(project, once=once)
            except Exception as exc:
                LOG.exception("the run of %s failed", current)
                end = RunEnd("failed", f"the run stopped: {type(exc).__name__}: {exc}")
            with self._lock:
                self._current = None  # before the end is written: a pause now finds no current run (D-058)
            self._finish(self.ws.project(current), end)

    def start(self) -> Runner:
        """Run the queue in a background thread until `close()`."""

        def loop() -> None:
            while not self._closed.is_set():
                self._wake.wait(0.5)
                self._wake.clear()
                try:
                    self.drain()
                except Exception:  # a project gone or unreadable: the runner goes on with the others
                    LOG.exception("the runner could not finish a run")

        self._thread = threading.Thread(target=loop, name="hone-frame-runner", daemon=True)
        self._thread.start()
        return self

    def close(self) -> None:
        self._closed.set()
        self._wake.set()
        with self._lock:
            self._cancel.set()
            self._halt = "stop"
        if self._thread is not None:
            self._thread.join(timeout=10)

    def _execute(self, project: Project, *, once: bool) -> RunEnd:
        record = project.run()
        project.update_run(
            when=("queued",), status="running", reason="", started_at=record.started_at or now()
        )
        resumed = bool(record.made or record.flow_runs)
        project.log("run_resumed" if resumed else "run_started", message=f"{project.id}: run")
        end: RunEnd | None = None
        while end is None:
            end = self._flow_run(project, once=once) if next_up(project)[0] else _rest(project)
        return end

    def _finish(self, project: Project, end: RunEnd) -> None:
        close = getattr(project.ws.models, "close", None)  # this library: the model's session ends (0027)
        if close is not None:
            close()
        project.update_run(
            status=end.status, reason=end.reason, item=end.item, current=None, current_started_at=None
        )
        if end.status in RUN_EVENT:
            project.log(RUN_EVENT[end.status], end.item, end.reason)
        if end.status in ("waiting", "failed", "done"):
            notify(project, end.status, end.item, f"{project.state().name}: {end.reason}")

    def _flow_run(self, project: Project, *, once: bool) -> RunEnd | None:
        """One hone-flow run over the marked items, top to bottom. None: start another (an item above
        was marked meanwhile); else how the run ends."""
        ids = [i.id for i in project.marked()]
        flow = _FlowRun()
        wf = fk.Workflow(
            project.id, storage=self.ws.root / "flows", version="1", measure=("timing",), fail_fast=True
        )

        @wf.step(version="1", deterministic=False)
        def make_item(item: fk.Item) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
            if flow.end is not None:
                return {"skipped": "the run ended before this item"}
            return self._step(project, item.id, flow, once=once)

        def on_event(event: dict[str, Any]) -> None:
            if event.get("event") == "run_started":
                with project_lock(project.root):
                    project.update_run(flow_runs=[*project.run().flow_runs, event["run_id"]])

        try:
            wf.run([fk.Item(i) for i in ids], label=f"{project.id}: {len(ids)} marked", on_event=on_event)
        except (
            fk.StepFailed
        ) as exc:  # the item is failed and `flow.end` says so; hone-flow keeps the traceback
            flow.end = flow.end or RunEnd("failed", str(exc))
        return flow.end

    def _step(self, project: Project, item_id: str, flow: _FlowRun, *, once: bool) -> dict[str, Any]:
        ready = next_up(project)[0]
        if self._halt is not None:
            flow.end = self._halted()
            return {"skipped": flow.end.reason}
        if not ready or ready[0].id != item_id:  # held back, or another item comes first now: next pass
            return {"skipped": "not the next item the run can make"}
        item = project.spec().item(item_id)
        project.update_run(current=item_id, current_started_at=now())
        try:
            outcome = make(project, item, self._cancel)
        except Exception as exc:
            flow.end = RunEnd("failed", f"{item_id} failed: {exc}", item_id)
            raise
        with project_lock(project.root):
            made = project.run().made + ([item_id] if outcome != "cancelled" else [])
            project.update_run(current=None, current_started_at=None, made=made)
        # a hold stops the run; a pick (count > 1) does not: the run goes on and the pick waits (D-075)
        kind = "made" if outcome == "waiting" and not item.hold else outcome
        flow.end = self._after(item_id, kind, once=once)
        return {"outcome": outcome, "item": item_id}

    def _after(self, item_id: str, outcome: str, *, once: bool) -> RunEnd | None:
        if outcome == "cancelled" or self._halt is not None:
            return self._halted()
        if outcome == "waiting":
            return RunEnd("waiting", f"waiting for you: {item_id}", item_id)
        if once:
            return RunEnd("paused", f"made {item_id} (one item at a time)", item_id)
        return None

    def _halted(self) -> RunEnd:
        return (
            RunEnd("paused", "paused by you")
            if self._halt == "pause"
            else RunEnd("stopped", "stopped by you")
        )


def _rest(project: Project) -> RunEnd:
    return RunEnd(*rest_of(project))
