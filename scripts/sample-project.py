"""Make a sample video project from the owner's song and the trial's real media, to see the dashboard.

    uv run scripts/sample-project.py            # run it to the end (every gate approved), then:
    uv run hone-music-video dashboard           # http://127.0.0.1:8794/ (projects in ./projects)

    uv run scripts/sample-project.py --live     # serve the dashboard and run slowly (0.5-2 s per model
                                                # call); the run stops at each gate: approve it there

What is real: the song, its lyrics and story (`samples/The Long Night/`), the song's length (ffprobe in
the `measure` stage) and every picture and clip, copied from the trial (`../pipeline-demo`: character
packs, start frames, clips). What is not: no model runs. The run goes through the library's real
workflow and `runs` API on a sample model set (`sample_models.py`, a `FakeModels`): the planners answer
from the lyrics and the trial's prompts with invented, evenly spread times, and every media call copies
a trial file. The library's assembly cuts `current/video.mp4` (1280x720, the size of the sample's
finished clips).

Everything copied or made stays in the projects folder (git-ignored). A dev script: not in the wheel.
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import shutil
import sys
import time
from pathlib import Path

from sample_models import SampleModels, parse_lyrics

from hone_music_video import Dashboard, Material, create_project, runs
from hone_music_video.project import Project
from hone_music_video.testing.fake_models import Call

ROOT = Path(__file__).resolve().parents[1]
FPS = 32
print = functools.partial(print, flush=True)  # --live prints while it serves


def slow_down(call: Call) -> None:
    """--live: 0.5 to 2 s per model call (always the same for the same call), so the page can follow."""
    if call.kind != "session":
        digest = hashlib.sha256(f"{call.kind}|{call.prompt}|{call.out}".encode()).digest()
        time.sleep(0.5 + 1.5 * digest[0] / 255)


def new_project(args: argparse.Namespace) -> Project:
    song = args.sample / "song.mp3"
    lyrics, story = args.sample / "lyrics.txt", args.sample / "story.md"
    material = Material(lyrics=lyrics.read_text(encoding="utf-8"), story=story.read_text(encoding="utf-8"))
    return create_project(args.projects, args.name, song, material)


def check_inputs(args: argparse.Namespace) -> None:
    missing = [
        str(p)
        for p in (
            args.sample / "song.mp3",
            args.sample / "lyrics.txt",
            args.sample / "story.md",
            args.trial_media / "character-packs",
            args.trial_media / "inputs" / "video-stills.toml",
        )
        if not p.exists()
    ]
    missing += [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    lyrics = args.sample / "lyrics.txt"
    if lyrics.is_file() and not any(
        kind == "line" for kind, _ in parse_lyrics(lyrics.read_text(encoding="utf-8"))
    ):
        missing.append(f"{lyrics}: sung lines (it has only [bracketed] notes)")
    if missing:
        sys.exit(
            "cannot make the sample, missing:\n  "
            + "\n  ".join(missing)
            + "\n(give --sample and --trial-media, and install ffmpeg)"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--live", action="store_true", help="serve the dashboard, run slowly, stop at every gate"
    )
    parser.add_argument(
        "--projects", type=Path, default=Path("projects"), help="the projects folder (./projects)"
    )
    parser.add_argument(
        "--sample",
        type=Path,
        default=ROOT / "samples" / "The Long Night",
        help="song.mp3, lyrics.txt, story.md",
    )
    parser.add_argument(
        "--trial-media", type=Path, default=ROOT.parent / "pipeline-demo", help="the trial's folder"
    )
    parser.add_argument("--name", default="The Long Night", help="the project's name")
    parser.add_argument("--port", type=int, default=8794, help="--live: the dashboard's port")
    args = parser.parse_args()
    check_inputs(args)
    models = SampleModels(
        args.trial_media,
        args.projects / ".sample-cache",
        (args.sample / "lyrics.txt").read_text(encoding="utf-8"),
        on_call=slow_down if args.live else None,
    )
    project = new_project(args)
    print(f"project: {project.root}")
    if args.live:
        dashboard = Dashboard(args.projects, models, port=args.port).start()
        dashboard.server.runner.submit(project.id, "start")
        print(f"open {dashboard.url}#/p/{project.id} and approve each gate there (Ctrl-C stops)")
        dashboard.wait()
        return
    state = runs.start(project, models)
    while state.waiting:
        print(f"approving {runs.approve(project)}")
        state = runs.resume(project, models)
    if state.status != "completed":
        failed = next((s for s in state.stages if s.error), None)
        sys.exit(f"the run is {state.status}" + (f": {failed.name}: {failed.error}" if failed else ""))
    print(f"run: {state.status}; video: {project.current / 'video.mp4'}")
    print(
        f"see it: uv run hone-music-video dashboard --projects {args.projects}   (http://127.0.0.1:8794/#/p/{project.id})"
    )


if __name__ == "__main__":
    main()
