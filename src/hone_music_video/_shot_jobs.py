"""What stages 8 and 9 share: a shot's folder, its job, making the jobs, and what they found made.

Every file is a version kept in `current/shots/<id>/versions/` with its `Made` record (D-009); the version
in use is copied to `still.png`, `clip-raw.mp4` or `clip.mp4`. A shot has one take since 0027: its start
frame is its scene's picture in use, so a shot whose picture, motion prompt or clip seed changed gets a
new key and only it is made again."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from hone_music_video._jobs import Job, ShotJob, Task, Units, choose, is_made, shot_job
from hone_music_video.errors import InvalidInput
from hone_music_video.records import ShotFile, ShotFiles

CHOSEN = {"stills": "still.png", "clips": "clip-raw.mp4", "finish": "clip.mp4"}  # in each shot's folder
SUFFIX = {"stills": ".png", "clips": ".mp4", "finish": ".mp4"}
SHOT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")  # a shot id names a folder
TaskSpec = tuple[str, str, dict[str, Any]]  # model, prompt, inputs


def shot_folder(job: Job, shot_id: str) -> Path:
    """`current/shots/<id>/`; an id that is not a safe folder name is refused (defence in depth)."""
    if not SHOT_ID.match(shot_id):
        raise InvalidInput(f"shot id {shot_id!r} is not letters, digits and dashes; fix the shot list")
    return job.project.current / "shots" / shot_id


def job_for(
    job: Job, shot: str, stage: str, task: TaskSpec, seed: int, *, chosen_copy: bool = True
) -> ShotJob:
    """The version to make for a shot, with the shot's chosen copy (none for another take, 0028 §5)."""
    model, prompt, inputs = task
    folder = shot_folder(job, shot)
    chosen = folder / CHOSEN[stage] if chosen_copy else None
    return shot_job(
        job, stage, Task(shot, model, prompt, inputs, folder / "versions", SUFFIX[stage], chosen), seed
    )


def make_all(units: Units, step: str, jobs: list[ShotJob]) -> None:
    """Make the versions not made yet, one session per model (D-005), each between its progress events
    (0003); then make every chosen file a copy of its version."""
    todo: dict[str, dict[Path, ShotJob]] = {}
    for made in jobs:
        if not is_made(made):
            todo.setdefault(made.task.model, {})[made.out] = made
    for model, waiting in todo.items():
        with nullcontext() if not waiting else units.job.models.session(model):
            for made in waiting.values():
                units.make(step, made)
    for made in jobs:
        choose(made)


def shot_files(job: Job, jobs: Mapping[str, ShotJob], others: Sequence[ShotJob] = ()) -> ShotFiles:
    """The version each shot uses; in `takes` every made file, the other takes' too (0028 §5)."""
    rows = [ShotFile(shot=s, file=job.project.relative(m.out), key=m.key) for s, m in jobs.items()]
    more = [ShotFile(shot=m.task.subject, file=job.project.relative(m.out), key=m.key) for m in others]
    made = [r for r, m in zip(rows, jobs.values(), strict=True) if is_made(m)]
    return ShotFiles(shots=rows, takes=made + [r for r, m in zip(more, others, strict=True) if is_made(m)])


def other_takes(files: ShotFiles) -> dict[str, list[str]]:
    """The files of the other takes a stage made, by shot (0028 §5)."""
    used = {f.file for f in files.shots}
    found: dict[str, list[str]] = {}
    for take in files.takes:
        if take.file not in used:
            found.setdefault(take.shot, []).append(take.file)
    return found


def by_shot(files: ShotFiles) -> dict[str, str]:
    """A stage's files by shot."""
    return {f.shot: f.file for f in files.shots}
