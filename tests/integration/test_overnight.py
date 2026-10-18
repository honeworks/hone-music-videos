"""A night of videos (0028 §5, §6) on fake models: a project prepared stops before the scenes with every
hosted call made, also through approved gates; "Run all prepared" runs them one after another to the end,
unattended; a run that failed is resumed by the runner; the queue a stopped dashboard left is picked up
when it starts again; a scene's takes never wait for a pick."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import hone_music_video as hmv
from hone_music_video import frame_stages, runs
from hone_music_video._dashboard_runner import QUEUE_FILE
from hone_music_video.frame import actions
from hone_music_video.testing import Call, FakeModels, make_song
from tests.conftest import LYRICS
from tests.integration.test_dashboard import call, upload, wait_for


def new_project(root: Path, name: str, ms: int = 20_000, **options: Any) -> hmv.Project:
    song = make_song(root / f"{name}.wav", ms)
    return hmv.create_project(root / "projects", name, song, hmv.Material(lyrics=LYRICS), **options)


def local(models: FakeModels) -> list[Call]:
    return models.calls_of("generate")


def test_a_prepared_project_stops_before_the_scenes_and_goes_on_when_resumed(tmp_path: Path) -> None:
    project = new_project(tmp_path, "Walk", prepare=True)
    models = FakeModels()
    state = hmv.start(project, models)
    while state.waiting:  # the owner approves the lyrics and the plan: the run still stops before the scenes
        hmv.approve(project)
        state = hmv.resume(project, models)
    assert state.status == "paused" and runs.prepared(project)
    assert next(s for s in state.stages if s.name == "scenes").status == "paused"
    assert local(models) == [] and models.calls_of("plan")  # every hosted call made, nothing local
    assert project.record().prepare

    hmv.set_approve_mode(project, "auto")
    state = hmv.resume(project, models)
    assert state.status == "completed" and not project.record().prepare
    assert local(models)


def test_run_all_prepared_runs_them_one_after_another(tmp_path: Path) -> None:
    dashboard = hmv.Dashboard(tmp_path / "projects", FakeModels(), port=0).start()
    base = dashboard.url.rstrip("/")
    try:
        ids = []
        for name in ("First", "Second"):
            song = upload(make_song(tmp_path / f"{name}.wav", 20_000))
            body = {"name": name, "song": song, "lyrics": LYRICS, "approve": "auto", "prepare": True}
            body["feeling"] = "dread, then relief"
            ids.append(call(base, "/api/projects", body)[1]["id"])
        for project_id in ids:
            found = wait_for(base, project_id, "paused")
            assert found["prepared"] and found["prepare"]
        assert call(base, "/api/run-prepared", {})[1] == {"queued": ids}  # the oldest first
        assert call(base, "/api/run-prepared", {})[1] == {"queued": []}  # queued once
        for project_id in ids:
            found = deadline_for(base, project_id, "completed")
            assert found["approve"] == "auto" and not found["prepared"]
        record = json.loads((tmp_path / "projects" / ids[0] / "project.json").read_text())
        assert record["inputs"]["feeling"] == "dread, then relief"
    finally:
        dashboard.close()


def deadline_for(base: str, project_id: str, status: str, seconds: float = 60) -> dict[str, Any]:
    end, found = time.monotonic() + seconds, {}
    while time.monotonic() < end:
        found = call(base, f"/api/projects/{project_id}")[1]
        if found["status"] == status:
            return found
        time.sleep(0.05)
    raise AssertionError(f"{project_id} never reached {status}: {found}")


def test_a_failed_run_is_resumed_by_the_runner(tmp_path: Path) -> None:
    failed: list[Call] = []

    def first_clip_fails(made: Call) -> None:
        if (
            made.kind == "generate"
            and made.out is not None
            and made.out.name.startswith("clips-")
            and not failed
        ):
            failed.append(made)
            raise hmv.ModelFailure("the job was interrupted")

    project = new_project(tmp_path, "Walk", approve="auto")
    dashboard = hmv.Dashboard(tmp_path / "projects", FakeModels(on_call=first_clip_fails), port=0).start()
    try:
        dashboard.server.runner.submit(project.id, "start")
        deadline_for(dashboard.url.rstrip("/"), project.id, "completed")
    finally:
        dashboard.close()
    events = [json.loads(line) for line in project.events_file.read_text().splitlines()]
    assert failed and [e["attempt"] for e in events if e["event"] == "run_retried"] == [1]


def test_the_queue_a_stopped_dashboard_left_is_picked_up(tmp_path: Path) -> None:
    project = new_project(tmp_path, "Walk")
    queue = {"jobs": [{"project": project.id, "action": "start"}, {"project": "gone", "action": "resume"}]}
    (tmp_path / "projects" / QUEUE_FILE).write_text(json.dumps(queue))
    dashboard = hmv.Dashboard(tmp_path / "projects", FakeModels(), port=0).start()
    try:
        wait_for(dashboard.url.rstrip("/"), project.id, "review_lyrics")  # started: the queue was kept
        kept = json.loads((tmp_path / "projects" / QUEUE_FILE).read_text())
        assert kept == {"jobs": []}  # nothing waits now
    finally:
        dashboard.close()


def test_a_scenes_takes_never_wait_for_a_pick(tmp_path: Path) -> None:
    project = new_project(tmp_path, "Walk", 40_000)  # asks at every gate; S005 has three takes
    models = FakeModels()
    state = hmv.start(project, models)
    while state.waiting != "review_scenes":
        hmv.approve(project)
        state = hmv.resume(project, models)
    fp = frame_stages.frame_project(frame_stages.workspace(project, models))
    runner = hmv.frame.Runner(frame_stages.workspace(project, models))
    for _ in range(50):  # the owner accepts the holds (the demo, the heroes) and nothing else
        holds = [i for i, st in fp.state().items.items() if st.status == "waiting"]
        assert all(not fp.state().items[i].candidates for i in holds), "a pick waits"
        for item in holds:
            actions.accept(fp, item)
        if not fp.marked():
            break
        runner.run(fp.id)
        runner.drain()
    takes = fp.state().items["S005"]  # planned with three takes
    assert takes.status == "done" and takes.current == takes.versions[0].n and len(takes.versions) == 3
    hmv.approve(project)  # every scene has its picture: the gate passes
