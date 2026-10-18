"""Stage 14 on its own (design §5.3, §12, D-035): each finished clip cut to its shot's frames from the
absolute times, the cuts joined under the song, the edit list; short clips, mismatched clips, the audio."""

import itertools
import json
import subprocess
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import _video, editor_files, stages_make
from hone_music_video._jobs import Job
from hone_music_video.events import EventLog
from hone_music_video.testing import FakeModels, make_clip

YAVG = ("-show_entries", "frame_tags=lavfi.signalstats.YAVG")
COLOURS = ((0, 0, 0), (255, 255, 255), (200, 30, 30))


def job(project: hmv.Project) -> Job:
    return Job(project, FakeModels(), project.settings, EventLog(project.events_file), seed=5)


SONG = hmv.Song(duration_ms=20_000, sample_rate=44_100, channels=1)  # the `measure` of the fixture's song


def assemble(made_by: Job, shots: hmv.Shots, finished: hmv.ShotFiles) -> hmv.Assembly:
    return stages_make.assemble(made_by, shots, finished, SONG)


def plan(*bounds: int) -> hmv.Shots:
    common = {"lines": [], "beat": "b", "framing": "wide", "faces": False, "cast": [], "location": "l"}
    prompts = {"camera": "c", "still_prompt": "p", "motion_prompt": "m"}
    return hmv.Shots.model_validate(
        {
            "shots": [
                common | prompts | {"id": f"S{n:03d}", "start_ms": a, "end_ms": b}
                for n, (a, b) in enumerate(itertools.pairwise(bounds), 1)
            ]
        }
    )


def clips(project: hmv.Project, shots: hmv.Shots, frames: list[int], **kw: object) -> hmv.ShotFiles:
    """A one-colour finished clip per shot (black, white, red...), `frames[n]` frames at 32 fps."""
    rows = []
    for n, (shot, count) in enumerate(zip(shots.shots, frames, strict=True)):
        path = project.current / "shots" / shot.id / "versions" / "finish-abc.mp4"
        make_clip(path, count, int(str(kw.get("fps", 32))), COLOURS[n % 3], str(kw.get("size", "64x36")))
        rows.append({"shot": shot.id, "file": project.relative(path), "key": "k"})
    return hmv.ShotFiles.model_validate({"shots": rows})


def probe(path: Path, entries: str, *args: str) -> dict[str, str]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-of", "json", *args, "-show_entries", entries, str(path)],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)["streams"][0]


