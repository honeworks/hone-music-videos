# pyright: reportUnusedFunction=false
# (the steps are registered by their decorators, never called by name)
"""The hone-flow workflow of a project (design §3.1): the 10 stages as steps, the 3 owner gates (0027).

The run has one item, the song. Every stage is a step of it, so a run killed during a stage resumes at
that stage and keeps every finished one (hone-flow commits per step); the frame run keeps every picture
it made, and stages 8 and 9 keep their finished shots. The workflow is made per project, with the models
to use."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import hone_flow as fk

from hone_music_video import frame_plan, frame_stages, notify, pause
from hone_music_video import stages_make as make
from hone_music_video import stages_plan as plan
from hone_music_video._files import write_json
from hone_music_video._jobs import Job
from hone_music_video.errors import InvalidInput, Paused
from hone_music_video.events import EventLog
from hone_music_video.lyrics_check import check_lyrics as check_lyrics_of
from hone_music_video.pause import Stoppable
from hone_music_video.ports import Models
from hone_music_video.project import Project, StoredSheet
from hone_music_video.records import Assembly, Report, ShotFiles, Shots, Song, Timeline, Words
from hone_music_video.records_frame import Planned, Scenes
from hone_music_video.settings import Settings, stored
from hone_music_video.shots_check import check_shots as check_shots_of
from hone_music_video.stages_plan import accept as keep_record

NAME = "video"  # runs live at <project>/runs/video/runs/<run id>/
PREPARED = "prepared: every hosted call is made; resume to make the scenes, clips and video (0028)"
ITEM = "song"
STAGES = (
    "measure",
    "transcribe",
    "lyrics",
    "check_lyrics",
    "plan",
    "check_plan",
    "scenes",
    "clips",
    "finish",
    "assemble",
)
# The owner's gates, after the stage whose result they review (design §3.1, 0027).
GATES = {
    "check_lyrics": "review_lyrics",
    "check_plan": "review_plan",
    "scenes": "review_scenes",
}

Conf = fk.Param[dict[str, Any]]  # the settings, recorded as the run's param
Remake = fk.Param[int]  # how many remakes the run is (0027 §7): a new value runs the clips again
Given = list[dict[str, Any]]  # the given sheets, an item input
JobOf = Callable[[dict[str, Any], fk.Context], Job]


def song_item(project: Project) -> fk.Item:
    """The run's one item: the song file and the owner's material (design §2)."""
    inputs = project.record().inputs
    return fk.Item(
        ITEM,
        {
            "song": fk.File(project.path(inputs.song)),
            "lyrics_text": inputs.lyrics,
            "story": inputs.story,
            "given_sheets": [s.model_dump() for s in inputs.sheets],
            "poses": [s.model_dump() for s in inputs.poses],
        },
    )


def _given(sheets: Given) -> list[StoredSheet]:
    return [StoredSheet.model_validate(s) for s in sheets]


def _lyrics_stages(wf: fk.Workflow, job: JobOf) -> None:
    @wf.step(version="1")
    def measure(song: fk.File) -> Song:
        return plan.measure(song.path)

    @wf.step(version="4", deterministic=False)
    def transcribe(
        song: fk.File, measure: Song, lyrics_text: str | None, settings: Conf, ctx: fk.Context
    ) -> Words:
        return plan.transcribe(job(settings, ctx), song.path, measure, lyrics_text)

    @wf.step(version="3", deterministic=False)
    def lyrics(
        measure: Song,
        transcribe: Words,
        lyrics_text: str | None,
        settings: Conf,
        ctx: fk.Context,
        *,
        review_note: str | None = None,
        previous: Timeline | None = None,
    ) -> Timeline:
        # rerun with the owner's note after a rejected lyrics gate (`runs.reject`, D-015)
        timed = job(settings, ctx)
        return plan.lyrics(timed, measure, transcribe, lyrics_text, note=review_note, previous=previous)

    @wf.step(version="2")
    def check_lyrics(lyrics: Timeline, transcribe: Words, lyrics_text: str | None) -> Report:
        return check_lyrics_of(lyrics, transcribe, lyrics_text)

    @wf.gate(version="1")
    def review_lyrics(lyrics: Timeline, check_lyrics: Report) -> Timeline:
        return lyrics


def _frame_stages(wf: fk.Workflow, job: JobOf) -> None:
    @wf.step(version="1", deterministic=False)
    def plan(  # noqa: PLR0917 - hone-flow passes a step's inputs by name
        review_lyrics: Timeline,
        story: str,
        given_sheets: Given,
        poses: Given,
        settings: Conf,
        ctx: fk.Context,
        *,
        review_note: str | None = None,  # the owner's note when review_plan sends the plan back
        previous: Planned | None = None,  # the plan sent back
    ) -> Planned:
        # the frame plan in several calls, written as the project file (0026, 0027 §3)
        planner = job(settings, ctx)
        keep_record(planner, "timeline.json", review_lyrics)  # the approved lyrics, for people (design §4)
        feeling = planner.project.record().inputs.feeling  # read here, not an item input (0028)
        inputs = frame_plan.Inputs(
            review_lyrics, story, _given(given_sheets), review_note or "", _given(poses), feeling
        )
        return frame_stages.install(planner, frame_plan.plan(planner, inputs))

    @wf.step(version="1")
    def check_plan(plan: Planned, review_lyrics: Timeline, settings: Conf, ctx: fk.Context) -> Report:
        project = job(settings, ctx).project
        shots = frame_stages.as_shots(frame_stages.read_shots(project))
        cast = sorted({c for s in shots.shots for c in s.cast})
        return check_shots_of(shots, review_lyrics, cast, Settings.model_validate(stored(settings)))

    @wf.gate(version="1")
    def review_plan(plan: Planned, check_plan: Report) -> Planned:
        return plan

    @wf.step(version="1", deterministic=False)
    def scenes(review_plan: Planned, settings: Conf, ctx: fk.Context) -> Scenes:
        # the frame run (Hone Frame's §8) until it ends; a gate after it (0027 §5)
        made = job(settings, ctx)
        record = made.project.record()
        if record.prepare:  # the hosted calls are done; the local stages wait for a resume (0028 §6)
            made.events.write("run_prepared")
            raise Paused(f"{pause.MESSAGE}: {PREPARED}")
        return frame_stages.run_scenes(made, unattended=record.approve == "auto")

    @wf.gate(version="1")
    def review_scenes(scenes: Scenes) -> Scenes:
        return scenes


def _make_stages(wf: fk.Workflow, job: JobOf) -> None:
    # Each reads the scenes as they are now (the pictures in use, the motion prompts of shots.json): a
    # remake forks the run from `clips`, and only the shots that changed are made again (0027 §7).
    @wf.step(version="4", deterministic=False)
    def clips(review_scenes: Scenes, settings: Conf, ctx: fk.Context, *, remake: Remake = 0) -> ShotFiles:
        # `remake` is read only so that a fork with a new value runs the clips again with the same seeds
        # (a refresh would give every clip a new seed): only a changed shot gets a new key (D-009)
        made = job(settings, ctx)
        shots, stills = _scenes(made)
        every = made.settings.take_clips == "all"  # else only the takes in use (0031)
        return make.clips(made, shots, stills, frame_stages.takes_now(made.project, made) if every else None)

    @wf.step(version="4", deterministic=False)
    def finish(clips: ShotFiles, settings: Conf, ctx: fk.Context) -> ShotFiles:
        made = job(settings, ctx)
        return make.finish(made, _scenes(made)[0], clips)

    @wf.step(version="2")
    def assemble(finish: ShotFiles, measure: Song, settings: Conf, ctx: fk.Context) -> Assembly:
        made = job(settings, ctx)
        return make.assemble(made, _scenes(made)[0], finish, measure)


def _scenes(made: Job) -> tuple[Shots, ShotFiles]:
    """The scenes in use, each a start frame; refused while a scene has no picture in use."""
    found = frame_stages.scenes_now(made.project, job=made)
    if found.shots is None or found.stills is None:
        raise InvalidInput(f"the scenes are not ready: {found.reason}; pick or make them, then go on")
    write_json(made.project.current / "shots.json", found.shots)  # the shots in use, for people (§4.3)
    return found.shots, found.stills


def build_workflow(project: Project, models: Models) -> fk.Workflow:
    """The 10 stages and 3 gates of design §3.1 (0027) as one hone-flow workflow over `project`; it notifies
    the owner's webhook when one is set (design §13.4, D-060). Its stages' model calls stop when the
    owner pauses (0022)."""
    wf = fk.Workflow(
        NAME,
        storage=project.runs_dir,
        version="1",
        measure=("timing",),
        notifications=notify.destinations(project),
    )
    events, stoppable = EventLog(project.events_file), Stoppable(models, project)  # 0022

    def job(settings: dict[str, Any], ctx: fk.Context) -> Job:
        return Job(project, stoppable, Settings.model_validate(stored(settings)), events, ctx.seed)

    for add in (_lyrics_stages, _frame_stages, _make_stages):
        add(wf, job)
    return wf
