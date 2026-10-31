"""AC-18: the project's options (pace, mood) and the story's world reach the frame planner's calls as data
(0009, D-084, D-085, 0027; design §2.3, §7, §14). Public API, CLI and dashboard API only."""

import json
import urllib.error
import urllib.request
from base64 import b64encode
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.cli import main
from hone_music_video.testing import FakeModels, make_song
from hone_music_video.testing.frame_answers import bible_answer
from tests.conftest import drive

pytestmark = pytest.mark.e2e
WORLD = bible_answer({})["world"]
MOOD = "dark, دلهره‌آور (dread)"


def by_schema(models: FakeModels) -> dict[str, dict[str, Any]]:
    """The data of each kind of planner call (the last of each)."""
    return {c.schema: c.data for c in models.calls_of("plan")}


def test_the_options_and_the_world_are_data_for_the_planners(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    song = make_song(tmp_path / "song.wav", 20_000)
    given = tmp_path / "settings.json"
    given.write_text(json.dumps({"pace": "energetic", "aspect_ratio": "1:1"}))
    args = ["new", "Dread", "--song", str(song), "--projects", str(tmp_path / "p"), "--settings", str(given)]
    assert main([*args, "--pace", "calm", "--mood", MOOD]) == 0  # the flags win
    project = hmv.open_project(capsys.readouterr().out.strip())
    settings = project.settings
    assert (settings.pace, settings.mood, settings.aspect_ratio) == ("calm", MOOD, "1:1")

    models = FakeModels()
    assert drive(project, models).status == "completed"
    data = by_schema(models)
    assert (data["Bible"]["settings"]["mood"], data["ShotList"]["settings"]["pace"]) == (MOOD, "calm")
    assert data["ShotList"]["pace_shot_ms"] == (6500, 8000)
    assert data["ShotList"]["bible"]["world"] == WORLD  # the bible's world, as data
    assert data["ScenePrompts"]["mood"] == MOOD and data["ScenePrompts"]["world"] == WORLD
    for call in models.calls_of("plan"):
        assert MOOD not in call.prompt  # the owner's words reach the planners as data only

    with pytest.raises(SystemExit):  # argparse names the paces
        main(["new", "Bad", "--song", str(song), "--projects", str(tmp_path / "p"), "--pace", "slow"])
    err = capsys.readouterr().err.replace("'", "")  # Python 3.12.8 and later quote the choices
    assert "choose from calm, balanced, energetic" in err
    assert [p.root for p in hmv.list_projects(tmp_path / "p")] == [project.root]  # none made


def post(url: str, body: dict[str, Any]) -> tuple[int, Any]:
    request = urllib.request.Request(  # noqa: S310 - our own server on 127.0.0.1
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:  # noqa: S310
            return reply.status, json.loads(reply.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


def test_the_dashboard_offers_the_options_stores_them_and_refuses_a_wrong_one(tmp_path: Path) -> None:
    song = {
        "name": "song.wav",
        "data_b64": b64encode(make_song(tmp_path / "s.wav", 2000).read_bytes()).decode(),
    }
    dashboard = hmv.Dashboard(tmp_path / "projects", FakeModels(), port=0).start()
    try:
        with urllib.request.urlopen(dashboard.url + "api/settings") as reply:  # noqa: S310 - our own server
            offered = json.loads(reply.read())
        assert offered["paces"] == ["calm", "balanced", "energetic"]
        assert (offered["defaults"]["pace"], offered["defaults"]["mood"]) == ("balanced", "")
        assert offered["defaults"]["models"]["frame"] == ["qwen-image-2.1-turbo"]
        assert "qwen-image-2.1-turbo" in [m["id"] for m in offered["image_models"]]
        status, refused = post(
            dashboard.url + "api/projects", {"name": "x", "song": song, "settings": {"pace": "slow"}}
        )
        assert status == 400 and "pace" in json.dumps(refused)
        options = {"pace": "calm", "mood": MOOD}
        status, made = post(
            dashboard.url + "api/projects", {"name": "Calm", "song": song, "settings": options}
        )
        assert status == 200
    finally:
        dashboard.close()
    stored = hmv.open_project(tmp_path / "projects" / made["id"]).settings
    assert (stored.pace, stored.mood) == ("calm", MOOD)
