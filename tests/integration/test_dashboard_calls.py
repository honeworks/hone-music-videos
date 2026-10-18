"""The planner's calls on the Plan view (0030 §2): each kept call with what was sent, the reply and the
problems the code found in it, listed in the order made, over the dashboard's API; a call kept before
0030 (no request) still reads."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video.testing import FakeModels
from tests.integration.test_dashboard import call, new_video, wait_for


@pytest.fixture
def base(tmp_path: Path) -> Iterator[str]:
    dashboard = hmv.Dashboard(tmp_path / "projects", FakeModels(), port=0).start()
    yield dashboard.url.rstrip("/")
    dashboard.close()


def test_the_plan_views_calls_show_what_was_sent_and_what_came_back(base: str, tmp_path: Path) -> None:
    project_id = new_video(base, tmp_path)
    wait_for(base, project_id, "review_lyrics")
    assert call(base, f"/api/projects/{project_id}/approve", {"gate": "review_lyrics"})[0] == 200
    wait_for(base, project_id, "review_plan")
    status, found, _ = call(base, f"/api/projects/{project_id}/calls")
    assert status == 200
    labels = [c["label"] for c in found["plan"]]
    assert labels[:3] == ["bible", "shots", "review"]  # in the order made
    assert any(label.startswith("subject-") for label in labels)
    assert any(label.startswith("scenes-") for label in labels)
    first = found["plan"][0]
    assert first["model"] and first["took_ms"] >= 0 and first["problems"] == 0 and first["sent_back"] == 0
    assert found["total"]["calls"] == len(labels)
    status, bible, _ = call(base, f"/api/projects/{project_id}/calls/{first['name']}")
    assert status == 200 and bible["request"]["schema"] == "Bible"
    assert "lyrics" in bible["request"]["data"] and bible["reply"]["kind"]
    assert bible["system_text"].startswith("# Role")
    assert call(base, f"/api/projects/{project_id}/calls/..%2Fproject")[0] == 404


def test_a_call_kept_before_0030_still_reads(base: str, tmp_path: Path) -> None:
    project_id = new_video(base, tmp_path)
    wait_for(base, project_id, "review_lyrics")
    calls = tmp_path / "projects" / project_id / "frame" / "calls"
    calls.mkdir(parents=True)
    old = {"label": "bible", "model": "claude-opus-5-5", "took_ms": 1200, "reply": {"story": "s"}}
    (calls / "bible-0123456789ab.json").write_text(json.dumps(old))
    found = call(base, f"/api/projects/{project_id}/calls")[1]
    assert [(c["label"], c["took_ms"], c["problems"]) for c in found["plan"]] == [("bible", 1200, 0)]
    one = call(base, f"/api/projects/{project_id}/calls/bible-0123456789ab")[1]
    assert one["request"] is None and one["system_text"] is None and one["reply"] == {"story": "s"}
