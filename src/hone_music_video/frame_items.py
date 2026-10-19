"""The items of a frame plan (0026), worked out by code from the bible and the shot list: which pictures
each character, object and place needs, their ids, sizes, seeds and references, and each scene's
references in order. No model is called here.

The items follow Hone Frame's guide: a character's hero (the whole figure from the front; an animal's
from the side) on the reference backdrop, then the views, close-ups and variants the shots use, each made
from the hero; an object's hero; a place's wide view empty of people, then its other views and states.
A scene's references are the place's view matching the camera first (the model edits image 1, 0034 §1),
then one picture per character (the view the shot sees, a close-up or an expression in a face shot), then
the objects; a wide shot without faces has its people in words (0034 §2)."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass, field

from hone_music_video._files import slug
from hone_music_video.records import Problem
from hone_music_video.records_frame import (
    Bible,
    CastUse,
    CharacterView,
    FrameCharacter,
    FrameItem,
    FrameShot,
    FrameVariant,
    Group,
    PlaceUse,
    PlaceView,
    Pose,
)

MAX_SCENE_REFS = 4  # three to five references drew a character twice most often (stress tests 2026-10-14)
# the scene sizes, each one Hone Frame accepts for Qwen-Image 2.1 Turbo (near its trained size but 4:5)
SCENE_SIZES = {"16:9": "1664x928", "9:16": "928x1664", "1:1": "1328x1328", "4:5": "704x880"}
PERSON_SIZE, ANIMAL_SIZE, SQUARE = "832x1248", "1536x1024", "1024x1024"
FACE_FRAMINGS = ("medium", "close-up", "extreme-close-up")
WIDE_FRAMINGS = ("wide", "extreme-wide")  # without faces: the people in words, no picture of them (0034 §2)
MASTER_FRAMINGS = ("wide", "medium")  # the first shot of a setup shows the whole arrangement (0034 §4)
MAX_EXPRESSIONS = 4
BODY_VIEWS: tuple[CharacterView, ...] = ("three-quarter", "side", "back", "front")
PLACE_VIEWS: tuple[PlaceView, ...] = ("wide", "reverse", "high", "low", "close")
VIEW_WORDS = {
    "three-quarter": "in a three-quarter view, turned halfway, the whole figure",
    "side": "in exact side profile, the whole figure",
    "back": "seen from directly behind, the whole figure",
    "front": "seen from the front, the whole figure",
}
PLACE_WORDS = {
    "reverse": "the same place seen from the opposite side, looking back to where the first camera stood",
    "high": "the same place seen from high above, looking down",
    "low": "the same place seen from low near the ground, looking up",
    "close": "a closer view of the part of the place the shots that use it show",
}
HERO_ROLES = {
    "person": "the hero: one full-length picture of the whole figure from the front, in a neutral pose",
    "other": "the hero: the whole body in full side view, standing square, all of it in the frame",
}
CLOSE_ROLE = "the neutral close-up made from image 1: head and shoulders fill the frame, a calm face"
EXPRESSION_ROLE = "an expression made from the neutral close-up, image 1: {face}; the same face, head and \
shoulders filling the frame"
# a pose picture made in words from the look's picture (0028; Hone Frame's guide, Poses), and its size
POSE_WORDS = {
    "sitting": "sitting, the whole figure, as the shots that use it need",
    "lying": "lying down, the whole figure, as the shots that use it need (on the back, side or front)",
    "kneeling": "kneeling, the whole figure, as the shots that use it need",
}
POSE_SIZES = {"sitting": PERSON_SIZE, "lying": ANIMAL_SIZE, "kneeling": PERSON_SIZE}


def seed_of(project_id: str, item_id: str) -> int:
    """Hone Frame's seed of an item without one: sha256 of `<project id>:<item id>` (its D-046)."""
    return int(hashlib.sha256(f"{project_id}:{item_id}".encode()).hexdigest()[:8], 16)


