"""The frame plan as a project file (0026, 0027): Hone Frame's stored format (its design §5), which
`hone_music_video.frame` reads and checks: `[project]`, `[defaults]`, `[demo]`, then every item in file
order, each referring only to items above it, then the sheets (a cast sheet, a turnaround per character
with views, a board per place with several pictures, the storyboard).

An item writes `size`, `seed`, `hold`, `count`, `model`, `refs`, and `prompt`, `prompts` or `file` (a given
picture, relative to the video project's folder: the import copies it into the frame project's
`assets/`). Strings are written as TOML basic strings (JSON's escapes are TOML's)."""

from __future__ import annotations

import json

from hone_music_video.records_frame import FrameItem, FramePlan

HEADER = """\
# Made by hone-music-video's frame planner (changes 0026, 0027) from the song's timed lyrics, in several
# planner calls that follow Hone Frame's prompt guide. This file is the source of truth of every picture
# up to the scenes: every prompt is sent exactly as written. Edit it here or in the Scenes view.
"""
BODY_VIEWS = ("hero", "three-quarter", "side", "back")  # a turnaround's order


def _s(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _list(values: list[str]) -> str:
    return "[" + ", ".join(map(_s, values)) + "]"


def _prompts(values: list[str]) -> str:
    return "[\n" + "".join(f"  {_s(v)},\n" for v in values) + "]"


def _table(item: FrameItem) -> str:
    if item.group == "scenes":
        return f"[scenes.{item.subject}]"
    return f"[{item.group}.{item.subject}.{item.name}]"


def _item(item: FrameItem) -> str:
    lines = [_table(item)]
    if item.file is not None:
        return "\n".join([*lines, f"file = {_s(item.file)}"])
    lines += [f"model = {_s(item.model)}"] if item.model else []
    lines += [f"size = {_s(item.size)}", f"seed = {item.seed}"]
    lines += ["hold = true"] if item.hold else []
    lines += [f"count = {item.count}"] if item.count > 1 else []
    lines += [f"refs = {_list(item.refs)}"] if item.refs else []
    if len(item.prompts) == 1:
        lines.append(f"prompt = {_s(item.prompts[0])}")
    else:
        lines.append(f"prompts = {_prompts(item.prompts)}")
    uses = f"# used by {', '.join(item.uses)}\n" if item.uses else ""
    return uses + "\n".join(lines)


def text(plan: FramePlan, name: str) -> str:
    """The project file's text."""
    bible = plan.bible
    parts = [
        HEADER,
        "[project]",
        f"name = {_s(name)}",
        f"style = {_s(bible.kind + ' ' + bible.finish)}   # reference only: never sent to a model",
        f"notes = {_s(bible.story)}",
        "",
        "[defaults]",
        f"model = {_s(plan.model)}",
        "hold = false",
    ]
    demo = [i for i in plan.items if i.group == "demo"]
    if demo:
        parts += [
            "",
            "# made first: the look of the whole video; the run waits until you accept it",
            "[demo]",
        ]
        parts += [f"size = {_s(demo[0].size)}", f"seed = {demo[0].seed}", "hold = true"]
        parts.append(f"prompts = {_prompts([i.prompts[0] for i in demo])}")
    for group in ("characters", "objects", "places", "scenes"):
        items = [i for i in plan.items if i.group == group]
        if items:
            parts += ["", f"# {'-' * 60} {group}"]
            parts += ["\n" + _item(i) for i in items]
    return "\n".join(parts) + "\n" + _sheets(plan)


def _sheet(name: str, layout: str, ids: list[str], labels: list[str], heading: str = "") -> str:
    head = f'\n[sheets.{name}]\nlayout = "{layout}"\n'
    head += "columns = 4\n" if layout == "contact-grid" else ""
    head += f"heading = {_s(heading)}\n" if heading else ""
    return head + f"images = {_list(ids)}\nlabels = {_list(labels)}\n"


def _sheets(plan: FramePlan) -> str:
    """The sheets, composed by Pillow once their pictures are made, never references (Hone Frame's guide,
    Sheets): the cast's heroes, each character's turnaround (front, three-quarter, side, back, those it
    has), each place's board, the storyboard of the scenes in order."""
    ids = {i.id: i for i in plan.items}
    names = {s.id: s.name for s in [*plan.bible.characters, *plan.bible.objects, *plan.bible.places]}
    heroes = [i for i in plan.items if i.group in ("characters", "objects") and i.name == "hero"]
    out = f"\n# {'-' * 60} sheets (composed, never references)\n"
    if heroes:
        out += _sheet(
            "cast", "contact-grid", [i.id for i in heroes], [names.get(i.subject, i.subject) for i in heroes]
        )
    for c in plan.bible.characters:
        views = [f"{c.id}.{v}" for v in BODY_VIEWS if f"{c.id}.{v}" in ids]
        if len(views) > 1:
            labels = [v.split(".", 1)[1].replace("hero", "front") for v in views]
            out += _sheet(f"{c.id}-turnaround", "four-view-turnaround", views, labels, c.name)
    for p in plan.bible.places:
        pictures = [i.id for i in plan.items if i.group == "places" and i.subject == p.id]
        if len(pictures) > 1:
            labels = [i.split(".", 1)[1] for i in pictures]
            out += _sheet(f"{p.id}-board", "environment-board", pictures, labels, p.name)
    scenes = [i.id for i in plan.items if i.group == "scenes"]
    if scenes:
        out += _sheet("storyboard", "contact-grid", scenes, scenes)
    return out
