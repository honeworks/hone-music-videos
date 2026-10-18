"""The dashboard's runner (design §13, D-011): one project at a time in a background thread, because there
is one GPU. Jobs from the API: `start`, `resume`, `remake` (the clips of the scenes that changed, 0027 §7)
and `assemble` (D-036). A project waiting its turn is `queued`.

For a night of videos (0028 §6): the queue is kept in `<projects>/.queue.json`, so a dashboard started
again picks it up (the project that was running first), and a run that failed is resumed at the end of
the queue, at most `RETRIES` times, so one bad clip does not cost the night."""

from __future__ import annotations

import logging
import queue
import re
import threading
from pathlib import Path

import hone_flow as fk
from pydantic import BaseModel

from hone_music_video import runs, runs_redo
from hone_music_video._files import read_json, write_json
from hone_music_video.errors import MusicVideoError
from hone_music_video.events import EventLog
from hone_music_video.ports import Models
from hone_music_video.project import Project, open_project

LOG = logging.getLogger("hone_music_video")
PROJECT_ID = re.compile(r"^[a-z0-9-]+$")
QUEUE_FILE = ".queue.json"
RETRIES = 2  # a failed run is resumed at most this many times in a row


class Job(BaseModel):
    project: str
    action: str = "resume"  # start, resume, remake or assemble


class Queue(BaseModel):
    """`.queue.json`: the running project first, then the jobs waiting."""

    jobs: list[Job] = []


class Runner:
    """Runs projects one at a time in a background thread; the frame runs of the Scenes view are each
    project's frame runner's (`frame_stages.runner_for`, Hone Frame's)."""

    def __init__(self, projects: Path, models: Models) -> None:
        self.projects, self.models = projects, models
        self.jobs: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self.queued: set[str] = set()
        self.waiting: list[tuple[str, str]] = []  # the jobs not started, in order (for `.queue.json`)
        self.retries: dict[str, int] = {}
        self.thread = threading.Thread(target=self._work, name="hone-music-video-runner", daemon=True)
        self.current: str | None = None
        self.closing = threading.Event()
        self._lock = threading.Lock()

    def submit(self, project_id: str, action: str) -> None:
        with self._lock:
            self.queued.add(project_id)
            self.waiting.append((project_id, action))
            self._save()
        self.jobs.put((project_id, action))

    def restore(self) -> list[str]:
        """Queue again what `.queue.json` kept (a dashboard stopped or killed with jobs waiting): the run
        that was running first, resumed. The projects queued."""
        path = self.projects / QUEUE_FILE
        try:
            kept = read_json(path, Queue).jobs if path.is_file() else []
        except (OSError, ValueError):
            LOG.warning("%s cannot be read; the queue starts empty", path)
            kept = []
        found: list[str] = []
        for job in kept:
            project_id = job.project
            if PROJECT_ID.match(project_id) and (self.projects / project_id / "project.json").is_file():
                started = runs.status(open_project(self.projects / project_id)).status != "not_started"
                if project_id not in found:  # a start whose run exists is a resume
                    self.submit(project_id, "resume" if job.action == "start" and started else job.action)
                    found.append(project_id)
        return found

    def _save(self) -> None:
        """`.queue.json`: the running project (to resume) and the jobs waiting, in order."""
        jobs = ([(self.current, "resume")] if self.current else []) + self.waiting
        try:
            write_json(self.projects / QUEUE_FILE, Queue(jobs=[Job(project=p, action=a) for p, a in jobs]))
        except OSError:
            LOG.warning("the queue could not be kept in %s", self.projects / QUEUE_FILE)

    def _run(self, project: Project, action: str) -> None:
        if action == "start":
            runs.start(project, self.models)
        elif action == "remake":  # the clips of the scenes that changed (0027 §7)
            runs_redo.remake(project, self.models)
        elif action == "assemble":  # the video cut again (D-036)
            runs_redo.assemble(project, self.models)
        else:
            runs.resume(project, self.models)

    def _attempt(self, project: Project, action: str) -> None:
        """Run one job; an error is shown in the project's progress."""
        try:
            self._run(project, action)
        except (MusicVideoError, fk.HoneFlowError) as error:
            EventLog(project.events_file).write("run_error", message=str(error))
        except Exception as error:
            LOG.exception("the run of %s failed", project.id)
            EventLog(project.events_file).write("run_error", message=f"{type(error).__name__}: {error}")

    def _retry(self, project: Project) -> None:
        """A run that failed (not paused, not stopped by the owner) is resumed at the end of the queue,
        at most `RETRIES` times in a row (0028 §6)."""
        if self.closing.is_set() or runs.status(project).status != "failed":
            self.retries.pop(project.id, None)
            return
        tried = self.retries.get(project.id, 0)
        if tried >= RETRIES:
            return
        self.retries[project.id] = tried + 1
        EventLog(project.events_file).write("run_retried", attempt=tried + 1, of=RETRIES)
        self.submit(project.id, "resume")

    def _work(self) -> None:
        while (job := self.jobs.get()) is not None and not self.closing.is_set():
            project_id, action = job
            with self._lock:
                self.queued.discard(project_id)
                if job in self.waiting:
                    self.waiting.remove(job)
                self.queued.update(p for p, _ in self.waiting)
                self.current = project_id
                self._save()
            try:
                project = open_project(self.projects / project_id)
                self._attempt(project, action)
                self._retry(project)
            except MusicVideoError as error:  # the project was removed or cannot be read
                LOG.warning("the queued job of %s was skipped: %s", project_id, error)
            finally:
                with self._lock:
                    if self.closing.is_set():  # stopped by the dashboard closing: resumed when it starts
                        self.waiting.insert(0, (project_id, "resume"))
                    self.current = None
                    self._save()
