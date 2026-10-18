"""The stage functions on their own: measuring, frames, per-shot work kept across reruns (D-005, D-009)."""

import shutil
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import records, stages_make, stages_plan
from hone_music_video._jobs import Job
from hone_music_video.events import EventLog
from hone_music_video.frame_calls import system
from hone_music_video.settings import AspectRatio
from hone_music_video.testing import FakeModels, make_picture, make_song
from tests.conftest import new_project

FFMPEG = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


@pytest.fixture
def project(tmp_path: Path) -> hmv.Project:
    return new_project(tmp_path)


def job(project: hmv.Project, models: FakeModels) -> Job:
    return Job(project, models, project.settings, EventLog(project.events_file), seed=5)


def test_measure_uses_ffprobe(tmp_path: Path) -> None:
    song = stages_plan.measure(make_song(tmp_path / "s.wav", 12_345, sample_rate=8000))
    assert (song.duration_ms, song.sample_rate, song.channels) == (12_345, 8000, 1)


def test_measure_says_what_to_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(hmv.ToolMissing, match="install ffmpeg"):
        stages_plan.measure(make_song(tmp_path / "s.wav", 1000))


@pytest.mark.parametrize(("ms", "frame"), [(0, 0), (15, 0), (16, 1), (31, 1), (1000, 32), (212_050, 6786)])
def test_frames_come_from_absolute_times(ms: int, frame: int) -> None:
    assert stages_make.frame_at(ms, 32) == frame
    assert abs(frame * 1000 / 32 - ms) <= 1000 / 64  # within half a frame (design §5.3)


@pytest.mark.parametrize(
    ("ms", "frames"), [(500, 33), (2000, 33), (2001, 34), (6210, 101), (8000, 129), (9000, 129)]
)
def test_clip_frames(ms: int, frames: int) -> None:
    assert stages_make.clip_frames(ms) == frames


def shots(*spans: tuple[int, int]) -> hmv.Shots:
    common = {"lines": [], "beat": "b", "framing": "wide", "faces": False, "cast": [], "location": "l"}
    return hmv.Shots.model_validate(
        {
            "shots": [
                common
                | {"id": f"S{n:03d}", "start_ms": a, "end_ms": b, "camera": "c", "still_prompt": f"p{n}"}
                | {"motion_prompt": "m"}
                for n, (a, b) in enumerate(spans, 1)
            ]
        }
    )


def stills(project: hmv.Project, plan: hmv.Shots) -> hmv.ShotFiles:
    """A start frame per shot, as the scenes give them (0027)."""
    rows = []
    for shot in plan.shots:
        picture = make_picture(project.current / "shots" / shot.id / "versions" / "stills-x.png")
        rows.append(records.ShotFile(shot=shot.id, file=project.relative(picture), key="x"))
    return hmv.ShotFiles(shots=rows)


@FFMPEG
def test_finished_shots_are_kept_and_one_session_per_stage(project: hmv.Project) -> None:
    plan = shots((0, 4000), (4000, 8000), (8000, 12000))
    frames, first = stills(project, plan), FakeModels()
    made = stages_make.clips(job(project, first), plan, frames)
    assert [c.kind for c in first.calls] == ["session", "generate", "generate", "generate"]
    s2 = project.current / "shots" / "S002"
    version = project.path(made.shots[1].file)
    assert version.parent == s2 / "versions" and version.name.startswith("clips-")
    assert (s2 / "clip-raw.mp4").read_bytes() == version.read_bytes()  # the chosen copy

    version.with_suffix(".json").unlink()  # as if killed before S002's record was written
    again = FakeModels()
    remade = stages_make.clips(job(project, again), plan, frames)
    assert [c.out.parent.parent.name for c in again.calls_of("generate") if c.out] == ["S002"]
    assert remade == made

    third = FakeModels()
    stages_make.clips(job(project, third), plan, frames)
    assert third.calls == []  # nothing to make: no model is even loaded


@FFMPEG
def test_every_version_is_kept_with_what_made_it(project: hmv.Project) -> None:
    frames = stills(project, shots((0, 4000)))
    first = stages_make.clips(job(project, FakeModels()), shots((0, 4000)), frames)
    edited = shots((0, 4000))
    edited.shots[0].motion_prompt = "Static camera. The veil lifts."
    models = FakeModels()
    second = stages_make.clips(job(project, models), edited, frames)
    assert [c.prompt for c in models.calls_of("generate")] == ["Static camera. The veil lifts."]
    old, new = project.path(first.shots[0].file), project.path(second.shots[0].file)
    assert old != new and old.is_file() and new.is_file()  # never overwritten (design §11.2)
    record = hmv.Made.model_validate_json(new.with_suffix(".json").read_bytes())
    assert (record.stage, record.subject, record.prompt, record.model) == (
        "clips", "S001", "Static camera. The veil lifts.", project.settings.models.clips,
    )  # fmt: skip
    assert record.settings == project.settings.model_dump(mode="json")
    seeded = shots((0, 4000))
    seeded.shots[0].clip_seed = 1  # a redo of the clip (0027 §7): a new seed, a new version
    third = FakeModels()
    stages_make.clips(job(project, third), seeded, frames)
    assert len(third.calls_of("generate")) == 1


