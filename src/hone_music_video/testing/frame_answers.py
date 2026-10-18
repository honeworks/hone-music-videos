"""Plausible frame planner answers (0026) built from each call's data, so the frame planner runs on fakes:
a bible with one singer (and a variant), one object and one street (and a night state); shots that tile
the song; prompts that name every picture by its number. They are not good plans."""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from typing import Any

from hone_music_video.testing.answers import cut_points

KIND = "A still from a quiet drama film shot on 35mm film."
FINISH = "Soft film grain, muted colours."


SINGER = {
    "id": "Singer",  # not a safe id: the planner makes it one
    "name": "Mara",
    "kind": "person",
    "noun": "the woman",
    "look": "A woman of about thirty, slim, an oval face, long dark hair, a red wool coat and black boots.",
    "variants": [
        {
            "id": "rain",
            "look": "A woman of about thirty, slim, an oval face, long dark hair soaked flat, a soaked red "
            "wool coat and black boots.",
            "why": "the last chorus",
        }
    ],
    "presence": "someone the viewer worries for: tired eyes, shoulders drawn in against the cold",
    "inner": "she is afraid of going home; she shows calm; her hands stay in fists in her pockets",
}
STREET = {
    "id": "street",
    "name": "the street",
    "look": "a narrow street, brick houses on both sides",
    "light": "street lamps from the left",
    "states": [{"id": "night", "look": "a narrow street, brick houses on both sides, in dark blue night"}],
}
MOVES = ("slow push-in", "static camera", "slow pan left", "slow pull-back", "handheld drift")


def bible_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "story": data.get("story") or "A woman walks home through the city at night.",
        "kind": KIND,
        "finish": FINISH,
        "world": "Today's city: phones, cars and street lights belong.",
        "reference_light": "On a plain seamless mid-grey backdrop, one soft key light from the upper left.",
        "demo": [f"{KIND} A woman in a red coat on a wet street at night. {FINISH}"] * 3,
        "characters": [SINGER],
        "objects": [{"id": "lamp", "name": "the brass lamp", "look": "a small brass oil lamp, round"}],
        "places": [STREET],
        "feeling": "A quiet unease that grows into dread, and lets go at the end.",
        "arc": [
            {
                "part": p["part"],
                "feel": "unease",
                "intensity": 2 + n % 3,
                "turn": "the street darkens",
                "evidence": "she walks faster, looking back over her shoulder",
            }
            for n, p in enumerate(data.get("music", []))
        ],
    }


def _shot(n: int, start: int, end: int, lines: list[dict[str, Any]]) -> dict[str, Any]:
    face = n % 2 == 1
    return {
        "id": f"S{n:03d}",
        "start_ms": start,
        "end_ms": end,
        "lines": [ln["id"] for ln in lines if ln["start_ms"] < end and ln["end_ms"] > start],
        "beat": f"beat {n}: the woman walks on",
        "framing": "medium" if face else "wide",
        "faces": face,
        "camera": MOVES[n % len(MOVES)],
        "light": "street lamps from the left",
        "cast": [{"character": "singer", "variant": "", "view": "close" if face else "back"}],
        "place": {"place": "street", "view": "wide", "state": "" if face else "night"},
        "objects": [] if face else ["lamp"],
        "takes": "prompts" if n % 4 == 0 else "count" if n % 5 == 0 else "one",
        "feel": "unease",
        "evidence": "her eyes on the dark doorway, her hands in fists",
        "motion": "she walks two steps forward",
        "ends": "she stands under the lamp",
    }


def shots_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    timeline, settings = data["timeline"], data["settings"]
    bounds = cut_points(timeline, settings["min_shot_ms"], settings["max_shot_ms"])
    pairs = enumerate(itertools.pairwise(bounds), 1)
    return {"shots": [_shot(n, a, b, timeline["lines"]) for n, (a, b) in pairs]}


def _named(refs: list[dict[str, Any]]) -> str:
    return " ".join(f"The {r['what']} is image {r['image']}." for r in refs)


def items_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    kind, finish = data["kind"], data["finish"]
    return {
        "items": [
            {"id": i["id"], "prompt": f"{kind} {i['role']}. {_named(i['refs'])} {finish}"}
            for i in data["items"]
        ]
    }


def scenes_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    kind, finish = data["kind"], data["finish"]
    scenes: list[dict[str, Any]] = []
    for shot in data["shots"]:
        prompt = f"{kind} {_named(shot['refs'])} {shot['beat']}. {finish}"
        takes = 2 if shot["takes"] == "prompts" else 1
        scenes.append(
            {
                "id": shot["id"],
                "facts": {"things": [], "links": [], "visible": [shot["beat"]], "moment": shot["beat"]},
                "prompts": [f"{prompt} Take {k}." for k in range(1, takes + 1)] if takes > 1 else [prompt],
                "motion_prompt": "Slow push-in. Her coat moves in the wind; the street stays still.",
            }
        )
    return {"scenes": scenes}


def review_answer(_data: Mapping[str, Any]) -> dict[str, Any]:
    return {"notes": []}


FRAME_ANSWERS = {
    "Bible": bible_answer,
    "ShotList": shots_answer,
    "ItemPrompts": items_answer,
    "ScenePrompts": scenes_answer,
    "ShotReview": review_answer,
}
