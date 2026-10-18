"""AC-7: replacing an item with a file makes a `provided` version and asks about its dependants.

Hone Frame: ported from its `tests/e2e/test_ac7_replace_file.py` (change 0027)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.errors import InvalidRequest
from hone_music_video.frame.views import item_view

from .conftest import run

pytestmark = pytest.mark.e2e

TEXT = """
[project]
name = "Replace"

[characters.woman.hero]
model = "z-image-turbo"
prompt = "hero"

[characters.woman.side]
model = "qwen-image-edit-2511"
refs = ["woman.hero"]
prompt = "side"
"""


def jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (30, 20), "blue").save(out, format="JPEG")
    return out.getvalue()


def test_ac7_a_file_becomes_a_provided_version(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    assert actions.dependants(project.spec(), "woman.hero") == ["woman.side"]  # the question's list
    marked = actions.provide(project, "woman.hero", jpeg(), "painted.jpg", with_dependants=True)
    assert marked == ["woman.side"]
    view = item_view(project, "woman.hero")
    assert [v.source for v in view.versions] == ["generated", "provided"] and view.current == 2
    assert view.status == "done" and not view.marked
    version = project.state().items["woman.hero"].version(2)
    assert version is not None and version.original == "painted.jpg"
    with Image.open(project.root / version.file) as image:
        assert image.format == "PNG" and image.size == (30, 20)


def test_ac7_kept_dependants_are_flagged(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    assert actions.provide(project, "woman.hero", jpeg(), "painted.jpg") == []
    assert item_view(project, "woman.side").older_refs == ["woman.hero"]


def test_ac7_not_an_image_is_refused(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    with pytest.raises(InvalidRequest, match="not an image"):
        actions.provide(project, "woman.hero", b"hello", "notes.txt")
    assert not project.state().items["woman.hero"].versions


def test_ac7_a_changed_file_field_makes_a_new_version(ws: hf.Workspace, tmp_path: object) -> None:
    project = ws.import_text(TEXT, "toml")
    (project.root / "assets").mkdir()
    for name, colour in (("a.png", "red"), ("b.png", "green")):
        Image.new("RGB", (8, 8), colour).save(project.root / "assets" / name)
    actions.edit(project, "woman.hero", {"file": "assets/a.png", "prompt": None, "model": None})
    actions.edit(project, "woman.hero", {"file": "assets/b.png"})
    actions.edit(project, "woman.hero", {"file": "assets/b.png"})  # unchanged: no new version
    state = project.state().items["woman.hero"]
    assert state.status == "provided" and [v.original for v in state.versions] == ["a.png", "b.png"]


def test_ac7_a_replaced_file_item_stays_replaced(ws: hf.Workspace, tmp_path: Path) -> None:
    """Replacing an item that has a `file` (or choosing a version) is not undone by the next write."""
    Image.new("RGB", (8, 8), "red").save(tmp_path / "mug.png")
    text = TEXT + '\n[objects.mug.hero]\nfile = "mug.png"\n'
    project = ws.import_text(text, "toml", files_root=tmp_path)
    actions.provide(project, "mug.hero", jpeg(), "painted.jpg")
    assert project.state().items["mug.hero"].current == 2
    actions.edit(project, "woman.hero", {"prompt": "another hero"})  # an unrelated edit
    mug = project.state().items["mug.hero"]
    assert (mug.current, len(mug.versions), mug.status) == (2, 2, "provided")
    actions.use_version(project, "mug.hero", 1)
    actions.edit(project, "woman.hero", {"prompt": "a third hero"})
    assert project.state().items["mug.hero"].current == 1
    Image.new("RGB", (8, 8), "green").save(project.root / "assets" / "mug.png")  # the file itself changed
    actions.edit(project, "woman.hero", {"prompt": "a fourth hero"})
    mug = project.state().items["mug.hero"]
    assert (mug.current, [v.original for v in mug.versions]) == (3, ["mug.png", "painted.jpg", "mug.png"])


def test_ac7_a_state_from_before_file_sha256_is_not_imported_twice(ws: hf.Workspace, tmp_path: Path) -> None:
    Image.new("RGB", (8, 8), "red").save(tmp_path / "mug.png")
    project = ws.import_text(TEXT + '\n[objects.mug.hero]\nfile = "mug.png"\n', "toml", files_root=tmp_path)
    with project.editing() as state:
        state.items["mug.hero"].file_sha256 = None  # written by an older Hone Frame
    actions.edit(project, "woman.hero", {"prompt": "another hero"})
    assert len(project.state().items["mug.hero"].versions) == 1
