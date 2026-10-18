"""Shared fixtures for the acceptance cases of change 0008: a workspace with fake models.

Hone Frame: ported from its `tests/e2e/conftest.py` (change 0027)."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame.api import Api, answer
from hone_music_video.frame.guide import guide_for
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels


@pytest.fixture
def fake() -> FakeModels:
    return FakeModels()


@pytest.fixture
def ws(tmp_path: Path, fake: FakeModels) -> hf.Workspace:
    return hf.Workspace(tmp_path / "studio", models=fake)


def run(ws: hf.Workspace, project: hf.Project, *, once: bool = False) -> hf.Runner:
    """Run the project to its end in this thread (it may end waiting, failed, done...)."""
    runner = hf.Runner(ws)
    runner.run(project.id)
    runner.drain(once=once)
    return runner


def statuses(project: hf.Project) -> dict[str, str]:
    return {k: v.status for k, v in project.state().items.items()}


class Board:
    """Hone Frame's dashboard API for the tests that call it (its `Dashboard` + `tests/client.py`): the
    same routes and answers, called without a server (0027: the server is this library's dashboard)."""

    def __init__(self, ws: hf.Workspace) -> None:
        self.api = Api(ws, hf.Runner(ws), partial(guide_for, ws))

    def call(self, method: str, path: str, body: Any = None) -> tuple[int, Any]:
        return answer(self.api, method, path.removeprefix("/api"), dict(body or {}), {})
