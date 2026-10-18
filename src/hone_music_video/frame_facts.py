"""A scene's facts checked (0029 §1): written before its prompt, each link's two ends named in every
prompt, and more than three of a kind kept as a warning (only the shot list could change it)."""

from __future__ import annotations

import re

from hone_music_video.records import Problem
from hone_music_video.records_frame import ScenePrompt

MAX_COUNT = 3  # more of a kind than this failed under every idea (0029)
DETERMINERS = re.compile(r"^(?:the|a|an|his|her|its|their|one)\s+")


def _plain(text: str) -> str:
    return " ".join(text.lower().split())


def facts_problems(scene: ScenePrompt) -> list[str]:
    """No facts, or a link with an end that a prompt does not name (without its article, any case)."""
    if scene.facts is None:
        return [
            "has no `facts`: write the things, links, visible and moment first, then the prompt from them"
        ]
    found: list[str] = []
    for link in scene.facts.links:
        ends = [
            e
            for e in link.ends
            if any(DETERMINERS.sub("", _plain(e)) not in _plain(p) for p in scene.prompts)
        ]
        if ends:
            named = ", ".join(f'"{e}"' for e in ends)
            found.append(f'the link "{link.sentence}" has ends the prompt does not name: {named}; '
                         "name both ends in the prompt as the link does")  # fmt: skip
    return found


def scene_warnings(scene: ScenePrompt) -> list[Problem]:
    """More than three of a kind in a scene's facts (0029 §2): kept in the plan's problems, not sent back,
    since only the shot list can change it."""
    things = scene.facts.things if scene.facts else []
    why = "more than three of a kind are seldom drawn exactly"
    return [
        Problem(rule="model-limit", where=scene.id, message=f"counts {t.count} {t.what!r}: {why}")
        for t in things
        if t.count > MAX_COUNT
    ]
