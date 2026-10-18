"""The frame planner (0026): a song's pictures planned the way Hone Frame's guide asks, in several calls.

1. **The bible** (one call): the story read, what the video should make the viewer feel and its arc over
   the song's parts (measured by `music`, with the lyrics' notes and the owner's feeling, 0028), the kind
   of picture every scene begins with, the closing style words, the world, the reference backdrop, a
   demo, and every character (its whole visible look, presence, inner life and variants), object and
   place (its layout, light and states).
2. **The shot list** (one call, repaired up to twice, then read by the review call and repaired once
   more with its notes, `frame_review`): the shots that tile the song, each with its opening frame, its
   motion, what it leaves, what the viewer should feel and the evidence, framing, camera, light, and which
   picture of each character, place and object it uses. No prompts, so the reply is short;
   `check_shots`, the bible and the camera's variety check it.
3. **The pictures** (code): the items each subject needs (`frame_items`).
4. **The subjects' prompts** (one call per subject) and **the scenes** (one call per six shots), side by
   side (`frame_prompts`).

Every reply is kept as it returns (`frame_calls`), so a plan made again calls only for what it lacks.
The plan is `current/frame/plan.json`, and its items are `current/frame/project.toml`, a Hone Frame
project file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hone_music_video import music
from hone_music_video._jobs import Job
from hone_music_video.frame_calls import RENDER_WORDS, Planner, system
from hone_music_video.frame_items import (
    MAX_SCENE_REFS,
    SCENE_SIZES,
    asset_items,
    normalized,
    scene_refs,
    seed_of,
    shot_problems,
)
from hone_music_video.frame_prompts import Choice, Context, scene_prompts, subject_prompts
from hone_music_video.frame_review import arc_problems, camera_problems, review_shots
from hone_music_video.pace import shot_range
from hone_music_video.project import StoredSheet
from hone_music_video.records import Problem, Shot, Shots, Timeline
from hone_music_video.records_frame import (
    Bible,
    FrameItem,
    FramePlan,
    FrameShot,
    ScenePrompt,
    ShotList,
)
from hone_music_video.settings import Settings
from hone_music_video.shots_check import check_shots
from hone_music_video.stages_plan import timeline_data

SHOT_REPAIRS = 2


@dataclass(frozen=True)
class Inputs:
    """What the planner reads: the approved timeline, the owner's story and pictures, a note."""

    timeline: Timeline
    story: str
    given: list[StoredSheet]
    note: str = ""
    poses: list[StoredSheet] = field(default_factory=list[StoredSheet])  # pose pictures by name (0027)
    feeling: str = ""  # what the owner wants the viewer to feel (0028)


def folder(job: Job) -> Path:
    """`<project>/frame/`: the frame workspace, the planner's calls (`calls/`) and the shots' sidecar."""
    return job.project.root / "frame"


# ------------------------------------------------------------------------------ 1: the bible


def _lyrics(timeline: Timeline) -> dict[str, Any]:
    sections = [
        {"section": s.id, "kind": s.kind, "lines": [ln.text for ln in timeline.lines if ln.section == s.id]}
        for s in timeline.sections
    ]
    spans = [{"kind": i.kind, "ms": i.end_ms - i.start_ms} for i in timeline.instrumental]
    return {"lyrics": sections, "instrumental": spans, "duration_ms": timeline.duration_ms}


def bible_problems(bible: Bible, given: list[str]) -> list[Problem]:
    """A bible without the kind of picture, with a demo of other than three to six prompts, words of a
    render in its shared words, a subject without its look, or a given picture it does not have."""
    found: list[str] = []
    if not bible.kind.strip():
        found.append("`kind` is empty: write the kind of picture as one sentence")
    if not 3 <= len(bible.demo) <= 6:
        found.append(f"`demo` has {len(bible.demo)} prompts; write three to six")
    for name, text in (("kind", bible.kind), ("finish", bible.finish), *(("demo", d) for d in bible.demo)):
        words = sorted({w.lower() for w in RENDER_WORDS.findall(text)})
        if words:
            found.append(f"`{name}` uses {', '.join(map(repr, words))}: words of a render")
    subjects = [*bible.characters, *bible.objects, *bible.places]
    found += [f"{s.id} has no look: describe what is seen" for s in subjects if not s.look.strip()]
    found += [f"{s.id} names the given picture {s.given!r}; the given pictures are {given or 'none'}"
              for s in subjects if s.given and s.given not in given]  # fmt: skip
    return [Problem(rule="frame-bible", where="bible", message=m) for m in found]


