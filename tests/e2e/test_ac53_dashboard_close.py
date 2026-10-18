"""AC-53: closing the dashboard stops the busy run and the ComfyUI its session started (0025 §3, D-160)."""

import subprocess
import time
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video import pause
from hone_music_video.dashboard import CLOSE_WAIT_S
from hone_music_video.ports import Generated
from hone_music_video.testing import FakeModels
from tests.conftest import new_project

pytestmark = pytest.mark.e2e


class Holding(FakeModels):
    """A session starts a stand-in ComfyUI (`sleep`); the clip model waits until Stop is asked."""

    def __init__(self, project: hmv.Project) -> None:
        super().__init__()
        self.project = project
        self.servers: list[subprocess.Popen[bytes]] = []
        self.blocking = False

    @contextmanager
    def session(self, model_id: str) -> Any:
        proc = None
        if model_id == self.project.settings.models.clips:
            proc = subprocess.Popen(["sleep", "600"])  # noqa: S607 - a stand-in ComfyUI process
            self.servers.append(proc)
        try:
            with super().session(model_id):
                yield
        finally:
            if proc is not None:
                proc.terminate()
                proc.wait(timeout=5)

    def generate(
        self, model_id: str, prompt: str, *, out: Path, seed: int, inputs: Mapping[str, Any]
    ) -> Generated:
        if model_id == self.project.settings.models.clips:
            self.blocking = True
            deadline = time.monotonic() + 30
            while pause.asked(self.project) is None:
                if time.monotonic() > deadline:
                    raise hmv.ModelFailure("stop was not asked")
                time.sleep(0.05)
            raise hmv.ModelFailure("interrupted")
        return super().generate(model_id, prompt, out=out, seed=seed, inputs=inputs)


def _wait_until(check: Callable[[], bool], seconds: float = 10) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.05)
    raise AssertionError("timed out")


def test_ac53_closing_the_dashboard_stops_the_run_and_its_comfyui(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = new_project(tmp_path)
    hmv.set_approve_mode(project, "auto")
    models = Holding(project)
    monkeypatch.setattr(pause, "interrupt", lambda: None)
    dashboard = hmv.Dashboard(tmp_path / "projects", models, port=0).start()
    dashboard.server.runner.submit(project.id, "start")
    _wait_until(lambda: models.blocking and any(p.poll() is None for p in models.servers))
    began = time.monotonic()
    dashboard.close()
    assert time.monotonic() - began < CLOSE_WAIT_S
    assert not dashboard.server.runner.thread.is_alive()
    assert all(p.poll() is not None for p in models.servers)
    assert hmv.status(project).status == "paused"


def test_ac53_a_job_queued_while_closing_is_not_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = new_project(tmp_path)
    second = new_project(tmp_path)
    hmv.set_approve_mode(first, "auto")
    models = Holding(first)
    monkeypatch.setattr(pause, "interrupt", lambda: None)
    dashboard = hmv.Dashboard(first.root.parent, models, port=0).start()
    dashboard.server.runner.submit(first.id, "start")
    _wait_until(lambda: models.blocking)
    dashboard.server.runner.submit(second.id, "start")
    dashboard.close()
    assert hmv.status(second).status == "not_started"


def test_ac53_close_without_a_run_returns_at_once(tmp_path: Path) -> None:
    hmv.Dashboard(tmp_path / "projects", FakeModels(), port=0).close()
