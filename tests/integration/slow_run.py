"""Run a project to the end on fake models, pausing inside the stills stage (a run that is busy).

    python slow_run.py PROJECT MARKER

At the first start frame it writes MARKER, then waits until MARKER is deleted. Public API only."""

import sys
import time
from pathlib import Path

import hone_music_video as hmv
from hone_music_video.testing import Call, FakeModels, settle_scenes

project, marker = hmv.open_project(sys.argv[1]), Path(sys.argv[2])
state_of = {"paused": False}


def on_call(call: Call) -> None:
    if call.kind == "generate" and "shots" in call.out.parts and not state_of["paused"]:  # pyright: ignore[reportOptionalMemberAccess]
        state_of["paused"] = True
        marker.write_text("in stills")
        while marker.exists():
            time.sleep(0.02)


models = FakeModels(on_call=on_call)
state = hmv.start(project, models)
while state.waiting:
    if state.waiting == "review_scenes":
        settle_scenes(project, models)
    hmv.approve(project)
    state = hmv.resume(project, models)
sys.exit(0 if state.status == "completed" else f"the run ended {state.status}")