def test_sizes_follow_the_aspect_ratio(project: hmv.Project) -> None:
    ratios: list[tuple[AspectRatio, str, str, str, str]] = [
        ("16:9", "1024x576", "832x480", "960x544", "1920x1080"),
        ("9:16", "576x1024", "480x832", "544x960", "1080x1920"),
        ("1:1", "768x768", "624x624", "720x720", "1080x1080"),
        ("4:5", "704x880", "576x720", "640x800", "1080x1350"),
    ]
    for ratio, _still, clip, faces, out in ratios:
        settings = hmv.Settings(aspect_ratio=ratio)
        sizes = (
            stages_make.clip_size(settings, faces=False, frames=33),
            stages_make.clip_size(settings, faces=True, frames=33),
        )
        assert sizes == (clip, faces)
        assert stages_make.output_size(settings) == out
    assert stages_make.output_size(hmv.Settings(resolution=720)) == "1280x720"


def test_a_long_face_clip_is_made_at_the_smaller_size() -> None:
    """D-082: a face clip longer than 110 frames does not fit the 8 GB card at the larger size, so it is
    made at the clip size; at 110 frames (6760 ms, the longest that worked) it keeps the larger size."""
    for settings, small, large in [
        (hmv.Settings(aspect_ratio="16:9"), "832x480", "960x544"),
        (hmv.Settings(aspect_ratio="9:16"), "480x832", "544x960"),
    ]:
        sizes = [
            stages_make.clip_size(settings, faces=True, frames=stages_make.clip_frames(ms))
            for ms in (6760, 6820, 7786)
        ]
        assert sizes == [large, small, small], (
            settings.aspect_ratio
        )  # 7786 ms: S003 of the real run, which ran out of memory


@pytest.mark.parametrize("bad", ["../escape", "a/b", "", "-x", "S 1"])
def test_a_shot_id_that_is_not_a_folder_name_is_refused(project: hmv.Project, bad: str) -> None:
    """Defence in depth: a shot id names a folder under `current/shots/` (D-031)."""
    plan = shots((0, 4000))
    frames = stills(project, plan)
    plan.shots[0].id = bad
    frames.shots[0].shot = bad
    with pytest.raises(hmv.InvalidInput, match="is not letters, digits and dashes"):
        stages_make.clips(job(project, FakeModels()), plan, frames)
    assert not (project.root / "escape").exists()


def test_a_file_that_is_not_a_song_is_named(tmp_path: Path) -> None:
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"not audio")
    with pytest.raises(hmv.InvalidInput, match=r"bad\.wav is not a song ffprobe can read"):
        stages_plan.measure(bad)
    silent_picture = make_picture(tmp_path / "picture.png")
    with pytest.raises(hmv.InvalidInput, match=r"picture\.png is not a song"):
        stages_plan.measure(silent_picture)


@FFMPEG
def test_progress_is_logged_per_version(project: hmv.Project) -> None:
    """Each shot is one unit of the clips stage: `units`, then a started and a made event per clip, with
    its file and measured time (0003, D-050)."""
    plan = shots((0, 3000), (3000, 6000))
    stages_make.clips(job(project, FakeModels()), plan, stills(project, plan))
    events, _ = EventLog(project.events_file).read()
    assert next(e for e in events if e["event"] == "units") | {"at": ""} == {
        "event": "units", "at": "", "stage": "clips", "totals": {"raw_clip": 2}, "made": {"raw_clip": 0},
    }  # fmt: skip
    started = [(e["shot"], e["kind"], e["n"], e["total"]) for e in events if e["event"] == "version_started"]
    assert started == [("S001", "raw_clip", 1, 2), ("S002", "raw_clip", 2, 2)]
    made = [e for e in events if e["event"] == "version_made"]
    assert [(e["shot"], e["done"], e["first"]) for e in made] == [("S001", 1, True), ("S002", 2, False)]
    assert all(e["file"].startswith(f"current/shots/{e['shot']}/versions/clips-") for e in made)


def test_system_prompts_carry_the_model_limits() -> None:
    shots_prompt = system("frame_shots", limits=True)
    assert "Faces must be large" in shots_prompt and "Tile the whole song" in shots_prompt
    assert "No text, letters or signs" not in shots_prompt  # the still image's rules are the guide's
    scenes = system("frame_scenes", guides=("scenes", "models"), limits=True)
    assert "### Scenes" in scenes and "never name the mouth" in scenes
    assert "Keep every time from a heard word" in stages_plan.system_prompt("lyrics")
