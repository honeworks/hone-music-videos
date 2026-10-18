"""AC-54 and AC-55: a blank picture of the frame run or a blank clip is refused and not kept; a dark
picture is (0025 §4, D-158, 0027)."""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

import hone_music_video as hmv
from hone_music_video import frame_stages
from hone_music_video._blank import blank_picture
from hone_music_video.ports import Generated
from hone_music_video.testing import FakeModels
from hone_music_video.testing.media import make_clip, png_bytes
from tests.conftest import drive, new_project

pytestmark = pytest.mark.e2e


class Blank(FakeModels):
    """Writes a one-colour file when `when` says so, after the usual fake output."""

    def __init__(self, when: Callable[[str, Path], bool]) -> None:
        super().__init__()
        self.when = when

    def generate(
        self, model_id: str, prompt: str, *, out: Path, seed: int, inputs: Mapping[str, Any]
    ) -> Generated:
        made = super().generate(model_id, prompt, out=out, seed=seed, inputs=inputs)
        if self.when(model_id, out):
            if out.suffix == ".mp4":
                make_clip(out, 17, 16, (0, 0, 0))
            else:
                out.write_bytes(png_bytes(32, 18, (0, 0, 0)))
        return made


def _failed(state: hmv.RunState) -> str:
    assert state.status == "failed"
    (failed,) = [s for s in state.stages if s.status == "failed" and s.error]
    assert failed.error is not None
    return failed.error


def test_ac54_a_blank_frame_picture_is_refused_and_not_kept(tmp_path: Path) -> None:
    project = new_project(tmp_path)
    frame_model = project.settings.models.frame[0]
    models = Blank(lambda model, out: model == frame_model and "demo.2" in str(out))
    assert "returned a blank picture" in _failed(drive(project, models))
    fp = frame_stages.frame_project(frame_stages.workspace(project, models))
    item = fp.state().items["demo.2"]
    assert item.status == "failed" and item.versions == [] and item.marked  # not kept, made again on Run


def test_ac55_a_blank_clip_is_refused(tmp_path: Path) -> None:
    project = new_project(tmp_path)
    clips = project.settings.models.clips
    models = Blank(lambda model, out: model == clips and out.suffix == ".mp4")
    assert "returned a blank clip" in _failed(drive(project, models))


def test_ac55_a_dark_picture_is_kept(tmp_path: Path) -> None:
    night = tmp_path / "night.png"
    picture = Image.new("RGB", (640, 360))
    for x in range(640):
        level = round(30 * x / 639)
        for y in range(360):
            picture.putpixel((x, y), (level, level, level))
    picture.save(night)
    assert blank_picture(night) is False
    black = tmp_path / "black.png"
    Image.new("RGB", (64, 36), (0, 0, 0)).save(black)
    assert blank_picture(black) is True
    almost = tmp_path / "almost.png"
    Image.new("RGB", (64, 36), (0, 0, 1)).save(almost)
    assert blank_picture(almost) is True
    marked = Image.new("RGB", (640, 360), (0, 0, 0))
    for x in range(40):
        for y in range(40):
            marked.putpixel((x, y), (255, 255, 255))
    spot = tmp_path / "spot.png"
    marked.save(spot)
    assert blank_picture(spot) is False
