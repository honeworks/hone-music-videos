"""The dashboard's JSON API (design §13.1): one `match` over the method and path, small handlers."""

from __future__ import annotations

import base64
import binascii
import re
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hone_music_video import frame_stages, runs, runs_pause, runs_redo
from hone_music_video._dashboard_calls import calls, one_call
from hone_music_video._dashboard_records import lyrics_records, records
from hone_music_video._dashboard_versions import shot_versions
from hone_music_video._run_progress import project_progress
from hone_music_video.errors import InvalidInput, NotFound, RunStateError
from hone_music_video.owner_timing import held
from hone_music_video.ports import Models
from hone_music_video.project import (
    GivenSheet,
    Material,
    Project,
    ProjectFile,
    create_project,
    open_project,
    read_projects,
    set_approve_mode,
    set_prepare,
)
from hone_music_video.settings import PACES, Settings, parse_settings
from hone_music_video.video_costs import costs

if TYPE_CHECKING:
    from hone_music_video._dashboard_runner import Runner

PROJECT_ID = re.compile(r"^[a-z0-9-]+$")


def project_at(projects: Path, project_id: str) -> Project:
    """The project with this id; `NotFound` for an id that is not one (no path tricks)."""
    if not PROJECT_ID.match(project_id):
        raise NotFound(f"there is no project {project_id!r}")
    return open_project(projects / project_id)


def route(projects: Path, runner: Runner, method: str, path: str, body: Any) -> Any:  # noqa: C901, PLR0911, PLR0912 - a case per route
    match method, path.strip("/").split("/"):
        case "GET", ["settings"]:
            return {
                "defaults": Settings().model_dump(mode="json"),
                "aspect_ratios": ["16:9", "9:16", "1:1", "4:5"],
                "paces": list(PACES),  # 0009
                "image_models": [asdict(i) for i in runner.models.image_models() if i.local],  # 0027
            }
        case "POST", ["estimate"]:
            return estimate(_object(body), runner.models)
        case "GET", ["projects"]:
            return [listed(p, found, runner) for p, found in read_projects(projects)]
        case "POST", ["projects"]:
            return new_video(projects, runner, _object(body))
        case "POST", ["run-prepared"]:  # every prepared project, one after another, unattended (0028)
            return run_prepared(projects, runner)
        case "GET", ["projects", project_id]:
            found = project_at(projects, project_id)
            return card(found, runner) | {
                "project": found.record().model_dump(mode="json"),
                "run": _run(found, runner),
            }
        case "GET", ["projects", project_id, "records"]:
            return records(project_at(projects, project_id))
        case "GET", ["projects", project_id, "costs"]:  # what the video cost; read only (design §13.5)
            return costs(project_at(projects, project_id)).model_dump(mode="json")
        case "GET", ["projects", project_id, "calls"]:  # the hosted calls (0030 §2)
            return calls(project_at(projects, project_id))
        case "GET", ["projects", project_id, "calls", name]:
            return one_call(project_at(projects, project_id), name)
        case "GET", ["projects", project_id, "shots", shot_id, "versions"]:  # the scene viewer (0024)
            return shot_versions(project_at(projects, project_id), shot_id)
        case "POST", ["projects", project_id, ("approve" | "reject") as action]:
            found = project_at(projects, project_id)
            done = decide(found, action, _object(body))
            runner.submit(found.id, "resume")
            return done
        case "POST", ["projects", project_id, "lyrics-timing"]:  # the owner's timing (0018)
            saved = runs.lyrics_timing(project_at(projects, project_id), _object(body))
            return lyrics_records(saved.timeline, saved.report, saved)
        case "POST", ["projects", project_id, ("remake" | "redo-clip" | "motion" | "assemble") as action]:
            return remake(project_at(projects, project_id), runner, action, _object(body))
        case "POST", ["projects", project_id, ("resume" | "approve-mode" | "pause" | "prepare") as action]:
            return steer(project_at(projects, project_id), runner, action, _object(body))
        case _:
            raise NotFound(f"no API route {method} {path}")


