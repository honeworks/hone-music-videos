"""AC-4: pausing during an image cancels it (the fake model sees the cancel), the item stays marked,
resume makes it again from the top; stop ends the run.

Hone Frame: ported from its `tests/e2e/test_ac4_pause.py` (change 0027)."""

from __future__ import annotations

import threading

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame._files import project_lock, running
from hone_music_video.frame.errors import RunStateError
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import run

pytestmark = pytest.mark.e2e

TEXT = """
[project]
name = "Pause"

[defaults]
model = "z-image-turbo"

[places.kitchen.wide]
prompt = "kitchen"

[places.hall.wide]
prompt = "hall"
"""


def start(ws: hf.Workspace, project: hf.Project) -> tuple[hf.Runner, threading.Thread]:
    """Run in a thread and return once a call blocks (the fake holds it until it is cancelled)."""
    runner = hf.Runner(ws)
    runner.run(project.id)
    thread = threading.Thread(target=runner.drain)
    thread.start()
    assert isinstance(ws.models, FakeModels)
    assert ws.models.started.wait(5)
    return runner, thread


def made_before(ws: hf.Workspace, project: hf.Project, fake: FakeModels, how: str) -> None:
    """Bring the kitchen to `how` ("todo", "done", "waiting" or "failed"), marked to run again."""
    if how == "failed":
        fake.fail_generate()
        run(ws, project)
    elif how != "todo":
        runner = run(ws, project)  # the kitchen holds: the run waits for it
        if how == "done":
            runner.accept(project.id, "kitchen.wide")
            runner.drain()
        assert project.state().items["kitchen.wide"].status == how
        actions.mark(project, "kitchen.wide")
    fake.started.clear()


@pytest.mark.parametrize(
    ("how", "count", "block_after"),
    [("todo", 1, 0), ("todo", 3, 1), ("done", 1, 0), ("waiting", 1, 0), ("failed", 1, 0)],
    ids=["todo", "todo-count-3-during-image-2", "done-redone", "waiting-redone", "failed-redone"],
)
def test_ac4_pause_puts_the_item_back_exactly(
    ws: hf.Workspace, fake: FakeModels, how: str, count: int, block_after: int
) -> None:
    text = TEXT.replace('prompt = "kitchen"', f'prompt = "kitchen"\ncount = {count}\nhold = true')
    project = ws.import_text(text, "toml")
    made_before(ws, project, fake, how)
    before = project.state().items["kitchen.wide"]
    calls = len(fake.calls)
    fake.block, fake.block_after = True, calls + block_after
    runner, thread = start(ws, project)
    assert project.run().current == "kitchen.wide"
    assert project.state().items["kitchen.wide"].status == "running"
    runner.pause(project.id)
    assert project.run().status in ("pausing", "paused")  # paused once the cancelled call returns
    thread.join(5)
    assert not thread.is_alive()
    assert fake.calls[-1].cancelled and len(fake.calls) == calls + block_after + 1
    assert project.run().status == "paused"
    after = project.state().items["kitchen.wide"]
    assert after.marked and (after.status, after.current, after.candidates, after.error) == (
        before.status, before.current, before.candidates, before.error,
    )  # fmt: skip
    assert (before.error is not None) == (how == "failed")
    assert len(after.versions) == len(before.versions) + block_after  # made images stay as versions
    assert len(fake.calls) == calls + block_after + 1  # the hall was not started

    fake.block = False
    runner.resume(project.id)
    runner.drain()  # made again from the top; it holds, so the run waits for it
    assert fake.prompts[-count:] == ["kitchen"] * count and project.run().status == "waiting"
    again = project.state().items["kitchen.wide"]
    assert again.status == "waiting" and len(again.versions) == len(after.versions) + count


def test_ac4_pause_cancels_the_image_and_resume_makes_it_again(ws: hf.Workspace, fake: FakeModels) -> None:
    fake.block = True
    project = ws.import_text(TEXT, "toml")
    runner, thread = start(ws, project)
    runner.pause(project.id)
    thread.join(5)
    assert not thread.is_alive()
    assert fake.calls[0].cancelled and project.run().status == "paused"
    kitchen = project.state().items["kitchen.wide"]
    assert kitchen.marked and kitchen.status == "todo" and not kitchen.versions
    fake.block = False
    runner.resume(project.id)
    runner.drain()
    assert fake.prompts == ["kitchen", "kitchen", "hall"]
    assert project.run().status == "done"


