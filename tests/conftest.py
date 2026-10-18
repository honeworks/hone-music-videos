"""Shared fixtures: a short silent song, a given sheet, and a project made from them."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hypothesis import settings

import hone_music_video as hmv
from hone_music_video import notify
from hone_music_video.adapters import hone_models as adapter
from hone_music_video.testing import make_sheet, make_song, settle_scenes

# property tests draw the same examples on every run, keep no database and have no deadline
settings.register_profile("hone", derandomize=True, database=None, deadline=None)
settings.load_profile("hone")

LYRICS = "she waits upon the balcony\nthe wind is in her hair\n\nand the night comes down"


@pytest.fixture(autouse=True)
def no_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test notifies a real webhook: neither the shell's settings nor a `.env` in the folder the tests
    run from (D-060); the notification tests set their own."""
    for name in (notify.URL_ENV, notify.KIND_ENV, notify.DASHBOARD_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(notify, "load_env_files", lambda: None)


@pytest.fixture(autouse=True)
def no_comfyui(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """No default test reads or interrupts a ComfyUI that happens to run on the machine (0025 §2); the
    real-model tests (`gpu`) and the tests of the check set their own."""
    if request.node.get_closest_marker("gpu") is None:
        monkeypatch.setattr(adapter, "server_argv", lambda _url: None)
        # nor sends it Stop's interrupt: a test's Stop once ended a real run's clip (port 9 refuses)
        monkeypatch.setenv("HONE_COMFYUI_URL", "http://127.0.0.1:9")


def new_project(root: Path, settings: dict[str, Any] | None = None) -> hmv.Project:
    """A project from a 20 s silent song, lyrics, story notes and one given picture, with `settings` when
    given."""
    return hmv.create_project(
        root / "projects",
        "Balcony",
        make_song(root / "material" / "song.wav", 20_000),
        hmv.Material(
            lyrics=LYRICS,
            story="A queen waits for a hero who does not come.",
            sheets=(
                hmv.GivenSheet("Darvin", make_sheet(root / "material" / "darvin.png"), "the hero, in armour"),
            ),
        ),
        settings,
    )


@pytest.fixture
def project(tmp_path: Path) -> hmv.Project:
    return new_project(tmp_path)


@pytest.fixture
def song(project: hmv.Project) -> Path:
    return project.root.parent.parent / "material" / "song.wav"


@pytest.fixture
def sheet(project: hmv.Project) -> Path:
    return project.root.parent.parent / "material" / "darvin.png"


def drive(project: hmv.Project, models: hmv.Models) -> hmv.RunState:
    """Start or resume the run and approve every gate until it ends (the scenes settled first)."""
    state = hmv.status(project)
    state = hmv.start(project, models) if state.status == "not_started" else hmv.resume(project, models)
    while state.waiting:
        if state.waiting == "review_scenes":
            settle_scenes(project, models)
        hmv.approve(project)
        state = hmv.resume(project, models)
    return state
