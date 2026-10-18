"""A shot's kept versions for the scene viewer (0024 §2, 0027 §7), read only: each version's record
(D-009) with the file it was made from (a start frame's scene picture, a clip's start frame, a finished
clip's clip) and whether the video uses it."""

from __future__ import annotations

import filecmp
from typing import Any

from pydantic import ValidationError

from hone_music_video import frame_stages
from hone_music_video._dashboard_records import url
from hone_music_video._files import read_json
from hone_music_video._jobs import KINDS
from hone_music_video._shot_jobs import CHOSEN
from hone_music_video.errors import NotFound
from hone_music_video.project import Project
from hone_music_video.records import Made

SOURCES = ("image", "video")  # a raw clip's start frame, a finished clip's raw clip


def _source(made: Made) -> str | None:
    found = next((made.inputs[k] for k in SOURCES if isinstance(made.inputs.get(k), dict)), None)
    return found.get("path") if found else None


def _records(project: Project, shot_id: str) -> dict[str, Made]:
    """The shot's version records by file, leaving out one that cannot be read or has no file."""
    found: dict[str, Made] = {}
    for path in (project.current / "shots" / shot_id / "versions").glob("*.json"):
        try:
            made = read_json(path, Made)
        except (OSError, ValidationError):
            continue
        if made.stage in KINDS and project.path(made.file).is_file():
            found[made.file] = made
    return found


def _in_use(project: Project, shot_id: str, made: Made) -> bool:
    chosen = project.current / "shots" / shot_id / CHOSEN[made.stage]
    return chosen.is_file() and filecmp.cmp(project.path(made.file), chosen, shallow=False)


def shot_versions(project: Project, shot_id: str) -> dict[str, Any]:
    """Every kept version of a planned shot, newest first; `NotFound` for a shot not in the plan."""
    ids = [s.scene for s in frame_stages.read_shots(project).shots] if frame_stages.has_plan(project) else []
    if shot_id not in ids:
        raise NotFound(f"there is no shot {shot_id!r} in the shot list")
    made = _records(project, shot_id)

    def link(file: str | None) -> str | None:
        return url(project, project.path(file)) if file else None

    newest_first = sorted(made.items(), key=lambda item: item[1].made_at, reverse=True)
    rows = [
        {
            "stage": m.stage,
            "kind": KINDS[m.stage],
            "url": link(file),
            "from": link(_source(m)),
            "scene_version": m.inputs.get("frame_version"),  # a start frame's scene picture (0027)
            "in_use": _in_use(project, shot_id, m),
            "model": m.model,
            "seed": m.seed,
            "prompt": m.prompt,
            "made_at": m.made_at,
        }
        for file, m in newest_first
    ]
    return {"shot": shot_id, "versions": rows}
