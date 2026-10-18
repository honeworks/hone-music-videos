"""The records of a project (design §4): JSON with `format_version: "1"`, times in integer milliseconds.

`Timeline` and `Shots` have exactly the fields of design §4.1 and §4.3; the frame's records are in
`records_frame.py` (0027). The other records are the
outputs of the stages of design §3.1 (D-009). The records of stages 1 to 4 live in `records_timeline.py`
and are imported here."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from hone_music_video.records_timeline import (
    STRICT,
    AlignedWord,
    Alignment,
    Disagreement,
    HostedCall,
    Instrumental,
    Line,
    ListenAgain,
    Moved,
    Ms,
    Retry,
    Section,
    Separation,
    Song,
    Timeline,
    Unsure,
    Version,
    Word,
    Words,
)

__all__ = [
    "STRICT",
    "AlignedWord",
    "Alignment",
    "Assembly",
    "Cut",
    "Disagreement",
    "Framing",
    "HostedCall",
    "Instrumental",
    "Line",
    "ListenAgain",
    "Made",
    "Moved",
    "Ms",
    "Problem",
    "Report",
    "Retry",
    "Section",
    "Separation",
    "Shot",
    "ShotFile",
    "ShotFiles",
    "Shots",
    "Song",
    "Timeline",
    "Unsure",
    "Version",
    "Word",
    "Words",
]

Framing = Literal["extreme-wide", "wide", "medium", "close-up", "extreme-close-up", "insert"]


# ---------------------------------------------------------------------------- §4.3 shots


class Shot(BaseModel):
    """One shot of the video (design §7.3)."""

    model_config = STRICT
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]*$")  # names the shot's folder (D-026)
    start_ms: Ms
    end_ms: Ms
    lines: list[str]
    beat: str
    framing: Framing
    faces: bool
    cast: list[str]
    location: str
    camera: str
    still_prompt: str  # the prompt of the scene's picture in use (0027)
    motion_prompt: str
    clip_seed: int = 0  # a clip redone with a new seed (0027 §7)


class Shots(BaseModel):
    """`shots.json` (design §4.3)."""

    model_config = STRICT
    format_version: Version = "1"

    shots: list[Shot]


# ---------------------------------------------------------------------------- checks, media


class Problem(BaseModel):
    """One validator finding: the rule, where, and what is wrong. An `acceptable` error does not break the
    video, so the owner may approve the gate with it (D-027)."""

    model_config = STRICT
    rule: str
    where: str
    message: str
    acceptable: bool = False


class Report(BaseModel):
    """A validator's result (stages `check_lyrics`, `check_shots`, design §5)."""

    model_config = STRICT
    format_version: Version = "1"

    errors: list[Problem] = []
    warnings: list[Problem] = []


class ShotFile(BaseModel):
    """The file a stage made for one shot."""

    model_config = STRICT
    shot: str
    file: str  # the version made, relative to the project folder
    key: str  # sha256 of what made it (see `Made`)
    take: int = 0  # always 0 since 0027 (one take per shot); kept so older records read


class ShotFiles(BaseModel):
    """Stages `stills`, `clips`, `finish`: the file the video uses per shot (`shots`), and the file of
    every take that has one (`takes`, D-031)."""

    model_config = STRICT
    format_version: Version = "1"

    shots: list[ShotFile]
    takes: list[ShotFile] = []


class Cut(BaseModel):
    """One shot in the assembled video (design §5.3, D-035): its frames `first_frame` to `last_frame`
    (both included) are the clip's frames from its first; a clip shorter than that has its last frame
    held `held_frames` times."""

    model_config = STRICT
    shot: str
    clip: str  # the finished clip of the take in use, relative to the project folder
    first_frame: int
    last_frame: int
    held_frames: int = 0


class Assembly(BaseModel):
    """Stage `assemble` (`current/edl.json`): the edit list (design §12) and the video it was cut to
    (None in a run assembled before 0.1's M6)."""

    model_config = STRICT
    format_version: Version = "1"

    fps: int
    edl: list[Cut]
    video: str | None = None


class Made(BaseModel):
    """What made one generated file, kept beside it: model, prompt, seed, inputs (files by path and
    sha256) and the settings (design §1, D-009)."""

    model_config = STRICT
    format_version: Version = "1"

    stage: str
    subject: str  # the shot, or the character of a sheet take
    file: str  # relative to the project folder; never overwritten
    key: str  # sha256 of the model, prompt, seed and inputs
    model: str
    prompt: str
    seed: int
    inputs: dict[str, Any]
    settings: dict[str, Any]
    made_at: str
    # the hosted call of an in-library client with its price (0020, D-130); None for every other file
    call: HostedCall | None = None
