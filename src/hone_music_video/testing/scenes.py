"""`settle_scenes`: at `review_scenes`, what the owner does in the Scenes view, for tests, examples and
demos (0027): accept each held item, pick each item's first picture, and run what is marked, until
nothing waits and nothing is marked."""

from __future__ import annotations

from hone_music_video import frame, frame_stages
from hone_music_video.frame import actions
from hone_music_video.ports import Models
from hone_music_video.project import Project

ROUNDS = 100


def settle_scenes(project: Project, models: Models) -> None:
    ws = frame_stages.workspace(project, models)
    fp = frame_stages.frame_project(ws)
    runner = frame.Runner(ws)
    for _ in range(ROUNDS):
        waiting = [(i, st) for i, st in fp.state().items.items() if st.status == "waiting"]
        for item, st in waiting:
            actions.accept(fp, item, st.candidates[0] if len(st.candidates) > 1 else None)
        if fp.marked():
            runner.run(fp.id)
            runner.drain()
        elif not waiting:
            return
    raise RuntimeError("the scenes did not settle")