def test_ac4_stop_ends_the_run(ws: hf.Workspace, fake: FakeModels) -> None:
    fake.block = True
    project = ws.import_text(TEXT, "toml")
    runner, thread = start(ws, project)
    runner.stop(project.id)
    thread.join(5)
    assert not thread.is_alive()
    assert fake.calls[0].cancelled and project.run().status == "stopped"
    assert project.state().items["kitchen.wide"].marked
    with pytest.raises(RunStateError, match="not paused"):
        runner.resume(project.id)
    with pytest.raises(RunStateError, match="no run to pause"):
        runner.pause(project.id)
    fake.block = False
    runner.run(project.id)  # run starts a new one
    runner.drain()
    assert project.run().status == "done" and project.run().made == ["kitchen.wide", "hall.wide"]


def test_ac4_pause_a_queued_run(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    runner = hf.Runner(ws)
    runner.run(project.id)
    runner.pause(project.id)
    assert project.run().status == "paused"
    runner.drain()  # nothing queued
    assert project.run().status == "paused"
    runner.stop(project.id)
    assert project.run().status == "stopped"


def test_ac4_a_dead_process_leaves_no_running_run(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    hf.Runner(ws).run(project.id)  # queued by a runner that never runs it
    assert hf.Runner(ws).recover() == [project.id]
    assert project.run().status == "stopped" and "run it again" in project.run().reason


def test_ac4_close_stops_the_background_runner(ws: hf.Workspace, fake: FakeModels) -> None:
    fake.block = True
    project = ws.import_text(TEXT, "toml")
    runner = hf.Runner(ws).start()
    runner.run(project.id)
    assert fake.started.wait(5)
    runner.close()
    assert project.run().status == "stopped" and fake.calls[0].cancelled


def test_ac4_a_pause_as_the_run_ends_does_not_undo_its_end(
    ws: hf.Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pause that arrives after the last item, while the end is being written, finds no current run."""
    project = ws.import_text(TEXT, "toml")
    runner = hf.Runner(ws)
    finish = runner._finish  # pyright: ignore[reportPrivateUsage]
    answers: list[str] = []

    def pause_meanwhile(p: hf.Project, end: object) -> None:
        try:
            runner.pause(p.id)
            answers.append("paused")
        except RunStateError as exc:
            answers.append(str(exc))
        finish(p, end)  # pyright: ignore[reportArgumentType]

    monkeypatch.setattr(runner, "_finish", pause_meanwhile)
    runner.run(project.id)
    runner.drain()
    assert answers == ["pause is running: there is no run to pause"]
    assert project.run().status == "done"


def test_ac4_an_item_left_running_is_put_back(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    hf.Runner(ws).run(project.id)
    with project.editing() as state:  # as a process that died while making them
        state.items["kitchen.wide"].status = "running"
        state.items["hall.wide"].status, state.items["hall.wide"].current = "running", 1
    assert hf.Runner(ws).recover() == [project.id]
    items = project.state().items
    assert (items["kitchen.wide"].status, items["kitchen.wide"].marked) == ("todo", True)
    assert items["hall.wide"].status == "done"


def test_ac4_run_json_changes_from_two_threads_are_all_kept(ws: hf.Workspace) -> None:
    """Every change of run.json re-reads it under the project lock (decisions D-068)."""
    project = ws.import_text(TEXT, "toml")

    def add(prefix: str) -> None:
        for n in range(40):
            with project_lock(project.root):
                project.update_run(made=[*project.run().made, f"{prefix}{n}"])

    threads = [threading.Thread(target=add, args=(p,)) for p in "ab"]
    for thread in threads:
        thread.start()
    project.update_run(status="pausing")
    for thread in threads:
        thread.join()
    assert len(project.run().made) == 80 and project.run().status == "pausing"
    assert project.update_run(when=("running",), status="paused").status == "pausing"  # not running: kept


def test_ac4_recover_leaves_a_run_another_process_is_making(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    other = ws.import_text(TEXT.replace('name = "Pause"', 'name = "Other"'), "toml")
    for p in (project, other):
        hf.Runner(ws).run(p.id)
        with p.editing() as state:
            state.items["kitchen.wide"].status = "running"
    with running(project.root):  # as the dashboard's process, making it now
        assert hf.Runner(ws).recover() == [other.id]
    assert project.run().status == "queued" and project.state().items["kitchen.wide"].status == "running"
    assert other.state().items["kitchen.wide"].status == "todo"


def test_ac4_recover_can_be_limited_to_one_project(ws: hf.Workspace) -> None:
    first = ws.import_text(TEXT, "toml")
    second = ws.import_text(TEXT.replace('name = "Pause"', 'name = "Other"'), "toml")
    for p in (first, second):
        hf.Runner(ws).run(p.id)
    assert hf.Runner(ws).recover([second.id]) == [second.id]
    assert first.run().status == "queued" and second.run().status == "stopped"
