"""Quickstart: a song in, a music video out, on fake models.

What: makes a project from a 12-second silent song with lyrics, runs every stage, approves each of the
owner's gates, and finds `current/video.mp4`: every finished clip cut to its shot's frames under the song.
At `review_scenes`, `settle_scenes` does what the owner does in the Scenes view (Hone Frame's workspace,
0027): it accepts each held picture, picks the first of several, and runs what is marked.

How: `hmv.create_project`, `hmv.start`, `hmv.approve`, `hmv.resume`; `FakeModels` stands in for every
model (no network, no GPU), and its clips are small real videos, so the assembly is the real one (ffmpeg).

Why: the same calls drive a real run (`hmv.HoneModels()` instead of `FakeModels()`); this shows the flow
and the files it leaves without the hours a real one takes.
"""

import tempfile
from pathlib import Path

import hone_music_video as hmv
from hone_music_video.testing import FakeModels, make_song, settle_scenes

with tempfile.TemporaryDirectory() as tmp:
    song = make_song(Path(tmp) / "song.wav", 12_000)
    lyrics = "she waits upon the balcony\nthe wind is in her hair"
    project = hmv.create_project(Path(tmp) / "projects", "Balcony", song, hmv.Material(lyrics=lyrics))

    models = FakeModels()
    state = hmv.start(project, models)  # runs until the first gate: the timed lyrics
    while state.waiting:
        if state.waiting == "review_scenes":
            settle_scenes(project, models)  # the pictures, made and picked in the frame workspace
        print("approving", hmv.approve(project))  # review_lyrics, review_plan, review_scenes
        state = hmv.resume(project, models)

    edl = hmv.Assembly.model_validate_json((project.current / "edl.json").read_bytes())
    for cut in edl.edl:
        print(f"{cut.shot}: frames {cut.first_frame} to {cut.last_frame} of {edl.video}")
    assert state.status == "completed"
    assert (project.current / "video.mp4").stat().st_size > 0
    assert edl.edl[-1].last_frame + 1 == 12_000 * edl.fps // 1000  # the pictures last the song