def remake(project: Project, runner: Runner, action: str, data: dict[str, Any]) -> dict[str, Any]:
    """After the video: a shot's motion prompt saved, shots' clips given new seeds, the clips of what
    changed made again (a fork from `clips`, 0027 §7), or the video assembled again (D-036); the runner
    runs the fork."""
    not_queued(project, runner)
    if action == "motion":
        shot, text = data.get("shot"), data.get("motion_prompt")
        if not isinstance(shot, str) or not isinstance(text, str):
            raise InvalidInput("send {shot, motion_prompt} as text", ["shot, motion_prompt: text"])
        return {"motion": shot, "warnings": runs_redo.set_motion(project, shot, text)}
    if action == "redo-clip":
        shots: Any = data.get("shots")
        if not isinstance(shots, list) or not all(isinstance(s, str) for s in shots):  # pyright: ignore[reportUnknownVariableType]
            raise InvalidInput("send {shots: [shot ids]}", ["shots: a list of shot ids"])
        ids = runs_redo.redo_clips(project, list(shots))  # pyright: ignore[reportUnknownArgumentType]
        if not data.get("now", True):
            return {"clip_seeds": ids}
    if action == "assemble":
        runs_redo.check_assemble(project, runner.models)
    else:
        runs_redo.check_remake(project)  # refused here, not in the runner's thread
    runner.submit(project.id, "assemble" if action == "assemble" else "remake")
    return {action: project.id}


def not_queued(project: Project, runner: Runner) -> None:
    if project.id in runner.queued:
        raise RunStateError(f"{project.id} is waiting for its turn to run; try again once it has run")


def steer(project: Project, runner: Runner, action: str, data: dict[str, Any]) -> dict[str, Any]:
    """Resume the run; pause or stop it (0022); or switch the project to unattended (`"auto"`) or asking
    (`"ask"`) runs (0004), and a run stopped at a gate then continues when the gate may pass."""
    if action == "resume":  # a second resume would wait behind the run it duplicates, then run again
        if runner.current == project.id:
            raise RunStateError(f"{project.id} is already running")
        not_queued(project, runner)
        started = runs.status(project).status != "not_started"  # a project made by `new` has no run yet
        runner.submit(project.id, "resume" if started else "start")
        return {"resuming": project.id}
    if action == "pause":  # Pause, or Stop with `now` (0022)
        return runs_pause.pause(project, now=data.get("now") is True).as_dict()
    if action == "prepare":  # stop before the local stages, or not (0028 §6)
        set_prepare(project, data.get("prepare") is not False)
        return {"prepare": project.record().prepare}
    mode = data.get("approve")
    set_approve_mode(project, mode)  # pyright: ignore[reportArgumentType] - checked there
    state = runs.status(project)
    if mode == "auto" and state.waiting and project.id not in runner.queued:
        runner.submit(project.id, "resume")
    return {"approve": mode}


def decide(project: Project, action: str, data: dict[str, Any]) -> dict[str, Any]:
    """A decision at the gate waiting; the runner then resumes the run."""
    if action == "approve":
        accept = data.get("accept_errors") is True  # the owner confirmed it in the Plan view (D-027)
        note = _note(data.get("note"))
        return {"approved": runs.approve(project, data.get("gate"), note=note, accept_errors=accept)}
    rejected = runs.reject(project, data.get("gate"), note=_note(data.get("note")))
    timed = held(project) if rejected == "review_lyrics" else []
    return {"rejected": rejected} | ({"timing_kept_for": timed} if timed else {})  # D-116


def estimate(data: dict[str, Any], models: Models) -> dict[str, Any]:
    """What the New video form warns of before Start: the image models whose licence forbids commercial
    use (0021 §4), from the settings; `text` stays None (no hosted picture costs since 0027)."""
    settings = parse_settings(_object(data.get("settings")))
    return {"text": None, "not_commercial": frame_stages.image_notices(settings, models)}


def _object(body: Any) -> dict[str, Any]:
    if body is None:
        return {}
    if not isinstance(body, dict):
        raise InvalidInput("send a JSON object")
    return body  # pyright: ignore[reportUnknownVariableType]


def _note(note: Any) -> str:
    """The owner's note (new takes, or a stage run again): text, or nothing."""
    if note is not None and not isinstance(note, str):
        raise InvalidInput("send the note as text", ["note: text"])
    return note or ""


def _run(project: Project, runner: Runner) -> dict[str, Any]:
    state = runs.status(project).as_dict()
    return state | {"status": "queued"} if project.id in runner.queued else state


