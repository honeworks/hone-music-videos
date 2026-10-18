"""The `hone-music-video` command: dashboard, new, run, resume, status, approve, reject, lyrics-timing,
check-shots, frame (the scenes' pictures, 0027), remake, redo, motion, pause, assemble, export, costs.

Exit codes: 0 success (a run that stops at a gate too), 1 failure (a failed run, an error printed as
`error: ...`, or `check-shots` finding errors), 2 usage error."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import hone_flow as fk

from hone_music_video import _cli_frame as frame_commands
from hone_music_video import _cli_redo as redo_commands
from hone_music_video import frame_stages, runs, runs_redo
from hone_music_video.adapters.hone_models import HoneModels
from hone_music_video.dashboard import Dashboard
from hone_music_video.editor_files import export
from hone_music_video.errors import InvalidInput, MusicVideoError
from hone_music_video.owner_timing import parse_spec
from hone_music_video.ports import Models
from hone_music_video.project import GivenSheet, Material, Project, create_project, open_project
from hone_music_video.settings import PACES, parse_settings
from hone_music_video.shots_check import check_shots
from hone_music_video.video_costs import Costs, costs

FAKE_HELP = "run every stage on fake models (no model is called; for demos and tests, D-011)"


def _models(fake: bool) -> Models:
    if fake:
        from hone_music_video.testing import FakeModels  # noqa: PLC0415 - only for --fake-models

        return FakeModels()
    return HoneModels()


def _given(flag: str, text: str) -> GivenSheet:
    name, _, rest = text.partition("=")
    file, _, note = rest.partition(":")
    if not name or not file:
        raise InvalidInput(f"{flag} {text!r}: write NAME=FILE or NAME=FILE:NOTE")
    return GivenSheet(name, Path(file), note)


def _new(args: argparse.Namespace) -> int:
    given: dict[str, Any] = json.loads(Path(args.settings).read_text()) if args.settings else {}
    options = {"pace": args.pace, "mood": args.mood}  # 0009
    settings = parse_settings(given | {k: v for k, v in options.items() if v is not None})
    models = _models(args.fake_models)
    for line in frame_stages.image_notices(settings, models):
        print(line, file=sys.stderr)
    material = Material(
        lyrics=Path(args.lyrics).read_text(encoding="utf-8") if args.lyrics else None,
        story=args.story or "",
        feeling=args.feeling or "",
        sheets=tuple(_given("--sheet", s) for s in args.sheet),
        poses=tuple(_given("--pose", s) for s in args.pose),
    )
    approve = "auto" if args.auto_approve else "ask"
    project = create_project(
        args.projects, args.name, args.song, material, settings, approve=approve, prepare=args.prepare
    )
    print(project.root)
    return 0


def _report(state: runs.RunState, as_json: bool) -> int:
    if as_json:
        print(json.dumps(state.as_dict(), indent=2))
    else:
        print(
            f"{state.project}: {state.status}" + (f" (waiting for {state.waiting})" if state.waiting else "")
        )
        for stage in state.stages:
            shots = f"  {stage.shots_done}/{stage.shots_total} shots" if stage.shots_total else ""
            error = f"  {stage.error}" if stage.error else ""
            print(f"  {stage.number:>2} {stage.name:<13} {stage.status}{shots}{error}")
    return 1 if state.status == "failed" else 0


def _decide(args: argparse.Namespace, project: Project) -> str:
    """A decision at the gate waiting: approve it, or run its stage again with a note (D-015)."""
    if args.command == "approve":
        return (
            f"approved {runs.approve(project, args.gate, note=args.note, accept_errors=args.accept_errors)}"
        )
    return f"rejected {runs.reject(project, args.gate, note=args.note)}"


def _lyrics_timing(project: Project, specs: list[str]) -> int:
    """At the lyrics gate: save the owner's times of lines (0018), then the check of the edited timeline;
    exit 1 when it finds errors (the gate cannot be approved until they are fixed)."""
    saved = runs.lyrics_timing(project, parse_spec(specs))
    for kind, problems in (("error", saved.report.errors), ("warning", saved.report.warnings)):
        for p in problems:
            print(f"{kind:<7}  {p.where:<6}  {p.rule:<17}  {p.message}")
    for line, why in saved.dropped.items():
        print(f"dropped  {line}: {why}")
    timed = ", ".join(saved.kept) or "none"
    print(f"timing saved (lines timed by you: {timed}); {len(saved.report.errors)} errors")
    return 1 if saved.report.errors else 0


def _check_shots(project: Project) -> int:
    """The shot list of the frame plan checked again (design §5.2): every error and warning with its
    shot, rule and amount; exit 1 when there are errors."""
    timeline = runs.stage_outputs(project, "review_lyrics")["review_lyrics"]
    if timeline is None or not frame_stages.has_plan(project):
        raise InvalidInput(f"{project.id} has no shot list yet; run it until the scenes are planned")
    shots = frame_stages.as_shots(frame_stages.read_shots(project))
    report = check_shots(shots, timeline, sorted({c for s in shots.shots for c in s.cast}), project.settings)
    for kind, problems in (("error", report.errors), ("warning", report.warnings)):
        for p in problems:
            print(f"{kind:<7}  {p.where:<6}  {p.rule:<17}  {p.message}")
    print(f"{len(shots.shots)} shots: {len(report.errors)} errors, {len(report.warnings)} warnings")
    return 1 if report.errors else 0


def _costs(found: Costs, as_json: bool) -> int:
    """What the video cost (design §13.5, D-062): the totals, then each stage's time and hosted cost."""
    if as_json:
        print(found.model_dump_json(indent=2))
        return 0
    unknown = f" and {found.unknown_calls} calls without a price" if found.unknown_calls else ""
    hours = found.gpu_ms / 3.6e6
    print(f"{found.project}: ${found.hosted_usd:.2f} of hosted calls{unknown}, {hours:.1f} h of GPU")
    print(f"  reruns and redos added ${found.added_usd:.2f} and {found.added_ms / 3.6e6:.1f} h")
    if not found.store_found:
        print(f"  no hone-models records found at {found.store}: the planners' calls are unknown")
    for s in found.stages:
        parts = (s.first, s.reruns, s.redos)
        spent, cost = sum(p.time_ms for p in parts), sum(p.cost_usd for p in parts)
        print(f"  {s.stage:<13} {s.where:<6} {spent / 60_000:>8.1f} min  ${cost:.4f}")
    return 0