def song_shape(job: Job, timeline: Timeline) -> list[dict[str, Any]]:
    """The song's parts measured (`music.shape`), with the first listen's vocals when they are kept."""
    vocals = sorted(job.project.vocals_dir.glob(f"{job.settings.models.vocals}-*.wav"))
    return music.shape(timeline, job.project.path(job.project.record().inputs.song), next(iter(vocals), None))


def plan_bible(planner: Planner, inputs: Inputs, shape: list[dict[str, Any]]) -> tuple[Bible, list[Problem]]:
    """Call 1, with the owner's pictures attached in order."""
    settings = planner.job.settings
    data: dict[str, Any] = _lyrics(inputs.timeline) | {
        "music": shape,
        "story": inputs.story,
        "feeling": inputs.feeling,
        "settings": {"style": settings.style, "mood": settings.mood, "aspect_ratio": settings.aspect_ratio},
        "given": [{"name": s.name, "note": s.note, "image": n} for n, s in enumerate(inputs.given, 1)],
    }
    if inputs.note:
        data["review_note"] = inputs.note
    names = [s.name for s in inputs.given]
    images = [planner.job.project.path(s.file) for s in inputs.given]
    text = system("frame_bible", guides=("hero", "objects", "places", "models"))
    parts = [p["part"] for p in shape]
    bible, problems = planner.call(
        "bible", text, data, Bible, images=images,
        check=lambda b: bible_problems(b, names) + arc_problems(b, parts),
    )  # fmt: skip
    return normalized(bible), problems


# ------------------------------------------------------------------------------ 2: the shot list


def _bible_data(bible: Bible) -> dict[str, Any]:
    keep = {"story", "world", "characters", "objects", "places", "feeling", "arc"}
    return bible.model_dump(mode="json", include=keep)


def as_shots(shots: list[FrameShot], prompts: dict[str, tuple[str, str]] | None = None) -> Shots:
    """The shot list as the video's `Shots`: the still prompt and motion prompt given per shot, else the
    beat and the camera (what `check_shots` reads of a shot list without prompts)."""
    rows = [
        Shot(
            id=s.id, start_ms=s.start_ms, end_ms=s.end_ms, lines=s.lines, beat=s.beat, framing=s.framing,
            faces=s.faces, cast=[u.character for u in s.cast], location=s.place.place if s.place else "",
            camera=s.camera, still_prompt=(prompts or {}).get(s.id, (s.beat, ""))[0],
            motion_prompt=(prompts or {}).get(s.id, ("", s.camera))[1],
        )
        for s in shots
    ]  # fmt: skip
    return Shots(shots=rows)


def numbered(reply: ShotList) -> list[FrameShot]:
    """The shots in time order, numbered S001, S002, ... (a shot id names a folder)."""
    shots = sorted(reply.shots, key=lambda s: (s.start_ms, s.end_ms))
    renamed = {shot.id: f"S{n:03d}" for n, shot in enumerate(shots, 1)}
    for shot in shots:
        shot.id = renamed[shot.id]
        shot.from_scene = renamed.get(shot.from_scene, "") if shot.from_scene else ""
    return shots


def plan_shot_list(planner: Planner, inputs: Inputs, bible: Bible) -> tuple[ShotList, list[Problem]]:
    """Call 2: the shot list, checked by `check_shots` (timing, lines, faces), against the bible and for
    the camera's variety, then read by the review call and repaired once more with its notes (0028)."""
    settings = planner.job.settings
    data: dict[str, Any] = {
        "timeline": timeline_data(inputs.timeline),
        "bible": _bible_data(bible),
        "settings": settings.for_planner(),
        "pace_shot_ms": shot_range(settings),
        "max_pictures": MAX_SCENE_REFS,
    }
    if inputs.note:
        data["review_note"] = inputs.note

    def check(reply: ShotList) -> list[Problem]:
        shots = numbered(reply.model_copy(deep=True))
        report = check_shots(as_shots(shots), inputs.timeline, [c.id for c in bible.characters], settings)
        setups = [s.id for s in reply.setups]
        return report.errors + shot_problems(bible, shots, setups=setups) + camera_problems(shots)

    text = system("frame_shots", limits=True)
    reply, problems = planner.call("shots", text, data, ShotList, check=check, repairs=SHOT_REPAIRS)
    lines = {ln.id: ln.text for ln in inputs.timeline.lines}
    notes = review_shots(planner, bible, numbered(reply.model_copy(deep=True)), lines=lines, reply=reply)
    if notes:
        again = data | {"previous_reply": reply.model_dump(mode="json")}
        again["problems"] = [p.model_dump(include={"where", "message"}) for p in [*notes, *problems]]
        reply, problems = planner.call("shots-review", text, again, ShotList, check=check)
    reply.shots = _kept_to_bible(bible, numbered(reply))
    return reply, problems


