"""AC-9: "no measurement yet" until three measurements per model and size, then a range.

Hone Frame: ported from its `tests/e2e/test_ac9_estimates.py` (change 0027)."""

from __future__ import annotations

from datetime import datetime

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.estimates import done_at, missing_text
from hone_music_video.frame.views import item_view, run_view
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import run

pytestmark = pytest.mark.e2e

TEXT = """
[project]
name = "Estimates"

[places.kitchen.wide]
model = "z-image-turbo"
size = "1024x1024"
prompt = "kitchen"

[places.hall.wide]
model = "flux.2-klein-4b"
refs = ["kitchen.wide"]
prompt = "hall"
count = 2
"""


def test_ac9_estimates_need_three_measurements(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    first = run_view(project).estimate
    assert first is not None and first["low_s"] == first["high_s"] == 0
    assert {(m["model"], m["size"], m["items"]) for m in first["missing"]} == {
        ("z-image-turbo", "1024x1024", 1),
        ("flux.2-klein-4b", None, 1),
    }
    assert "no measurement yet for z-image-turbo at 1024x1024: 1 item" in missing_text(first)
    assert done_at(first) is None and item_view(project, "kitchen.wide").estimate is None

    for seconds in (10.0, 20.0, 30.0):
        fake.elapsed_s = seconds
        actions.mark(project, "kitchen.wide")
        actions.unmark(project, "hall.wide")
        run(ws, project)
    assert item_view(project, "kitchen.wide").estimate == {"low_s": 15.0, "high_s": 25.0}
    actions.mark(project, "kitchen.wide")
    actions.mark(project, "hall.wide")
    estimate = run_view(project).estimate
    assert estimate is not None
    assert (estimate["low_s"], estimate["high_s"]) == (15.0, 25.0)  # the hall is left out of the sum
    assert estimate["missing"] == [{"model": "flux.2-klein-4b", "size": None, "items": 1}]
    assert item_view(project, "hall.wide").estimate is None


def test_ac9_done_at_is_the_high_end() -> None:
    start = datetime(2026, 10, 13, 9, 0).astimezone()
    assert (
        done_at({"low_s": 60, "high_s": 600, "missing": []}, start) == (start.replace(minute=10)).isoformat()
    )