def _command(args: argparse.Namespace) -> int:
    if args.command == "new":
        return _new(args)
    if args.command == "dashboard":
        dashboard = Dashboard(args.projects, _models(args.fake_models), args.port).start()
        print(f"hone-music-video dashboard: {dashboard.url}  (projects in {args.projects})", flush=True)
        dashboard.wait()
        return 0
    project = open_project(args.project)
    if args.command in ("approve", "reject"):
        print(f"{_decide(args, project)}; continue with `resume`")
        return 0
    if args.command in ("check-shots", "export", "costs", "lyrics-timing"):
        return _read(args, project)
    if args.command in redo_commands.COMMANDS:
        state = redo_commands.command(args, project, _models(args.fake_models))
        return 0 if state is None else _report(state, args.json)
    return _report(_state(args, project), args.json)


def _read(args: argparse.Namespace, project: Project) -> int:
    """`check-shots`, `export` or `costs` (from what the run made), or `lyrics-timing` (the owner's times
    saved at the gate): no run and no model made."""
    if args.command == "lyrics-timing":
        return _lyrics_timing(project, args.line)
    if args.command == "check-shots":
        return _check_shots(project)
    if args.command == "export":
        print("\n".join(map(str, export(project))))
        return 0
    return _costs(costs(project), args.json)


def _state(args: argparse.Namespace, project: Project) -> runs.RunState:
    """`run`, `resume`, `assemble` or `status`: the run's state afterwards."""
    if args.command == "assemble":
        return runs_redo.assemble(project, _models(args.fake_models))
    if args.command == "run":
        return runs.start(project, _models(args.fake_models))
    if args.command == "resume":
        return runs.resume(project, _models(args.fake_models))
    return runs.status(project)


