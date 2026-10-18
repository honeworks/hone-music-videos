"""AC-16: an item with `prompts = [...]` makes one prompt at a time: the first (or the one in use), and
another only when the owner runs it, with seeds `seed + k`; each version records its own prompt; running a
prompt keeps the picture in use and marks nothing made from it (hone-music-video 0033); the combinations
that cannot mean one thing are refused; an old `count` file is unchanged (decisions D-076).

Hone Frame: ported from its `tests/e2e/test_ac16_prompts.py` (change 0027); hone-music-video 0033 changes
"one image per prompt, then a pick"."""

from __future__ import annotations

import re
from typing import Any

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.errors import InvalidRequest, NotFound
from hone_music_video.frame.making import made_with
from hone_music_video.frame.views import item_view
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import Board, run, statuses

pytestmark = pytest.mark.e2e

TEXT = """\
[project]
name = "Shots"

[defaults]
model = "qwen-image-edit-2511"
count = 2                                # ignored by an item with prompts

[places.hall.wide]
prompt = "hall"
count = 1

[scenes.chase]
refs = ["hall.wide"]
seed = 40
# three shots of one moment
prompts = [
  "wide: she runs down the hall",
  \"\"\"close: her face,
out of breath\"\"\",
  "low: her feet on the tiles",
]

[scenes.after]
refs = ["hall.wide"]
prompt = "after"
count = 1
"""
PROMPTS = ["wide: she runs down the hall", "close: her face,\nout of breath", "low: her feet on the tiles"]


LATER = (
    TEXT
    + """
[scenes.later]
refs = ["chase"]
prompt = "later"
"""
)


def test_ac16_only_the_first_prompt_is_made(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    assert [(c.prompt, c.seed) for c in fake.calls if c.prompt in PROMPTS] == [(PROMPTS[0], 40)]
    st = project.state().items["chase"]
    assert st.status == "done" and st.current == 1 and [v.prompt for v in st.versions] == [PROMPTS[0]]
    assert project.run().status == "done"  # one picture never waits for a pick
    view = item_view(project, "chase")
    assert view.prompts == PROMPTS and view.effective["prompts"] == PROMPTS
    assert view.effective["count"] == 3 and view.effective["per_run"] == 1 and view.count is None
    assert view.prompt == "" and item_view(project, "hall.wide").prompts is None


def test_ac16_run_this_prompt(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(LATER, "toml")
    run(ws, project)
    actions.run_prompt(project, "chase", 2)
    assert item_view(project, "chase").run_prompt == 2
    assert {k for k, st in project.state().items.items() if st.marked} == {"chase"}  # nothing made from it
    calls = len(fake.calls)
    run(ws, project)
    assert [(c.prompt, c.seed) for c in fake.calls[calls:]] == [(PROMPTS[2], 42)]  # that prompt alone
    st = project.state().items["chase"]
    assert st.current == 1 and st.status == "done"  # the picture in use stays
    assert [(v.n, v.prompt) for v in st.versions] == [(1, PROMPTS[0]), (2, PROMPTS[2])]
    assert st.run_prompt is None and not st.marked and not project.state().items["later"].marked
    assert actions.use_version(project, "chase", 2, with_dependants=True) == ["later"]  # as before

    # a plain mark makes the prompt of the picture in use again
    actions.mark(project, "chase")
    calls = len(fake.calls)
    run(ws, project)
    assert [c.prompt for c in fake.calls[calls:]] == [PROMPTS[2], "later", "later"]  # count = 2
    assert project.state().items["chase"].current == 3


def test_ac16_run_this_prompt_refused(ws: hf.Workspace) -> None:
    project = ws.import_text(LATER, "toml")
    with pytest.raises(InvalidRequest):
        actions.run_prompt(project, "later", 0)  # one prompt: Mark to run makes it
    with pytest.raises(NotFound):
        actions.run_prompt(project, "chase", 3)
    actions.run_prompt(project, "chase", 1)
    actions.unmark(project, "chase")
    assert project.state().items["chase"].run_prompt is None


def test_ac16_run_this_prompt_on_the_dashboard(ws: hf.Workspace, dashboard: Board) -> None:
    project = ws.import_text(TEXT, "toml")
    status, item = call(
        dashboard, "POST", f"/api/projects/{project.id}/items/chase/run-prompt", {"prompt": 1}
    )
    assert status == 200 and item["marked"] and item["run_prompt"] == 1
    status, _ = call(dashboard, "POST", f"/api/projects/{project.id}/items/chase/run-prompt", {"prompt": 9})
    assert status == 404


def test_ac16_one_prompt_is_like_prompt(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT.replace('  "low: her feet on the tiles",\n', "").replace(
        '  "wide: she runs down the hall",\n', ""), "toml")  # fmt: skip
    project.write_text(project.text().replace('"""close: her face,\nout of breath"""', '"close"'))
    run(ws, project)
    assert statuses(project)["chase"] == "done" and project.run().status == "done"
    assert [c.seed for c in fake.calls if c.prompt == "close"] == [40]


EMPTY_LIST = re.sub(r"prompts = \[.*?\n\]\n", "prompts = []\n", TEXT, count=1, flags=re.S)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (TEXT.replace("seed = 40", 'seed = 40\nprompt = "one"'), "set prompt or prompts, not both"),
        (TEXT.replace("seed = 40", "seed = 40\ncount = 2"), "count = 2, but prompts has 3"),
        (EMPTY_LIST, "prompts"),
        (TEXT.replace("count = 2  ", 'prompts = ["a"]  '), "unknown field 'prompts': [defaults] takes"),
        (TEXT.replace('  "low: her feet on the tiles",', '  "",'), "prompt 3 is empty"),
    ],
    ids=["both", "count", "empty-list", "defaults", "empty-prompt"],
)
def test_ac16_refused_combinations(ws: hf.Workspace, text: str, message: str) -> None:
    assert text != TEXT
    with pytest.raises(InvalidRequest) as refused:
        ws.import_text(text, "toml")
    items = {p.item for p in refused.value.problems}
    assert items == ({"defaults"} if "defaults" in message else {"chase"})
    assert any(message in p.message for p in refused.value.problems), refused.value.problems