def _thumbnail(project: Project) -> str | None:
    """The first start frame, else the frame's first picture made (thumbnails first, design §13.3)."""
    current = project.current
    found = sorted(current.glob("shots/*/still.png")) or sorted(
        project.root.glob("frame/projects/*/items/*/v001.png")
    )
    return f"/files/{project.id}/{project.relative(found[0])}" if found else None


def listed(project: Project, found: ProjectFile | str, runner: Runner) -> dict[str, Any]:
    """A project's card; one this version cannot read is listed as `unreadable` with the reason, so the
    other projects still show."""
    if not isinstance(found, str):
        return card(project, runner, found)

    empty = dict.fromkeys(("created", "stage", "waiting", "approve", "duration_ms", "thumbnail", "progress"))
    return {"id": project.id, "name": project.id, "status": "unreadable", "problem": found} | empty


def card(project: Project, runner: Runner, record: ProjectFile | None = None) -> dict[str, Any]:
    """What the Projects view shows of a project (its `project.json` when already read)."""
    state = runs.status(project)
    record = record or project.record()
    stage = next((s for s in state.stages if s.status not in ("done", "not_started")), None)
    return {
        "id": project.id,
        "name": record.name,
        "created": record.created,
        "status": "queued" if project.id in runner.queued else state.status,
        "stage": stage.name if stage else None,
        "waiting": state.waiting,
        "approve": record.approve,  # 0004
        "prepare": record.prepare,  # 0028
        "prepared": record.prepare and runs.prepared(project, state),
        "duration_ms": runs.duration_ms(project),
        "thumbnail": _thumbnail(project),
        "progress": project_progress(project, state, round(time.time() * 1000)),  # 0003
    }


def _upload(folder: Path, upload: Any, field: str) -> Path:
    if not isinstance(upload, dict) or "data_b64" not in upload:
        raise InvalidInput(f"{field}: send the file as {{name, data_b64}}", [f"{field}: missing file"])
    name = Path(str(upload.get("name") or "upload")).name  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    target = folder / f"{len(list(folder.iterdir()))}-{name}"
    try:
        target.write_bytes(base64.b64decode(str(upload["data_b64"]), validate=True))  # pyright: ignore[reportUnknownArgumentType]
    except (binascii.Error, ValueError):
        raise InvalidInput(f"{field}: the file is not valid base64", [f"{field}: not valid base64"]) from None
    return target


def _sheet(folder: Path, sheet: dict[str, Any], field: str = "sheets") -> GivenSheet:
    file = _upload(folder, sheet.get("file"), field)
    return GivenSheet(str(sheet.get("name") or ""), file, str(sheet.get("note") or ""))


def new_video(projects: Path, runner: Runner, data: dict[str, Any]) -> dict[str, Any]:
    """New video: the song, lyrics, story notes, given sheets and settings; Start (design §13.2)."""
    settings = parse_settings(_object(data.get("settings")))
    frame_stages.image_notices(settings, runner.models)  # an image model the registry does not know (0027)
    with tempfile.TemporaryDirectory(dir=projects, prefix=".upload-") as tmp:
        folder = Path(tmp)
        song = _upload(folder, data.get("song"), "song")
        given: list[Any] = data.get("sheets") or []
        poses: list[Any] = data.get("poses") or []
        material = Material(
            lyrics=data.get("lyrics") or None,
            story=str(data.get("story") or ""),
            feeling=str(data.get("feeling") or ""),  # 0028
            sheets=tuple(_sheet(folder, _object(s)) for s in given),
            poses=tuple(_sheet(folder, _object(s), "poses") for s in poses),
        )
        approve = data.get("approve", "ask")  # "Run without stopping" (0004); create_project checks it
        prepare = data.get("prepare") is True  # "Prepare only": the hosted calls, then wait (0028 §6)
        made = create_project(
            projects, str(data.get("name") or ""), song, material, settings, approve=approve, prepare=prepare
        )
    runner.submit(made.id, "start")
    return card(made, runner)


def run_prepared(projects: Path, runner: Runner) -> dict[str, Any]:
    """Every prepared project, oldest first, queued to run to the end without stopping (`approve: auto`):
    the night's videos, offline (0028 §6)."""
    ready = [
        p
        for p, found in reversed(read_projects(projects))
        if not isinstance(found, str) and p.id not in runner.queued and p.id != runner.current
        and runs.prepared(p)
    ]  # fmt: skip
    for project in ready:
        set_approve_mode(project, "auto")
        runner.submit(project.id, "resume")
    return {"queued": [p.id for p in ready]}
