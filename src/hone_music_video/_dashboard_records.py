"""What the project views show (design §13.2), read-only: the run's records as the stages made them (so a
gate shows what it is about), the shot list of the frame plan, and the files made so far as URLs the page
can load. The pictures up to the scenes are the frame workspace's, read through its own API (0027 §6)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import hone_flow as fk
from pydantic import BaseModel

from hone_music_video import frame_stages, owner_timing, runs
from hone_music_video._shot_jobs import CHOSEN
from hone_music_video.owner_timing import Reviewed
from hone_music_video.project import Project
from hone_music_video.records import Report, Shots, Timeline

NEWEST = ("finish", "clips", "stills")  # a shot's newest file is its furthest stage's (0003)
PLANS = (
    "lyrics",
    "check_lyrics",
    "review_lyrics",
    "plan",
    "check_plan",
    "scenes",
    "review_scenes",
    "assemble",
)


def url(project: Project, path: Path) -> str | None:
    """The file's dashboard URL (changing when the file does, so a page never shows a stale copy)."""
    if not path.is_file():
        return None
    relative = path.resolve().relative_to(project.root.resolve()).as_posix()  # the frame's paths are absolute
    return f"/files/{project.id}/{relative}?v={path.stat().st_mtime_ns}"


def _dump(record: BaseModel | None) -> dict[str, Any] | None:
    return record.model_dump(mode="json") if record is not None else None


def _versions(folder: Path) -> dict[str, int]:
    """How many versions each stage has kept in a shot's `versions/` folder (D-009)."""
    made = [p.name for p in folder.glob("*-*.*") if p.suffix != ".json"]
    return {stage: sum(name.startswith(f"{stage}-") for name in made) for stage in CHOSEN}


def _shot_files(project: Project, shots: Shots | None) -> dict[str, dict[str, Any]]:
    """Per shot: the start frame, raw clip and finished clip in use, the newest of them (what the clip
    views show, 0003) and the count of versions kept. Until the shot keeps its start frame, its scene's
    picture in use in the frame workspace, so the Preview shows the scenes as they are made."""
    if shots is None:
        return {}
    pictures = frame_stages.pictures_in_use(project) if frame_stages.has_plan(project) else {}
    found: dict[str, dict[str, Any]] = {}
    for shot in shots.shots:
        folder = project.current / "shots" / shot.id
        files = {stage: url(project, folder / name) for stage, name in CHOSEN.items()}
        if files["stills"] is None and shot.id in pictures:
            files["stills"] = url(project, pictures[shot.id])
        furthest = next((kind for kind in NEWEST if files[kind]), None)
        newest = {"kind": furthest, "url": files[furthest]} if furthest else None
        found[shot.id] = files | {"newest": newest, "versions": _versions(folder / "versions")}
    return found


def lyrics_records(
    timeline: Timeline | None, report: Report | None, timed: Reviewed | None = None
) -> dict[str, Any]:
    """The timed lyrics as the Lyrics view reads them: the timeline, its check, and the owner's timing
    edits kept and dropped (0018)."""
    summary = timed.summary() if timed else None
    return {"timeline": _dump(timeline), "lyrics_check": _dump(report), "lyrics_timing": summary}


def _lyrics(project: Project, plans: dict[str, Any]) -> dict[str, Any]:
    """The approved timeline once the gate is decided (checked again when the owner timed it); before,
    the lyrics stage's with the owner's saved timing applied (0018, D-113)."""
    run = runs.latest_run(project)
    approved: Timeline | None = plans["review_lyrics"]
    if approved is not None:
        by_owner = run is not None and approved.owner_timed
        report = owner_timing.checked(project, run, approved) if run and by_owner else plans["check_lyrics"]
        return lyrics_records(approved, report)
    timed = owner_timing.under_review(project, run) if run and plans["lyrics"] else None
    if timed is not None:
        return lyrics_records(timed.timeline, timed.report, timed)
    return lyrics_records(plans["lyrics"], plans["check_lyrics"])


def _plans(project: Project) -> dict[str, Any]:
    """The stages' outputs; one being run again has none for a moment, and then counts as not done. A
    project made before 0027 has other stages: theirs are not read."""
    found: dict[str, Any] = {}
    for stage in PLANS:
        try:
            found[stage] = runs.stage_outputs(project, stage)[stage]
        except (FileNotFoundError, fk.HoneFlowError, ValueError, KeyError):
            found[stage] = None
    return found


def shot_list(project: Project) -> Shots | None:
    """The shot list of the frame plan, each still prompt its scene's prompt in use when it has one."""
    if not frame_stages.has_plan(project):
        return None
    shots = frame_stages.read_shots(project)
    now = frame_stages.scenes_now(project)
    return now.shots if now.shots is not None else frame_stages.as_shots(shots)


def _feelings(project: Project) -> dict[str, dict[str, str]]:
    if not frame_stages.has_plan(project):
        return {}
    shots = frame_stages.read_shots(project).shots
    return {s.scene: {"feel": s.feel, "evidence": s.evidence} for s in shots if s.feel or s.evidence}


def characters(project: Project) -> dict[str, dict[str, Any]]:
    """Each character of the frame project with its picture in use (its close-up, else its hero), for the
    views' avatars: read from the frame's state, no check of its file (0027)."""
    if not frame_stages.has_plan(project):
        return {}
    fp = frame_stages.frame_project(frame_stages.workspace(project))
    state = fp.state()
    found: dict[str, dict[str, Any]] = {}
    for item_id in state.items:
        subject, _, name = item_id.partition(".")
        if name not in ("hero", "close") or subject == "demo":
            continue
        picture = fp.current_image(state, item_id)
        row = found.setdefault(subject, {"name": subject.replace("-", " ").title(), "picture": None})
        if picture is not None and (name == "close" or row["picture"] is None):
            row["picture"] = url(project, picture)
    return found


def records(project: Project) -> dict[str, Any]:
    """Everything the Lyrics, Plan, Scenes, Clips and Video views read, in one answer."""
    record = project.record()
    plans = _plans(project)
    shots = shot_list(project)
    pictures = [*record.inputs.sheets, *record.inputs.poses]
    given = [s.model_dump() | {"url": url(project, project.path(s.file))} for s in pictures]
    frame = (
        frame_stages.frame_project(frame_stages.workspace(project)).id
        if frame_stages.has_plan(project)
        else None
    )
    return {
        "song": url(project, project.path(record.inputs.song)),
        "story": record.inputs.story,
        **_lyrics(project, plans),
        "given": given,
        "plan": _dump(plans["plan"]),
        "plan_check": _dump(plans["check_plan"]),
        "frame": frame,  # the frame project's id: the Scenes view reads it through the frame API (0027)
        "characters": characters(project),
        "scenes_missing": frame_stages.not_ready(project) if frame else [],  # live: no picture in use yet
        "shots": _dump(shots),
        "feelings": _feelings(project),  # each shot's feel and evidence, as planned (0028)
        "shot_files": _shot_files(project, shots),
        "scenes": _dump(plans["review_scenes"] or plans["scenes"]),
        "assembly": _dump(plans["assemble"]),
        "edl": url(project, project.current / "edl.json"),
        "edit_xml": url(project, project.current / "edit.xml"),  # for DaVinci Resolve, Premiere (D-063)
        "edit_edl": url(project, project.current / "edit.edl"),
        "video": url(project, project.current / "video.mp4"),
    }