def lumas(video: Path) -> list[float]:
    """Each frame's mean brightness (0 black, 255 white)."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-f", "lavfi", f"movie={video},signalstats", "-of", "json", *YAVG],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [float(f["tags"]["lavfi.signalstats.YAVG"]) for f in json.loads(out)["frames"]]


def test_each_clip_is_cut_to_its_frames_and_joined_in_order(project: hmv.Project) -> None:
    shots = plan(0, 1015, 2000, 3010)  # 1015 ms is frame 32.48 -> 32; 2000 -> 64; 3010 -> 96.32 -> 96
    assembly = assemble(job(project), shots, clips(project, shots, [40, 40, 40]))
    assert [(c.first_frame, c.last_frame, c.held_frames) for c in assembly.edl] == [
        (0, 31, 0),
        (32, 63, 0),
        (64, 95, 0),
    ]
    video = project.path(assembly.video or "")
    assert assembly.video == "current/video.mp4" and video.is_file()
    luma = lumas(video)
    assert len(luma) == 96
    assert all(y < 40 for y in luma[:32]) and all(y > 200 for y in luma[32:64])
    assert all(60 < y < 120 for y in luma[64:])  # red: each shot from the start of its own clip
    found = hmv.Assembly.model_validate_json((project.current / "edl.json").read_bytes())
    assert found == assembly and found.edl[1].clip == "current/shots/S002/versions/finish-abc.mp4"


def noisy(tmp_path: Path, name: str, *codec: str) -> hmv.Project:
    """A project whose 2 s song is noise (silence would encode to almost nothing at any bit rate)."""
    song = tmp_path / name
    source = ["-f", "lavfi", "-i", "anoisesrc=d=2:c=white:a=0.3", "-ar", "44100", "-ac", "2"]
    subprocess.run(["ffmpeg", "-v", "error", *source, *codec, str(song)], check=True)  # noqa: S607
    return hmv.create_project(tmp_path / "projects", name, song)


@pytest.mark.parametrize(
    ("name", "codec", "kbps"),  # a WAV becomes AAC asked at 320 kb/s (the encoder spends less on 2 s of
    # noise); an AAC song is copied as it is
    [("song.wav", (), (150, 330)), ("song.m4a", ("-c:a", "aac", "-b:a", "64k"), (50, 80))],
)
def test_the_video_is_h264_at_32_fps_over_the_song(
    tmp_path: Path, name: str, codec: tuple[str, ...], kbps: tuple[int, int]
) -> None:
    project = noisy(tmp_path, name, *codec)
    shots = plan(0, 1000, 2000)
    assembly = assemble(job(project), shots, clips(project, shots, [40, 40]))
    video = project.path(assembly.video or "")
    found = probe(video, "stream=codec_name,pix_fmt,r_frame_rate,nb_read_packets", "-count_packets")
    assert [found[k] for k in ("codec_name", "pix_fmt", "r_frame_rate", "nb_read_packets")] == [
        "h264",
        "yuv420p",
        "32/1",
        "64",
    ]
    audio = probe(video, "stream=codec_name,bit_rate", "-select_streams", "a")
    assert audio["codec_name"] == "aac" and kbps[0] < int(audio["bit_rate"]) / 1000 < kbps[1]


def test_a_short_clip_holds_its_last_frame_and_says_so(project: hmv.Project) -> None:
    shots = plan(0, 1000, 2000)
    assembly = assemble(job(project), shots, clips(project, shots, [20, 40]))
    assert [c.held_frames for c in assembly.edl] == [12, 0]
    luma = lumas(project.path(assembly.video or ""))
    assert len(luma) == 64 and all(y < 40 for y in luma[:32]) and all(y > 200 for y in luma[32:])
    events, _ = EventLog(project.events_file).read()
    assert [(e["shot"], e["held_frames"]) for e in events if e["event"] == "clip_short"] == [("S001", 12)]


@pytest.mark.parametrize(("size", "fps"), [("96x54", 32), ("64x36", 30)])
def test_clips_of_another_size_or_rate_are_refused(project: hmv.Project, size: str, fps: int) -> None:
    shots = plan(0, 1000, 2000)
    finished = clips(project, shots, [40, 40])
    make_clip(project.path(finished.shots[1].file), 40, fps, size=size)
    with pytest.raises(hmv.InvalidInput, match=rf"S002 is {size} at {fps}/1 fps.*redo the odd shots"):
        assemble(job(project), shots, finished)
    assert not (project.current / "video.mp4").exists()


@pytest.mark.parametrize(
    ("missing", "said"),
    [
        ({"ffmpeg"}, "ffmpeg is not installed"),
        ({"ffprobe"}, "ffprobe is not installed"),
        ({"ffmpeg", "ffprobe"}, "ffmpeg and ffprobe are not installed"),
    ],
)
def test_missing_tools_are_named(
    project: hmv.Project, monkeypatch: pytest.MonkeyPatch, missing: set[str], said: str
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None if name in missing else "/usr/bin/" + name)
    with pytest.raises(hmv.ToolMissing, match=f"^{said}; install ffmpeg"):
        assemble(job(project), plan(0, 1000), hmv.ShotFiles(shots=[]))
    assert said in (Path(__file__).parents[2] / "docs" / "troubleshooting.md").read_text()


def test_ffmpeg_failing_says_what_it_said(tmp_path: Path) -> None:
    with pytest.raises(hmv.MusicVideoError, match=r"(?s)ffmpeg failed: .*missing\.mp4"):
        _video.ffmpeg("-i", tmp_path / "missing.mp4", tmp_path / "out.mp4")


def test_a_shot_under_half_a_frame_gets_no_frames(project: hmv.Project) -> None:
    """1000 to 1010 ms is frames 32 to 32.32: no frame of its own; the video still lasts the song."""
    shots = plan(0, 1000, 1010, 2000)
    assembly = assemble(job(project), shots, clips(project, shots, [40, 40, 40]))
    assert [(c.first_frame, c.last_frame) for c in assembly.edl] == [(0, 31), (32, 31), (32, 63)]
    luma = lumas(project.path(assembly.video or ""))
    assert len(luma) == 64 and all(y < 40 for y in luma[:32]) and all(60 < y < 120 for y in luma[32:])


def ramp(path: Path, frames: int, timestamps: str = "N") -> Path:
    """A clip whose frame n has brightness 6n, at 32 fps; `timestamps` gives frame n's time in frames."""
    path.parent.mkdir(parents=True, exist_ok=True)
    look = f"geq=lum='N*6':cb=128:cr=128,setpts='({timestamps})/(32*TB)'"
    source = ["-f", "lavfi", "-i", "color=c=black:s=64x36:r=32", "-frames:v", str(frames), "-vf", look]
    x264 = ["-fps_mode", "passthrough", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]
    subprocess.run(["ffmpeg", "-v", "error", *source, *x264, str(path)], check=True)  # noqa: S607
    return path


