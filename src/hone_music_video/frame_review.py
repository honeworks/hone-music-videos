"""The feeling checked (0028 §2): the bible's arc against the song's parts, the camera's variety by code,
and the review call, which reads the shot list for what the viewer should feel.

The review is a check, not a planner: it runs on `models.review` (Claude Haiku 5.5 by default) and its
notes go back to the shot list as problems to repair, like the technical checks. Nothing is refused."""

from __future__ import annotations

import dataclasses
from collections import Counter
from typing import Any

from hone_music_video.frame_calls import Planner, system
from hone_music_video.records import Problem
from hone_music_video.records_frame import Bible, FrameShot, ShotList, ShotReview
from hone_music_video.shots_check import model_limits

MOST_OF_ONE_MOVE = 0.4  # no camera move on more than 40% of the shots
RUN_OF_ONE_MOVE = 4  # never four shots in a row with the same move
FEW_SHOTS = 8  # a list this short is not checked for variety


def arc_problems(bible: Bible, parts: list[str]) -> list[Problem]:
    """An arc that misses a part of the song or names one it does not have, an intensity outside 1 to 5,
    an entry without its feeling, or a character without its presence."""
    found: list[str] = []
    named = [a.part for a in bible.arc]
    found += [f"`arc` has no entry for the part {p!r}" for p in parts if p not in named]
    found += [f"`arc` names the part {p!r}, which the song does not have" for p in named if p not in parts]
    for a in bible.arc:
        if not 1 <= a.intensity <= 5:
            found.append(f"`arc` {a.part}: intensity {a.intensity}; give 1 (quiet) to 5 (the strongest)")
        if not a.feel.strip() or not a.evidence.strip():
            found.append(f"`arc` {a.part}: write its `feel` and its `evidence`")
    if not bible.feeling.strip():
        found.append("`feeling` is empty: write what the whole video should make the viewer feel")
    found += [f"{c.id} has no `presence`: what the viewer should feel about them, and what shows it"
              for c in bible.characters if not c.presence.strip()]  # fmt: skip
    return [Problem(rule="frame-arc", where="bible", message=m) for m in found]


def move(camera: str) -> str:
    """A camera's move, for comparing: "Slow push-in, low" -> "slow push-in"."""
    return camera.split(",", maxsplit=1)[0].split(";", maxsplit=1)[0].strip().lower().rstrip(".")


def camera_problems(shots: list[FrameShot]) -> list[Problem]:
    """One move on more than 40% of the shots, or four shots in a row with the same move (0028 §2)."""
    if len(shots) < FEW_SHOTS:
        return []
    moves = [move(s.camera) for s in shots]
    found: list[Problem] = []
    for name, n in Counter(moves).most_common():
        if n > MOST_OF_ONE_MOVE * len(shots):
            why = f"{n} of {len(shots)} shots are a {name!r}: choose each move for the feeling, and vary them"
            found.append(Problem(rule="camera", where="shots", message=why))
    for k in range(RUN_OF_ONE_MOVE - 1, len(moves)):
        if len(set(moves[k - RUN_OF_ONE_MOVE + 1 : k + 1])) == 1:
            why = f"is the {RUN_OF_ONE_MOVE}th {moves[k]!r} in a row: change the move or the distance"
            found.append(Problem(rule="camera", where=shots[k].id, message=why))
    return found


def _review_data(
    bible: Bible, shots: list[FrameShot], lines: dict[str, str], reply: ShotList
) -> dict[str, Any]:
    keep = {"id", "start_ms", "end_ms", "beat", "motion", "ends", "feel", "evidence", "focus", "framing",
            "camera", "cast", "place", "setup", "from_scene", "takes"}  # fmt: skip
    limits = [p for s in shots for p in model_limits(s.id, s.beat, s.framing)]
    return {
        "feeling": bible.feeling,
        "arc": [a.model_dump(mode="json") for a in bible.arc],
        "characters": [
            {
                "id": c.id,
                "name": c.name,
                "noun": c.noun,
                "presence": c.presence,
                "inner": c.inner,
            }
            for c in bible.characters
        ],
        "setups": [s.model_dump(mode="json") for s in reply.setups],
        "shots": [
            s.model_dump(mode="json", include=keep) | {"sung": [lines[i] for i in s.lines if i in lines]}
            for s in shots
        ],
        "code_found": [p.model_dump(include={"where", "message"}) for p in limits],
    }


def review_shots(
    planner: Planner, bible: Bible, shots: list[FrameShot], *, lines: dict[str, str], reply: ShotList
) -> list[Problem]:
    """The review call on the settings' `review` model, with what code found the models can't draw (0029
    §2): its notes as problems for the shot list's repair."""
    reviewer = dataclasses.replace(planner, model=planner.job.settings.models.review)
    data = _review_data(bible, shots, lines, reply)
    found, _ = reviewer.call("review", system("frame_review", limits=True), data, ShotReview)
    return [Problem(rule="feeling", where=n.where, message=n.problem) for n in found.notes if n.problem]