def _unique(ids: Iterable[str], fallback: str) -> list[str]:
    seen: list[str] = []
    for raw in ids:
        name = base = slug(raw, fallback)
        n = 2
        while name in seen:
            name, n = f"{base}-{n}", n + 1
        seen.append(name)
    return seen


def normalized(bible: Bible) -> Bible:
    """The bible with every id a safe name (lower-case letters, digits, dashes) used once: the subjects
    share one namespace in Hone Frame; a character's variants and a place's states their own."""
    subjects = [*bible.characters, *bible.objects, *bible.places]
    for subject, name in zip(subjects, _unique((s.id for s in subjects), "subject"), strict=True):
        subject.id = name
    for character in bible.characters:
        names = _unique((v.id for v in character.variants), "look")
        for variant, name in zip(character.variants, names, strict=True):
            variant.id = name
        faces = _unique((e.id for e in character.expressions), "face")
        for expression, name in zip(character.expressions, faces, strict=True):
            expression.id = name
    for place in bible.places:
        for state, name in zip(place.states, _unique((s.id for s in place.states), "state"), strict=True):
            state.id = name
    return bible


def hero_view(character: FrameCharacter) -> CharacterView:
    """The side a character's hero shows: a person's front, an animal's or a creature's side."""
    return "front" if character.kind == "person" else "side"


def character_item(character: FrameCharacter, use: CastUse) -> str:
    """The id of the picture a shot gets of a character: its hero, a view, its close-up or an expression
    (`<look>-close-<expression>`, 0034), a variant, a pose (`<look>-lying`) or a detail
    (`<look>-detail-<part>`, 0028); a pose wins over a body view."""
    base = f"{character.id}.{use.variant}" if use.variant else f"{character.id}.hero"
    prefix = f"{character.id}.{use.variant}-" if use.variant else f"{character.id}."
    if use.view == "detail":
        return f"{prefix}detail-{slug(use.part, 'part')}"
    if use.view == "close" and use.expression:
        return f"{prefix}close-{slug(use.expression, 'face')}"
    if use.pose and use.view != "close":
        return f"{prefix}{use.pose}"
    if use.view == hero_view(character):
        return base
    return f"{prefix}{use.view}"


def place_item(use: PlaceUse) -> str:
    """A place's picture: `<place>.wide` (the hero), `<place>.<state>` (the hero's camera in a state),
    `<place>.<view>`, `<place>.<view>-<state>`."""
    if use.view == "wide":
        return f"{use.place}.{use.state or 'wide'}"
    return f"{use.place}.{use.view}-{use.state}" if use.state else f"{use.place}.{use.view}"


def object_item(object_id: str) -> str:
    return f"{object_id}.hero"


def people_in_words(shot: FrameShot) -> bool:
    """A wide shot without faces: its people are words in the scene, never pictures (0034 §2); a shot
    that wants its place in words keeps its characters (0029 §3)."""
    return not shot.faces and shot.framing in WIDE_FRAMINGS and not shot.place_in_words


def scene_refs(bible: Bible, shot: FrameShot, limit: int = MAX_SCENE_REFS) -> list[str]:
    """A scene's references in order: the place's view first, the picture the model edits (0034 §1;
    none when the shot wants the place in words, 0029 §3), each character's picture (none in a wide
    shot without faces, 0034 §2), the objects; the objects past `limit` are left to the words. A scene
    made from a scene has that scene only (0027; Hone Frame's guide, "A scene made from another
    scene")."""
    if shot.from_scene:
        return [shot.from_scene]
    characters = {c.id: c for c in bible.characters}
    refs = [place_item(shot.place)] if shot.place and not shot.place_in_words else []
    if not people_in_words(shot):
        refs += [character_item(characters[u.character], u) for u in shot.cast if u.character in characters]
    kept = len(dict.fromkeys(refs))
    refs += [object_item(o) for o in shot.objects]
    return list(dict.fromkeys(refs))[: max(limit, kept)]


# ------------------------------------------------------------------------------ the shot list checked


