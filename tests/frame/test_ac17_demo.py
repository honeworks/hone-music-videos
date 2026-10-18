"""AC-17: an optional `[demo]` of reference-free prompts is made first, one image per prompt with seeds
`seed + k`, wherever the table sits in the file; it never waits for a pick, and `hold = true` stops the
run after the last demo image; references to and from the demo are refused; a file without `[demo]` is
unchanged (decisions D-077).

Hone Frame: ported from its `tests/e2e/test_ac17_demo.py` (change 0027)."""

from __future__ import annotations

from typing import Any

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.errors import InvalidRequest
from hone_music_video.frame.views import item_view, project_view
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import Board, run, statuses

pytestmark = pytest.mark.e2e

BODY = """\
[project]
name = "Night palace"

[defaults]
model = "qwen-image-edit-2511"
size = "1024x576"

[places.palace.wide]
prompt = "palace"

[scenes.arrival]
refs = ["palace.wide"]
prompt = "arrival"
count = 2
"""
DEMO = """
# the feel of the whole film, before anything else
[demo]
seed = 7
prompts = [
  "A moonlit stone palace, painterly",   # the look
  \"\"\"A young woman in a dark bedchamber,
candle light\"\"\",
  "  a chase across the roofs  ",
]
"""
PROMPTS = ["A moonlit stone palace, painterly", "A young woman in a dark bedchamber,\ncandle light",
           "  a chase across the roofs  "]  # fmt: skip
TEXT = BODY + DEMO  # the demo at the end of the file


def test_ac17_the_demo_is_made_first_one_image_per_prompt(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    assert [i.id for i in project.spec().items][:3] == ["demo.1", "demo.2", "demo.3"]
    run(ws, project)
    first = fake.calls[:3]
    assert [c.prompt for c in first] == PROMPTS  # first, in order, byte for byte
    assert [c.seed for c in first] == [7, 8, 9]
    assert all(c.references == [] for c in first)  # no references sent
    assert all(c.model == "qwen-image-edit-2511" and c.inputs.get("size") == "1024x576" for c in first)
    assert fake.prompts[3] == "palace"
    view = item_view(project, "demo.2")
    assert view.group == "demo" and view.prompt == PROMPTS[1] and view.refs == []
    assert view.effective["seed"] == 8 and view.seed == 7 and view.effective["count"] == 1
    assert [v.prompt for v in view.versions] == [PROMPTS[1]]
    assert [i.group for i in project_view(project).items][:3] == ["demo"] * 3


def test_ac17_no_pick_wait_and_the_run_goes_on(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    assert {k: v for k, v in statuses(project).items() if k.startswith("demo.")} == dict.fromkeys(
        ("demo.1", "demo.2", "demo.3"), "done"
    )
    assert statuses(project)["arrival"] == "waiting"  # its own pick; the demo waited for nothing


def test_ac17_hold_stops_the_run_after_the_last_demo_image(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT.replace("seed = 7", "seed = 7\nhold = true"), "toml")
    assert [i.hold for i in project.spec().items[:3]] == [False, False, True]
    runner = run(ws, project)
    assert fake.prompts == PROMPTS  # nothing else was made
    assert project.run().status == "waiting" and project.run().item == "demo.3"
    assert statuses(project)["demo.3"] == "waiting" and statuses(project)["palace.wide"] == "todo"
    runner.accept(project.id, "demo.3")
    runner.drain()
    assert fake.prompts[3:] == ["palace", "arrival", "arrival"]


def test_ac17_without_a_seed_each_demo_image_has_its_derived_seed(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT.replace("seed = 7\n", ""), "toml")
    seeds = [item_view(project, f"demo.{k}").effective["seed"] for k in (1, 2, 3)]
    assert len(set(seeds)) == 3 and item_view(project, "demo.1").seed is None


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (TEXT.replace("seed = 7", 'seed = 7\nrefs = ["palace.wide"]'), "a demo has no references"),
        (TEXT.replace("seed = 7", 'seed = 7\nfile = "a.png"'), "a demo has no references"),
        (BODY + "\n[demo]\nprompts = []\n", "prompts is empty"),
        (TEXT.replace('"  a chase across the roofs  "', '"  "'), "prompt 3 is empty"),
        (BODY + "\n[demo]\nseed = 1\n", "no prompts"),
        (BODY + '\n[demo]\nprompts = ["a"]\ncount = 2\n', "unknown field 'count': [demo] takes"),
        (TEXT.replace('refs = ["palace.wide"]', 'refs = ["demo.1"]'), "demo pictures are a preview"),
        (BODY.replace('model = "qwen-image-edit-2511"\n', "") + DEMO, "no model"),
    ],
    ids=["refs", "file", "empty-list", "empty-prompt", "no-prompts", "count", "ref-to-demo", "no-model"],
)
def test_ac17_refused(ws: hf.Workspace, text: str, message: str) -> None:
    with pytest.raises(InvalidRequest) as refused:
        ws.import_text(text, "toml")
    assert any(message in p.message for p in refused.value.problems), refused.value.problems


def test_ac17_a_file_without_demo_is_unchanged(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(BODY, "toml")
    assert [i.id for i in project.spec().items] == ["palace.wide", "arrival"]
    run(ws, project)
    assert fake.prompts == ["palace", "arrival", "arrival"]


def test_ac17_editing_a_demo_item(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    actions.edit(project, "demo.2", {"prompt": "A young woman by a window", "size": "1024x1024"})
    spec = project.spec()
    assert spec.item("demo.2").prompt == "A young woman by a window"
    assert [spec.item(f"demo.{k}").size for k in (1, 2, 3)] == ["1024x1024"] * 3  # shared by the demo
    with pytest.raises(InvalidRequest, match="refs"):
        actions.edit(project, "demo.1", {"refs": ["palace.wide"]})
    with pytest.raises(InvalidRequest, match="empty"):
        actions.edit(project, "demo.1", {"prompt": None})


@pytest.fixture
def dashboard(ws: hf.Workspace) -> Board:
    return Board(ws)


def call(board: Board, method: str, path: str, body: Any = None) -> tuple[int, Any]:
    return board.call(method, path, body)


def test_ac17_dashboard_write_back_keeps_comments(ws: hf.Workspace, dashboard: Board) -> None:
    project = ws.import_text(TEXT, "toml")
    path = f"/api/projects/{project.id}/items/demo.3"
    status, item = call(dashboard, "PATCH", path, {"prompt": 'a chase across the "roofs"', "hold": True})
    assert status == 200 and item["prompt"] == 'a chase across the "roofs"'
    assert item["effective"]["hold"] is True
    text = project.text()
    assert "# the feel of the whole film" in text and "# the look" in text
    assert project.spec().item("demo.3").prompt == 'a chase across the "roofs"'
    assert project.spec().item("demo.1").prompt == PROMPTS[0] and "hold = true" in text
    status, error = call(dashboard, "PATCH", path, {"count": 2})
    assert status == 400 and "demo" in error["items"][0]["message"]