def _kept_to_bible(bible: Bible, shots: list[FrameShot]) -> list[FrameShot]:
    """What a shot names that the bible lacks is left out, so every picture a scene uses exists."""
    characters = {c.id: {v.id for v in c.variants} for c in bible.characters}
    places = {p.id: {s.id for s in p.states} for p in bible.places}
    objects = {o.id for o in bible.objects}
    for shot in shots:
        shot.cast = [u for u in shot.cast if u.character in characters]
        for use in shot.cast:
            use.variant = use.variant if use.variant in characters[use.character] else ""
        if shot.place and shot.place.place not in places:
            shot.place = None
        if shot.place and shot.place.state not in places[shot.place.place]:
            shot.place.state = ""
        shot.objects = [o for o in shot.objects if o in objects]
    return shots


# ------------------------------------------------------------------------------ the plan


def _given_files(bible: Bible, items: list[FrameItem], given: list[StoredSheet]) -> None:
    """A subject with a given picture: its hero is that file (Hone Frame's `file`), never drawn."""
    paths = {s.name: s.file for s in given}
    named = {s.id: s.given for s in [*bible.characters, *bible.objects, *bible.places] if s.given}
    for item in items:
        hero = item.name == "hero" or (item.group == "places" and item.name == "wide")
        if hero and named.get(item.subject) in paths:
            item.file, item.hold = paths[named[item.subject]], False


def _demo(project_id: str, bible: Bible, size: str) -> list[FrameItem]:
    seed = seed_of(project_id, "demo")
    return [
        FrameItem(id=f"demo.{k}", group="demo", subject="demo", name=str(k), role="demo", size=size,
                  seed=seed + k - 1, prompts=[prompt])
        for k, prompt in enumerate(bible.demo, 1)
    ]  # fmt: skip


COUNT = 3  # takes of one prompt for a shot planned `takes: "count"` (Hone Frame's guide: keep one in three)


def _scene_item(project_id: str, bible: Bible, shot: FrameShot, size: str, scene: ScenePrompt) -> FrameItem:
    return FrameItem(
        id=shot.id, group="scenes", subject=shot.id, role=shot.beat, size=size,
        seed=seed_of(project_id, shot.id), refs=scene_refs(bible, shot), prompts=scene.prompts,
        count=COUNT if shot.takes == "count" and len(scene.prompts) == 1 else 1, model=scene.model,
    )  # fmt: skip


def plan(job: Job, inputs: Inputs, *, model: str | None = None, fresh: bool = False) -> FramePlan:
    """The four steps: the bible, the shot list, the pictures each subject needs, their prompts and the
    scenes'. The plan is written as the project file by `frame_stages` (0027)."""
    settings = job.settings
    planner = Planner(job, model or settings.models.planner, folder(job) / "calls", fresh=fresh)
    shape = song_shape(job, inputs.timeline)
    bible, problems = plan_bible(planner, inputs, shape)
    shot_list, wrong = plan_shot_list(planner, inputs, bible)
    shots = shot_list.shots
    size = SCENE_SIZES[settings.aspect_ratio]
    poses = {s.name: s.file for s in inputs.poses}
    items = asset_items(job.project.id, bible, shots, size, poses)
    _given_files(bible, items, inputs.given)
    choice = Choice(tuple(job.models.image_info(m) for m in image_models(settings)))
    wrong += subject_prompts(planner, bible, items, shots, choice)
    context = Context(
        lines={ln.id: ln.text for ln in inputs.timeline.lines},
        parts=tuple((p["start_ms"], p["part"]) for p in shape),
        setups={s.id: s.layout for s in shot_list.setups},
    )
    scenes, still_wrong = scene_prompts(planner, bible, shots, context, settings.mood, choice)
    for scene in scenes.values():
        scene.model = choice.chosen(
            scene.model, len(scene_refs(bible, next(s for s in shots if s.id == scene.id)))
        )
    scene_items = [_scene_item(job.project.id, bible, s, size, scenes[s.id]) for s in shots]
    found = FramePlan(
        model=image_models(settings)[0],
        bible=bible,
        shots=shots,
        items=_demo(job.project.id, bible, size) + items + scene_items,
        motion={s.id: scenes[s.id].motion_prompt for s in shots},
        problems=[f"{p.where}: {p.message}" for p in [*problems, *wrong, *still_wrong]],
    )
    job.events.write("frame_planned", shots=len(shots), items=len(found.items), problems=len(found.problems))
    return found


def image_models(settings: Settings) -> list[str]:
    """The project's image models: `[defaults] model` first, then the others an item may name (0027)."""
    return list(dict.fromkeys(settings.models.frame))
