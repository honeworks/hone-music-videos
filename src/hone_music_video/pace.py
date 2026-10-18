"""The pace of the cut (0009, design §2.3, §5.2, §7.3; D-084): how long the shots should be.

`pace` is a project option. "calm" asks for long shots (about 6.5 to 8 s), few cuts inside a verse and
cuts on line or section starts; "energetic" for short ones; "balanced" leaves the length to the shot
limits alone. The shot planner gets the range as data, and `check_shots` warns on a shot outside it
(a warning, never an error: a line may force a shorter shot)."""

from __future__ import annotations

from hone_music_video.records import Problem, Shot
from hone_music_video.settings import Pace, Settings

SHOT_MS: dict[Pace, tuple[int, int] | None] = {
    "calm": (6500, 8000),
    "balanced": None,
    "energetic": (2000, 4500),
}


def shot_range(settings: Settings) -> tuple[int, int] | None:
    """The shot length the pace prefers, inside the shot limits; None when it prefers none, or when the
    limits leave none of it (the project's limits win, D-084)."""
    preferred = SHOT_MS[settings.pace]
    if preferred is None:
        return None
    low, high = max(preferred[0], settings.min_shot_ms), min(preferred[1], settings.max_shot_ms)
    return (low, high) if low < high else None


def pace_warnings(shots: list[Shot], settings: Settings) -> list[Problem]:
    """A `pace` warning for each shot outside the pace's range, but the last (it ends with the song)."""
    found = shot_range(settings)
    if found is None:
        return []
    low, high = found
    warned: list[Problem] = []
    for shot in shots[:-1]:
        length = shot.end_ms - shot.start_ms
        if not low <= length <= high:
            off = low - length if length < low else length - high
            side = "shorter" if length < low else "longer"
            why = f"lasts {length} ms, {off} ms {side} than the {settings.pace} pace's {low}-{high} ms"
            warned.append(Problem(rule="pace", where=shot.id, message=why))
    return warned