def _cast_problems(bible: Bible, shot: FrameShot) -> list[str]:
    characters = {c.id: c for c in bible.characters}
    found: list[str] = []
    for use in shot.cast:
        character = characters.get(use.character)
        if character is None:
            known = ", ".join(characters) or "none"
            found.append(f"names {use.character!r}, who is not a character of the bible ({known})")
            continue
        variants = [v.id for v in character.variants] or ["none"]
        if use.variant and use.variant not in variants:
            found.append(f"gives {use.character} the variant {use.variant!r}; theirs: {', '.join(variants)}")
        if use.view == "close" and shot.framing not in FACE_FRAMINGS:
            found.append(f"uses {use.character}'s close-up in a {shot.framing} shot; give a full-body view")
        if use.view == "detail" and not use.part.strip():
            found.append(f"uses a detail of {use.character} without its `part`: name the part it shows")
        found += _expression_problems(character, use)
    who = [u.character for u in shot.cast]
    found += [f"names {c} twice: one picture per character" for c in dict.fromkeys(who) if who.count(c) > 1]
    return found


def _expression_problems(character: FrameCharacter, use: CastUse) -> list[str]:
    """An expression on a view that is not a close-up, or one the bible does not give the character."""
    if not use.expression:
        return []
    if use.view != "close":
        return [f"gives {use.character} the expression {use.expression!r} on a {use.view} view: only a close"]
    known = [e.id for e in character.expressions]
    if use.expression not in known:
        theirs = ", ".join(known) or "none"
        return [f"gives {use.character} the expression {use.expression!r}; theirs: {theirs}"]
    return []


def _place_problems(bible: Bible, shot: FrameShot) -> list[str]:
    places, objects = {p.id: p for p in bible.places}, {o.id for o in bible.objects}
    found = [f"shows {o!r}, which is not an object of the bible" for o in shot.objects if o not in objects]
    if shot.place is None:
        return found
    place = places.get(shot.place.place)
    if place is None:
        known = ", ".join(places) or "none"
        return [*found, f"is in {shot.place.place!r}, which is not a place of the bible ({known})"]
    states = [s.id for s in place.states] or ["none"]
    if shot.place.state and shot.place.state not in states:
        found.append(f"gives {place.id} the state {shot.place.state!r}; its states: {', '.join(states)}")
    return found


def _feeling_problems(shot: FrameShot, setups: set[str]) -> list[str]:
    """A shot without what it should make the viewer feel, its evidence or its motion (0028), or with a
    setup the list does not declare."""
    empty = [k for k in ("feel", "evidence", "motion") if not getattr(shot, k).strip()]
    found = [f"has no `{k}`: write it" for k in empty]
    if shot.setup and shot.setup not in setups:
        found.append(f"names the setup {shot.setup!r}, which `setups` does not declare")
    return found


def shot_problems(
    bible: Bible, shots: list[FrameShot], limit: int = MAX_SCENE_REFS, setups: Iterable[str] = ()
) -> list[Problem]:
    """What a shot list names that the bible does not have, scenes with more pictures than `limit` for
    their people and place (objects past it are left to the words), a scene made from a scene that is
    not an earlier one, a shot without its feeling, evidence or motion (0028), an expression the bible
    lacks, and a setup whose first shot is not its master (0034)."""
    found: list[Problem] = []
    declared = set(setups)
    opened: set[str] = set()
    for n, shot in enumerate(shots):
        why = _cast_problems(bible, shot) + _place_problems(bible, shot) + _feeling_problems(shot, declared)
        earlier = {s.id for s in shots[:n]}
        if shot.from_scene and shot.from_scene not in earlier:
            why.append(f"is made from {shot.from_scene!r}, which is not an earlier shot")
        if shot.setup and shot.setup not in opened:
            opened.add(shot.setup)
            if shot.framing not in MASTER_FRAMINGS:
                why.append(f"opens the setup {shot.setup!r} as a {shot.framing} shot: its master, the "
                           "first shot of a setup, shows the whole arrangement, wide or medium")  # fmt: skip
        cast = 0 if people_in_words(shot) else len(shot.cast)
        pictures = cast + (shot.place is not None and not shot.place_in_words)
        if pictures > limit:
            why.append(f"needs {pictures} pictures for its people and place, more than {limit}: show fewer")
        found += [Problem(rule="frame-shot", where=shot.id, message=m) for m in why]
    return found


