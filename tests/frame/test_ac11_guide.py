"""AC-11: the guide for chosen models has the per-stage sections, each model's limits, pose support and
licence, and each model's notes under the stages that need them; a new project gets its own GUIDE.md.

Hone Frame: ported from its `tests/e2e/test_ac11_guide.py` (change 0027)."""

from __future__ import annotations

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame.guide import STAGE_TITLES, guide_for
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels
from hone_music_video.testing.frame_fakes import FakeNote

pytestmark = pytest.mark.e2e

NOTES = {
    "qwen-image-edit-2511": [
        FakeNote("faces", "Small faces in a wide shot lose their identity.", "evidence.md"),
        FakeNote("scenes", "Name every reference by its image number."),
        FakeNote("general", "Edits keep what the prompt does not change."),
    ]
}
TEXT = """
[project]
name = "Guide test"

[characters.woman.hero]
model = "z-image-turbo"
prompt = "hero"

[characters.woman.side]
model = "qwen-image-2.1-turbo"
refs = ["woman.hero"]
prompt = "side"
"""


@pytest.fixture
def fake() -> FakeModels:
    return FakeModels(notes=NOTES)


def section(text: str, title: str) -> str:
    """The text of one stage, up to the next stage's heading."""
    start = text.index(f"### {title}") if f"### {title}" in text else text.index(title)
    following = [text.find(f"### {t}", start + 1) for t in STAGE_TITLES.values()]
    end = min([i for i in following if i > start] or [len(text)])
    return text[start:end]


def test_ac11_the_guide_for_two_models(ws: hf.Workspace) -> None:
    text = guide_for(ws, ["z-image-turbo", "qwen-image-edit-2511"])
    for heading in ("## 1. How a project file works", "## 2. Stages", "## 3. Models"):
        assert heading in text
    assert all(title in text for title in STAGE_TITLES.values())
    assert "Small faces in a wide shot lose their identity. (evidence.md)" in text
    assert "Small faces" not in section(text, STAGE_TITLES["objects"])  # notes go where the stage needs them
    assert "Name every reference by its image number." in section(text, STAGE_TITLES["scenes"])
    assert "Edits keep what the prompt does not change." in text.split("## 3. Models")[1]
    assert "References: no reference pictures" in text and "References: up to 3 reference pictures" in text
    assert "Pose support: as a reference picture" in text and "Pose support: none" in text
    assert "RESEARCH-LICENCE WARNING" not in text


def test_ac11_a_research_licence_is_warned_and_a_project_gets_its_guide(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    written = (project.root / "GUIDE.md").read_text(encoding="utf-8")
    assert written == guide_for(ws, [], project.id)
    assert written.startswith("# Prompt guide: Guide test")
    assert "`z-image-turbo`, `qwen-image-2.1-turbo`" in written  # the project's models, in file order
    assert "RESEARCH-LICENCE WARNING: `qwen-image-2.1-turbo`" in written


def test_ac11_the_guide_shows_the_time_measured_here(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    for seconds in (10.0, 12.0, 14.0):
        project.log("item_made", "woman.hero", model="z-image-turbo", size="", elapsed_s=seconds)
    assert "default size: about 12 s per image (median)" in guide_for(ws, ["z-image-turbo"])


def test_ac11_the_guide_lists_the_inputs_an_item_may_set(ws: hf.Workspace) -> None:
    text = guide_for(ws, ["qwen-image-2.1-turbo"])
    line = next(x for x in text.splitlines() if x.startswith("- `inputs` it takes:"))
    assert "`ref_resolution`" in line and "`steps`" in line  # the model's own inputs, from its guide
    assert "`size`" not in line and "`references`" not in line  # an item's own fields, never `inputs`
