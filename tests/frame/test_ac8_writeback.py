"""AC-8: dashboard edits are written back to `project.toml`, its comments and order kept; an item whose
fields differ from what made its current version is flagged "changed since made".

Hone Frame: ported from its `tests/e2e/test_ac8_writeback.py` (change 0027)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions

from .conftest import Board, run

pytestmark = pytest.mark.e2e

TEXT = """\
# Morning: my notes stay here
[project]
name = "Write back"

[defaults]
model = "z-image-turbo"   # the fast one

[characters.woman.hero]
# the hero shot
prompt = "a woman"
seed = 7

[places.kitchen.wide]
prompt = "a kitchen"
"""


@pytest.fixture
def dashboard(ws: hf.Workspace) -> Board:
    return Board(ws)


def call(board: Board, method: str, path: str, body: Any = None) -> tuple[int, Any]:
    return board.call(method, path, body)


def test_ac8_edits_keep_comments_and_order(ws: hf.Workspace, dashboard: Board) -> None:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    edit = {"prompt": "a tall woman", "seed": None, "hold": True}
    status, item = call(dashboard, "PATCH", f"/api/projects/{project.id}/items/woman.hero", edit)
    assert status == 200 and item["prompt"] == "a tall woman" and item["hold"] is True
    text = (project.root / "project.toml").read_text()
    assert text == TEXT.replace('prompt = "a woman"\nseed = 7\n', 'prompt = "a tall woman"\nhold = true\n')
    assert item["changed_since_made"] is True and not item["marked"]  # never marked by itself
    view = call(dashboard, "GET", f"/api/projects/{project.id}")[1]
    flags = {i["id"]: i["changed_since_made"] for i in view["items"]}
    assert flags == {"woman.hero": True, "kitchen.wide": False}


def test_ac8_invalid_edits_are_refused_and_not_written(ws: hf.Workspace, dashboard: Board) -> None:
    project = ws.import_text(TEXT, "toml")
    status, error = call(
        dashboard, "PATCH", f"/api/projects/{project.id}/items/woman.hero", {"model": "nope"}
    )
    assert status == 400 and [i["item"] for i in error["items"]] == ["woman.hero"]
    assert "unknown model" in error["items"][0]["message"]
    status, error = call(
        dashboard, "PATCH", f"/api/projects/{project.id}/items/woman.hero", {"colour": "red"}
    )
    assert status == 400 and "unknown field 'colour'" in error["error"]
    assert (project.root / "project.toml").read_text() == TEXT


def test_ac8_json_files_are_written_as_json(ws: hf.Workspace) -> None:
    data = {"project": {"name": "J"}, "places": {"k": {"w": {"model": "z-image-turbo", "prompt": "k"}}}}
    project = ws.import_text(json.dumps(data), "json")
    actions.edit(project, "k.w", {"inputs": {"steps": 4}})
    data = json.loads((project.root / "project.json").read_text())
    assert data["places"]["k"]["w"] == {"model": "z-image-turbo", "prompt": "k", "inputs": {"steps": 4}}


def test_ac8_an_item_added_to_the_file_by_hand_can_be_used_at_once(
    ws: hf.Workspace, dashboard: Board
) -> None:
    project = ws.import_text(TEXT, "toml")
    project.file.write_text(TEXT + '\n[objects.mug.hero]\nprompt = "a mug"\n')  # not through Hone Frame
    base = f"/api/projects/{project.id}/items/mug.hero"
    assert call(dashboard, "POST", f"{base}/unmark", {})[1]["marked"] is False  # not a 500
    assert call(dashboard, "POST", f"{base}/mark", {"dependants": False})[1] == {"marked": ["mug.hero"]}
    assert project.state().items["mug.hero"].status == "todo"