# ------------------------------------------------------------------------------ the asset items


@dataclass(frozen=True)
class Assets:
    """What the asset items are made for: the project (for the seeds), the scenes' size, every picture
    the scenes use with the shots that use it, and the owner's pose pictures by name (0027)."""

    project_id: str
    scene_size: str
    used: dict[str, list[str]]
    poses: dict[str, str] = field(default_factory=dict[str, str])
    parts: dict[str, str] = field(default_factory=dict[str, str])  # a detail item's part, in words (0028)

    def item(self, group: Group, item_id: str, role: str, *, size: str, refs: list[str]) -> FrameItem:
        subject, _, name = item_id.partition(".")
        return FrameItem(
            id=item_id, group=group, subject=subject, name=name, role=role, size=size,
            seed=seed_of(self.project_id, item_id), refs=refs, uses=self.used.get(item_id, []),
            hold=name == "hero" or (group == "places" and name == "wide"),
        )  # fmt: skip

    def uses_any(self, prefix: str) -> bool:
        return any(k == prefix or k.startswith(f"{prefix}-") for k in self.used)


def _uses(bible: Bible, shots: list[FrameShot]) -> dict[str, list[str]]:
    """Each picture the scenes use, with the shots that use it."""
    used: dict[str, list[str]] = {}
    for shot in shots:
        for ref in scene_refs(bible, shot, limit=99):
            used.setdefault(ref, []).append(shot.id)
    return used


def _parts(bible: Bible, shots: list[FrameShot]) -> dict[str, str]:
    """Each detail picture the shots use, with the part it shows in words (0028)."""
    characters = {c.id: c for c in bible.characters}
    return {
        character_item(characters[u.character], u): u.part.strip()
        for s in shots
        for u in s.cast
        if u.view == "detail" and u.character in characters
    }


def _look_items(a: Assets, c: FrameCharacter, variant: str, parent: str, size: str) -> list[FrameItem]:
    """The views, close-up, poses and details of one look of a character (the hero's or a variant's) the
    shots use, each made from the look's picture."""
    items: list[FrameItem] = []
    for view in BODY_VIEWS:
        item_id = character_item(c, CastUse(character=c.id, variant=variant, view=view))
        if item_id != parent and item_id in a.used:
            role = f"a view made from image 1: {VIEW_WORDS[view]}"
            items.append(a.item("characters", item_id, role, size=size, refs=[parent]))
    close = character_item(c, CastUse(character=c.id, variant=variant, view="close"))
    faces = [
        (character_item(c, CastUse(character=c.id, variant=variant, view="close", expression=e.id)), e.face)
        for e in c.expressions
    ]
    faces = [(item_id, face) for item_id, face in faces if item_id in a.used]
    if close in a.used or faces:
        items.append(a.item("characters", close, CLOSE_ROLE, size=SQUARE, refs=[parent]))
    for item_id, face in faces:
        role = EXPRESSION_ROLE.format(face=face)
        items.append(a.item("characters", item_id, role, size=SQUARE, refs=[close]))
    poses: tuple[Pose, ...] = ("sitting", "lying", "kneeling")
    for pose in poses:
        item_id = character_item(c, CastUse(character=c.id, variant=variant, pose=pose))
        if item_id in a.used:
            role = f"a pose made from image 1: {POSE_WORDS[pose]}; the same look, every garment kept"
            items.append(a.item("characters", item_id, role, size=POSE_SIZES[pose], refs=[parent]))
    prefix = f"{c.id}.{variant}-detail-" if variant else f"{c.id}.detail-"
    for item_id, part in a.parts.items():
        if item_id.startswith(prefix) and item_id in a.used:
            role = f"a close detail made from image 1: {part} fills the frame; the same look"
            items.append(a.item("characters", item_id, role, size=SQUARE, refs=[parent]))
    return items


