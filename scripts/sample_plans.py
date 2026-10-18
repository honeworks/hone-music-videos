"""The cast plan and the shot plan of the sample model set (see `sample_models.py`)."""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from hone_music_video.testing.answers import word_edge

PROPS = [
    {
        "id": "armband",
        "name": "the onyx armband",
        "carried_by": "loren",
        "note": "carved gold with an oval black onyx stone, Darvin's token, tied on the left upper arm",
    },
    {
        "id": "khanjar",
        "name": "Darvin's khanjar",
        "carried_by": "darvin",
        "note": "a heavy curved steel dagger",
    },
    {
        "id": "zereh",
        "name": "Loren's armour",
        "carried_by": "loren",
        "note": "steel and bronze lamellar armour",
    },
]
FRAMING_WORDS = (
    ("ultra-wide", "extreme-wide"),
    ("epic wide", "extreme-wide"),
    ("single object", "insert"),
    ("macro", "extreme-close-up"),
    ("close-up", "close-up"),
    ("wide", "wide"),
    ("silhouette", "wide"),
)
CAMERAS = {
    "extreme-wide": "slow crane up",
    "wide": "slow push-in",
    "medium": "gentle handheld drift",
    "close-up": "very slow push-in",
    "extreme-close-up": "slow macro slide",
    "insert": "slow macro slide",
}
FACES = ("medium", "close-up", "extreme-close-up")
BEATS = {  # the trial's scenes (inputs/video-stills.toml) in a few words
    "s01-balcony-dusk": "Celina alone on the balcony at dusk, looking towards the far plains",
    "s02-cradle-infant": "Celina watches over the newborn Loren",
    "s03-armband-velvet": "The onyx armband, the token Darvin left behind",
    "s04-young-loren-scimitar": "Loren at ten draws his first scimitar",
    "s05-imperial-crown": "The crown he means to win for his father",
    "s06-darvin-cliff-storm": "Darvin on the cliff, a giant against the storm",
    "s07-blood-red-sunrise": "A blood-red sun rises over the battlefield",
    "s08-loren-heroic-portrait": "Loren grown, fierce as a young lion",
    "s09-loren-gallop": "Loren rides to war on the grey stallion",
    "s10-turanian-army": "The Turanian army marches under gold banners",
    "s11-armband-lacing": "The armband tied on, hidden under the vambrace",
    "s12-canyon-clash": "Two armies clash; father and son face each other",
    "s13-darvin-firelight": "Darvin by firelight, too proud to give his name",
    "s14-darvin-khanjar": "Darvin draws the khanjar",
    "s15-loren-shield": "Loren braces behind his shield",
    "s16-tragic-silhouette": "The fatal moment, in silhouette",
    "s17-celina-collapse": "Celina collapses at the news",
    "s18-battlefield-still-life": "The riderless stallion on the empty battlefield",
    "s19-darvin-horror": "Darvin sees what he has done",
    "s20-armband-reveal": "The armband revealed on the dying son's arm",
    "s21-darvin-ash-grief": "Darvin heaps ash on his head in grief",
    "s22-celina-mourning": "Celina in mourning, her braids cut",
    "s23-celina-breastplate": "Celina holds her son's breastplate",
    "s24-stallion-moonlight": "Loren's stallion alone in the moonlight",
    "s25-celina-final-rest": "Celina lies down on her son's empty armour",
    "s26-tomb-milky-way": "The tomb in Vellmoor under the Milky Way",
    "s27-cradle-swaddled": "The cradle, only the swaddling linen left",
}


def _story(text: str) -> str:
    """The story notes' one-paragraph summary ("In short, ..."), else their first paragraph."""
    paragraphs = [
        p.strip() for p in text.split("\n\n") if p.strip() and not p.lstrip().startswith(("#", "-"))
    ]
    short = [p for p in paragraphs if p.startswith("In short")]
    return (short or paragraphs or ["The tragedy of Darvin and Loren."])[0].replace("**", "")


def cast_answer(data: Mapping[str, Any], characters: dict[str, dict[str, str]]) -> dict[str, Any]:
    """The trial's characters, each with a sheet to draw."""
    lines = data["timeline"]["lines"]

    def first_line(name: str) -> str | None:
        return next((ln["id"] for ln in lines if name.lower() in ln["text"].lower()), None)

    cast = [
        {
            "id": cid,
            "name": c["name"],
            "kind": "animal" if c["noun"] == "horse" else "person",
            "noun": c["noun"],
            "cue": c["cue"],
            "source": "make",
            "sheet_prompt": f"One wide studio photograph of {c['cue']}, shown four times in full figure: "
            "front, three-quarter, side and back, on a plain light grey background, 35mm film look.",
            "portrait": c["noun"] != "horse",
            "first_line": first_line(c["name"]),
        }
        for cid, c in characters.items()
    ]
    return {"characters": cast, "props": PROPS, "story": _story(str(data.get("story") or ""))}


