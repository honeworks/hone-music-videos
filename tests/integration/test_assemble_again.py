"""Assembling again (D-036): a run assembled by an older version (M1's stub, which wrote only the edit
list) is cut with this version's assembly as a fork of the run where only `assemble` runs, and no model
is called. It needs the finished clips and a stopped run, and runs nothing else."""

import json
import threading
from typing import Any

import hone_flow as fk
import pytest

import hone_music_video as hmv
from hone_music_video import runs, stages_make
from hone_music_video._dashboard_records import records
from hone_music_video._files import write_json
from hone_music_video._jobs import Job
from hone_music_video.cli import main
from hone_music_video.testing import Call, FakeModels
from tests.conftest import drive
from tests.integration.test_dashboard import call


def stub_assemble(job: Job, shots: hmv.Shots, finished: hmv.ShotFiles, _audio: hmv.Song) -> hmv.Assembly:
    """M1's assembly (0.1 until M6): the edit list only, no video."""
    fps, clip = job.settings.fps, {f.shot: f.file for f in finished.shots}
    edl = [
        {
            "shot": s.id,
            "clip": clip[s.id],
            "first_frame": stages_make.frame_at(s.start_ms, fps),
            "last_frame": stages_make.frame_at(s.end_ms, fps) - 1,
        }
        for s in shots.shots
    ]
    assembly = hmv.Assembly.model_validate({"fps": fps, "edl": edl})
    write_json(job.project.current / "edl.json", assembly)
    return assembly


@pytest.fixture
def stub_assembled(project: hmv.Project, monkeypatch: pytest.MonkeyPatch) -> hmv.Project:
    with monkeypatch.context() as patch:
        patch.setattr(stages_make, "assemble", stub_assemble)
        assert drive(project, FakeModels()).status == "completed"
    assert not (project.current / "video.mp4").exists()
    return project


def fork_plan(project: hmv.Project) -> dict[str, str]:
    run = runs.latest_run(project)
    assert run is not None
    fork = run.read_manifest().fork_of
    assert fork is not None
    return {row.step: row.action for row in fork.plan}


def test_a_stub_assembled_run_is_assembled_again_without_a_model(stub_assembled: hmv.Project) -> None:
    project, models = stub_assembled, FakeModels()
    state = hmv.assemble(project, models)
    assert state.status == "completed" and models.calls == []
    plan = fork_plan(project)
    assert plan.pop("assemble") == "run" and set(plan.values()) == {"reuse"}  # nothing else ran
    edl = hmv.Assembly.model_validate_json((project.current / "edl.json").read_bytes())
    assert edl.video == "current/video.mp4" and (project.current / "video.mp4").stat().st_size > 0
    assert runs.stage_outputs(project, "assemble")["assemble"] == edl
    events = [json.loads(line)["event"] for line in project.events_file.read_text().splitlines()]
    assert "assemble_again" in events


def test_assemble_from_the_command_line(
    stub_assembled: hmv.Project, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["assemble", str(stub_assembled.root), "--fake-models"]) == 0
    assert "completed" in capsys.readouterr().out
    assert (stub_assembled.current / "video.mp4").is_file()


def test_assembling_needs_the_finished_clips(project: hmv.Project) -> None:
    with pytest.raises(hmv.RunStateError, match="no finished clips yet"):
        hmv.assemble(project, FakeModels())
    hmv.start(project, FakeModels())  # stops at the lyrics gate
    with pytest.raises(hmv.RunStateError, match="no finished clips yet; resume the run"):
        hmv.assemble(project, FakeModels())
    assert main(["assemble", str(project.root)]) == 1


@pytest.fixture
def measure_changed(monkeypatch: pytest.MonkeyPatch) -> None:
    """This version's `measure` step is version 2 (the run's is 1): a fork would measure again."""
    step = fk.Workflow.step

    def bumped(self: fk.Workflow, *args: Any, **kw: Any) -> Any:
        def register(fn: Any) -> Any:
            return step(self, *args, **(kw | {"version": "2"} if fn.__name__ == "measure" else kw))(fn)

        return register

    monkeypatch.setattr(fk.Workflow, "step", bumped)


def test_assembling_again_runs_nothing_else(stub_assembled: hmv.Project, measure_changed: None) -> None:
    """A run whose `measure` an older version made: forking would measure again, so assembling again
    refuses rather than run more than the assembly."""
    run_id = runs.latest_run(stub_assembled).run_id  # type: ignore[union-attr]
    models = FakeModels()
    with pytest.raises(hmv.RunStateError, match=r"would also run measure \(version_changed 1->2\)"):
        hmv.assemble(stub_assembled, models)
    assert models.calls == [] and runs.latest_run(stub_assembled).run_id == run_id  # type: ignore[union-attr]


def test_the_command_line_says_why_it_refuses(
    stub_assembled: hmv.Project, measure_changed: None, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["assemble", str(stub_assembled.root), "--fake-models"]) == 1
    error = capsys.readouterr().err
    assert error.startswith("error: assembling again would also run measure (version_changed 1->2)")
    assert "makes no model call" in error


def test_the_dashboard_refuses_at_once(stub_assembled: hmv.Project, measure_changed: None) -> None:
    """The dashboard checks the fork before queueing it: a refusal is a 409 the page shows (D-036)."""
    run_id = runs.latest_run(stub_assembled).run_id  # type: ignore[union-attr]
    dashboard = hmv.Dashboard(stub_assembled.root.parent, FakeModels(), port=0)  # not started: nothing runs
    threading.Thread(target=dashboard.server.serve_forever, daemon=True).start()
    try:
        status, error, _ = call(dashboard.url.rstrip("/"), f"/api/projects/{stub_assembled.id}/assemble", {})
        assert status == 409 and "would also run measure" in error["error"]
        assert dashboard.server.runner.queued == set()
    finally:
        dashboard.close()
    assert runs.latest_run(stub_assembled).run_id == run_id  # type: ignore[union-attr]


def test_a_running_run_is_not_assembled(project: hmv.Project) -> None:
    """While another thread's run is inside a stage, assembling again is refused."""
    inside, release = threading.Event(), threading.Event()

    def hold(call: Call) -> None:
        if call.kind == "transcribe":
            inside.set()
            release.wait(10)

    worker = threading.Thread(target=hmv.start, args=(project, FakeModels(on_call=hold)))
    worker.start()
    try:
        assert inside.wait(10)
        with pytest.raises(hmv.RunStateError, match="is running; assemble the video again once it stops"):
            hmv.assemble(project, FakeModels())
    finally:
        release.set()
        worker.join(10)


PRE_M6 = """{"format_version": "1", "fps": 32,
 "edl": [{"shot": "S001", "clip": "current/shots/S001/versions/finish-0123456789ab.mp4",
          "first_frame": 0, "last_frame": 31}]}"""


def test_an_edit_list_from_before_m6_reads(stub_assembled: hmv.Project) -> None:
    """M1's edit list had no `held_frames` and no video: it reads, as the stub's run output does in the
    dashboard's records."""
    old = hmv.Assembly.model_validate_json(PRE_M6)
    assert old.video is None and old.edl[0].held_frames == 0
    found = records(stub_assembled)
    assert found["video"] is None and found["assembly"]["video"] is None
    assert {c["held_frames"] for c in found["assembly"]["edl"]} == {0}
