# pyright: reportUnusedFunction=false, reportPrivateUsage=false
# (the old steps are registered by their decorators; the shared stages are the workflow's own)
"""A project and a run made by the scene pipeline before 0027 (its settings with keys since retired, its
run with the cast and shot stages) under this version: the settings are read with the retired keys
dropped, and resuming the run forks it, keeps its timed lyrics and plans the scenes the frame way."""

import json
from pathlib import Path
from typing import Any

import hone_flow as fk

import hone_music_video as hmv
from hone_music_video import frame_stages, workflow
from hone_music_video._jobs import Job
from hone_music_video.events import EventLog
from hone_music_video.settings import Settings, stored
from hone_music_video.testing import FakeModels, make_song
from hone_music_video.workflow import Conf

OLD_SETTINGS = {
    "packs": "views", "face_refs": "one-body", "polish": "off", "quality_check": True,
    "quality_gate": "off", "pick_best_of": 1, "still_retries": 2, "sheet_retries": 2,
    "models": {"cast": "claude-opus-5-5", "shots": "claude-sonnet-5-5", "stills": "qwen-image-2.1-turbo",
               "sheets": "z-image-turbo", "views": "qwen-image-2.1-turbo", "polish": "z-image-turbo-polish",
               "quality": "claude-sonnet-5-5"},
}  # fmt: skip


def old_workflow(project: hmv.Project, models: hmv.Models) -> fk.Workflow:
    """The lyrics stages, then a stage of the old pipeline (`plan_cast`, its gate)."""
    wf = fk.Workflow(workflow.NAME, storage=project.runs_dir, version="1", measure=("timing",))
    events = EventLog(project.events_file)

    def job(settings: dict[str, Any], ctx: fk.Context) -> Job:
        return Job(project, models, Settings.model_validate(stored(settings)), events, ctx.seed)

    workflow._lyrics_stages(wf, job)

    @wf.step(version="1")
    def plan_cast(review_lyrics: hmv.Timeline, settings: Conf) -> dict[str, Any]:
        return {"characters": []}

    @wf.gate(version="1")
    def review_cast(plan_cast: dict[str, Any]) -> dict[str, Any]:
        return plan_cast

    return wf


def test_old_settings_are_read_with_the_retired_keys_dropped() -> None:
    settings = Settings.model_validate(stored(OLD_SETTINGS))
    assert settings.models.planner == "claude-sonnet-5-5"  # its shot planner
    assert settings.models.frame == ("qwen-image-2.1-turbo",)  # its start-frame model


def test_an_old_run_resumes_as_a_fork_that_keeps_its_lyrics(tmp_path: Path) -> None:
    project = hmv.create_project(tmp_path / "projects", "Old", make_song(tmp_path / "song.wav", 20_000))
    record = json.loads((project.root / "project.json").read_text())
    record["settings"] |= OLD_SETTINGS
    (project.root / "project.json").write_text(json.dumps(record))
    models = FakeModels()
    wf = old_workflow(project, models)
    run = wf.run([workflow.song_item(project)], params={"settings": record["settings"]})
    while (gate := hmv.status(project).waiting) and gate != "review_cast":
        hmv.approve(project)
        run = wf.open_run(run.run_id)
        run.resume()
    transcribed = len(models.calls_of("transcribe"))

    state = hmv.resume(project, models)
    assert state.waiting == "review_plan"
    assert len(models.calls_of("transcribe")) == transcribed  # the lyrics stages are kept
    assert frame_stages.has_plan(project)
    events = [json.loads(line)["event"] for line in project.events_file.read_text().splitlines()]
    assert "run_forked_for_new_version" in events
