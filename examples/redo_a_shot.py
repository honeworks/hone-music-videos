"""Remake one shot's clip, then assemble again.

What: after a finished run, shot S002 gets a new clip seed and the remake makes only its clip and its
finished clip (the video is assembled again with it); then the video is cut again from the finished clips
without calling any model.

How: `hmv.redo_clips(project, ["S002"])` and `hmv.remake(project, models)` (0027 §7), then
`hmv.assemble(project, models)` (D-036); each is a fork of the run that makes only what changed. A scene's
picture is changed in the Scenes view (or `hone-music-video frame`), and the next remake makes that scene's
clip again. Every version stays on disk in `current/shots/<id>/versions/`.

Why: a five-minute video takes hours to make; one weak shot should cost minutes, and a video assembled
by an older version should be cut again without making anything.
"""

import tempfile
from pathlib import Path

import hone_music_video as hmv
from hone_music_video.testing import FakeModels, make_song, settle_scenes

with tempfile.TemporaryDirectory() as tmp:
    song = make_song(Path(tmp) / "song.wav", 12_000)
    project = hmv.create_project(Path(tmp) / "projects", "Redo", song)
    state = hmv.start(project, FakeModels())
    while state.waiting:
        if state.waiting == "review_scenes":
            settle_scenes(project, FakeModels())
        hmv.approve(project)
        state = hmv.resume(project, FakeModels())

    models = FakeModels()
    hmv.redo_clips(project, ["S002"])  # a new clip seed: the next remake makes its clip again
    hmv.remake(project, models)
    made = sorted({c.out.parents[1].name for c in models.calls_of("generate") if c.out})
    print("the remake made files for", made)  # ['S002']: a new clip and its finish, nothing else
    assert made == ["S002"]

    models = FakeModels()
    state = hmv.assemble(project, models)  # the video cut again from the finished clips
    print("assembled again:", state.status, "with", len(models.calls), "model calls")
    assert state.status == "completed"
    assert models.calls == []
