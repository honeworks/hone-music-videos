"""Estimates (design §9.1): measured per (model, size), the last 50, a range times `count`.

Hone Frame: ported from its `tests/unit/test_estimates.py` (change 0027)."""

from __future__ import annotations

from pathlib import Path

from hone_music_video.frame.estimates import KEEP_LAST, item_estimate, measured, run_estimate
from hone_music_video.frame.events import append_line
from hone_music_video.frame.project_file import ItemSpec


def made(home: Path, model: str, size: str, seconds: list[float], *, start: int = 0) -> None:
    for n, s in enumerate(seconds, start=start):
        row = {"at": f"2026-10-13T09:{n // 60:02d}:{n % 60:02d}Z", "kind": "item_made", "model": model}
        append_line(home / "projects" / "p" / "events.jsonl", row | {"size": size, "elapsed_s": s})


def item(model: str, size: str, count: int = 1) -> ItemSpec:
    fields = {"model": model, "size": size, "count": count, "prompt": "x"}
    return ItemSpec("a.b", "places", "a", "b", ("places", "a", "b"), "image", fields, fields)


def test_count_multiplies_the_range(tmp_path: Path) -> None:
    made(tmp_path, "m", "512x512", [10.0, 20.0, 30.0])
    durations = measured(tmp_path)
    assert item_estimate(item("m", "512x512"), durations) == {"low_s": 15.0, "high_s": 25.0}
    assert item_estimate(item("m", "512x512", count=3), durations) == {"low_s": 45.0, "high_s": 75.0}


def test_measurements_are_kept_per_model_and_size(tmp_path: Path) -> None:
    made(tmp_path, "m", "512x512", [10.0, 20.0, 30.0])
    durations = measured(tmp_path)
    assert item_estimate(item("m", "1024x1024"), durations) is None  # the same model at another size
    estimate = run_estimate([item("m", "512x512"), item("m", "1024x1024", count=2)], durations)
    assert estimate == {
        "low_s": 15.0,
        "high_s": 25.0,
        "missing": [{"model": "m", "size": "1024x1024", "items": 1}],
    }


def test_only_the_last_fifty_count(tmp_path: Path) -> None:
    made(tmp_path, "m", "512x512", [1000.0] * 10)  # the oldest, left out
    made(tmp_path, "m", "512x512", [10.0] * KEEP_LAST, start=10)
    assert KEEP_LAST == 50 and measured(tmp_path)[("m", "512x512")] == [10.0] * 50
    assert item_estimate(item("m", "512x512"), measured(tmp_path)) == {"low_s": 10.0, "high_s": 10.0}
