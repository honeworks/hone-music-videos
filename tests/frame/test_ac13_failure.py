"""AC-13: a failure marks the item `failed` with the error and stops the run; a notification is written.

Hone Frame: ported from its `tests/e2e/test_ac13_failure.py` (change 0027)."""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.notifications import mark_read, notifications
from hone_music_video.frame.views import item_view
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import run, statuses

pytestmark = pytest.mark.e2e

TEXT = """
[project]
name = "Failure"

[defaults]
model = "z-image-turbo"

[places.kitchen.wide]
prompt = "kitchen"

[places.hall.wide]
prompt = "hall"
"""


def test_ac13_a_failure_stops_the_run(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    fake.fail_generate()
    run(ws, project)
    assert statuses(project) == {"kitchen.wide": "failed", "hall.wide": "todo"}
    view = item_view(project, "kitchen.wide")
    assert view.error is not None and "scripted failure" in view.error
    assert view.marked  # run again to retry
    assert project.run().status == "failed" and "kitchen.wide failed" in project.run().reason
    assert len(fake.calls) == 1
    found = notifications(ws.root)
    assert [(n["kind"], n["project"], n["read"]) for n in found] == [("failed", project.id, False)]
    assert mark_read(ws.root, found[0]["id"])["read"] is True
    assert notifications(ws.root)[0]["read"] is True

    run(ws, project)  # retried, then the next
    assert statuses(project) == {"kitchen.wide": "done", "hall.wide": "done"}
    assert [n["kind"] for n in notifications(ws.root)] == ["done", "failed"]


def test_ac13_a_ref_without_an_image_fails_with_what_to_do(ws: hf.Workspace) -> None:
    text = TEXT + '[scenes.s]\nmodel = "qwen-image-edit-2511"\nrefs = ["hall.wide"]\nprompt = "s"\n'
    project = ws.import_text(text, "toml")
    actions.unmark(project, "hall.wide")
    run(ws, project)
    assert "hall.wide has no image yet: mark it to run" in str(item_view(project, "s").error)


def test_ac13_the_execution_record_is_in_hone_flow(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    fake.fail_generate()
    run(ws, project)
    record = project.run()
    assert len(record.flow_runs) == 1
    folder = ws.root / "flows" / project.id / "runs" / record.flow_runs[0]
    assert (folder / "spans.jsonl").is_file()
    assert "scripted failure" in (folder / "spans.jsonl").read_text()


def test_ac13_an_error_outside_a_model_call_fails_the_run_and_the_runner_goes_on(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    other = ws.import_text(TEXT.replace('name = "Failure"', 'name = "Other"'), "toml")
    runner = hf.Runner(ws)
    runner.run(project.id)
    runner.run(other.id)
    good = project.text()
    project.file.write_text(good + "\n[places.broken\n")  # hand-edited while queued: invalid
    runner.start()
    try:
        wait_until(lambda: project.run().status == "failed" and other.run().status == "done")
        assert "does not parse" in project.run().reason
        # the run's end is written before its notification: wait for both (a race in Hone Frame's test)
        wait_until(lambda: sorted(n["kind"] for n in notifications(ws.root)) == ["done", "failed"])
        project.file.write_text(good)
        runner.run(project.id)  # the runner thread is still alive
        wait_until(lambda: project.run().status == "done")
    finally:
        runner.close()


def wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + 10
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.01)
