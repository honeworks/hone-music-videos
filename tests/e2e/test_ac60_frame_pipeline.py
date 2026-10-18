"""AC-60 to AC-65 (change 0027): the frame path is the scene pipeline. The plan is made in several calls
and written as the frame workspace's project file; stage 6 runs it as Hone Frame runs a project (the
demo first, holds, picks); `review_scenes` takes the scenes as they are; the clips follow; a changed
scene or motion prompt remakes only its clip, and the video is cut again."""

from __future__ import annotations

import math
import shutil
import threading
import tomllib
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import frame, frame_stages, pause, runs
from hone_music_video.frame import actions
from hone_music_video.frame_prompts import SCENES_PER_CALL
from hone_music_video.testing import Call, FakeModels, make_song
from hone_music_video.testing.frame_answers import KIND
from tests.conftest import LYRICS, drive, settle_scenes

pytestmark = pytest.mark.e2e
FFMPEG = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


@pytest.fixture
def project(tmp_path: Path) -> hmv.Project:
    """A project of a 40 s song: seven shots on fakes, S004 planned as different prompts, S005 as takes."""
    return hmv.create_project(
        tmp_path / "projects", "Walk", make_song(tmp_path / "song.wav", 40_000), hmv.Material(lyrics=LYRICS)
    )


def to_gate(project: hmv.Project, models: FakeModels, gate: str) -> hmv.RunState:
    state = hmv.start(project, models)
    while state.waiting != gate:
        assert state.waiting is not None, state
        if state.waiting == "review_scenes":
            settle_scenes(project, models)
        hmv.approve(project)
        state = hmv.resume(project, models)
    return state


def frame_project(project: hmv.Project) -> frame.Project:
    return frame_stages.frame_project(frame_stages.workspace(project, FakeModels()))


def pictures(models: FakeModels) -> list[Call]:
    return [c for c in models.calls_of("generate") if c.out is not None and "/frame/projects/" in str(c.out)]


def test_ac60_the_plan_is_written_as_the_frame_project_file(project: hmv.Project) -> None:
    models = FakeModels()
    to_gate(project, models, "review_plan")

    calls = [
        c.schema
        for c in models.calls_of("plan")
        if c.schema in ("Bible", "ShotList", "ItemPrompts", "ScenePrompts")
    ]
    shots = frame_stages.read_shots(project).shots
    assert calls[:2] == ["Bible", "ShotList"]
    assert calls.count("ItemPrompts") == 3 and calls.count("ScenePrompts") == math.ceil(
        len(shots) / SCENES_PER_CALL
    )
    fp = frame_project(project)
    data = tomllib.loads(fp.text())
    assert data["demo"]["hold"] is True and len(data["demo"]["prompts"]) == 3
    assert data["characters"]["singer"]["hero"]["hold"] is True
    assert data["scenes"]["S004"]["prompts"] and data["scenes"]["S005"]["count"] == 3  # prompts, count
    assert all(
        p.startswith(KIND) for s in data["scenes"].values() for p in s.get("prompts", [s.get("prompt")])
    )
    assert "storyboard" in data["sheets"] and "cast" in data["sheets"]
    state = fp.state()
    assert all(st.marked and st.status == "todo" for st in state.items.values())  # all marked at import
    assert [s.scene for s in shots] == [f"S{n:03d}" for n in range(1, len(shots) + 1)]
    report = runs.stage_outputs(project, "check_plan")["check_plan"]
    assert report.errors == []


def test_ac61_the_scenes_stage_runs_the_file_as_hone_frame_runs_it(project: hmv.Project) -> None:
    models = FakeModels()
    state = to_gate(project, models, "review_plan")
    hmv.approve(project)
    state = hmv.resume(project, models)

    assert state.waiting == "review_scenes"
    made = pictures(models)
    assert [c.out.parent.name for c in made if c.out] == ["demo.1", "demo.2", "demo.3"]  # the demo first
    fp = frame_project(project)
    assert fp.run().status == "waiting" and fp.run().item == "demo.3"  # its hold stops the run
    with pytest.raises(hmv.RunStateError, match="marked and not made yet"):
        hmv.approve(project)

    settle_scenes(project, models)
    spec, state_now = fp.spec(), fp.state()
    for call in pictures(models):
        item = spec.item(call.out.parent.name if call.out else "")
        version = next(v for v in state_now.items[item.id].versions if v.seed == call.seed)
        assert call.seed is not None
        assert call.prompt == version.prompt == item.prompt_for(call.seed - item.seed(fp.id))  # as written
        used = [fp.root / "items" / r / f"v{version.made_from[r]:03d}.png" for r in item.refs]
        assert call.inputs.get("references", []) == used  # the refs' pictures, in order
    s004 = state_now.items["S004"].versions
    assert [v.prompt for v in s004] == (spec.item("S004").prompts or [])[:1]  # the first prompt (0033)
    assert len(state_now.items["S005"].versions) == 3  # count = 3
    hmv.approve(project)
    scenes = runs.stage_outputs(project, "review_scenes")["review_scenes"]
    assert scenes.shots is not None and len(scenes.stills.shots) == len(scenes.shots.shots)


@FFMPEG
def test_ac62_an_unattended_project_makes_the_video(project: hmv.Project) -> None:
    hmv.set_approve_mode(project, "auto")
    models = FakeModels()
    state = drive(project, models)

    assert state.status == "completed"
    assert project.path("current/video.mp4").is_file()
    fp = frame_project(project)
    assert all(st.status in ("done", "provided") for st in fp.state().items.values())
    still = project.current / "shots" / "S001" / "still.png"
    picture = fp.current_image(fp.state(), "S001")
    assert picture is not None and still.read_bytes() == picture.read_bytes()


