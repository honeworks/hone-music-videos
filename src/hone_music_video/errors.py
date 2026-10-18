"""Typed errors. Every message says what happened and what to do about it."""

from __future__ import annotations


class MusicVideoError(RuntimeError):
    """The base of every error hone-music-video raises on purpose."""


class InvalidInput(MusicVideoError):
    """Settings, inputs or plans that do not fit (an unknown setting, a missing song, a cast member
    without a picture...).

    `problems` lists each problem as `"<field>: <what is wrong>"`."""

    def __init__(self, message: str, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.problems = problems or []


class NotFound(MusicVideoError):
    """A project, gate or file that does not exist."""


class ProjectUnreadable(MusicVideoError):
    """A project whose `project.json` this version cannot read (made by a newer version, or damaged)."""


class RunStateError(MusicVideoError):
    """The run is not in a state that allows the operation (no run yet, no gate waiting, busy...)."""


class Paused(MusicVideoError):
    """The owner paused or stopped the run (0022); Resume goes on from what is made."""


class ModelFailure(MusicVideoError):
    """A model call that gave no usable answer (an error result or an invalid reply)."""


class ToolMissing(MusicVideoError):
    """A local program the stage needs (ffprobe) is not installed."""