def _character_items(a: Assets, c: FrameCharacter) -> list[FrameItem]:
    size = PERSON_SIZE if c.kind == "person" else ANIMAL_SIZE
    hero_role = HERO_ROLES["person" if c.kind == "person" else "other"] + ", alone on the reference backdrop"
    hero = f"{c.id}.hero"
    items = [a.item("characters", hero, hero_role, size=size, refs=[])]
    items += _look_items(a, c, "", hero, size)
    for v in c.variants:
        parent = f"{c.id}.{v.id}"
        if a.uses_any(parent):
            items += _variant_items(a, c, v, size)
            items += _look_items(a, c, v.id, parent, size)
    return items


def _variant_items(a: Assets, c: FrameCharacter, v: FrameVariant, size: str) -> list[FrameItem]:
    """A variant made from the hero; with a given pose picture, that picture first as an item with `file`
    and then as the variant's image 2 (Hone Frame's guide, Poses: "With a pose picture of your own")."""
    hero, parent = f"{c.id}.hero", f"{c.id}.{v.id}"
    role = f"the variant {v.id!r} made from image 1: {v.look}; the whole figure, as the hero shows it"
    pose = a.poses.get(v.pose) if v.pose else None
    if pose is None:
        return [a.item("characters", parent, role, size=size, refs=[hero])]
    pose_id = f"{c.id}.{v.id}-pose"
    given = a.item("characters", pose_id, f"the owner's pose picture {v.pose!r}", size=size, refs=[])
    given.file, given.hold = pose, False
    role += "; image 2 is only a pose guide: the body pose of the figure in it, nothing else of it"
    return [given, a.item("characters", parent, role, size=size, refs=[hero, pose_id])]


def _place_items(a: Assets, place: str, states: list[str]) -> list[FrameItem]:
    wide = f"{place}.wide"
    role = "the place hero: a wide view of the whole place from its main viewpoint at eye level, empty"
    items = [a.item("places", wide, role, size=a.scene_size, refs=[])]
    for view in PLACE_VIEWS[1:]:
        view_id = place_item(PlaceUse(place=place, view=view))
        if a.uses_any(view_id):
            role = f"{PLACE_WORDS[view]}, made from image 1; empty"
            items.append(a.item("places", view_id, role, size=a.scene_size, refs=[wide]))
    for state in states:
        for view in PLACE_VIEWS:
            state_id = place_item(PlaceUse(place=place, view=view, state=state))
            if state_id in a.used:
                role = f"the same view as image 1, from the same camera, in the state {state!r}; empty"
                parent = place_item(PlaceUse(place=place, view=view))
                items.append(a.item("places", state_id, role, size=a.scene_size, refs=[parent]))
    return items


def asset_items(
    project_id: str,
    bible: Bible,
    shots: list[FrameShot],
    scene_size: str,
    poses: dict[str, str] | None = None,
) -> list[FrameItem]:
    """Every picture the scenes need, in file order (characters, objects, places), each after the
    pictures it is made from; a subject no shot uses gets none. The heroes and the places' wide views
    hold, as Hone Frame's guide asks: everything of the subject is made from them."""
    a = Assets(project_id, scene_size, _uses(bible, shots), dict(poses or {}), _parts(bible, shots))
    items: list[FrameItem] = []
    for c in bible.characters:
        if any(k.startswith(f"{c.id}.") for k in a.used):
            items += _character_items(a, c)
    for o in bible.objects:
        if object_item(o.id) in a.used:
            role = "the object hero: the object alone and whole, on the reference backdrop"
            items.append(a.item("objects", object_item(o.id), role, size=SQUARE, refs=[]))
    for p in bible.places:
        if any(k.startswith(f"{p.id}.") for k in a.used):
            items += _place_items(a, p.id, [s.id for s in p.states])
    return items
