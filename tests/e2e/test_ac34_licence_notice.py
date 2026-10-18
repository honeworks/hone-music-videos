"""AC-34 (0021 §4, 0027): `new` and the New video form list the frame's image models whose licence
forbids commercial use, as a notice that never blocks; an image model the registry does not know is
refused before anything is made. Public API, the CLI and the dashboard's estimate."""

from pathlib import Path

import pytest

from hone_music_video import cli, list_projects
from hone_music_video._dashboard_api import estimate
from hone_music_video.testing import FakeModels, make_song

pytestmark = pytest.mark.e2e
NOTICE = "notice: qwen-image-2.1-turbo is under Qwen research license: not for commercial use"


def test_ac34_new_and_the_new_video_form_list_the_models_that_forbid_commercial_use(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    song = make_song(tmp_path / "song.wav", 4000)
    projects = str(tmp_path / "projects")
    assert cli.main(["new", "Isolde", "--song", str(song), "--projects", projects, "--fake-models"]) == 0
    said = capsys.readouterr()
    assert said.err.splitlines()[0] == NOTICE and said.out.strip().endswith("isolde")
    assert estimate({"settings": {}}, FakeModels())["not_commercial"] == [NOTICE]
    other = {"models": {"frame": ["z-image-turbo"]}}
    assert estimate({"settings": other}, FakeModels())["not_commercial"] == []


def test_an_unknown_image_model_is_refused_before_the_project_is_made(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    song = make_song(tmp_path / "song.wav", 4000)
    settings = tmp_path / "settings.json"
    settings.write_text('{"models": {"frame": ["no-such-model"]}}')
    args = ["new", "X", "--song", str(song), "--projects", str(tmp_path / "p"), "--settings", str(settings)]
    assert cli.main([*args, "--fake-models"]) == 1
    assert "no-such-model" in capsys.readouterr().err
    assert list_projects(tmp_path / "p") == []
