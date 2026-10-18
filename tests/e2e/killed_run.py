"""Run a project on fake models and SIGKILL this process during one stage (guarantee 11's crash).

    python killed_run.py PROJECT STAGE CALLS_LOG [start|second-call|call-N|first-cut]

`start` (the default) dies as the stage starts; `second-call` (`call-2`) or `call-N` dies during the
stage's second or Nth generate
call (a stage that makes several files: sheets, stills, clips, finish); `first-cut` dies as soon as the
assembly has begun writing its first cut (its work folder `.assemble-*` in the project). Every model call
is logged to CALLS_LOG (one JSON line each) before it can be killed. Public API only."""

import json
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any

import hone_music_video as hmv
from hone_music_video.testing import Call, FakeModels, settle_scenes

project = hmv.open_project(sys.argv[1])
stage, log = sys.argv[2], Path(sys.argv[3])
mode = sys.argv[4] if len(sys.argv) > 4 else "start"
running = {"step": "", "calls": 0}
dies_at = 2 if mode == "second-call" else int(mode[5:]) if mode.startswith("call-") else 0


def die() -> None:
    os.kill(os.getpid(), signal.SIGKILL)


def on_call(call: Call) -> None:
    with log.open("a") as handle:
        handle.write(json.dumps({"kind": call.kind, "model": call.model, "prompt": call.prompt}) + "\n")
    if dies_at and call.kind == "generate" and running["step"] == stage:
        running["calls"] += 1
        if running["calls"] == dies_at:
            die()


def die_at_the_first_cut() -> None:
    while not any(project.root.glob(".assemble-*/*.mp4")):
        threading.Event().wait(0.001)
    die()


def on_event(event: dict[str, Any]) -> None:
    if event["event"] == "step_started":
        running["step"] = event["step"]
        if event["step"] == stage and mode == "start":
            die()
        if event["step"] == stage and mode == "first-cut":
            threading.Thread(target=die_at_the_first_cut, daemon=True).start()


models = FakeModels(on_call=on_call)
state = hmv.start(project, models, on_event=on_event)
while state.waiting:
    if state.waiting == "review_scenes":
        running["step"] = "settle"
        settle_scenes(project, models)
    hmv.approve(project)
    state = hmv.resume(project, models, on_event=on_event)
sys.exit(f"the run ended ({state.status}) without reaching {stage}")
