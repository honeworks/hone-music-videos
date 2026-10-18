"""AC-10: the assembled video lasts `duration_ms` (±1 frame), and every cut is within half a frame of its
planned time (design §5.3, §12, §14).

A run on fake models to the end (its finished clips are small real videos, one colour per shot); then
ffprobe reads the video: its frames, its length, and where each frame's colour changes, which is where a
shot's clip gives way to the next. Public API and CLI only."""

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.cli import main
from hone_music_video.testing import FakeModels, make_song
from hone_music_video.testing.frame_answers import shots_answer
from tests.conftest import drive, settle_scenes

pytestmark = pytest.mark.e2e
FPS = 32
FRAME_MS = 1000 / FPS
STATS = "frame_tags=lavfi.signalstats.YAVG,lavfi.signalstats.UAVG,lavfi.signalstats.VAVG"


def ffprobe(*args: str | Path) -> Any:
    command = ["ffprobe", "-v", "error", "-of", "json", *map(str, args)]
    return json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)


def colours(video: Path) -> list[list[float]]:
    """Each frame's mean Y, U and V."""
    frames = ffprobe("-f", "lavfi", f"movie={video},signalstats", "-show_entries", STATS)["frames"]
    return [[float(v) for v in f["tags"].values()] for f in frames]


def differ(one: list[float], two: list[float]) -> bool:
    return max(abs(a - b) for a, b in zip(one, two, strict=True)) > 3


def cuts_in(video: Path) -> list[int]:
    """The frames where the picture changes colour: the first frame of every shot but the first."""
    found = colours(video)
    return [n for n in range(1, len(found)) if differ(found[n - 1], found[n])]


def check_clips_differ(project: hmv.Project, edl: list[dict[str, Any]]) -> None:
    """The fake's clips are one colour each, from the call: neighbours must differ for a cut to show."""
    first = [colours(project.path(c["clip"]))[0] for c in edl]
    for n in range(1, len(edl)):
        assert differ(first[n - 1], first[n]), f"{edl[n - 1]['shot']} and {edl[n]['shot']} have one colour"


def shots(project: hmv.Project) -> list[hmv.Shot]:
    return hmv.Shots.model_validate_json((project.current / "shots.json").read_bytes()).shots


def check_on_time(project: hmv.Project, song_ms: int) -> None:
    video = project.current / "video.mp4"
    found = ffprobe(
        "-select_streams", "v", "-count_packets", "-show_entries", "stream=nb_read_packets", video
    )
    frames = int(found["streams"][0]["nb_read_packets"])
    length_ms = float(ffprobe("-show_entries", "format=duration", video)["format"]["duration"]) * 1000
    assert abs(frames * FRAME_MS - song_ms) <= FRAME_MS / 2  # the pictures last the song, to half a frame
    assert abs(length_ms - song_ms) <= FRAME_MS  # the video (pictures and song) lasts duration_ms, ±1 frame
    edl = json.loads((project.current / "edl.json").read_text())["edl"]
    assert [c["held_frames"] for c in edl] == [0] * len(edl)  # no clip was short: none hides behind a hold
    assert '"clip_short"' not in project.events_file.read_text()
    check_clips_differ(project, edl)
    planned = [s.start_ms for s in shots(project)[1:]]
    cuts = cuts_in(video)
    assert len(cuts) == len(planned)  # one cut per shot boundary, none elsewhere
    for frame, ms in zip(cuts, planned, strict=True):
        assert abs(frame * FRAME_MS - ms) <= FRAME_MS / 2  # every cut within half a frame of its time


def test_the_video_lasts_the_song_and_cuts_on_time(project: hmv.Project) -> None:
    assert drive(project, FakeModels()).status == "completed"
    check_on_time(project, 20_000)
    edl = json.loads((project.current / "edl.json").read_text())
    assert edl["video"] == "current/video.mp4" and edl["fps"] == FPS
    assert [c["first_frame"] for c in edl["edl"][1:]] == cuts_in(project.current / "video.mp4")


def test_a_song_of_odd_length_cut_on_odd_times(tmp_path: Path) -> None:
    """A song that is not a whole number of frames (21 337 ms is 682.78 frames at 32 fps), from the CLI."""
    song = make_song(tmp_path / "odd.wav", 21_337)
    project = hmv.create_project(tmp_path / "projects", "Odd", song, settings={"min_shot_ms": 2500})
    assert main(["run", str(project.root), "--fake-models"]) == 0
    while waiting := hmv.status(project).waiting:
        if waiting == "review_scenes":
            settle_scenes(project, FakeModels())
        assert main(["approve", str(project.root)]) == 0
        assert main(["resume", str(project.root), "--fake-models"]) == 0
    assert hmv.status(project).status == "completed"
    assert any(s.start_ms * FPS % 1000 for s in shots(project)[1:])  # some cut falls between two frames
    check_on_time(project, 21_337)


def on_fraction(t: int, words: list[tuple[int, int]], above: bool) -> int:
    """The time nearest `t`, outside every sung word, whose frame position at 32 fps has a fraction just
    above .5 (rounded up) or just below (rounded down)."""
    for c in sorted(range(t - 300, t + 301), key=lambda c: abs(c - t)):
        fraction = c * FPS % 1000
        if (500 < fraction <= 560 if above else 440 <= fraction < 500) and not any(
            a < c < b for a, b in words
        ):
            return c
    raise AssertionError(f"no time near {t} ms")


def scripted(data: Mapping[str, Any]) -> dict[str, Any]:
    """The fake plan with its cuts moved onto frame fractions alternately above and below .5."""
    plan, timeline = shots_answer(data), data["timeline"]
    words = [(w[0], w[1]) for line in timeline["lines"] for w in line["words"]]
    cuts = plan["shots"]
    for n in range(1, len(cuts)):
        cuts[n - 1]["end_ms"] = cuts[n]["start_ms"] = on_fraction(cuts[n]["start_ms"], words, n % 2 == 0)
    for shot in cuts:
        overlaps = [
            ln
            for ln in timeline["lines"]
            if ln["start_ms"] < shot["end_ms"] and ln["end_ms"] > shot["start_ms"]
        ]
        shot["lines"] = [ln["id"] for ln in overlaps]
    return plan


def test_cuts_between_frames_round_to_the_nearest(tmp_path: Path) -> None:
    """Scripted cuts at frame fractions above and below .5 (30 s, five shots): each shot starts at the
    rounded frame of its own time; flooring, or adding rounded lengths, would land a frame off."""
    song = make_song(tmp_path / "song.wav", 30_000)
    project = hmv.create_project(tmp_path / "projects", "Fractions", song, settings={"max_shot_ms": 7000})
    assert drive(project, FakeModels(answers={"ShotList": scripted})).status == "completed"
    starts = [s.start_ms for s in shots(project)[1:]]
    fractions = [ms * FPS % 1000 for ms in starts]
    assert any(f > 500 for f in fractions) and any(f < 500 for f in fractions), fractions
    edl = json.loads((project.current / "edl.json").read_text())["edl"]
    assert [c["first_frame"] for c in edl[1:]] == [(ms * FPS + 500) // 1000 for ms in starts]
    check_on_time(project, 30_000)
