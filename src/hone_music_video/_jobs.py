"""What the stages share: the `Job` of a stage, and making one generated file as a kept version.

Every generated file is a version that is never overwritten, named after the sha256 key of what made it,
with a `Made` record beside it (design §1, D-009). The record is written last: a file with its record is
finished, so a stage run again (a resume after a crash) skips it."""

from __future__ import annotations

import filecmp
import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hone_music_video._blank import refuse_blank
from hone_music_video._files import now, write_json
from hone_music_video.events import EventLog
from hone_music_video.ports import Models
from hone_music_video.project import Project
from hone_music_video.records import Made
from hone_music_video.settings import Settings


@dataclass(frozen=True)
class Job:
    """What every stage needs: the project, the models, the settings, the progress log and a seed."""

    project: Project
    models: Models
    settings: Settings
    events: EventLog
    seed: int = 0


@dataclass(frozen=True)
class Task:
    """What a stage asks for one shot or one sheet take, and where its versions go."""

    subject: str  # the shot id, or the character id
    model: str
    prompt: str
    inputs: dict[str, Any]
    folder: Path  # where the versions are kept
    suffix: str  # ".png", ".mp4"
    chosen: Path | None = None  # the file the video uses: a copy of the latest version


@dataclass(frozen=True)
class ShotJob:
    """A task with its seed and key computed once, and the version file it makes."""

    task: Task
    seed: int
    key: str
    out: Path  # `<folder>/<stage>-<key[:12]><suffix>`, never overwritten


def seed_for(base: int, *parts: object) -> int:
    """A seed for one thing, stable across resumes: sha256 of the stage's seed and the parts."""
    text = "|".join(str(p) for p in (base, *parts))
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def described(project: Project, value: Any) -> Any:
    """An input as recorded: a file becomes its path in the project and its sha256."""
    if isinstance(value, Path):
        digest = hashlib.sha256(value.read_bytes()).hexdigest()
        path = project.relative(value) if value.is_relative_to(project.root) else str(value)
        return {"path": path, "sha256": digest}
    if isinstance(value, dict):
        return {k: described(project, v) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, list | tuple):
        return [described(project, v) for v in value]  # pyright: ignore[reportUnknownVariableType]
    return value


def shot_job(job: Job, stage: str, task: Task, seed: int) -> ShotJob:
    """The task's key: sha256 of the model, the prompt, the seed and the inputs (files by content)."""
    made = {
        "model": task.model,
        "prompt": task.prompt,
        "seed": seed,
        "inputs": described(job.project, task.inputs),
    }
    key = hashlib.sha256(json.dumps(made, sort_keys=True).encode()).hexdigest()
    return ShotJob(task, seed, key, task.folder / f"{stage}-{key[:12]}{task.suffix}")


def is_made(made: ShotJob) -> bool:
    """The version exists with its record (the record is written last)."""
    return made.out.is_file() and made.out.with_suffix(".json").is_file()


def copy_chosen(version: Path, chosen: Path) -> None:
    """Make `chosen` (a shot's `still.png`, ...) a copy of `version`, unless it is one already."""
    if not (chosen.is_file() and filecmp.cmp(version, chosen, shallow=False)):
        tmp = chosen.with_name(f".{chosen.name}.tmp")
        shutil.copyfile(version, tmp)
        tmp.replace(chosen)


def choose(made: ShotJob) -> None:
    """Make the chosen file a copy of this version (until the owner chooses, M5)."""
    if made.task.chosen is not None:
        copy_chosen(made.out, made.task.chosen)


def make(job: Job, stage: str, made: ShotJob) -> None:
    """Generate the version, then its `Made` record, then the chosen copy."""
    task = made.task
    made.out.parent.mkdir(parents=True, exist_ok=True)
    done = job.models.generate(task.model, task.prompt, out=made.out, seed=made.seed, inputs=task.inputs)
    refuse_blank(task.model, done.path)
    record = Made(
        stage=stage,
        subject=task.subject,
        file=job.project.relative(made.out),
        key=made.key,
        model=task.model,
        prompt=task.prompt,
        seed=made.seed,
        inputs=described(job.project, task.inputs) | dict(done.recorded or {}),
        settings=job.settings.model_dump(mode="json"),
        made_at=now(),
        call=done.call,
    )
    write_json(made.out.with_suffix(".json"), record)
    choose(made)


# ------------------------------------------------------------------------------ progress events (0003)

# what each version prefix makes, as the dashboard names it (D-050)
KINDS = {"stills": "still", "clips": "raw_clip", "finish": "clip"}  # what each stage keeps (D-050)


@dataclass
class Units:
    """A stage's units of work (one model-made file each) and how many are made, for its progress
    events (0003, D-050): `totals` and `made` per kind."""

    job: Job
    stage: str
    totals: dict[str, int] = field(default_factory=dict[str, int])
    made: dict[str, int] = field(default_factory=dict[str, int])
    first: set[str] = field(default_factory=set[str])  # the models whose session made a file already

    @property
    def done(self) -> int:
        return sum(self.made.values())

    @property
    def total(self) -> int:
        return sum(self.totals.values())

    def count(self, step: str, jobs: list[ShotJob], *, total: int | None = None) -> None:
        """Count a step's distinct versions (`total` when they cannot all be known yet) and those made."""
        distinct = {m.out: m for m in jobs}
        kind = KINDS[step]
        self.totals[kind] = self.totals.get(kind, 0) + (len(distinct) if total is None else total)
        self.made[kind] = self.made.get(kind, 0) + sum(map(is_made, distinct.values()))

    def announce(self) -> None:
        """The `units` event: what the stage will have made at the end, and what was made already."""
        self.job.events.write("units", stage=self.stage, totals=self.totals, made=self.made)

    def make(self, step: str, made: ShotJob) -> None:
        """Make one version between a `version_started` and a `version_made` event."""
        kind, task, events = KINDS[step], made.task, self.job.events
        who = {"shot": task.subject}
        first = task.model not in self.first
        events.write("version_started", stage=self.stage, kind=kind, **who, n=self.done + 1, total=self.total)
        began = time.monotonic()
        make(self.job, step, made)
        took = round((time.monotonic() - began) * 1000)
        self.first.add(task.model)
        self.made[kind] = self.made.get(kind, 0) + 1
        file = self.job.project.relative(made.out)
        events.write(
            "version_made",
            stage=self.stage,
            kind=kind,
            **who,
            file=file,
            took_ms=took,
            first=first,
            done=self.done,
            total=self.total,
        )
