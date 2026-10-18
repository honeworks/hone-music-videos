"""AC-15: a format-"1" workspace is refused with a message that says what to do.

Hone Frame: ported from its `tests/e2e/test_ac15_old_workspace.py` (change 0027)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame.errors import HoneFrameError
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

pytestmark = pytest.mark.e2e

MESSAGE = "this workspace was made by an older Hone Frame; start a new workspace and import your project file"


def test_ac15_format_1_is_refused(tmp_path: Path) -> None:
    (tmp_path / "workspace.json").write_text(json.dumps({"format_version": "1"}))
    with pytest.raises(HoneFrameError) as raised:
        hf.Workspace(tmp_path)
    assert MESSAGE in str(raised.value)


def test_ac15_a_newer_format_says_upgrade(tmp_path: Path) -> None:
    (tmp_path / "workspace.json").write_text(json.dumps({"format_version": "3"}))
    with pytest.raises(HoneFrameError, match="upgrade hone-frame"):
        hf.Workspace(tmp_path)


def test_ac15_a_new_workspace_is_format_2(tmp_path: Path) -> None:
    hf.Workspace(tmp_path / "new")
    assert json.loads((tmp_path / "new" / "workspace.json").read_text())["format_version"] == "2"


def test_ac15_an_old_project_in_a_new_workspace_is_refused(tmp_path: Path) -> None:
    ws = hf.Workspace(tmp_path / "studio", models=FakeModels())
    project = ws.import_text(
        '[project]\nname = "Old"\n[places.k.w]\nmodel = "z-image-turbo"\nprompt = "k"\n', "toml"
    )
    state = json.loads((project.root / "state.json").read_text())
    (project.root / "state.json").write_text(json.dumps(state | {"format_version": "1"}))
    with pytest.raises(HoneFrameError) as raised:
        project.state()
    assert MESSAGE in str(raised.value) and "state.json" in str(raised.value)
