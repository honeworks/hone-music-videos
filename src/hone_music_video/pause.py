"""Pause and Stop a running video (0022).

The dashboard or the CLI writes `current/pause.json`; the stages' `Models`, wrapped in `Stoppable`, read
it before every call and raise `Paused`, which ends the step. Pause lets the call being made finish;
Stop also interrupts ComfyUI's job and stops waiting for a hosted planner or transcription call, whose
answer is dropped when it comes. A request older than the run's start is a leftover and is removed."""

from __future__ import annotations

import contextvars
import http.client
import os
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel

from hone_music_video._files import read_json, write_json
from hone_music_video.errors import Paused
from hone_music_video.events import EventLog
from hone_music_video.ports import Generated, ImageInfo, Models
from hone_music_video.project import Project
from hone_music_video.records import AlignedWord, Words
from hone_music_video.records_timeline import STRICT

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)
PAUSE_FILE = "pause.json"
MESSAGE = "paused by the owner"
POLL_S = 0.5
COMFYUI_URL = "http://127.0.0.1:8188"  # hone-models' default, `HONE_COMFYUI_URL` overrides it


class Request(BaseModel):
    """What the owner asked: Pause (`now` false) or Stop (`now` true), and when (seconds since the epoch)."""

    model_config = STRICT

    now: bool
    at: float


def request(project: Project, *, now: bool) -> None:
    """Ask the run to pause, or with `now` to stop: the file first, then ComfyUI's interrupt."""
    write_json(project.current / PAUSE_FILE, Request(now=now, at=time.time()))
    if now:
        interrupt()


def asked(project: Project) -> Request | None:
    path = project.current / PAUSE_FILE
    return read_json(path, Request) if path.is_file() else None


def clear(project: Project) -> None:
    (project.current / PAUSE_FILE).unlink(missing_ok=True)


def interrupt() -> None:
    """ComfyUI's `POST /interrupt`: the job being run ends. TODO(hone-models): until hone-models can
    interrupt a call, this one request bypasses it (0022 §2); no server answering is fine."""
    url = urlparse((os.environ.get("HONE_COMFYUI_URL") or COMFYUI_URL).rstrip("/"))
    connection = http.client.HTTPConnection(url.hostname or "127.0.0.1", url.port or 80, timeout=5)
    try:
        connection.request("POST", f"{url.path}/interrupt")
        connection.getresponse().read()
    except OSError:
        pass
    finally:
        connection.close()


class Stoppable:
    """`models` for one run: each call first looks for the owner's request (0022)."""

    def __init__(self, models: Models, project: Project) -> None:
        self.models, self.project, self.began = models, project, time.time()

    def _asked(self) -> Request | None:
        found = asked(self.project)
        if found is not None and found.at < self.began:  # left by an earlier run or a crash
            clear(self.project)
            return None
        return found

    def _check(self) -> None:
        found = self._asked()
        if found is not None:
            EventLog(self.project.events_file).write("run_paused", now=found.now)
            raise Paused(MESSAGE)

    def _hosted(self, call: Callable[[], T]) -> T:
        """A hosted call on a helper thread (its tracing context copied), waited for until it answers or
        the owner stops the run; local calls stay on the stage's thread, which holds the GPU lease."""
        self._check()
        context, box, done = contextvars.copy_context(), dict[str, Any](), threading.Event()

        def work() -> None:
            try:
                box["value"] = context.run(call)
            except BaseException as error:
                box["error"] = error
            finally:
                done.set()

        threading.Thread(target=work, name="hone-music-video-hosted", daemon=True).start()
        while not done.wait(POLL_S):
            found = self._asked()
            if found is not None and found.now:
                self._check()
        if "error" in box:
            raise box["error"]
        return box["value"]

    def plan(
        self, model_id: str, *, system: str, data: Mapping[str, Any], images: Sequence[Path], schema: type[M]
    ) -> M:
        return self._hosted(
            lambda: self.models.plan(model_id, system=system, data=data, images=images, schema=schema)
        )

    def transcribe(self, model_id: str, audio: Path, *, language: str | None, prompt: str | None) -> Words:
        return self._hosted(lambda: self.models.transcribe(model_id, audio, language=language, prompt=prompt))

    def separate_vocals(self, model_id: str, audio: Path, *, out: Path) -> Path:
        self._check()
        return self.models.separate_vocals(model_id, audio, out=out)

    def align(self, model_id: str, audio: Path, lines: Sequence[str]) -> list[list[AlignedWord]]:
        self._check()
        return self.models.align(model_id, audio, lines)

    def generate(
        self, model_id: str, prompt: str, *, out: Path, seed: int, inputs: Mapping[str, Any]
    ) -> Generated:
        self._check()
        try:
            return self.models.generate(model_id, prompt, out=out, seed=seed, inputs=inputs)
        except Exception:
            self._check()  # a job Stop interrupted: the pause, not the model's error
            raise

    def image_info(self, model_id: str) -> ImageInfo:
        return self.models.image_info(model_id)

    def image_models(self) -> list[ImageInfo]:
        return self.models.image_models()

    def image_guide(self, model_id: str) -> Any:
        return self.models.image_guide(model_id)

    def session(self, model_id: str) -> AbstractContextManager[None]:
        return self.models.session(model_id)
