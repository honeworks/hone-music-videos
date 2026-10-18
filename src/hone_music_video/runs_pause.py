"""Pause and Stop a running video (0022).

`pause` writes the owner's request (`pause.request`); the run's stages stop at their next model call, and
the frame run (stage 6) pauses or stops at once, cancelling the picture being made (0027 §5)."""

from __future__ import annotations

from hone_music_video import pause as requests
from hone_music_video import runs
from hone_music_video.errors import RunStateError
from hone_music_video.events import EventLog
from hone_music_video.project import Project


def pause(project: Project, *, now: bool = False) -> runs.RunState:
    """Ask the running video to pause (finish the file being made) or, with `now`, to stop at once."""
    if runs.status(project).status != "running":
        raise RunStateError(f"{project.id} is not running; there is nothing to pause")
    requests.request(project, now=now)
    EventLog(project.events_file).write("pause_asked", now=now)
    return runs.status(project)


def paused(project: Project) -> bool:
    return runs.status(project).status == "paused"
