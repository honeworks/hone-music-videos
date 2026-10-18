"""The frame's model port over this library's `Models` (change 0027, `frame/models.py`): a picture goes
through the library's port with its prompt as written, its references in order, its size and inputs; a
model's info comes from the registry; a cancel ends the call (Hone Frame: hone-models' cancel)."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from hone_music_video import pause
from hone_music_video.frame import FrameModels, Workspace
from hone_music_video.frame.errors import NotFound
from hone_music_video.frame.ports import Cancelled
from hone_music_video.frame.runner import Runner
from hone_music_video.testing import Call, FakeModels

TEXT = """\
[project]
name = "Port"

[defaults]
model = "qwen-image-2.1-turbo"

[characters.woman.hero]
size = "832x1248"
prompt = "A woman, full figure.  Two spaces kept."

[scenes.coffee]
size = "1664x928"
refs = ["woman.hero"]
inputs = { steps = 6 }
prompt = "The woman from image 1 drinks coffee."
"""


def test_a_picture_goes_through_the_library_port_as_written(tmp_path: Path) -> None:
    models = FakeModels()
    ws = Workspace(tmp_path / "frame", models=FrameModels(models))
    project = ws.import_text(TEXT, "toml")
    runner = Runner(ws)
    runner.run(project.id)
    runner.drain()

    hero, scene = models.calls_of("generate")
    assert hero.prompt == "A woman, full figure.  Two spaces kept."
    assert hero.inputs == {"size": "832x1248"}
    assert scene.inputs["references"] == [project.root / "items" / "woman.hero" / "v001.png"]
    assert scene.inputs["size"] == "1664x928" and scene.inputs["steps"] == 6
    assert scene.seed == project.spec().item("coffee").seed(project.id)
    assert project.state().items["coffee"].versions[0].elapsed_s is not None


def test_info_comes_from_the_registry(tmp_path: Path) -> None:
    port = FrameModels(FakeModels())
    info = port.info("qwen-image-2.1-turbo")
    assert (info.max_references, info.local, info.commercial_use) == (6, True, False)
    assert "1664x928" in info.sizes and "references" in (info.inputs or ())
    with pytest.raises(NotFound):
        port.info("no-such-model")
    ws = Workspace(tmp_path / "frame", models=port)
    bad = TEXT.replace('size = "1664x928"', 'size = "1000x1000"')
    with pytest.raises(Exception, match="size 1000x1000"):
        ws.import_text(bad, "toml")


def test_a_cancel_ends_the_call_and_interrupts_comfyui(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    started, release = threading.Event(), threading.Event()
    interrupted: list[bool] = []
    monkeypatch.setattr(pause, "interrupt", lambda: (interrupted.append(True), release.set()))

    def slow(call: Call) -> None:
        if call.kind == "generate":
            started.set()
            release.wait(5)

    port, cancel = FrameModels(FakeModels(on_call=slow)), threading.Event()
    threading.Timer(0.2, cancel.set).start()
    with pytest.raises(Cancelled):
        port.generate("qwen-image-2.1-turbo", "p", out=tmp_path / "x.png", seed=1, references=[], inputs={},
                      cancel=cancel)  # fmt: skip
    assert started.is_set() and interrupted == [True]
    assert not (tmp_path / "x.png").exists()  # nothing of a cancelled picture is kept


def test_a_run_holds_one_session_per_model_and_ends_it(tmp_path: Path) -> None:
    """A model's session (which starts ComfyUI, 0025) opens on its first picture, stays open for the
    next, and ends when the run ends, so the clips stage gets its own server."""
    models = FakeModels()
    ws = Workspace(tmp_path / "frame", models=FrameModels(models))
    project = ws.import_text(TEXT, "toml")
    runner = Runner(ws)
    runner.run(project.id)
    runner.drain()
    kinds = [c.kind for c in models.calls if c.kind in ("session", "generate")]
    assert kinds == ["session", "generate", "generate"]  # one session for both pictures
    assert ws.models._open is None  # pyright: ignore[reportPrivateUsage, reportAttributeAccessIssue]
