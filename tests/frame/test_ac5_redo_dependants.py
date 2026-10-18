"""AC-5: marking a base item to redo lists its dependants; with `dependants: true` they are marked; kept
ones are flagged "made from an older" ref after the base is made again.

Hone Frame: ported from its `tests/e2e/test_ac5_redo_dependants.py` (change 0027)."""

from __future__ import annotations

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.errors import RunStateError
from hone_music_video.frame.views import item_view
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import run

pytestmark = pytest.mark.e2e

TEXT = """
[project]
name = "Redo"

[defaults]
model = "qwen-image-edit-2511"

[characters.woman.hero]
prompt = "hero"

[characters.woman.side]
refs = ["woman.hero"]
prompt = "side"

[places.kitchen.wide]
prompt = "kitchen"

[scenes.coffee]
refs = ["woman.side", "kitchen.wide"]
prompt = "coffee"
"""


@pytest.fixture
def made(ws: hf.Workspace) -> hf.Project:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    assert project.run().status == "done"
    return project


def test_ac5_dependants_are_transitive_and_in_file_order(made: hf.Project) -> None:
    assert actions.dependants(made.spec(), "woman.hero") == ["woman.side", "coffee"]
    assert actions.dependants(made.spec(), "kitchen.wide") == ["coffee"]
    assert item_view(made, "woman.hero").dependants == ["woman.side", "coffee"]


def test_ac5_redo_with_dependants_marks_them(ws: hf.Workspace, made: hf.Project, fake: FakeModels) -> None:
    assert actions.mark(made, "woman.hero", with_dependants=True) == ["woman.hero", "woman.side", "coffee"]
    view = item_view(made, "woman.hero")
    assert view.marked and view.status == "done" and view.current == 1  # still shows its current version
    run(ws, made)
    assert fake.prompts[4:] == ["hero", "side", "coffee"]
    assert not any(item_view(made, i).older_refs for i in ("woman.side", "coffee"))


def test_ac5_kept_dependants_are_flagged(ws: hf.Workspace, made: hf.Project) -> None:
    assert actions.mark(made, "woman.hero") == ["woman.hero"]
    run(ws, made)
    assert item_view(made, "woman.side").older_refs == ["woman.hero"]
    assert item_view(made, "coffee").older_refs == []  # made from the side, which is unchanged
    assert actions.mark(made, "woman.side") == ["woman.side"] and item_view(made, "woman.side").marked
    actions.unmark(made, "woman.side")
    assert not item_view(made, "woman.side").marked
    assert item_view(made, "woman.side").older_refs == ["woman.hero"]  # still flagged until made again


def test_ac5_a_provided_item_is_never_marked(ws: hf.Workspace, tmp_path: object) -> None:
    project = ws.import_text(TEXT, "toml")
    actions.provide(project, "woman.hero", _png(), "hero.png")
    project.write_text(project.text().replace('prompt = "hero"', 'file = "items/woman.hero/v001.png"'))
    assert project.state().items["woman.hero"].status == "provided"
    with pytest.raises(RunStateError, match="provided file"):
        actions.mark(project, "woman.hero")


def _png() -> bytes:
    import io

    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(out, format="PNG")
    return out.getvalue()
