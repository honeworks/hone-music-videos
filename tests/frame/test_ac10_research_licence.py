"""AC-10: a research-licence model is accepted, with a warning in the project, the item and the models.

Hone Frame: ported from its `tests/e2e/test_ac10_research_licence.py` (change 0027)."""

from __future__ import annotations

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.estimates import measured
from hone_music_video.frame.views import item_view, model_view, project_view
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

pytestmark = pytest.mark.e2e

TEXT = """
[project]
name = "Licence"

[characters.woman.hero]
model = "qwen-image-2.1-turbo"
prompt = "hero"

[places.kitchen.wide]
model = "z-image-turbo"
prompt = "kitchen"
"""


def test_ac10_research_licence_is_a_warning(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    warning = "qwen-image-2.1-turbo: Qwen research licence, not for commercial use"
    assert project.spec().warnings == [warning]
    assert project_view(project).warnings == [warning]
    actions.unmark(project, "woman.hero")
    assert project_view(project).warnings == []  # only for the models of marked items
    assert item_view(project, "woman.hero").license_warning == warning
    assert item_view(project, "kitchen.wide").license_warning is None
    view = model_view(fake.info("qwen-image-2.1-turbo"), measured(ws.root))
    assert view.warning == warning and view.commercial_use is False and view.pose == "reference"
