"""What is stored (design §4): `state.json` per project, a version record per image, `run.json`.

Hone Frame: ported from `src/hone_frame/records.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from hone_music_video.frame._files import FORMAT_VERSION

Status = Literal["todo", "running", "waiting", "done", "failed", "provided"]
Source = Literal["generated", "provided", "composed"]
RunStatus = Literal["idle", "queued", "running", "pausing", "paused", "waiting", "stopped", "failed", "done"]


class Record(BaseModel):
    """A stored record: unknown keys are ignored so newer files stay readable."""

    model_config = ConfigDict(extra="ignore")


class Version(Record):
    """One image of an item (`items/<item>/vNNN.png`) and what made it (`vNNN.json`). Never deleted."""

    n: int
    file: str  # relative to the project folder
    source: Source
    at: str
    model: str | None = None
    prompt: str | None = None
    negative: str | None = None
    seed: int | None = None
    size: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict[str, Any])
    refs: list[str] = Field(default_factory=list[str])
    made_from: dict[str, int] = Field(default_factory=dict[str, int])  # ref -> its version used
    made_with: dict[str, Any] = Field(default_factory=dict[str, Any])  # the item's fields that made it
    elapsed_s: float | None = None
    original: str | None = None  # a provided file's own name
    sha256: str | None = None  # a provided file's hash: a changed `file` makes a new version


class ItemState(Record):
    """One item's state in `state.json`: its status, mark, current version and every version."""

    status: Status = "todo"
    marked: bool = False
    current: int | None = None
    error: str | None = None
    candidates: list[int] = Field(default_factory=list[int])  # what a waiting count > 1 item is picked from
    run_prompt: int | None = None  # hone-music-video 0033: the prompt (from 0) "Run this prompt" asked for
    file_sha256: str | None = None  # the item's `file` when it was last imported: only a change re-imports
    versions: list[Version] = Field(default_factory=list[Version])

    def version(self, n: int) -> Version | None:
        return next((v for v in self.versions if v.n == n), None)


class ProjectState(Record):
    """`state.json`: what exists, per item. The project file says what to make (design §4.2)."""

    format_version: str = FORMAT_VERSION
    id: str
    name: str
    created_at: str
    source: str = ""  # the name of the file that was imported
    items: dict[str, ItemState] = Field(default_factory=dict[str, ItemState])


class RunRecord(Record):
    """`run.json`: the project's run (design §8)."""

    format_version: str = FORMAT_VERSION
    status: RunStatus = "idle"
    reason: str = ""
    current: str | None = None
    item: str | None = None  # the item the run ended on (the one it waits for, or that failed)
    current_started_at: str | None = None
    made: list[str] = Field(default_factory=list[str])
    started_at: str | None = None
    flow_runs: list[str] = Field(default_factory=list[str])  # the hone-flow runs of this run
