"""The command line's `frame` (0027): the project's frame workspace, steered as Hone Frame's dashboard
steers it. Each command is a Hone Frame action (`hone_music_video.frame.actions`, its design §6) or a run
of the marked items (its §8):

    hone-music-video frame status PROJECT [--json]
    hone-music-video frame run PROJECT [--once]
    hone-music-video frame accept PROJECT ITEM [N]
    hone-music-video frame use PROJECT ITEM N [--dependants]
    hone-music-video frame redo PROJECT ITEM [--dependants]
    hone-music-video frame unmark PROJECT ITEM
    hone-music-video frame run-prompt PROJECT ITEM N
    hone-music-video frame replace PROJECT ITEM FILE [--dependants]
    hone-music-video frame edit PROJECT ITEM FIELD=VALUE ...
    hone-music-video frame guide PROJECT

Hone Frame: its CLI has `run` and `status`; the actions are its dashboard's buttons."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hone_music_video import frame_stages, runs
from hone_music_video.errors import InvalidInput, RunStateError
from hone_music_video.frame import Runner, actions
from hone_music_video.frame.guide import guide_for
from hone_music_video.frame.project import Project as FrameProject
from hone_music_video.frame.views import ItemView, project_view
from hone_music_video.ports import Models
from hone_music_video.project import Project

COMMAND = "frame"
ModelsOf = Callable[[bool], Models]


def _line(item: ItemView) -> str:
    flags = ["marked"] if item.marked else []
    flags += ["changed since made"] if item.changed_since_made else []
    flags += [f"made from an older {r}" for r in item.older_refs]
    pick = f" pick from {item.candidates}" if item.candidates else ""
    current = f"v{item.current}" if item.current else "-"
    return f"  {item.id:<34} {item.status:<9} {current:<5} of {len(item.versions)}{pick}  {', '.join(flags)}"


def _status(args: argparse.Namespace, fp: FrameProject) -> int:
    view = project_view(fp)
    if args.json:
        print(view.model_dump_json(indent=2))
        return 0
    for item in view.items:
        print(_line(item))
    print(f"run: {view.run.status}" + (f" ({view.run.reason})" if view.run.reason else ""))
    return 0


def _value(text: str) -> Any:
    """A field's value: JSON when it parses (numbers, true, lists, null), else the text itself."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _edit(fp: FrameProject, item: str, pairs: list[str]) -> None:
    changes: dict[str, Any] = {}
    for pair in pairs:
        field, sep, value = pair.partition("=")
        if not sep or not field:
            raise InvalidInput(f'{pair!r}: write FIELD=VALUE (prompt="...", seed=7, hold=true, refs=null)')
        changes[field] = _value(value)
    actions.edit(fp, item, changes)


def _run(args: argparse.Namespace, project: Project, models: Models) -> int:
    if runs.status(project).status == "running":
        raise RunStateError(f"{project.id} is running: its scenes stage runs the marked items")
    ws = frame_stages.workspace(project, models)
    fp = frame_stages.frame_project(ws)
    runner = Runner(ws)
    runner.recover([fp.id])
    if fp.run().status == "paused":
        runner.resume(fp.id)
    else:
        runner.run(fp.id)
    runner.drain(once=args.once)
    end = fp.run()
    print(f"run: {end.status}" + (f" ({end.reason})" if end.reason else ""))
    return 1 if end.status == "failed" else 0


def _act(args: argparse.Namespace, fp: FrameProject) -> str:
    """An action on one item: what it did, said for the owner."""
    what, item = args.frame_command, args.item
    if what == "accept":
        actions.accept(fp, item, args.version)
        return f"{item}: accepted" + (f" v{args.version}" if args.version else "")
    if what == "use":
        marked = actions.use_version(fp, item, args.version, with_dependants=args.dependants)
        return f"{item}: v{args.version} in use" + (f"; marked {', '.join(marked)}" if marked else "")
    if what == "redo":
        return "marked " + ", ".join(actions.mark(fp, item, with_dependants=args.dependants))
    if what == "unmark":
        actions.unmark(fp, item)
        return f"{item}: unmarked"
    if what == "replace":
        path = Path(args.file)
        marked = actions.provide(fp, item, path.read_bytes(), path.name, with_dependants=args.dependants)
        return f"{item}: replaced with {path.name}" + (f"; marked {', '.join(marked)}" if marked else "")
    _edit(fp, item, args.fields)
    return f"{item}: edited"


def command(args: argparse.Namespace, project: Project, models_of: ModelsOf) -> int:
    """Run one `frame` command; the exit code."""
    what = args.frame_command
    if what == "run":
        return _run(args, project, models_of(args.fake_models))
    ws = frame_stages.workspace(project, models_of(args.fake_models))
    fp = frame_stages.frame_project(ws)
    if what == "status":
        return _status(args, fp)
    if what == "guide":
        print(guide_for(ws, [], fp.id))
        return 0
    if what == "run-prompt":
        actions.run_prompt(fp, args.item, args.prompt - 1)
        print(f"{args.item}: marked to make prompt {args.prompt}; `frame run` makes it")
        return 0
    print(_act(args, fp))
    return 0


def parsers(add_parser: Callable[..., argparse.ArgumentParser], fake_help: str) -> None:
    frame = add_parser(COMMAND, help="the scenes' pictures: Hone Frame's actions on the project file (0027)")
    sub = frame.add_subparsers(dest="frame_command", required=True)

    def cmd(name: str, text: str, *, item: bool = True) -> argparse.ArgumentParser:
        found = sub.add_parser(name, help=text)
        found.add_argument("project", help="the project folder")
        if item:
            found.add_argument("item", help="the item's id (darvin.hero, oasis.dawn, S004)")
        found.add_argument("--fake-models", action="store_true", help=fake_help)
        return found

    status = cmd("status", "every item: status, picture in use, versions, flags; the run", item=False)
    status.add_argument("--json", action="store_true", help="print the project view as JSON")
    run = cmd("run", "make the marked items, top to bottom", item=False)
    run.add_argument("--once", action="store_true", help="make one item, then pause")
    accept = cmd("accept", "accept a held item, or pick one of its pictures")
    accept.add_argument("version", type=int, nargs="?", help="the picture to keep (its version number)")
    use = cmd("use", "make a version of an item the one in use")
    use.add_argument("version", type=int, help="the version number")
    redo = cmd("redo", "mark an item to make again")
    cmd("unmark", "clear an item's mark")
    run_prompt = cmd("run-prompt", "mark an item with several prompts to make one of them (0033)")
    run_prompt.add_argument("prompt", type=int, help="the prompt's number, from 1")
    replace = cmd("replace", "replace an item's picture with your own file")
    replace.add_argument("file", help="a PNG, JPEG or WebP file")
    for found in (use, redo, replace):
        found.add_argument("--dependants", action="store_true", help="mark the items made from it too")
    edit = cmd("edit", "change an item's fields in the project file")
    edit.add_argument("fields", nargs="+", help='FIELD=VALUE: prompt="...", seed=7, hold=true, count=null')
    cmd("guide", "the prompt guide for the project's models", item=False)
