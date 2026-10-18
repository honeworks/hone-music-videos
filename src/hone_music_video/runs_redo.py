"""Remake the video after a scene changed (0027 §7), redo a clip with a new seed, edit a motion prompt, or
assemble the video again (D-036).

A scene changes in the frame workspace: a pick, a version used, a redo, a file given (Hone Frame's
actions). `remake` then forks the project's run from `clips`: the clip stages read the scenes as they are
now, and each makes only the versions it does not have (D-009), so only the shots whose start frame,
motion prompt or clip seed changed get a new clip and finished clip; the video is assembled once. Every
version stays on disk; the fork is the project's run from then on (`runs.latest_run`). Assembling again
is a fork too, where only `assemble` runs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import hone_flow as fk

from hone_music_video import frame_stages, runs
from hone_music_video._auto_approve import scenes_ready
from hone_music_video._gates import busy, pass_on_its_own
from hone_music_video.errors import InvalidInput, NotFound, RunStateError
from hone_music_video.events import EventLog
from hone_music_video.ports import Models
from hone_music_video.project import Project
from hone_music_video.prompt_words import words_of_speech
from hone_music_video.records_frame import SceneShots
from hone_music_video.video_costs import write_costs
from hone_music_video.workflow import build_workflow


def shot_ids(shots: SceneShots, wanted: str | Sequence[str]) -> list[str]:
    """The shot ids asked for, in plan order: ids, and ranges like `S012-S015` (both ends included)."""
    order = [s.scene for s in shots.shots]
    found: set[str] = set()
    for text in [wanted] if isinstance(wanted, str) else wanted:
        first, _, last = (text, "", "") if text in order else text.partition("-")
        if first not in order or (last and last not in order):
            raise NotFound(
                f"there is no shot {text!r}; the shots are {', '.join(order)} (a range: S012-S015)"
            )
        a, b = sorted((order.index(first), order.index(last or first)))
        found.update(order[a : b + 1])
    if not found:
        raise InvalidInput("say which shots: their ids, or a range like S012-S015")
    return [i for i in order if i in found]


def _stopped(project: Project, what: str = "remake") -> fk.Run:
    run, state = runs.latest_run(project), runs.status(project)
    if run is None:
        raise RunStateError(f"{project.id} has no run yet; start it (`hone-music-video run`)")
    if state.status == "running":
        raise RunStateError(f"{project.id} is running; {what} once it stops")
    return run


def fork(
    project: Project,
    models: Models,
    event: dict[str, Any],
    *,
    refresh: tuple[str, ...] = (),
    params: dict[str, Any] | None = None,
    on_event: runs.OnEvent | None = None,
) -> str:
    """A fork of the project's run where the `refresh` stages, and those reading changed `params`, run
    again, until it ends or stops at a gate; `event` is logged once it has started. The fork's run id."""
    run = _stopped(project)
    log, wf = runs.logger(project, on_event), build_workflow(project, models)

    def record(flow_event: dict[str, Any]) -> None:
        if flow_event["event"] == "run_started":
            EventLog(project.events_file).record(event)
        log(flow_event)

    try:
        source = wf.open_run(run.run_id)
        forked = source.fork(refresh, params=params, label=project.record().name, on_event=record)
    except fk.RunLocked as error:
        raise busy(project, error) from None
    return forked.run_id


def _go_on(project: Project, models: Models, run_id: str, on_event: runs.OnEvent | None) -> runs.RunState:
    """After a fork: an unattended project's gates pass, and `current/costs.json` follows the run."""
    pass_on_its_own(project, build_workflow(project, models), run_id, runs.logger(project, on_event))
    write_costs(project)
    return runs.status(project)


def remake(project: Project, models: Models, *, on_event: runs.OnEvent | None = None) -> runs.RunState:
    """Make the clips of the shots whose scene, motion prompt or clip seed changed, and cut the video
    again: a fork of the run from `clips` (0027 §7). Refused before the scenes were approved, while the
    run is running, and while a scene has no picture in use."""
    check_remake(project)
    count = int(_stopped(project).read_manifest().params.get("remake") or 0) + 1
    forked = fork(
        project, models, {"event": "remake", "remake": count}, params={"remake": count}, on_event=on_event
    )
    return _go_on(project, models, forked, on_event)


def check_remake(project: Project) -> None:
    """Why a remake is refused now: the run running, the scenes not approved, a scene without a picture."""
    _stopped(project)
    if runs.stage_outputs(project, "review_scenes")["review_scenes"] is None:
        raise RunStateError(f"{project.id}: approve the scenes first (review_scenes); the clips follow")
    scenes_ready(project)


def redo_clips(project: Project, shots: str | Sequence[str]) -> list[str]:
    """New clip seeds for these shots (`shots.json`): the next remake makes their clips again (0027 §7).
    The shots, in order."""
    found = frame_stages.read_shots(project)
    ids = shot_ids(found, shots)
    rows = [s.model_copy(update={"clip_seed": s.clip_seed + 1}) if s.scene in ids else s for s in found.shots]
    frame_stages.write_shots(project, found.model_copy(update={"shots": rows}))
    EventLog(project.events_file).write("clip_seed", shots=ids)
    return ids


def set_motion(project: Project, shot: str, text: str) -> list[str]:
    """A shot's motion prompt (`shots.json`); the next remake makes its clip again. Returns the words of
    speech or of the mouth it names (a warning: the video model would move the mouth, D-088)."""
    if not text.strip():
        raise InvalidInput("the motion prompt is empty: say what moves and what stays still")
    found = frame_stages.read_shots(project)
    (shot_id,) = shot_ids(found, shot)
    rows = [s.model_copy(update={"motion_prompt": text}) if s.scene == shot_id else s for s in found.shots]
    frame_stages.write_shots(project, found.model_copy(update={"shots": rows}))
    EventLog(project.events_file).write("motion_edited", shot=shot_id)
    return words_of_speech(text, motion=True)


def check_assemble(project: Project, models: Models) -> None:
    """The video can be assembled again once every clip is finished, while the run is stopped, and when
    the fork would run nothing but the assembly (D-036)."""
    if runs.latest_run(project) is not None:
        _stopped(project, "assemble the video again")
    if runs.latest_run(project) is None or runs.stage_outputs(project, "finish")["finish"] is None:
        raise RunStateError(
            f"{project.id} has no finished clips yet; resume the run (`hone-music-video resume`) to make "
            "them, and it assembles the video"
        )
    run = _stopped(project, "assemble the video again")
    plan = build_workflow(project, models).open_run(run.run_id).fork(["assemble"], dry_run=True)
    others = [f"{r.step} ({r.reason})" for r in plan.rows if r.action == "run" and r.step != "assemble"]
    if others:
        raise RunStateError(
            f"assembling again would also run {', '.join(others)}: they changed since this run was made, "
            "and assembling again makes no model call"
        )


def assemble(project: Project, models: Models, *, on_event: runs.OnEvent | None = None) -> runs.RunState:
    """Assemble the video again from the finished clips the run has, with this version's code: a fork of
    the run where only `assemble` runs (D-036). It makes no model call."""
    check_assemble(project, models)
    forked = fork(project, models, {"event": "assemble_again"}, refresh=("assemble",), on_event=on_event)
    return _go_on(project, models, forked, on_event)
