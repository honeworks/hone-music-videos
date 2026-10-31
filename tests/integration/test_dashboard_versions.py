"""A shot's versions for the scene viewer (0024 §2, case 47; 0027 §7) over real HTTP, on fake models: every
kept version with what it was made from and whether the video uses it, the start frame naming its scene's
picture version, a remade clip in use and the earlier one kept, an unreadable record left out, unknown
projects and shots refused, and nothing written by the request."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.testing import FakeModels
from tests.integration.test_dashboard import call, new_video, to_the_end, wait_for


@pytest.fixture
def base(tmp_path: Path) -> Iterator[str]:
    dashboard = hmv.Dashboard(tmp_path / "projects", FakeModels(), port=0).start()
    yield dashboard.url.rstrip("/")
    dashboard.close()


def versions(base: str, project_id: str, shot: str) -> tuple[int, Any]:
    status, found, _ = call(base, f"/api/projects/{project_id}/shots/{shot}/versions")
    return status, found


def finished_video(base: str, tmp_path: Path) -> str:
    project_id = new_video(base, tmp_path)
    to_the_end(base, project_id)
    return project_id


def by_kind(found: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    kinds: dict[str, list[dict[str, Any]]] = {}
    for v in found["versions"]:
        kinds.setdefault(v["kind"], []).append(v)
    return kinds


def test_each_version_names_what_it_was_made_from_and_whether_it_is_used(base: str, tmp_path: Path) -> None:
    project_id = finished_video(base, tmp_path)
    status, found = versions(base, project_id, "S001")
    assert status == 200 and found["shot"] == "S001"
    kinds = by_kind(found)
    (still,), (clip,), (finish,) = kinds["still"], kinds["raw_clip"], kinds["clip"]
    assert finish["from"] == clip["url"] and all(v["in_use"] for v in found["versions"])
    assert clip["from"] is not None and still["scene_version"] == 1  # its scene's picture, version 1
    assert {"stage", "model", "seed", "prompt", "made_at"} <= set(still)
    assert still["url"].startswith(f"/files/{project_id}/current/shots/S001/versions/stills-")
    times = [v["made_at"] for v in found["versions"]]
    assert times == sorted(times, reverse=True)  # newest first

    assert call(base, f"/api/projects/{project_id}/redo-clip", {"shots": ["S001"]})[0] == 200
    deadline = time.monotonic() + 20

    def remade() -> bool:  # the new clip is listed, in use, and the remake's run has ended
        clips = by_kind(versions(base, project_id, "S001")[1])["raw_clip"]
        done = call(base, f"/api/projects/{project_id}")[1]["status"] == "completed"
        return len(clips) >= 2 and clips[0]["in_use"] and done

    while not remade():
        assert time.monotonic() < deadline, "the clip was never remade"
        time.sleep(0.05)
    kinds = by_kind(versions(base, project_id, "S001")[1])
    assert len(kinds["still"]) == 1  # a new seed keeps the start frame
    newer, older = kinds["raw_clip"]
    assert newer["in_use"] and not older["in_use"] and newer["seed"] != older["seed"]


def test_an_unreadable_record_is_left_out_and_reading_writes_nothing(base: str, tmp_path: Path) -> None:
    project_id = finished_video(base, tmp_path)
    folder = tmp_path / "projects" / project_id / "current" / "shots" / "S001" / "versions"
    (folder / "stills-bbbbbbbbbbbb.png").write_bytes(b"png")
    (folder / "stills-bbbbbbbbbbbb.json").write_text("{ not json")
    record = json.loads(next(folder.glob("clips-*.json")).read_text())
    (folder / "clips-cccccccccccc.json").write_text(json.dumps(record | {"file": "current/gone.mp4"}))
    before = snapshot(tmp_path / "projects" / project_id)

    found = versions(base, project_id, "S001")[1]
    assert not any("bbbbbbbbbbbb" in v["url"] or "gone" in v["url"] for v in found["versions"])
    assert len(found["versions"]) == 3
    assert snapshot(tmp_path / "projects" / project_id) == before  # the request writes nothing


def test_unknown_projects_and_shots_are_not_found(base: str, tmp_path: Path) -> None:
    project_id = new_video(base, tmp_path)
    wait_for(base, project_id, "review_lyrics")
    assert versions(base, project_id, "S001")[0] == 404  # no shot plan yet
    assert versions(base, "missing", "S001")[0] == 404
    assert versions(base, project_id, "..")[0] == 404


def snapshot(root: Path) -> dict[str, int]:
    return {str(p.relative_to(root)): p.stat().st_mtime_ns for p in sorted(root.rglob("*"))}
