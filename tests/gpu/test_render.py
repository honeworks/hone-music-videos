"""Real models for the clips and their finishing (skipped): one shot with a face, its start frame a
picture as the Scenes view leaves it (0027: the scene's picture in use), its clip and its finishing, on
ComfyUI.

    scripts/gpu-lock.sh uv run pytest -m gpu tests/gpu/test_render.py -q

Needs the lock (`scripts/gpu-lock.sh`) and a ComfyUI that answers or `HONE_COMFYUI_START` (with
sageattention in ComfyUI's Python, D-033); media go to `$HONE_TEST_MEDIA_DIR` (default
`.hone/test-media`, git-ignored), not `/tmp`. About 6 minutes; hone-models frees the models at the end
of every session and stops a ComfyUI it started. The scenes' own pictures are Hone Frame's real-model
cases (the frame models wrap the same `Models`)."""

import json
import os
import subprocess
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import stages_make
from hone_music_video._jobs import Job
from hone_music_video.events import EventLog
from hone_music_video.testing import make_sheet, make_song

pytestmark = [pytest.mark.gpu, pytest.mark.comfyui]


def probe(clip: Path) -> dict[str, object]:
    command = ["ffprobe", "-v", "error", "-select_streams", "v", "-count_frames", "-show_entries",
               "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", str(clip)]  # fmt: skip
    found = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(found.stdout)["streams"][0]


def test_one_shot_with_a_face_clip_and_finish() -> None:
    if os.environ.get("HONE_GPU_LOCK_HELD") != "1":
        pytest.skip("run through scripts/gpu-lock.sh (the machine-wide GPU lock)")
    media = Path(os.environ.get("HONE_TEST_MEDIA_DIR", ".hone/test-media")).resolve()
    still = make_sheet(media / "start.png")  # a scene's picture in use, as `scenes_now` copies it
    project = hmv.create_project(media, "Real render", make_song(media / "song.wav", 3000))
    job = Job(project, hmv.HoneModels(), project.settings, EventLog(project.events_file), seed=1)
    frame = project.current / "shots" / "S001" / "still.png"
    frame.parent.mkdir(parents=True, exist_ok=True)
    frame.write_bytes(still.read_bytes())
    shot = {"id": "S001", "start_ms": 0, "end_ms": 3000, "lines": [], "beat": "b", "framing": "close-up",
            "faces": True, "cast": ["darvin"], "location": "a tent", "camera": "static camera",
            "still_prompt": "Cinematic close-up portrait of a bearded hero by firelight.",
            "motion_prompt": "Static camera. He breathes; the firelight flickers."}  # fmt: skip
    shots = hmv.Shots.model_validate({"shots": [shot]})
    stills = hmv.ShotFiles.model_validate(
        {"shots": [{"shot": "S001", "file": project.relative(frame), "key": "k"}]}
    )

    clips = stages_make.clips(job, shots, stills)
    finished = stages_make.finish(job, shots, clips)

    raw = probe(project.path(clips.shots[0].file))
    assert (raw["width"], raw["height"], raw["r_frame_rate"]) == (960, 544, "16/1")  # faces: the larger size
    assert int(str(raw["nb_read_frames"])) == stages_make.clip_frames(3000)
    final = probe(project.path(finished.shots[0].file))
    assert (final["width"], final["height"], final["r_frame_rate"]) == (1920, 1080, "32/1")