def _outside_word(target: int, limit: int, words: list[tuple[int, int]]) -> int:
    """`target` moved to the nearer edge of the sung word it falls in, or to the word's start when the end
    would pass `limit` (the longest shot)."""
    edge = word_edge(target, words)
    return edge if edge <= limit else next(a for a, b in words if a < target < b)


def cuts(
    duration: int, candidates: list[int], words: list[tuple[int, int]], low: int = 5000, high: int = 8000
) -> list[int]:
    """Shot boundaries from 0 to the end: at a line or section start near 7.8 s when one is in reach, else
    near 7.8 s at the nearer edge of the sung word there (never inside a word)."""
    bounds = [0]
    while duration - bounds[-1] > high:
        t = bounds[-1]
        window = [c for c in candidates if t + low <= c <= t + high]
        bounds.append(
            min(window, key=lambda c: abs(c - t - 7800))
            if window
            else _outside_word(t + 7800, t + high, words)
        )
    if duration - bounds[-1] < low and len(bounds) > 1:  # a too-short last shot: share it with the one before
        bounds[-1] = _outside_word((bounds[-2] + duration) // 2, bounds[-2] + high, words)
    return [*bounds, duration]


def _framing(prompt: str, cast: list[str]) -> str:
    lower = prompt.lower()
    found = next((f for word, f in FRAMING_WORDS if word in lower), "medium")
    return "insert" if found == "extreme-close-up" and not cast else found


def _close(scene: dict[str, Any], names: dict[str, str]) -> tuple[str, list[str]]:
    """A second shot of a scene: a close-up of its first character (or a detail without one)."""
    cast = scene.get("cast", [])[:1]
    if not cast:
        return (
            "Cinematic extreme close-up detail, a still from a live-action historical epic film. "
            + scene["prompt"].split(". ", 2)[-1]
        ), []
    who = cast[0]
    return (
        "Cinematic close-up portrait, a still from a live-action historical epic film. "
        f"The face of {{{who}}}, {names.get(who, who)}, in the same moment: the same light, eyes catching "
        "the light, shallow depth of field. 35mm film photograph, natural film grain, real skin texture."
    ), cast


@dataclass(frozen=True)
class Plan:
    """What every shot of one plan reads: the timeline, the characters' names, the trial's motions."""

    timeline: dict[str, Any]
    names: dict[str, str]
    motions: dict[str, str]


def _shot(n: int, bounds: tuple[int, int], scene: dict[str, Any], repeat: bool, plan: Plan) -> dict[str, Any]:
    start, end = bounds
    prompt, cast = _close(scene, plan.names) if repeat else (scene["prompt"], list(scene.get("cast", [])))
    framing = ("close-up" if cast else "insert") if repeat else _framing(prompt, cast)
    beat = BEATS.get(scene["id"], scene["id"].split("-", 1)[1].replace("-", " "))
    return {
        "id": f"S{n:03d}",
        "start_ms": start,
        "end_ms": end,
        "lines": [ln["id"] for ln in plan.timeline["lines"] if ln["start_ms"] < end and ln["end_ms"] > start],
        "beat": f"{'Closer: ' if repeat else ''}{beat}",
        "framing": framing,
        "faces": bool(cast) and framing in FACES,
        "cast": cast,
        "location": "Vellmoor and the plains beyond",
        "camera": CAMERAS[framing],
        "still_prompt": prompt,
        "motion_prompt": plan.motions.get(scene["id"])
        or f"{CAMERAS[framing].capitalize()}. Dust drifts in the light; "
        "cloth and hair move gently in the wind. Real film footage, natural motion.",
        "refs": None,
    }


def shots_answer(
    data: Mapping[str, Any], scenes: list[dict[str, Any]], motions: dict[str, str]
) -> dict[str, Any]:
    """Shots tiling the song, the trial's scenes in story order spread over them."""
    timeline = data["timeline"]
    duration = int(timeline["duration_ms"])
    candidates = sorted(
        {ln["start_ms"] for ln in timeline["lines"]}
        | {s["start_ms"] for s in timeline["sections"]}
        | {i["end_ms"] for i in timeline["instrumental"]}
    )
    words = [(w[0], w[1]) for line in timeline["lines"] for w in line["words"]]  # [start_ms, end_ms, text]
    bounds = cuts(duration, candidates, words)
    plan = Plan(timeline, {c["id"]: c["name"] for c in data["cast"]["characters"]}, motions)
    shots, last = [], None
    for n, (start, end) in enumerate(itertools.pairwise(bounds), 1):
        scene = scenes[min(len(scenes) - 1, start * len(scenes) // duration)]
        shots.append(_shot(n, (start, end), scene, scene["id"] == last, plan))
        last = scene["id"]
    return {"shots": shots}
