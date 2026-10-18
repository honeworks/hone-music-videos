"""Estimates (design §9.1): measured seconds per (model, size) from the workspace's `events.jsonl`
files, the last 50 of each. With at least 3, a range from the 25th to the 75th percentile; without,
"no measurement yet". No made-up figures.

Hone Frame: ported from `src/hone_frame/estimates.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from hone_music_video.frame.events import read_lines
from hone_music_video.frame.project_file import ItemSpec

MIN_MEASUREMENTS = 3
KEEP_LAST = 50
Key = tuple[str, str]  # (model, size); size "" when the model's default


def key(item: ItemSpec) -> Key | None:
    """The measurement an image item is estimated from; a sheet is composed in a moment (None)."""
    return (str(item.model), item.size or "") if item.kind == "image" and not item.file else None


def measured(home: Path) -> dict[Key, list[float]]:
    """Seconds per image, per (model, size), from every project of the workspace, the last 50 of each."""
    found: dict[Key, list[tuple[str, float]]] = defaultdict(list)
    for path in (home / "projects").glob("*/events.jsonl"):
        for row in read_lines(path):
            if row.get("kind") == "item_made" and row.get("elapsed_s") is not None:
                found[(str(row.get("model")), row.get("size") or "")].append(
                    (row["at"], float(row["elapsed_s"]))
                )
    return {k: [s for _, s in sorted(v)[-KEEP_LAST:]] for k, v in found.items()}


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low, high = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def item_estimate(item: ItemSpec, durations: dict[Key, list[float]]) -> dict[str, float] | None:
    """`{low_s, high_s}` for making the item (`count` images), or None without 3 measurements."""
    k = key(item)
    if k is None:
        return {"low_s": 0.0, "high_s": 0.0}
    values = durations.get(k, [])
    if len(values) < MIN_MEASUREMENTS:
        return None
    return {
        "low_s": round(item.per_run * quantile(values, 0.25), 1),
        "high_s": round(item.per_run * quantile(values, 0.75), 1),
    }


def run_estimate(items: Iterable[ItemSpec], durations: dict[Key, list[float]]) -> dict[str, Any] | None:
    """The remaining time of these items: the sum of those with measurements, and `missing` listing
    the (model, size) pairs left out of the sum. None when there is nothing to make."""
    items = list(items)
    if not items:
        return None
    low = high = 0.0
    missing: dict[Key, int] = defaultdict(int)
    for item in items:
        found = item_estimate(item, durations)
        if found is None:
            missing[key(item) or ("", "")] += 1
        else:
            low, high = low + found["low_s"], high + found["high_s"]
    rows = [{"model": m, "size": s or None, "items": n} for (m, s), n in missing.items()]
    return {"low_s": round(low, 1), "high_s": round(high, 1), "missing": rows}


def done_at(estimate: dict[str, Any] | None, start: datetime | None = None) -> str | None:
    """The local time (ISO 8601) at the high end of the estimate, when every item has measurements."""
    if not estimate or estimate["missing"]:
        return None
    end = (start or datetime.now().astimezone()) + timedelta(seconds=estimate["high_s"])
    return end.isoformat(timespec="seconds")


def missing_text(estimate: dict[str, Any]) -> list[str]:
    """ "no measurement yet for <model> at <size>: N items", one line per pair."""
    return [
        f"no measurement yet for {m['model']} at {m['size'] or 'its default size'}: {m['items']} item"
        + ("s" if m["items"] != 1 else "")
        for m in estimate["missing"]
    ]
