"""Two processes on one projects folder: a busy run refuses a second writer, and two projects made at
once under the same name get two ids."""

import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video.cli import main
from hone_music_video.testing import FakeModels, make_song

SLOW = Path(__file__).with_name("slow_run.py")


def wait_for(path: Path, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 30
    while not path.exists():
        assert process.poll() is None, process.stderr.read().decode() if process.stderr else ""
        assert time.monotonic() < deadline, "the run never reached the stills stage"
        time.sleep(0.02)


def test_a_busy_run_refuses_a_second_writer(
    project: hmv.Project, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marker = tmp_path / "paused"
    process = subprocess.Popen(
        [sys.executable, str(SLOW), str(project.root), str(marker)], stderr=subprocess.PIPE
    )
    try:
        wait_for(marker, process)
        assert hmv.status(project).status == "running"
        assert hmv.status(project).waiting is None
        with pytest.raises(hmv.RunStateError, match="running in another process"):
            hmv.resume(project, FakeModels())
        with pytest.raises(hmv.RunStateError, match="still running"):
            hmv.approve(project)
        with pytest.raises(hmv.RunStateError, match="still running"):
            hmv.reject(project, note="again")
        for command in (["approve", str(project.root)], ["resume", str(project.root), "--fake-models"]):
            assert main(command) == 1
            err = capsys.readouterr().err
            assert err.startswith("error: ") and "Traceback" not in err
    finally:
        marker.unlink(missing_ok=True)
        assert process.wait(timeout=60) == 0
    assert hmv.status(project).status == "completed"
    lines = project.events_file.read_text().splitlines()
    shots = Counter(e["file"] for e in map(json.loads, lines) if e["event"] == "version_made" and "shot" in e)
    assert set(shots.values()) == {1}, "a file was made twice"  # a shot's other takes are files of their own


MAKER = """
import sys, time
import hone_music_video as hmv
projects, song, start = sys.argv[1], sys.argv[2], float(sys.argv[3])
while time.time() < start:
    pass
for _ in range(5):
    print(hmv.create_project(projects, "Same Song", song).id)
"""


def test_projects_made_at_once_under_one_name_get_their_own_ids(tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 1000)
    start = str(time.time() + 1.0)
    command = [sys.executable, "-c", MAKER, str(tmp_path / "projects"), str(song), start]
    makers = [subprocess.Popen(command, stdout=subprocess.PIPE, text=True) for _ in range(2)]
    ids = [line for m in makers for line in m.communicate(timeout=60)[0].split()]
    assert all(m.returncode == 0 for m in makers)
    assert len(ids) == len(set(ids)) == 10
    made = hmv.list_projects(tmp_path / "projects")
    assert sorted(p.id for p in made) == sorted(ids)
    assert all(p.record().id == p.id for p in made)
