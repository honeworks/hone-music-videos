"""The project folder (design §4): inputs copied, `project.json`, ids, refusals."""

import json
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video.testing import make_picture
from tests.conftest import LYRICS


def test_a_project_holds_its_inputs(project: hmv.Project, song: Path, sheet: Path) -> None:
    root = project.root
    assert project.id == "balcony"
    assert (root / "input" / "song.wav").read_bytes() == song.read_bytes()
    assert (root / "input" / "lyrics.txt").read_text() == LYRICS + "\n"
    assert (root / "input" / "sheets" / "Darvin.png").read_bytes() == sheet.read_bytes()
    assert (root / "runs").is_dir() and (root / "current").is_dir()
    saved = json.loads((root / "project.json").read_text())
    assert saved["format_version"] == "1" and saved["name"] == "Balcony"
    assert saved["inputs"] == {
        "song": "input/song.wav",
        "lyrics": LYRICS,
        "story": "A queen waits for a hero who does not come.",
        "sheets": [{"name": "Darvin", "file": "input/sheets/Darvin.png", "note": "the hero, in armour"}],
        "poses": [],
    }
    assert saved["settings"] == hmv.Settings().model_dump(mode="json")
    assert hmv.open_project(root).record() == project.record()


def test_ids_are_unique_and_every_project_is_listed(tmp_path: Path, song: Path) -> None:
    first = hmv.create_project(tmp_path / "p", "Same Name!", song)
    second = hmv.create_project(tmp_path / "p", "Same Name!", song)
    assert (first.id, second.id) == ("same-name", "same-name-2")
    assert {p.id for p in hmv.list_projects(tmp_path / "p")} == {"same-name", "same-name-2"}
    assert hmv.list_projects(tmp_path / "nothing") == []
    assert first.record().inputs.lyrics is None


def test_every_problem_is_named_and_nothing_is_left_behind(tmp_path: Path) -> None:
    text = tmp_path / "notes.txt"
    text.write_text("not a song")
    pic = make_picture(tmp_path / "a.png")
    with pytest.raises(hmv.InvalidInput) as caught:
        hmv.create_project(
            tmp_path / "p",
            " ",
            text,
            hmv.Material(
                sheets=(hmv.GivenSheet("a/b", pic), hmv.GivenSheet("Twin", pic), hmv.GivenSheet("Twin", text))
            ),
        )
    problems = " | ".join(caught.value.problems)
    for expected in (
        "song: .txt is not one of",
        "'a/b' is not a usable name",
        "used twice",
        "needs a picture",
        "name:",
    ):
        assert expected in problems
    assert list((tmp_path / "p").iterdir()) == [] if (tmp_path / "p").exists() else True


def test_missing_song_and_bad_settings(tmp_path: Path, song: Path) -> None:
    with pytest.raises(hmv.InvalidInput, match="is not a file"):
        hmv.create_project(tmp_path / "p", "x", tmp_path / "gone.wav")
    with pytest.raises(hmv.InvalidInput, match="colour"):
        hmv.create_project(tmp_path / "p", "x", song, settings={"colour": "red"})


def test_open_project_needs_project_json(tmp_path: Path) -> None:
    with pytest.raises(hmv.NotFound, match="hone-music-video new"):
        hmv.open_project(tmp_path)