def ramps(project: hmv.Project, shots: hmv.Shots, timestamps: str = "N") -> hmv.ShotFiles:
    rows = []
    for shot in shots.shots:
        path = ramp(project.current / "shots" / shot.id / "versions" / "finish-abc.mp4", 40, timestamps)
        rows.append({"shot": shot.id, "file": project.relative(path), "key": "k"})
    return hmv.ShotFiles.model_validate({"shots": rows})


def test_each_shot_shows_its_clip_from_the_clips_first_frame(project: hmv.Project) -> None:
    shots = plan(0, 1000, 1500, 2500)  # 32, 16 and 32 frames
    assembly = assemble(job(project), shots, ramps(project, shots))
    luma = lumas(project.path(assembly.video or ""))
    expected = [6 * n for n in range(32)] + [6 * n for n in range(16)] + [6 * n for n in range(32)]
    assert len(luma) == len(expected)
    assert all(abs(y - e) < 4 for y, e in zip(luma, expected, strict=True)), luma


def test_a_gap_in_a_clips_timestamps_takes_its_next_frames(project: hmv.Project) -> None:
    """A 32 fps clip whose frame 10 comes five frames late: the shot still shows frames 0, 1, 2... of
    the clip in order; asking ffmpeg for a rate (`-r`) would fill the gap with copies of frame 9."""
    shots = plan(0, 1000)
    assembly = assemble(job(project), shots, ramps(project, shots, "if(gte(N,10),N+5,N)"))
    luma = lumas(project.path(assembly.video or ""))
    assert len(luma) == 32
    assert all(abs(y - 6 * n) < 4 for n, y in enumerate(luma)), luma


def test_a_clip_ffmpeg_cannot_read_is_named(project: hmv.Project) -> None:
    shots = plan(0, 1000)
    bad = project.current / "shots" / "S001" / "clip.mp4"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b"not a video")
    finished = hmv.ShotFiles.model_validate(
        {"shots": [{"shot": "S001", "file": project.relative(bad), "key": "k"}]}
    )
    with pytest.raises(
        hmv.InvalidInput, match=r"S001's finished clip: clip\.mp4 is not a file ffprobe can read"
    ):
        assemble(job(project), shots, finished)


def test_a_clip_showing_fewer_frames_than_its_packets_is_cut_to_the_exact_length(
    project: hmv.Project,
) -> None:
    """An MP4 whose edit list hides its first second: 64 packets, 32 frames shown. The estimate says
    nothing is held, the cut still makes exactly the shot's frames (the last one held)."""
    shots = plan(0, 1500, 2500)  # 48 frames, then 32
    finished = clips(project, shots, [64, 40])
    whole = project.path(finished.shots[0].file)
    trimmed = whole.with_name("trimmed.mp4")
    hide = ["ffmpeg", "-v", "error", "-ss", "1", "-i", str(whole), "-c", "copy", str(trimmed)]
    subprocess.run(hide, check=True)
    trimmed.replace(whole)
    assembly = assemble(job(project), shots, finished)
    assert assembly.edl[0].held_frames == 0  # the packets' estimate
    luma = lumas(project.path(assembly.video or ""))
    assert len(luma) == 80 and all(y < 40 for y in luma[:48]) and all(y > 200 for y in luma[48:])


def test_the_editor_files_use_the_clips_measured_for_the_cut(
    project: hmv.Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-063: the assembly hands its measured clips and the run's song to the editor files: no second
    ffprobe of them."""

    def no_probe(path: Path) -> None:
        raise AssertionError(f"probed {path} again")

    monkeypatch.setattr(editor_files, "probe", no_probe)
    monkeypatch.setattr(editor_files, "measure", no_probe)
    shots = plan(0, 1000, 2000)
    assemble(job(project), shots, clips(project, shots, [40, 40]))
    assert "<samplerate>44100</samplerate>" in (project.current / "edit.xml").read_text()


def test_an_editor_file_failure_is_a_warning_not_a_failed_assembly(
    project: hmv.Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_: object) -> None:
        raise OSError("disk full (planted)")

    monkeypatch.setattr(editor_files, "write", broken)
    shots = plan(0, 1000, 2000)
    assembly = assemble(job(project), shots, clips(project, shots, [40, 40]))
    assert (project.current / "video.mp4").is_file() and len(assembly.edl) == 2
    found = [json.loads(line) for line in project.events_file.read_text().splitlines()]
    assert {"event": "editor_files_failed", "error": "OSError: disk full (planted)"}.items() <= found[
        -1
    ].items()