def test_ac16_a_matching_count_is_accepted(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT.replace("seed = 40", "seed = 40\ncount = 3", 1), "toml")
    assert project.spec().item("chase").count == 3


def test_ac16_an_old_count_file_is_unchanged(ws: hf.Workspace, fake: FakeModels) -> None:
    old = TEXT.replace("count = 2  ", "count = 3  ")
    old = old[: old.index("[scenes.chase]")] + old[old.index("[scenes.after]") :]
    project = ws.import_text(old.replace('prompt = "after"\ncount = 1', 'prompt = "after"'), "toml")
    run(ws, project)
    assert fake.prompts == ["hall", "after", "after", "after"]
    assert [c.seed for c in fake.calls[1:]] == [fake.calls[1].seed + k for k in range(3)]
    after = project.state().items["after"]
    assert after.status == "waiting" and [v.prompt for v in after.versions] == ["after"] * 3
    item = project.spec().item("after")
    assert set(made_with(project.id, item)) == {
        "prompt",
        "negative",
        "model",
        "size",
        "seed",
        "refs",
        "inputs",
    }
    view = item_view(project, "after")
    assert view.prompts is None and view.effective["prompts"] == ["after"] * 3


def test_ac16_changed_since_made_when_one_prompt_changes(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    assert item_view(project, "chase").changed_since_made is False
    actions.edit(project, "chase", {"prompts": [PROMPTS[0], PROMPTS[1], "low: her shoes on the tiles"]})
    assert item_view(project, "chase").changed_since_made is True
    actions.edit(project, "chase", {"prompts": PROMPTS})
    assert item_view(project, "chase").changed_since_made is False


@pytest.fixture
def dashboard(ws: hf.Workspace) -> Board:
    return Board(ws)


def call(board: Board, method: str, path: str, body: Any = None) -> tuple[int, Any]:
    return board.call(method, path, body)


def test_ac16_dashboard_write_back_keeps_comments(ws: hf.Workspace, dashboard: Board) -> None:
    project = ws.import_text(TEXT, "toml")
    path = f"/api/projects/{project.id}/items/chase"
    changed = [*PROMPTS[:2], "low: her feet", 'a fourth "shot"']
    status, item = call(dashboard, "PATCH", path, {"prompts": changed})
    assert status == 200 and item["prompts"] == changed and item["effective"]["count"] == 4
    text = project.text()
    assert "# three shots of one moment" in text and "# ignored by an item with prompts" in text
    assert project.spec().item("chase").fields["prompts"] == changed  # a TOML array, read back exactly

    # "Use several prompts": a single prompt becomes a list of one
    path = f"/api/projects/{project.id}/items/after"
    status, item = call(dashboard, "PATCH", path, {"prompt": None, "count": None, "prompts": ["after"]})
    assert status == 200 and item["prompts"] == ["after"] and item["prompt"] == ""
    status, item = call(dashboard, "PATCH", path, {"prompts": ["after", "after, from above"]})
    assert status == 200 and item["effective"]["count"] == 2
    assert "prompts = [" in project.text() and "# three shots of one moment" in project.text()

    status, error = call(dashboard, "PATCH", path, {"prompt": "both"})
    assert status == 400 and "set prompt or prompts, not both" in error["items"][0]["message"]
