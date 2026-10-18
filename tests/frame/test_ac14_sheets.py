"""AC-14: a sheet item is composed by Pillow when its images are done, byte-identical on recomposition.

Hone Frame: ported from its `tests/e2e/test_ac14_sheets.py` (change 0027)."""

from __future__ import annotations

import pytest
from PIL import Image

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.making import NOT_READY
from hone_music_video.frame.sheets import LAYOUTS
from hone_music_video.frame.views import run_view
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import run, statuses

pytestmark = pytest.mark.e2e

TEXT = """
[project]
name = "Sheets"

[defaults]
model = "z-image-turbo"

[characters.woman.front]
prompt = "front"

[characters.woman.side]
prompt = "side"

[sheets.turnaround]
layout = "{layout}"
images = ["woman.front", "woman.side"]
labels = ["Front", "Side"]
notes = "Line one.\\nLine two."
palette = ["#C9A27E"]
show_meta = true
"""


@pytest.mark.parametrize("layout", sorted(LAYOUTS))
def test_ac14_sheets_are_composed_and_repeatable(ws: hf.Workspace, fake: FakeModels, layout: str) -> None:
    project = ws.import_text(TEXT.replace("{layout}", layout), "toml")
    run(ws, project)
    assert len(fake.calls) == 2  # the sheet needs no model
    state = project.state().items["turnaround"]
    assert state.status == "done" and state.versions[0].source == "composed"
    assert state.versions[0].made_from == {"woman.front": 1, "woman.side": 1}
    first = (project.root / state.versions[0].file).read_bytes()
    actions.mark(project, "turnaround")
    run(ws, project)
    second = project.state().items["turnaround"].versions[1]
    assert (project.root / second.file).read_bytes() == first
    with Image.open(project.root / second.file) as sheet:
        assert sheet.format == "PNG" and sheet.width > 100


SOURCES = """
[project]
name = "Sources"

[defaults]
model = "z-image-turbo"

[characters.woman.front]
prompt = "front"
hold = true

[characters.woman.side]
prompt = "side"

[sheets.turnaround]
images = ["woman.front", "woman.side"]
"""


def test_ac14_a_sheet_waits_for_a_waiting_source(ws: hf.Workspace) -> None:
    project = ws.import_text(SOURCES, "toml")
    runner = run(ws, project)
    assert project.run().status == "waiting"  # on the front, which holds
    runner.run(project.id)  # the owner runs on without accepting: the side is made, the sheet waits
    runner.drain()
    assert project.run().status == "waiting"
    assert "waiting for you: woman.front" in project.run().reason
    assert project.run().item == "woman.front" and run_view(project).item == "woman.front"
    assert statuses(project)["turnaround"] == "todo" and project.state().items["turnaround"].marked
    runner.accept(project.id, "woman.front")  # the run continues by itself and composes the sheet
    runner.drain()
    assert statuses(project)["turnaround"] == "done" and project.run().status == "done"
    version = project.state().items["turnaround"].versions[0]
    assert version.made_from == {"woman.front": 1, "woman.side": 1}


@pytest.mark.parametrize("source", ["todo", "failed"])
def test_ac14_a_sheet_from_a_source_not_made_fails(ws: hf.Workspace, fake: FakeModels, source: str) -> None:
    project = ws.import_text(SOURCES.replace("hold = true", ""), "toml")
    if source == "failed":
        fake.fail_generate()
        run(ws, project)
    actions.unmark(project, "woman.front")
    run(ws, project)
    sheet = project.state().items["turnaround"]
    assert sheet.status == "failed" and not sheet.versions and project.run().status == "failed"
    assert sheet.error is not None and sheet.error.startswith(f"woman.front {NOT_READY[source]}")
