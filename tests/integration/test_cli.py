"""The `hone-music-video` command: new, run, status, approve, resume on fake models; exit codes."""

import json
import subprocess
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video.cli import main
from hone_music_video.testing import make_picture, make_song


def test_help_runs_as_a_program() -> None:
    done = subprocess.run(["hone-music-video", "--help"], capture_output=True, text=True, check=True)  # noqa: S607
    for command in ("dashboard", "new", "run", "resume", "status", "approve", "frame", "remake", "export"):
        assert command in done.stdout


def settle(folder: str, capsys: pytest.CaptureFixture[str]) -> None:
    """At review_scenes, from the command line: accept what waits (a pick's first picture), run what is
    marked, until nothing waits and nothing is marked (0027)."""
    for _ in range(50):
        assert main(["frame", "status", folder, "--json", "--fake-models"]) == 0
        items = json.loads(capsys.readouterr().out)["items"]
        waiting = [i for i in items if i["status"] == "waiting"]
        for item in waiting:
            pick = [str(item["candidates"][0])] if len(item["candidates"]) > 1 else []
            assert main(["frame", "accept", folder, item["id"], *pick, "--fake-models"]) == 0
        if any(i["marked"] for i in items):
            assert main(["frame", "run", folder, "--fake-models"]) == 0
        elif not waiting:
            capsys.readouterr()
            return
        capsys.readouterr()
    raise AssertionError("the scenes did not settle")


def test_a_video_from_the_command_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    song = make_song(tmp_path / "song.wav", 12_000)
    sheet = make_picture(tmp_path / "darvin.png")
    lyrics = tmp_path / "lyrics.txt"
    lyrics.write_text("one two three four five six")
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"aspect_ratio": "1:1"}))
    new = [
        "new",
        "Night Ride",
        "--song",
        str(song),
        "--projects",
        str(tmp_path / "p"),
        "--lyrics",
        str(lyrics),
    ]
    new += ["--story", "a ride at night", "--sheet", f"Darvin={sheet}:the hero", "--settings", str(settings)]
    new += ["--pose", f"kneeling={sheet}", "--fake-models"]
    assert main(new) == 0
    out = capsys.readouterr()
    folder = out.out.strip()
    assert "not for commercial use" in out.err  # the frame model's licence, a notice (0021 §4)
    project = hmv.open_project(folder)
    assert project.settings.aspect_ratio == "1:1" and project.record().inputs.sheets[0].note == "the hero"
    assert project.record().inputs.poses[0].name == "kneeling"

    assert main(["run", folder, "--fake-models"]) == 0
    assert "waiting for review_lyrics" in capsys.readouterr().out
    for gate in ("review_lyrics", "review_plan"):
        assert main(["approve", folder]) == 0
        assert f"approved {gate}" in capsys.readouterr().out
        assert main(["resume", folder, "--fake-models"]) == 0
        capsys.readouterr()
    assert main(["check-shots", folder]) == 0
    capsys.readouterr()
    settle(folder, capsys)
    assert main(["approve", folder]) == 0
    assert "approved review_scenes" in capsys.readouterr().out
    assert main(["resume", folder, "--fake-models"]) == 0
    capsys.readouterr()
    assert main(["status", folder, "--json"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["status"] == "completed" and len(state["stages"]) == 10
    assert main(["status", folder]) == 0
    assert " 8 clips         done  2/2 shots" in capsys.readouterr().out

    assert main(["motion", folder, "S001", "Static camera. The rain falls; she stays still."]) == 0
    assert main(["remake", folder, "--fake-models"]) == 0
    assert "completed" in capsys.readouterr().out
    assert main(["redo", folder, "S002", "--fake-models"]) == 0
    assert "new clip seeds for S002" in capsys.readouterr().out

    assert main(["frame", "run-prompt", folder, "S001", "1", "--fake-models"]) == 1  # one prompt (0033)
    two = 'prompts=["A still. Rain.", "A still. Rain, closer."]'
    assert main(["frame", "edit", folder, "S001", "prompt=null", "count=null", two, "--fake-models"]) == 0
    capsys.readouterr()
    assert main(["frame", "run-prompt", folder, "S001", "2", "--fake-models"]) == 0
    assert "marked to make prompt 2" in capsys.readouterr().out


def test_an_unattended_video_from_the_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`new --auto-approve` (0004): `run` goes to the end without an approval; the frame run accepts each
    hold and takes each pick's first picture (0027)."""
    song = make_song(tmp_path / "song.wav", 12_000)
    assert (
        main(["new", "Alone", "--song", str(song), "--projects", str(tmp_path / "p"), "--auto-approve"]) == 0
    )
    folder = capsys.readouterr().out.strip()
    assert hmv.open_project(folder).record().approve == "auto"
    assert main(["run", folder, "--fake-models"]) == 0
    assert "completed" in capsys.readouterr().out


def test_errors_exit_with_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["status", str(tmp_path)]) == 1
    assert "no project at" in capsys.readouterr().err
    song = make_song(tmp_path / "song.wav", 3000)
    assert (
        main(["new", "x", "--song", str(song), "--projects", str(tmp_path / "p"), "--sheet", "nofile"]) == 1
    )
    assert "NAME=FILE" in capsys.readouterr().err
    with pytest.raises(SystemExit) as usage:
        main(["paint"])
    assert usage.value.code == 2


def test_a_failed_run_exits_with_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    song = tmp_path / "song.wav"
    song.write_bytes(b"not audio")
    project = hmv.create_project(tmp_path / "p", "Broken", song)
    assert main(["run", str(project.root), "--fake-models"]) == 1
    assert "measure       failed" in capsys.readouterr().out