def clip_calls(models: FakeModels) -> list[Call]:
    return [c for c in models.calls_of("generate") if c.out is not None and c.out.suffix == ".mp4"]


@FFMPEG
def test_ac63_a_changed_scene_remakes_only_its_clip(project: hmv.Project) -> None:
    models = FakeModels()
    drive(project, models)
    before = len(clip_calls(models))
    fp = frame_project(project)
    takes = [c for c in clip_calls(models) if c.out and c.out.parent.parent.name == "S005"]
    assert len(takes) == 2  # of its three takes only the one in use has a clip and a finished clip (0031)

    def used() -> str:
        found = runs.stage_outputs(project, "finish")["finish"]
        assert found is not None
        return next(f.file for f in found.shots if f.shot == "S005")

    before_pick = used()
    actions.use_version(fp, "S005", 2)  # another of its three takes: it has no clip yet

    state = hmv.remake(project, models)
    assert state.status == "completed"
    made = clip_calls(models)[before:]
    assert [c.out.parent.parent.name for c in made if c.out] == ["S005", "S005"]  # its clip and finish
    assert used() != before_pick and project.path("current/video.mp4").is_file()  # the cut uses the take
    actions.use_version(fp, "S005", 1)  # back to the first take: its clip was made already
    before = len(clip_calls(models))
    hmv.remake(project, models)
    assert clip_calls(models)[before:] == [] and used() == before_pick  # only the cut is made again
    s005 = project.current / "shots" / "S005"
    assert (s005 / "still.png").read_bytes() == fp.current_image(fp.state(), "S005").read_bytes()  # type: ignore[union-attr]

    hmv.set_motion(project, "S002", "Static camera. Her hair moves; the street stays still.")
    before = len(clip_calls(models))
    hmv.remake(project, models)
    remade = clip_calls(models)[before:]
    assert {c.out.parent.parent.name for c in remade if c.out} == {"S002"}
    assert remade[0].prompt == "Static camera. Her hair moves; the street stays still."

    hmv.redo_clips(project, ["S001"])
    before = len(clip_calls(models))
    hmv.remake(project, models)
    assert {c.out.parent.parent.name for c in clip_calls(models)[before:] if c.out} == {"S001"}
    versions = list((project.current / "shots" / "S005" / "versions").glob("clips-*.mp4"))
    assert len(versions) == 2  # every version kept: one raw clip per take that was used


def test_ac64_pause_in_the_scenes_stage_cancels_the_picture(
    project: hmv.Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    started, release = threading.Event(), threading.Event()
    interrupts: list[int] = []

    def interrupt() -> None:  # the second interrupt is the frame run's cancel of the picture
        interrupts.append(1)
        if len(interrupts) > 1:
            release.set()

    monkeypatch.setattr(pause, "interrupt", interrupt)

    def slow(call: Call) -> None:
        if call.kind == "generate" and call.out is not None and "demo.2" in str(call.out):
            started.set()
            release.wait(10)

    models = FakeModels(on_call=slow)
    to_gate(project, models, "review_plan")
    hmv.approve(project)

    def stop() -> None:
        started.wait(10)
        pause.request(project, now=True)

    threading.Thread(target=stop).start()
    state = hmv.resume(project, models)
    assert state.status == "paused"
    fp = frame_project(project)
    assert fp.run().status == "stopped"
    assert fp.state().items["demo.2"].marked and fp.state().items["demo.2"].versions == []  # nothing kept
    pause.clear(project)
    state = hmv.resume(project, FakeModels())
    assert state.waiting == "review_scenes" and fp.state().items["demo.2"].versions  # made on resume


def test_ac65_an_edit_of_the_file_is_checked_and_kept_with_its_comments(project: hmv.Project) -> None:
    models = FakeModels()
    to_gate(project, models, "review_plan")
    fp = frame_project(project)
    text = fp.text()
    assert "# used by" in text
    actions.edit(fp, "singer.hero", {"prompt": "A woman in a green coat, full figure."})
    assert "# used by" in fp.text() and 'prompt = "A woman in a green coat, full figure."' in fp.text()
    with pytest.raises(frame.errors.InvalidRequest, match="unknown model"):
        actions.edit(fp, "singer.hero", {"model": "no-such-model"})
    with pytest.raises(frame.errors.InvalidRequest, match="not above it"):
        actions.edit(fp, "singer.hero", {"refs": ["S001"]})


def test_ac63_with_take_clips_all_every_take_gets_its_clip(tmp_path: Path) -> None:
    """`take_clips: "all"` (0028 §5): every take of a scene gets its clip and finished clip overnight, so
    picking another take later makes no clip, only the cut."""
    song = make_song(tmp_path / "song.wav", 40_000)
    project = hmv.create_project(
        tmp_path / "projects", "Walk", song, hmv.Material(lyrics=LYRICS), {"take_clips": "all"}
    )
    models = FakeModels()
    drive(project, models)
    takes = [c for c in clip_calls(models) if c.out and c.out.parent.parent.name == "S005"]
    assert len(takes) == 6  # its three takes each made a clip and a finished clip
    actions.use_version(frame_project(project), "S005", 2)
    before = len(clip_calls(models))
    assert hmv.remake(project, models).status == "completed" and clip_calls(models)[before:] == []
