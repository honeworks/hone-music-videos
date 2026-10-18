"""AC-13: settings are validated (unknown keys rejected) and never appear as words the owner had to write
into a prompt: the planners get them as data (design §2.3, §7.1, §14)."""

import json
import urllib.error
import urllib.request
from base64 import b64encode
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import frame_stages
from hone_music_video.cli import main
from hone_music_video.testing import FakeModels, make_song
from tests.conftest import drive

pytestmark = pytest.mark.e2e
UNKNOWN = [{"colour": "red"}, {"models": {"singer": "x"}}, {"fps": 32, "frame_rate": 24}]
OWN = {
    "style": "hand-drawn ink, muted colours",
    "aspect_ratio": "9:16",
    "min_shot_ms": 3000,
    "max_shot_ms": 6000,
    "language": "en",
}
STORY = "A queen waits on a balcony for a hero who does not come."


@pytest.mark.parametrize("settings", UNKNOWN)
def test_unknown_settings_are_refused_by_the_api(tmp_path: Path, settings: dict[str, object]) -> None:
    song = make_song(tmp_path / "song.wav", 3000)
    with pytest.raises(hmv.InvalidInput) as caught:
        hmv.create_project(tmp_path / "projects", "x", song, settings=settings)
    assert "Extra inputs are not permitted" in str(caught.value)
    assert not (tmp_path / "projects").exists()


def test_unknown_settings_are_refused_by_the_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    song = make_song(tmp_path / "song.wav", 3000)
    file = tmp_path / "settings.json"
    file.write_text(json.dumps({"colour": "red"}))
    args = ["new", "x", "--song", str(song), "--projects", str(tmp_path / "p"), "--settings", str(file)]
    assert main(args) == 1
    assert "colour: Extra inputs are not permitted" in capsys.readouterr().err
    assert hmv.list_projects(tmp_path / "p") == []


def test_unknown_settings_are_refused_by_the_dashboard(tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 3000)
    dashboard = hmv.Dashboard(tmp_path / "projects", FakeModels(), port=0).start()
    body = {
        "name": "x",
        "settings": {"colour": "red"},
        "song": {"name": "song.wav", "data_b64": b64encode(song.read_bytes()).decode()},
    }
    request = urllib.request.Request(  # noqa: S310 - our own server on 127.0.0.1
        dashboard.url + "api/projects",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=10)  # noqa: S310
        assert caught.value.code == 400
        assert json.loads(caught.value.read())["problems"] == ["colour: Extra inputs are not permitted"]
    finally:
        dashboard.close()
    assert hmv.list_projects(tmp_path / "projects") == []


# The settings, as words an owner might have had to write: none may appear in a prompt's text.
AS_WORDS = ("hand-drawn ink", "muted colours", "9:16", "3000", "6000", "3 s", "6 s", "3 seconds", "6 seconds")


def test_the_planners_get_the_settings_as_data(tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 20_000)
    project = hmv.create_project(tmp_path / "projects", "Ink", song, hmv.Material(story=STORY), OWN)
    models = FakeModels()
    assert drive(project, models).status == "completed"

    calls = models.calls_of("plan")
    lyrics, bible, shot_list = calls[0], calls[1], calls[2]
    assert (bible.schema, shot_list.schema) == ("Bible", "ShotList")
    expected = hmv.Settings.model_validate(OWN)
    assert bible.data["settings"] == {"style": OWN["style"], "mood": "", "aspect_ratio": "9:16"}
    assert shot_list.data["settings"] == expected.for_planner()  # as data, all of them
    assert bible.data["story"] == STORY  # the owner's words, unchanged: no settings written into them
    for call in calls:
        for words in AS_WORDS:
            assert words not in call.prompt, f"{words!r} is in the {call.schema} planner's prompt"
    assert lyrics.data["language"] == "en"
    assert models.calls_of("transcribe")[0].data == {"language": "en"}

    shots = frame_stages.read_shots(project).shots
    assert all(3000 <= s.end_ms - s.start_ms <= 6000 for s in shots)  # the limits were used
