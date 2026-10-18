"""AC-3: a run makes the topmost marked item first, then the next; a `hold` item stops the run as
`waiting`; accepting continues it; `count = 3` makes three versions and waits for a pick.

Hone Frame: ported from its `tests/e2e/test_ac3_run_order.py` (change 0027)."""

from __future__ import annotations

import time

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.errors import RunStateError
from hone_music_video.frame.notifications import notifications
from hone_music_video.frame.views import item_view
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import run, statuses

pytestmark = pytest.mark.e2e

TEXT = """
[project]
name = "Order"

[defaults]
model = "qwen-image-edit-2511"

[characters.woman.hero]
prompt = "hero"
hold = true

[places.kitchen.wide]
prompt = "kitchen"

[characters.woman.side]
refs = ["woman.hero"]
prompt = "side"

[scenes.coffee]
refs = ["woman.hero", "kitchen.wide"]
prompt = "coffee"
count = 3
"""


def test_ac3_top_to_bottom_with_hold_and_pick(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    runner = run(ws, project)
    assert fake.prompts == ["hero"]  # the topmost first; it holds
    assert project.run().status == "waiting" and "woman.hero" in project.run().reason
    assert statuses(project)["woman.hero"] == "waiting"
    assert [n["kind"] for n in notifications(ws.root)] == ["waiting"]

    runner.accept(project.id, "woman.hero")  # the run continues by itself
    assert project.run().status == "queued"
    runner.drain()
    assert fake.prompts == ["hero", "kitchen", "side", "coffee", "coffee", "coffee"]
    assert [c.seed for c in fake.calls[3:]] == [fake.calls[3].seed + k for k in range(3)]
    coffee = project.state().items["coffee"]
    assert coffee.status == "waiting" and [v.n for v in coffee.versions] == [1, 2, 3]
    assert project.run().status == "waiting"
    assert project.run().made == ["woman.hero", "kitchen.wide", "woman.side", "coffee"]

    runner.accept(project.id, "coffee", 2)  # a pick: nothing is marked, the run is done
    assert project.state().items["coffee"].current == 2
    assert statuses(project) == dict.fromkeys(statuses(project), "done")
    assert project.run().status == "done"
    assert fake.calls[2].references == [project.root / "items" / "woman.hero" / "v001.png"]


def test_ac3_refs_are_sent_in_order(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT.replace("hold = true", ""), "toml")
    run(ws, project)
    coffee = fake.calls[3]
    assert coffee.references == [
        project.root / "items" / "woman.hero" / "v001.png",
        project.root / "items" / "kitchen.wide" / "v001.png",
    ]
    version = project.state().items["coffee"].versions[0]
    assert version.made_from == {"woman.hero": 1, "kitchen.wide": 1}


def test_ac3_accept_needs_a_waiting_item(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    runner = hf.Runner(ws)
    with pytest.raises(RunStateError, match="not waiting"):
        runner.accept(project.id, "woman.hero")


def test_ac3_a_run_needs_a_mark_and_one_at_a_time(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    runner = hf.Runner(ws)
    runner.run(project.id)
    with pytest.raises(RunStateError, match="already queued"):
        runner.run(project.id)
    runner.stop(project.id)
    assert project.run().status == "stopped"
    for item in project.spec().items:
        actions.unmark(project, item.id)
    with pytest.raises(RunStateError, match="nothing"):
        runner.run(project.id)


def test_ac3_projects_run_one_at_a_time_in_order(ws: hf.Workspace, fake: FakeModels) -> None:
    first = ws.import_text(TEXT.replace("hold = true", ""), "toml")
    second = ws.import_text(
        TEXT.replace('name = "Order"', 'name = "Second"').replace("hold = true", ""), "toml"
    )
    fake.block = True
    runner = hf.Runner(ws).start()
    try:
        runner.run(first.id)
        assert fake.started.wait(5)
        runner.run(second.id)
        assert second.run().status == "queued" and second.run().reason == f"queued behind {first.id}"
        assert runner.queue() == [first.id, second.id]
        assert len(fake.calls) == 1 and first.run().current == "woman.hero"  # one call at a time
        fake.block = False
        runner.stop(first.id)  # unblocks the first: its call is cancelled, the second starts
        deadline = time.monotonic() + 10
        while second.run().status != "waiting":
            assert time.monotonic() < deadline, second.run()
            time.sleep(0.01)
    finally:
        runner.close()
    assert first.run().status == "stopped"
    assert [c.cancelled for c in fake.calls] == [True] + [False] * 6  # the second's six calls
    assert {c.prompt for c in fake.calls[1:]} == {"hero", "kitchen", "side", "coffee"}


def test_ac3_once_makes_one_item(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT.replace("hold = true", ""), "toml")
    runner = run(ws, project, once=True)
    assert fake.prompts == ["hero"] and project.run().status == "paused"
    runner.resume(project.id)
    runner.drain()
    assert project.run().status == "waiting"  # coffee, count 3


def test_ac3_a_pick_lists_its_candidates(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT.replace("hold = true", ""), "toml")
    run(ws, project)
    view = item_view(project, "coffee")
    assert view.candidates == [1, 2, 3] and view.count == 3 and view.effective["count"] == 3
    hero = item_view(project, "woman.hero")
    assert hero.model is None and hero.effective["model"] == "qwen-image-edit-2511"  # from [defaults]
    assert hero.seed is None and hero.effective["seed"] == project.spec().item("woman.hero").seed(project.id)
    assert hero.layout is None and hero.versions[0].prompt == "hero"
    hf.Runner(ws).accept(project.id, "coffee", 3)
    assert item_view(project, "coffee").candidates == []
    note = notifications(ws.root)[-1]
    assert note["item"] == "coffee" and note["project_name"] == "Order"


@pytest.mark.parametrize("how", ["use-version", "mark-again", "replace-file", "unmark-below"])
def test_ac3_a_waiting_run_goes_on_however_the_item_stops_waiting(
    ws: hf.Workspace, fake: FakeModels, tmp_path: object, how: str
) -> None:
    """D-074: not only Accept: using a version, marking it again or replacing it also lets the run go on."""
    project = ws.import_text(TEXT, "toml")
    runner = run(ws, project)
    assert project.run().status == "waiting" and project.run().item == "woman.hero"
    if how == "use-version":
        actions.use_version(project, "woman.hero", 1)
    elif how == "mark-again":
        actions.mark(project, "woman.hero")
    elif how == "replace-file":
        actions.provide(
            project, "woman.hero", (project.root / "items" / "woman.hero" / "v001.png").read_bytes(), "h.png"
        )
    else:
        actions.use_version(project, "woman.hero", 1)
        for item in ("kitchen.wide", "woman.side", "coffee"):
            actions.unmark(project, item)
    runner.settle(project.id)
    if how == "unmark-below":
        assert project.run().status == "done"  # nothing is marked: the run ends instead of waiting forever
        return
    assert project.run().status == "queued"
    runner.drain()
    assert project.run().status == "waiting" and project.run().item in ("woman.hero", "coffee")


def test_ac3_a_run_not_waiting_is_left_alone_by_settle(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    runner = run(ws, project)
    runner.settle(project.id)  # still waiting for the hero: nothing changes
    assert project.run().status == "waiting" and project.run().item == "woman.hero"


PICKS = """
[project]
name = "Picks"

[defaults]
model = "qwen-image-edit-2511"

[places.hall.wide]
prompt = "hall"

[scenes.one]
refs = ["hall.wide"]
prompt = "one"
count = 3

[scenes.two]
refs = ["one"]
prompt = "two"

[scenes.three]
refs = ["hall.wide"]
prompt = "three"
count = 2

[sheets.board]
images = ["one", "three"]
"""


def test_ac3_a_pick_does_not_stop_the_run(ws: hf.Workspace, fake: FakeModels) -> None:
    """D-075: a count item waits for its pick without stopping the run; what is made from it is held back
    until the pick, then made when the run goes on by itself."""
    project = ws.import_text(PICKS, "toml")
    runner = run(ws, project)
    assert fake.prompts == ["hall", "one", "one", "one", "three", "three"]  # two and the board held back
    assert statuses(project) == {
        "hall.wide": "done", "one": "waiting", "two": "todo", "three": "waiting", "board": "todo",
    }  # fmt: skip
    assert project.run().status == "waiting" and project.run().item == "one"
    assert "waiting for you: one, three" in project.run().reason
    assert [n["kind"] for n in notifications(ws.root)] == ["waiting"]  # one ring at the end, not per pick

    runner.accept(project.id, "one", 2)  # two can be made now; the board still needs three
    runner.drain()
    assert fake.prompts[-1] == "two" and statuses(project)["two"] == "done"
    assert project.run().status == "waiting" and project.run().item == "three"

    runner.accept(project.id, "three", 1)
    runner.drain()
    assert set(statuses(project).values()) == {"done"} and project.run().status == "done"


def test_ac3_a_hold_still_stops_the_run(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(PICKS.replace('prompt = "hall"', 'prompt = "hall"\nhold = true'), "toml")
    run(ws, project)
    assert fake.prompts == ["hall"] and project.run().item == "hall.wide"  # nothing after a hold
