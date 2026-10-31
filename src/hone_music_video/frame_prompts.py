"""Calls 3 and 4 of the frame planner (0026): the prompts of each subject's pictures, one call per
subject, and the scene prompts, one call per few shots; the calls run side by side.

Every reply is checked by code (`frame_calls.prompt_problems`, the motion prompt's words) and sent back
once with what is wrong. A picture still without a usable prompt gets one written by code from its role
and the bible, so the plan is always whole; what is still wrong goes into the plan's `problems`."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from hone_music_video.frame_calls import CALLS_AT_ONCE, Planner, prompt_problems, system
from hone_music_video.frame_facts import facts_problems, scene_warnings
from hone_music_video.frame_focus import focus_of
from hone_music_video.frame_items import MAX_SCENE_REFS, hero_view, scene_refs
from hone_music_video.ports import ImageInfo
from hone_music_video.prompt_words import words_of_speech
from hone_music_video.records import Problem
from hone_music_video.records_frame import (
    Bible,
    FrameCharacter,
    FrameItem,
    FramePlace,
    FrameShot,
    ItemPrompts,
    ScenePrompt,
    ScenePrompts,
)

SCENES_PER_CALL = 6
SUBJECT_REPAIRS = 2  # a hero over the limit came back over it after one repair (0034 §5)
MOTION_CHARS = 1000
GUIDES = {
    "characters": ("project-file", "hero", "views", "faces", "poses", "models"),
    "objects": ("project-file", "objects", "models"),
    "places": ("project-file", "places", "models"),
}
RECIPE_END = "#### Start with a demo"  # the guide's general part stops here: the rest is the file format


# ------------------------------------------------------------------------------ what each picture is


def _character(c: FrameCharacter, name: str) -> dict[str, str]:
    variants = sorted(c.variants, key=lambda v: -len(v.id))  # the longest id first: "wet" after "wet-coat"
    variant = next((v for v in variants if name == v.id or name.startswith(f"{v.id}-")), None)
    view = name.removeprefix(variant.id).strip("-") if variant else name
    view = hero_view(c) if view in ("", "hero") else view
    look = variant.look if variant else c.look  # a variant's look is whole (0028)
    return {"what": f"{c.name}, {c.noun}: {view} view", "look": look}


def _place(p: FramePlace, name: str) -> dict[str, str]:
    states = {s.id: s for s in p.states}
    view, _, state_id = ("wide", "", name) if name in states else name.partition("-")
    state = states.get(state_id)
    look = state.look if state else f"{p.look} {p.light}"  # a state's look is whole (0028)
    return {"what": f"{p.name}: {view} view" + (f", {state.id}" if state else ""), "look": look}


def describe(bible: Bible, item_id: str) -> dict[str, str]:
    """What a picture shows, for the prompt writers: who or what, the view, and the look to keep."""
    subject, _, name = item_id.partition(".")
    character = next((c for c in bible.characters if c.id == subject), None)
    if character is not None:
        return _character(character, name)
    place = next((p for p in bible.places if p.id == subject), None)
    if place is not None:
        return _place(place, name)
    thing = next((o for o in bible.objects if o.id == subject), None)
    return {"what": thing.name, "look": thing.look} if thing else {"what": item_id, "look": ""}


def _numbered(bible: Bible, refs: list[str]) -> list[dict[str, Any]]:
    return [{"image": n, "id": r, **describe(bible, r)} for n, r in enumerate(refs, 1)]


# ------------------------------------------------------------------------------ the image models


@dataclass(frozen=True)
class Choice:
    """The project's image models (0027): the first is `[defaults] model`; when there are several, a
    picture may name another (Hone Frame's per-item `model`)."""

    models: tuple[ImageInfo, ...] = ()

    def data(self) -> list[dict[str, Any]]:
        """What the prompt writers are told of the models; nothing when there is one."""
        if len(self.models) < 2:
            return []
        keep = ("id", "max_references", "license", "commercial_use")
        return [{k: getattr(m, k) for k in keep} for m in self.models]

    def problems(self, where: str, model: str, pictures: int) -> list[Problem]:
        if not model or len(self.models) < 2:
            return []
        found = next((m for m in self.models if m.id == model), None)
        if found is None:
            known = ", ".join(m.id for m in self.models)
            return [Problem(rule="frame-model", where=where, message=f"names {model!r}; the models: {known}")]
        if found.max_references is not None and pictures > found.max_references:
            why = f"{model} takes {found.max_references} pictures, this has {pictures}: choose another"
            return [Problem(rule="frame-model", where=where, message=why)]
        return []

    def chosen(self, model: str, pictures: int) -> str:
        """The item's own model: one of the others that takes its pictures, else "" (the default)."""
        ok = len(self.models) > 1 and model != self.models[0].id and not self.problems("", model, pictures)
        return model if model and ok else ""


ONE = Choice()  # one model: `[defaults] model` everywhere


# ------------------------------------------------------------------------------ call 3: the subjects


def _subject_data(
    bible: Bible, group: str, items: list[FrameItem], shots: dict[str, FrameShot], choice: Choice
) -> dict[str, Any]:
    entries = {"characters": bible.characters, "objects": bible.objects, "places": bible.places}[group]
    subject = next(s for s in entries if s.id == items[0].subject)
    others = [
        {"name": c.name, "noun": c.noun, "look": c.look} for c in bible.characters if c.id != subject.id
    ]
    return {
        "kind": bible.kind,
        "finish": bible.finish,
        "world": bible.world,
        "reference_light": bible.reference_light,
        "subject": subject.model_dump(mode="json"),
        "others": others if group == "characters" else [],
        "items": [
            {
                "id": i.id,
                "role": i.role,
                "refs": _numbered(bible, i.refs),
                "size": i.size,
                "uses": [shots[s].beat for s in i.uses[:6] if s in shots],
            }
            for i in items
        ],
    } | ({"models": choice.data()} if choice.data() else {})


def _item_check(items: list[FrameItem], choice: Choice) -> Callable[[ItemPrompts], list[Problem]]:
    wanted = {i.id: i for i in items}

    def check(reply: ItemPrompts) -> list[Problem]:
        got = {p.id: p for p in reply.items}
        found = [_missing(i, "prompt") for i in wanted if i not in got]
        for item_id, written in got.items():
            if item_id in wanted:
                pictures = len(wanted[item_id].refs)
                found += prompt_problems(item_id, written.prompt, pictures)
                found += choice.problems(item_id, written.model, pictures)
        return found

    return check


def _fallback_item(bible: Bible, item: FrameItem) -> str:
    """A prompt written by code when the planner gave none: the kind, the role, the look, the light."""
    look = describe(bible, item.id)["look"]
    light = "" if item.group == "places" else f" {bible.reference_light}"
    ref = " Image 1 is the picture it is made from: the same subject." if item.refs else ""
    return f"{bible.kind} {item.role[0].upper()}{item.role[1:]}.{ref} {look}{light} {bible.finish}".strip()


def subject_prompts(
    planner: Planner, bible: Bible, items: list[FrameItem], shots: list[FrameShot], choice: Choice = ONE
) -> list[Problem]:
    """Call 3: one call per subject with the pictures it needs; each item's `prompts` is set (a given
    picture is not written). What is still wrong is returned."""
    by_id = {s.id: s for s in shots}
    groups: dict[str, list[FrameItem]] = {}
    for item in items:
        if item.file is None:
            groups.setdefault(item.subject, []).append(item)

    def one(subject_items: list[FrameItem]) -> list[Problem]:
        group = subject_items[0].group
        text = system("frame_assets", guides=GUIDES[group], until=RECIPE_END)
        data = _subject_data(bible, group, subject_items, by_id, choice)
        label = f"subject-{subject_items[0].subject}"
        check = _item_check(subject_items, choice)
        reply, problems = planner.call(label, text, data, ItemPrompts, check=check, repairs=SUBJECT_REPAIRS)
        got = {p.id: p for p in reply.items}
        for item in subject_items:
            written = got.get(item.id)
            item.prompts = [
                written.prompt if written and written.prompt.strip() else _fallback_item(bible, item)
            ]
            item.model = choice.chosen(written.model, len(item.refs)) if written else ""
        return problems

    with ThreadPoolExecutor(CALLS_AT_ONCE) as pool:
        return [p for found in pool.map(one, groups.values()) for p in found]


# ------------------------------------------------------------------------------ call 4: the scenes


def _scene_refs(bible: Bible, shots: list[FrameShot], shot: FrameShot) -> list[dict[str, Any]]:
    """A scene's numbered pictures; a scene made from a scene has that scene's picked picture (0027)."""
    if not shot.from_scene:
        return _numbered(bible, scene_refs(bible, shot))
    source = next((s for s in shots if s.id == shot.from_scene), None)
    what = f"the picked picture of shot {shot.from_scene}"
    return [{"image": 1, "id": shot.from_scene, "what": what, "look": source.beat if source else ""}]


@dataclass(frozen=True)
class Context:
    """What every scene of the video shares besides the bible (0028): the sung lines by id, the song's
    parts in time order (`music.parts`), the shot list's setups by id."""

    lines: dict[str, str]
    parts: tuple[tuple[int, str], ...] = ()  # (start_ms, part id)
    setups: dict[str, str] | None = None


def _arc_of(bible: Bible, context: Context, start_ms: int) -> dict[str, Any] | None:
    """The arc's entry for the part of the song a shot starts in."""
    part = next((p for at, p in reversed(context.parts) if at <= start_ms), None)
    found = next((a for a in bible.arc if a.part == part), None)
    return found.model_dump(mode="json") if found else None


def _people(bible: Bible, shot: FrameShot) -> list[dict[str, str]]:
    """The cast's presence and inner life, for the performance (0028)."""
    cast = {u.character for u in shot.cast}
    return [
        {"who": f"{c.name}, {c.noun}", "presence": c.presence, "inner": c.inner}
        for c in bible.characters
        if c.id in cast and (c.presence or c.inner)
    ]


def _place_words(bible: Bible, shot: FrameShot) -> list[dict[str, str]]:
    """The place of a shot that has it in words, not as a picture (0029 §3): its look, light and state."""
    place = next((p for p in bible.places if shot.place and p.id == shot.place.place), None)
    if place is None or not shot.place_in_words or shot.place is None:
        return []
    state = next((s.look for s in place.states if s.id == shot.place.state), "")
    light = place.light if place.light.endswith(".") else f"{place.light}."
    look = " ".join(w for w in (place.look, f"{light[0].upper()}{light[1:]}", state) if w)
    return [{"what": place.name, "look": look}]


def _shot_data(bible: Bible, shots: list[FrameShot], n: int, context: Context) -> dict[str, Any]:
    shot = shots[n]
    refs = scene_refs(bible, shot)
    left = [o for o in shot.objects if f"{o}.hero" not in refs]
    words = _place_words(bible, shot) + [
        {"what": o.name, "look": o.look} for o in bible.objects if o.id in left
    ]
    before = shots[n - 1] if n > 0 else None
    return {
        "id": shot.id,
        "duration_ms": shot.end_ms - shot.start_ms,
        "beat": shot.beat,
        "motion": shot.motion,
        "feel": shot.feel,
        "evidence": shot.evidence,
        "arc": _arc_of(bible, context, shot.start_ms),
        "people": _people(bible, shot),
        "lines": [context.lines[i] for i in shot.lines if i in context.lines],
        "focus": focus_of(shot),
        "framing": shot.framing,
        "faces": shot.faces,
        "camera": shot.camera,
        "light": shot.light,
        "takes": shot.takes,
        "from_scene": shot.from_scene or None,
        "setup": (context.setups or {}).get(shot.setup) if shot.setup else None,
        "refs": _scene_refs(bible, shots, shot),
        "in_words": words,
        "before": (before.ends or before.beat) if before else None,
        "after": shots[n + 1].beat if n + 1 < len(shots) else None,
    }


def scene_problems(bible: Bible, shot: FrameShot, scene: ScenePrompt) -> list[Problem]:
    """A scene's prompts checked (the kind first, every picture named and no other, no words of a render,
    the length), as many as the shot asks (two or three for a hard one), its facts written and each
    link's ends named in every prompt (0029 §1), and its motion prompt (written, not too long, no word
    of speech or of the mouth)."""
    pictures = len(scene_refs(bible, shot))
    found: list[Problem] = []
    many = shot.takes == "prompts"
    if not scene.prompts or len(scene.prompts) > 3 or many != (len(scene.prompts) > 1):
        want = "two or three different shots" if many else "one prompt"
        found.append(
            Problem(rule="frame-prompts", where=shot.id, message=f"has {len(scene.prompts)}; write {want}")
        )
    for prompt in scene.prompts:
        found += prompt_problems(shot.id, prompt, pictures, starts=bible.kind)
    found += [Problem(rule="frame-facts", where=shot.id, message=m) for m in facts_problems(scene)]
    why = _motion_problem(scene.motion_prompt)
    return found + ([Problem(rule="frame-motion", where=shot.id, message=why)] if why else [])


def _motion_problem(motion: str) -> str:
    said = words_of_speech(motion, motion=True)
    if not motion.strip():
        return "the motion prompt is empty"
    if len(motion) > MOTION_CHARS:
        return f"the motion prompt has {len(motion)} characters, over {MOTION_CHARS}"
    if said:
        return f"the motion prompt names {', '.join(map(repr, said))}: never the mouth or speech, nor negated"
    return ""


def _missing(where: str, what: str) -> Problem:
    return Problem(rule="missing", where=where, message=f"no {what} was written")


def _fallback_scene(bible: Bible, shot: FrameShot) -> ScenePrompt:
    """A scene written by code when the planner gave none: the kind, each picture's role, the beat."""
    pictures = _numbered(bible, scene_refs(bible, shot))
    roles = " ".join(f"{d['what']} is image {d['image']}." for d in pictures)
    prompt = f"{bible.kind} {roles} {shot.beat} A {shot.framing} shot. {shot.light}. {bible.finish}"
    return ScenePrompt(
        id=shot.id,
        prompts=[" ".join(prompt.split())],
        motion_prompt=f"{shot.camera.capitalize()}. {shot.motion}".strip(),
    )


def scene_prompts(  # noqa: PLR0917 - the scene call's inputs
    planner: Planner,
    bible: Bible,
    shots: list[FrameShot],
    context: Context,
    mood: str | None,
    choice: Choice = ONE,
) -> tuple[dict[str, ScenePrompt], list[Problem]]:
    """Call 4: the scenes, `SCENES_PER_CALL` shots a call; every shot gets its scene."""
    by_id = {s.id: s for s in shots}
    text = system("frame_scenes", guides=("scenes", "models"), limits=True)

    def one(start: int) -> tuple[list[ScenePrompt], list[Problem]]:
        batch = range(start, min(start + SCENES_PER_CALL, len(shots)))
        data = {
            "kind": bible.kind, "finish": bible.finish, "world": bible.world, "mood": mood,
            "feeling": bible.feeling,
            "shots": [_shot_data(bible, shots, n, context) for n in batch],
        } | ({"models": choice.data()} if choice.data() else {})  # fmt: skip
        ids = {shots[n].id for n in batch}

        def check(reply: ScenePrompts) -> list[Problem]:
            got = {s.id: s for s in reply.scenes if s.id in ids}
            found = [_missing(i, "scene") for i in ids if i not in got]
            pictures = {i: len(scene_refs(bible, by_id[i])) for i in got}
            found += [p for s in got.values() for p in choice.problems(s.id, s.model, pictures[s.id])]
            return found + [p for s in got.values() for p in scene_problems(bible, by_id[s.id], s)]

        label = f"scenes-{shots[start].id}"
        reply, problems = planner.call(label, text, data, ScenePrompts, check=check)
        scenes = [s for s in reply.scenes if s.id in ids]
        return scenes, problems + [p for s in scenes for p in scene_warnings(s)]

    found: dict[str, ScenePrompt] = {}
    problems: list[Problem] = []
    with ThreadPoolExecutor(CALLS_AT_ONCE) as pool:
        for scenes, wrong in pool.map(one, range(0, len(shots), SCENES_PER_CALL)):
            found |= {s.id: s for s in scenes}
            problems += wrong
    for shot in shots:
        found.setdefault(shot.id, _fallback_scene(bible, shot))
    return found, problems


__all__ = [
    "MAX_SCENE_REFS",
    "Context",
    "describe",
    "scene_problems",
    "scene_prompts",
    "scene_warnings",
    "subject_prompts",
]
