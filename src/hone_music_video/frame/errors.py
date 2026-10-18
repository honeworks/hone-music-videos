"""The frame's typed errors (change 0027). Hone Frame: `errors.py`, word for word, but the base class is
this library's `MusicVideoError`, so the command line prints them as it prints its own."""

from __future__ import annotations

from dataclasses import dataclass

from hone_music_video.errors import MusicVideoError


class HoneFrameError(MusicVideoError):
    """Base class of every frame error."""


class NotFound(HoneFrameError):  # noqa: N818 - Hone Frame's name
    """A project, item, version, model or file that does not exist."""


@dataclass(frozen=True)
class Problem:
    """One reason a project file or an edit was refused: the item it is about and what to do."""

    item: str
    message: str

    def __str__(self) -> str:
        return f"{self.item}: {self.message}"


class InvalidRequest(HoneFrameError):  # noqa: N818 - Hone Frame's name
    """A project file, an edit or a request that cannot be accepted; `problems` lists every reason."""

    def __init__(self, message: str, problems: list[Problem] | None = None) -> None:
        super().__init__(message if not problems else f"{message}: " + "; ".join(map(str, problems)))
        self.problems = problems or []


class RunStateError(HoneFrameError):
    """An action that the run's or the item's current state does not allow."""
