"""Plausible planner answers built from the call's data, so every stage can run on fakes.

They follow the data the stages send (see `hone_music_video.stages_plan`); they are not good plans."""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping
from typing import Any

from hone_music_video._files import slug

WORDS_PER_LINE = 6
ANCHOR = "A still from a drama film, real locations, the present day."  # the fake cast's anchor (0014)
WORLD = "Today's city: phones, cars and street lights belong; nothing from another age."  # (0009)
STILL = " The rest of the frame stays still."  # what the fake check adds to a motion prompt it rewrites


def lyrics_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    """The lyrics editor's reply (`LyricsEdit`): the heard words in lines of six, as heard, one verse,
    instrumental spans before the first line and after the last."""
    heard = list(data["heard_words"])
    lines = [
        {
            "section": "verse-1",
            "text": " ".join(w["text"] for w in heard[start : start + WORDS_PER_LINE]),
            "heard_first": start,
            "heard_last": min(start + WORDS_PER_LINE, len(heard)) - 1,
        }
        for start in range(0, len(heard), WORDS_PER_LINE)
    ]
    ends = [{"after_line": 0, "kind": "intro"}, {"after_line": len(lines), "kind": "outro"}]
    return {
        "language": data.get("language"),
        "sections": [{"id": "verse-1", "kind": "verse"}],
        "lines": lines,
        "instrumental": ends if lines else [],
    }


def cast_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    """One person per given sheet (with a portrait); without sheets, one character to make; their traits
    and the story's anchor (0014)."""
    first_line = next((line["id"] for line in data["timeline"]["lines"]), None)
    characters = [
        {
            "id": slug(sheet["name"], "character"),
            "name": sheet["name"],
            "kind": "person",
            "noun": "person",
            "cue": f"{sheet['name']}, as in the given sheet",
            "source": f"given:{sheet['name']}",
            "portrait": True,
            "first_line": first_line,
            "traits": "as in the given sheet",
        }
        for sheet in data["sheets"]
    ]
    pictures = data.get("settings", {}).get("packs") == "views"  # one figure, and a detail (0020)
    if not characters:
        singer = {
            "sheet_prompt": "one studio photograph of one woman, full body, facing the camera"
            if pictures
            else "one wide studio photograph of the same woman four times, full body",
        }
        details = (
            {"details": [{"id": "ring", "look": "a thin silver ring on her left hand"}]} if pictures else {}
        )
        characters.append(
            {
                "id": "singer",
                "name": "The singer",
                "kind": "person",
                "noun": "woman",
                "cue": "a young woman with long dark hair in a grey coat",
                "source": "make",
                "portrait": True,
                "first_line": first_line,
                "traits": "a woman of thirty, slender, long dark hair",
            }
            | singer
            | details
        )
    story = data.get("story") or "a song"
    return {"characters": characters, "props": [], "story": story, "anchor": ANCHOR, "world": WORLD}


def word_edge(t: int, words: list[tuple[int, int]]) -> int:
    """`t`, or the nearer edge of the sung word `(start_ms, end_ms)` it falls strictly inside: a cut
    there passes `check_shots` (heard words do not overlap, D-017)."""
    inside = next(((a, b) for a, b in words if a < t < b), None)
    if inside is None:
        return t
    return inside[0] if t - inside[0] <= inside[1] - t else inside[1]


def cut_points(timeline: Mapping[str, Any], low: int, high: int) -> list[int]:
    """0, the cuts, the song's end: shots of about four fifths of the longest, each cut moved out of the
    sung word it falls in."""
    duration = int(timeline["duration_ms"])
    words = [(w[0], w[1]) for line in timeline["lines"] for w in line["words"]]  # [start_ms, end_ms, text]
    count = max(1, math.ceil(duration * 5 / (high * 4)))
    while count > 1 and duration / count < low:
        count -= 1
    return [0, *(word_edge(round(i * duration / count), words) for i in range(1, count)), duration]


def _shot(
    n: int, start: int, end: int, lines: list[dict[str, Any]], who: list[str], *, anchor: str
) -> dict[str, Any]:
    still = f"Medium shot, {{{who[0]}}} looks up." if who else "Wide shot of the street."
    return {
        "id": f"S{n:03d}",
        "start_ms": start,
        "end_ms": end,
        "lines": [ln["id"] for ln in lines if ln["start_ms"] < end and ln["end_ms"] > start],
        "beat": f"beat {n}",
        "framing": "medium" if who else "wide",
        "faces": bool(who),
        "cast": who,
        "location": "a quiet street at dusk",
        "camera": "slow push-in" if who else "static camera",
        "still_prompt": f"{anchor} {still}".strip(),
        "motion_prompt": "Slow push-in. Her hair moves in the wind." if who else "Static camera.",
        "refs": None,
    }


def replan_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    """A re-plan (0008): the previous plan with the note added to each listed shot's still prompt."""
    listed, note = data["replan"]["shots"], data["replan"]["note"]
    return {
        "shots": [
            s | {"still_prompt": f"{s['still_prompt']} {note}"} if s["id"] in listed else s
            for s in data["previous_plan"]["shots"]
        ]
    }


def shots_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    """Shots of about equal length that tile the song, no cut inside a sung word, alternating a medium shot
    of the cast and a wide shot; a re-plan's answer is `replan_answer`'s."""
    if "replan" in data:
        return replan_answer(data)
    timeline, settings = data["timeline"], data["settings"]
    bounds = cut_points(timeline, settings["min_shot_ms"], settings["max_shot_ms"])
    cast = [c["id"] for c in data["cast"]["characters"]][:1]
    pairs = enumerate(itertools.pairwise(bounds), 1)
    anchor = data.get("anchor") or ""  # every still prompt begins with it (0014)
    return {
        "shots": [
            _shot(n, a, b, timeline["lines"], cast if n % 2 else [], anchor=anchor) for n, (a, b) in pairs
        ]
    }


def stills_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    """The start-frame check's reply (`StillsReview`): every still shown scores 7 and has no flags; a
    motion prompt it is asked to rewrite gets `STILL` added (0014)."""
    return {
        "stills": [
            {"label": s["label"], "score": 7, "flags": []}
            | ({"motion_prompt": s["motion_prompt"] + STILL} if s.get("rewrite") else {})
            for s in data["stills"]
        ]
    }


def drafts_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    """The check of the drafts (`DraftsReview`, 0015): every draft shown scores 7 and has no flags, so
    nothing is drawn again."""
    return {"stills": [{"label": s["label"], "score": 7, "flags": []} for s in data["stills"]]}


def sheets_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    """The judge of the sheet takes (`SheetsReview`, 0019): every take shown scores 7 with the figures
    and views it must have and no flags, so nothing is drawn again."""
    return {
        "sheets": [
            {
                "label": t["label"],
                "score": 7,
                "figures": t["subject"]["figures"],
                "views": t["subject"]["views"],
            }
            for t in data["takes"]
        ]
    }


DEFAULT_ANSWERS = {
    "LyricsEdit": lyrics_answer,
    "Cast": cast_answer,
    "Shots": shots_answer,
    "StillsReview": stills_answer,
    "DraftsReview": drafts_answer,
    "SheetsReview": sheets_answer,
}
