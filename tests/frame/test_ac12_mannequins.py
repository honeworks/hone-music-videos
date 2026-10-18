"""AC-12 (since D-072): mannequins were removed. A `mannequin:` ref or a `[mannequins.*]` table is refused,
naming the item and saying what to do instead; a pose picture is an item with `file`, referred to like any
item.

Hone Frame: ported from its `tests/e2e/test_ac12_mannequins.py` (change 0027)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from hone_music_video import frame as hf
from hone_music_video.frame.errors import InvalidRequest
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import run, statuses

pytestmark = pytest.mark.e2e

REMOVED = (
    'mannequins were removed; give a pose picture as an item with `file = "..."` '
    "and refer to it like any item"
)
TEXT = """
[project]
name = "Poses"

[characters.woman.hero]
model = "z-image-turbo"
prompt = "hero"

[characters.woman.kneeling]
model = "qwen-image-edit-2511"
refs = ["woman.hero", "mannequin:kneeling"]
prompt = "The woman from image 1 in the pose of the figure in image 2."
"""


def problems(ws: hf.Workspace, text: str) -> list[tuple[str, str]]:
    with pytest.raises(InvalidRequest) as caught:
        ws.import_text(text, "toml")
    return [(p.item, p.message) for p in caught.value.problems]


def test_ac12_a_mannequin_ref_is_refused(ws: hf.Workspace) -> None:
    assert problems(ws, TEXT) == [("woman.kneeling", f"refers to 'mannequin:kneeling': {REMOVED}")]
    assert not list((ws.root / "projects").iterdir())  # nothing left behind


def test_ac12_a_mannequins_table_is_refused(ws: hf.Workspace) -> None:
    text = '[project]\nname = "Poses"\n\n[mannequins.lunge]\nmodel = "z-image-turbo"\nprompt = "a lunge"\n'
    assert problems(ws, text) == [("mannequins", REMOVED)]


def test_ac12_a_pose_picture_is_an_item_with_a_file(tmp_path: Path, fake: FakeModels) -> None:
    folder = tmp_path / "mine"
    (folder / "assets").mkdir(parents=True)
    Image.new("RGB", (32, 48), (200, 180, 150)).save(folder / "assets" / "kneeling.png")
    text = TEXT.replace(
        "[characters.woman.kneeling]",
        '[characters.woman.pose]\nfile = "assets/kneeling.png"\n\n[characters.woman.kneeling]',
    ).replace("mannequin:kneeling", "woman.pose")
    (folder / "poses.toml").write_text(text, encoding="utf-8")
    ws = hf.Workspace(tmp_path / "studio", models=fake)
    project = ws.import_file(folder / "poses.toml")
    run(ws, project)
    assert statuses(project) == {"woman.hero": "done", "woman.pose": "provided", "woman.kneeling": "done"}
    assert fake.calls[1].references[1] == project.current_image(project.state(), "woman.pose")
