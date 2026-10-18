"""AC-6: `check_shots` rejects gaps, overlaps, cuts inside words, shots outside the length limits, unknown
cast and `faces: true` on wide framing; a plan that passes tiles the song exactly (design §5.2, §14)."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.cli import main
from hone_music_video.testing import FakeModels
from hone_music_video.testing.frame_answers import shots_answer
from tests.conftest import new_project

pytestmark = pytest.mark.e2e
SETTINGS = hmv.Settings(min_shot_ms=2000, max_shot_ms=8000)
TIMELINE = hmv.Timeline.model_validate(
    {
        "duration_ms": 12_000,
        "sections": [{"id": "v", "kind": "verse", "start_ms": 2000, "end_ms": 7000}],
        "lines": [
            {
                "id": "L001",
                "section": "v",
                "text": "she waits",
                "start_ms": 2000,
                "end_ms": 7000,
                "words": [
                    {"text": "she", "start_ms": 2000, "end_ms": 3000},
                    {"text": "waits", "start_ms": 3500, "end_ms": 7000},
                ],
            }
        ],
        "instrumental": [{"start_ms": 0, "end_ms": 2000, "kind": "intro"}],
    }
)
CAST = ["celina"]  # the characters of the plan (0027)


def shot(n: int, start: int, end: int, **more: Any) -> dict[str, Any]:
    return {
        "id": f"S{n:03d}",
        "start_ms": start,
        "end_ms": end,
        "lines": ["L001"] if start < 7000 and end > 2000 else [],
        "beat": "b",
        "framing": "medium",
        "faces": True,
        "cast": ["celina"],
        "location": "a balcony",
        "camera": "static camera",
        "still_prompt": "Medium shot of the queen at the balustrade.",
        "motion_prompt": "Static camera. She lowers her eyes.",
    } | more


def errors(*plan: dict[str, Any]) -> set[tuple[str, str]]:
    report = hmv.check_shots(hmv.Shots.model_validate({"shots": list(plan)}), TIMELINE, CAST, SETTINGS)
    return {(p.rule, p.where) for p in report.errors}


GOOD = (shot(1, 0, 3200), shot(2, 3200, 7000), shot(3, 7000, 12_000))


def test_a_plan_that_tiles_the_song_passes() -> None:
    assert errors(*GOOD) == set()


@pytest.mark.parametrize(
    ("plan", "found"),
    [
        ((shot(1, 1, 3200), *GOOD[1:]), ("song-start", "S001")),
        ((*GOOD[:2], shot(3, 7000, 11_999)), ("song-end", "S003")),
        ((*GOOD[:2], shot(3, 7000, 12_001)), ("song-end", "S003")),
        ((GOOD[0], shot(2, 3201, 7000), GOOD[2]), ("gap", "S002")),
        ((GOOD[0], shot(2, 3199, 7000), GOOD[2]), ("overlap", "S002")),
    ],
    ids=["starts-1-ms-late", "ends-1-ms-early", "ends-1-ms-late", "1-ms-gap", "1-ms-overlap"],
)
def test_a_plan_off_the_tiling_by_one_millisecond_is_rejected(
    plan: tuple[dict[str, Any], ...], found: tuple[str, str]
) -> None:
    assert found in errors(*plan)


@pytest.mark.parametrize(
    ("plan", "found"),
    [
        ((shot(1, 0, 3200), shot(2, 3300, 7000), GOOD[2]), ("gap", "S002")),
        ((shot(1, 0, 3200), shot(2, 3100, 7000), GOOD[2]), ("overlap", "S002")),
        ((shot(1, 0, 4000), shot(2, 4000, 7000), GOOD[2]), ("cut-in-word", "S002")),
        ((shot(1, 0, 3501), shot(2, 3501, 7000), GOOD[2]), ("cut-in-word", "S002")),
        ((shot(1, 0, 3200), shot(2, 3200, 4500), shot(3, 4500, 12_000)), ("length", "S002")),
        ((shot(1, 0, 3200), shot(2, 3200, 12_000)), ("length", "S002")),
        ((GOOD[0], shot(2, 3200, 7000, cast=["loren"]), GOOD[2]), ("unknown-cast", "S002")),
        ((GOOD[0], GOOD[1], shot(3, 7000, 12_000, framing="wide")), ("faces", "S003")),
    ],
    ids=[
        "gap",
        "overlap",
        "cut-inside-a-word",
        "cut-1-ms-inside-a-word",
        "too-short",
        "too-long",
        "unknown-cast",
        "faces-on-wide",
    ],
)
def test_each_rule_rejects_its_plan(plan: tuple[dict[str, Any], ...], found: tuple[str, str]) -> None:
    assert found in errors(*plan)


def late(data: Mapping[str, Any]) -> dict[str, Any]:
    plan = shots_answer(data)
    plan["shots"][1]["start_ms"] += 40
    return plan


def to_shots(project: hmv.Project, models: FakeModels) -> None:
    state = hmv.start(project, models)
    while state.waiting != "review_plan":
        hmv.approve(project)
        state = hmv.resume(project, models)


def test_the_command_prints_every_finding_with_its_shot_rule_and_amount(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = new_project(tmp_path)
    to_shots(project, FakeModels(answers={"ShotList": late}))
    assert main(["check-shots", str(project.root)]) == 1
    out = capsys.readouterr().out
    assert "error    S002    gap                starts 40 ms after S001 ends" in out
    printed = [line for line in out.splitlines() if line.startswith("error ")]
    assert f"shots: {len(printed)} errors" in out  # one line per error, then the count

    clean = new_project(tmp_path / "clean")
    to_shots(clean, FakeModels())
    assert main(["check-shots", str(clean.root)]) == 0
    assert "0 errors" in capsys.readouterr().out
    assert main(["check-shots", str(new_project(tmp_path / "new").root)]) == 1
    assert "has no shot list yet" in capsys.readouterr().err
