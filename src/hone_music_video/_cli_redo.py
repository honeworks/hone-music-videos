"""The command line's `remake`, `redo` (a clip with a new seed), `motion` and `pause` (0022, 0027 §7)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from hone_music_video import runs, runs_pause, runs_redo
from hone_music_video.ports import Models
from hone_music_video.project import Project

COMMANDS = ("remake", "redo", "motion", "pause")


def command(args: argparse.Namespace, project: Project, models: Models) -> runs.RunState | None:
    """The run's state afterwards; None when no run was made (a motion prompt or clip seeds saved)."""
    if args.command == "pause":
        state = runs_pause.pause(project, now=args.now)
        print("stopping now" if args.now else "pausing after the file being made; `resume` goes on")
        return state
    if args.command == "redo":
        ids = runs_redo.redo_clips(project, args.shots)
        print(f"new clip seeds for {', '.join(ids)}")
        return runs_redo.remake(project, models) if not args.later else None
    if args.command == "motion":
        for word in runs_redo.set_motion(project, args.shot, args.text):
            print(f"warning: the motion prompt names {word!r}: the video model would move the mouth")
        print(f"{args.shot}: motion prompt saved; `remake` makes its clip again", file=sys.stderr)
        return None
    return runs_redo.remake(project, models)


def parsers(add_parser: Callable[..., argparse.ArgumentParser], fake_help: str) -> None:
    def cmd(name: str, text: str) -> argparse.ArgumentParser:
        found = add_parser(name, help=text)
        found.add_argument("project", help="the project folder")
        found.add_argument("--json", action="store_true", help="print the state as JSON")
        found.add_argument("--fake-models", action="store_true", help=fake_help)
        return found

    cmd("remake", "make the clips of the scenes that changed, and cut the video again (0027)")
    redo = cmd("redo", "make shots' clips again with a new seed, then remake")
    redo.add_argument("shots", nargs="+", help="shot ids, or ranges like S012-S015")
    redo.add_argument("--later", action="store_true", help="only save the new seeds; `remake` makes them")
    motion = cmd("motion", "set a shot's motion prompt; `remake` makes its clip again")
    motion.add_argument("shot", help="the shot's id")
    motion.add_argument("text", help="the motion prompt: what moves, how, and what stays still")
    held = cmd("pause", "pause the running video after the file being made, or stop it (0022)")
    held.add_argument("--now", action="store_true", help="stop at once: the picture or clip being made too")