def _look_flags(new: argparse.ArgumentParser) -> None:
    """Pace and mood on `hone-music-video new` (0009)."""
    new.add_argument(
        "--pace", choices=PACES, help="calm: long shots; energetic: short ones (default: balanced)"
    )
    new.add_argument("--mood", help='the mood in free words, any language: "tragic", "tender, hopeful"')


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="hone-music-video", description="Song in, music video out.")
    sub = top.add_subparsers(dest="command", required=True)
    dash = sub.add_parser("dashboard", help="serve the web dashboard on localhost")
    dash.add_argument("--projects", default="projects", help="the projects folder (default: ./projects)")
    dash.add_argument("--port", type=int, default=8794)
    dash.add_argument("--fake-models", action="store_true", help=FAKE_HELP)
    new = sub.add_parser("new", help="make a project from a song")
    new.add_argument("name", help="the video's name")
    new.add_argument("--song", required=True, help="the audio file (WAV, FLAC, MP3, M4A, OGG)")
    new.add_argument("--projects", default="projects", help="the projects folder (default: ./projects)")
    new.add_argument("--lyrics", help="a text file with the lyrics, one sung line per line")
    new.add_argument("--story", help="notes on the story, setting and characters")
    new.add_argument(
        "--feeling", help="what the viewer should feel, and how it changes through the song (0028)"
    )
    new.add_argument("--sheet", action="append", default=[], help="a given picture: NAME=FILE[:NOTE]")
    new.add_argument(
        "--pose",
        action="append",
        default=[],
        help="a pose picture a character's variant takes: NAME=FILE[:NOTE]",
    )
    new.add_argument("--settings", help="a JSON file of settings (design §2.3); unknown keys are refused")
    _look_flags(new)
    new.add_argument(
        "--auto-approve",
        action="store_true",
        help="run without stopping for approval: each gate passes unless a check errs (0004)",
    )
    new.add_argument(
        "--prepare",
        action="store_true",
        help="stop before the scenes, every hosted call made; `resume` makes the rest offline (0028)",
    )
    new.add_argument("--fake-models", action="store_true", help=FAKE_HELP)
    for name, text in (
        ("run", "start the run"),
        ("resume", "continue the run"),
        ("status", "show the run"),
        ("assemble", "cut the video again from the finished clips (no model is called)"),
    ):
        cmd = sub.add_parser(name, help=text)
        cmd.add_argument("project", help="the project folder")
        cmd.add_argument("--json", action="store_true", help="print the state as JSON")
        if name != "status":
            cmd.add_argument("--fake-models", action="store_true", help=FAKE_HELP)
    approve = sub.add_parser("approve", help="approve the gate waiting for the owner")
    approve.add_argument("project", help="the project folder")
    approve.add_argument("--gate", help="the gate's name (default: the one waiting)")
    approve.add_argument("--note", default="", help="a note kept with the decision")
    approve.add_argument(
        "--accept-errors",
        action="store_true",
        help="approve a shot list whose remaining errors do not break the video (D-027)",
    )
    reject = sub.add_parser("reject", help="run the gate's stage again with a note (D-015)")
    reject.add_argument("project", help="the project folder")
    reject.add_argument("--gate", help="the gate's name (default: the one waiting)")
    reject.add_argument("--note", required=True, help="what should change; the planner reads it")
    timed = sub.add_parser("lyrics-timing", help="at review_lyrics: set lines' start and end by hand (0018)")
    timed.add_argument("project", help="the project folder")
    timed.add_argument("line", nargs="+", help="LINE=START-END in ms (L012=77300-81200), or LINE=- to undo")
    check = sub.add_parser("check-shots", help="check the shot list: every error and warning (design §5.2)")
    check.add_argument("project", help="the project folder")
    spent = sub.add_parser("costs", help="what the video cost: hosted calls and GPU time, by stage")
    spent.add_argument("project", help="the project folder")
    spent.add_argument("--json", action="store_true", help="print costs.json")
    export_ = sub.add_parser(
        "export", help="write the edit for DaVinci Resolve and Premiere (edit.xml, edit.edl)"
    )
    export_.add_argument("project", help="the project folder")
    redo_commands.parsers(sub.add_parser, FAKE_HELP)
    frame_commands.parsers(sub.add_parser, FAKE_HELP)
    return top


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == frame_commands.COMMAND:  # 0026, experimental
            return frame_commands.command(args, open_project(args.project), _models)
        return _command(args)
    except (MusicVideoError, fk.HoneFlowError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # Ctrl-C, also a second one while the dashboard closes
        return 130


if __name__ == "__main__":
    sys.exit(main())
