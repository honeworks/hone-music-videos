"""The records of the frame planner and of the scenes (changes 0026, 0027).

The planner's replies, call by call: the `Bible` (who and what is in the story, the kind of picture),
the `ShotList` (when each shot is and what it shows, no prompts), `ItemPrompts` (one subject's
pictures), `ScenePrompts` (a batch of scenes). Code puts them together as `FrameItem`s, written as the
project file (`frame_toml`), the source of truth of every picture (`hone_music_video.frame`). What a
project file cannot hold is `SceneShots`, the sidecar `frame/shots.json`: each shot's times and motion
prompt. `Planned` is stage 5's record; `Scenes` is the scenes as the clips take them (stage 6 and its
gate)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from hone_music_video.records import STRICT, Framing, Ms, ShotFiles, Shots, Version

CharacterView = Literal["front", "three-quarter", "side", "back", "close", "detail"]
Pose = Literal["", "sitting", "lying", "kneeling"]  # a body position a scene needs a picture of (0028)
PlaceView = Literal["wide", "reverse", "high", "low", "close"]
Group = Literal["demo", "characters", "objects", "places", "scenes"]


# ---------------------------------------------------------------------------- call 1: the bible


class FrameVariant(BaseModel):
    """A look of a character that a scene must copy and words alone cannot give: another costume, a
    state (wounded, wet, asleep without the helmet). It gets a picture of its own, made from the hero;
    with a given pose picture (`pose`, its name) that picture is its last reference (0027)."""

    id: str
    look: str  # the whole look in this state, complete like the hero's (0028; before: the changes only)
    why: str = ""  # when in the story
    pose: str = ""  # the name of a given pose picture the variant's body takes


class Expression(BaseModel):
    """A feeling the arc gives a character, as what the face does (0034 §3): a close-up made from its
    look's neutral close-up, for the face shots that name it."""

    id: str
    face: str  # the eyes, the brows, the mouth held, the jaw: "her eyes wide, brows drawn up, lips pressed"


class FrameCharacter(BaseModel):
    """Someone on screen: a person, an animal or a creature, with the whole visible look of its hero."""

    id: str
    name: str
    kind: Literal["person", "animal", "creature"]
    noun: str  # how a prompt names it beside its picture: "the old king", "the grey stallion"
    look: str  # the hero's description: age as it looks, build, face, hair, every garment, sides
    given: str = ""  # the name of a given sheet that is its hero picture
    variants: list[FrameVariant] = []
    presence: str = ""  # what the viewer should feel about them, and the visible traits that do it (0028)
    inner: str = ""  # what they feel, what they show, and how the feeling leaks, visibly (0028)
    expressions: list[Expression] = []  # up to four, for the face shots (0034 §3)


class FrameObject(BaseModel):
    """A thing that must look the same every time it is seen."""

    id: str
    name: str
    look: str  # shape, size, material, colours, details, the side that faces the camera
    given: str = ""


class PlaceState(BaseModel):
    """A time of day, weather or light of a place, made from one of its views with the same camera."""

    id: str
    look: str  # the whole place in this light or weather, complete (0028)


class FramePlace(BaseModel):
    """A location that recurs, empty of people in its pictures."""

    id: str
    name: str
    look: str  # the layout with positions, materials and colours
    light: str  # its light in the hero picture: the source and where it comes from
    states: list[PlaceState] = []
    given: str = ""


class ArcPart(BaseModel):
    """What one part of the song (a section or an instrumental span) should make the viewer feel (0028)."""

    part: str  # the part's id: a section's, or `instrumental-<n>`
    feel: str  # what the viewer should feel here
    intensity: int  # 1 (quiet) to 5 (the strongest moment of the video)
    turn: str = ""  # what changed from the part before
    evidence: str = ""  # what the viewer can see that makes them feel it


class Bible(BaseModel):
    """Call 1: the story read, the words every prompt shares, and every subject that gets a picture."""

    story: str
    kind: str  # the kind of picture, the first sentence of every scene: "A still from a 1920s drama."
    finish: str  # the texture and style words that close a prompt: "35mm film grain, soft contrast."
    world: str  # what belongs in the story's world and what never appears in it
    reference_light: str  # the backdrop and light of every hero and view
    demo: list[str]  # three to six prompts without references: the look of the whole video
    characters: list[FrameCharacter] = []
    objects: list[FrameObject] = []
    places: list[FramePlace] = []
    feeling: str = ""  # what the whole video should make the viewer feel, and how it changes (0028)
    arc: list[ArcPart] = []  # one entry per part of the song, in order (0028)


# ---------------------------------------------------------------------------- call 2: the shot list


class CastUse(BaseModel):
    """A character in a shot: which of its pictures the scene is made from."""

    character: str
    variant: str = ""  # one of its variants, or "" for the hero's look
    view: CharacterView = "front"  # the side the shot sees; `close` for a face shot; `detail` for a part
    pose: Pose = ""  # its body position, when the scene needs a picture of it (0028)
    part: str = ""  # with `view: "detail"`: the part the frame shows ("the snake on his left shoulder")
    expression: str = ""  # with `view: "close"`: one of the character's expressions; "" the neutral face


class PlaceUse(BaseModel):
    """The place of a shot: the view whose camera matches the shot's, and its state."""

    place: str
    view: PlaceView = "wide"
    state: str = ""


class FrameShot(BaseModel):
    """One shot of the video, without prompts: when, what happens, what is in the frame."""

    id: str
    start_ms: int
    end_ms: int
    lines: list[str] = []
    beat: str  # the opening frame only: what the first frame shows (0028)
    framing: Framing
    faces: bool
    camera: str  # the camera's one move during the clip
    light: str  # the light of this moment and where it comes from
    cast: list[CastUse] = []
    place: PlaceUse | None = None
    objects: list[str] = []
    # how the scene is taken (0027): one picture; `count`, three takes of one prompt (the moment is clear,
    # only the draw varies); `prompts`, two or three different shots of a hard moment
    takes: Literal["one", "count", "prompts"] = "one"
    from_scene: str = ""  # an earlier shot whose picked picture is this scene's only reference (0027)
    feel: str = ""  # what the viewer should feel at this moment (0028)
    evidence: str = ""  # what the viewer sees that makes them feel it: faces, bodies, staging, camera
    motion: str = ""  # the one change during the clip
    ends: str = ""  # what the next shot inherits: where people are, what they hold, what changed
    setup: str = ""  # the recurring arrangement it belongs to, one of the shot list's `setups`
    # an overhead, straight-down or worm's-eye camera, or two creatures fighting: the place has no picture,
    # its words go to the scene (0029 §3; the place picture fixes the camera to its own)
    place_in_words: bool = False


class Setup(BaseModel):
    """An arrangement several shots share (two people on a bed, a table): who is where (0028)."""

    id: str
    layout: str  # who is where, by their own left and right, against what; what touches what


class ShotList(BaseModel):
    """Call 2: every shot of the video."""

    shots: list[FrameShot]
    setups: list[Setup] = []


class ReviewNote(BaseModel):
    where: str  # a shot id, a part id, or "shots" for the whole list
    problem: str  # what is wrong and what would fix it


class ShotReview(BaseModel):
    """The review call (0028 §2): what in the shot list fails the feeling."""

    notes: list[ReviewNote] = []


# ---------------------------------------------------------------------------- calls 3 and 4: prompts


class ItemPrompt(BaseModel):
    id: str
    prompt: str
    model: str = ""  # one of the project's image models, when it names several (0027); "" the default


class ItemPrompts(BaseModel):
    """Call 3, one per subject: the prompt of each of its pictures."""

    items: list[ItemPrompt]


class Thing(BaseModel):
    what: str  # "black snake", "woman"
    count: int
    image: int = 0  # the picture that shows it; 0 when only words describe it


class SceneLink(BaseModel):
    sentence: str  # "the snake on the right of the picture grows from the top of his left shoulder"
    ends: list[str]  # what it joins, named in the prompt the same way: ["the snake", "his left shoulder"]


class SceneFacts(BaseModel):
    """What a scene must show, written before its prompt and not sent to the image model (0029 §1)."""

    things: list[Thing]  # everyone and every countable thing, with its count
    links: list[SceneLink]  # each relationship the beat depends on
    visible: list[str]  # what the camera must show for the links to read
    moment: str  # the one frozen instant


class ScenePrompt(BaseModel):
    id: str
    facts: SceneFacts | None = None  # None only in a reply that left them out: it is sent back
    prompts: list[str]  # one, or two or three different shots of a hard moment
    motion_prompt: str
    model: str = ""  # as an item's (0027)


class ScenePrompts(BaseModel):
    """Call 4, one per batch of shots: the scenes' prompts and their motion."""

    scenes: list[ScenePrompt]


# ---------------------------------------------------------------------------- the plan


class FrameItem(BaseModel):
    """One item of the project file as the planner writes it: `[<group>.<subject>.<name>]`, or
    `[scenes.<shot>]`, or one prompt of `[demo]`."""

    model_config = STRICT
    id: str  # "darvin.hero", "oasis.dawn", "S004", "demo.1"
    group: Group
    subject: str
    name: str = ""
    role: str = ""  # what the picture is, for its prompt writer
    size: str
    seed: int
    refs: list[str] = []
    prompts: list[str] = []  # one is the item's `prompt`; more are its `prompts`
    count: int = 1  # takes of one prompt (Hone Frame's `count`)
    model: str = ""  # its own model, "" for `[defaults] model`
    file: str | None = None  # a given picture, relative to the video project's folder
    hold: bool = False
    uses: list[str] = []  # the shots that use this picture


class FramePlan(BaseModel):
    """What the planner made, before it is written: the bible, the shots, the items in file order, the
    motion prompts, and what the checks still found after the repairs."""

    model_config = STRICT
    model: str  # `[defaults] model`
    bible: Bible
    shots: list[FrameShot]
    items: list[FrameItem]
    motion: dict[str, str] = {}
    problems: list[str] = []


class SceneShot(BaseModel):
    """One shot as the sidecar keeps it (`frame/shots.json`): what Hone Frame's file cannot hold. `scene`
    is its scene item's id; the start frame is that item's picture in use."""

    model_config = STRICT
    scene: str
    start_ms: Ms
    end_ms: Ms
    lines: list[str] = []
    beat: str = ""
    framing: Framing
    faces: bool
    cast: list[str] = []
    location: str = ""
    camera: str = ""
    motion_prompt: str
    clip_seed: int = 0  # a clip redone with a new seed (`redo PROJECT SHOT --seed`, 0027 §7)
    feel: str = ""  # what the viewer should feel, and the evidence, as planned (0028), for people
    evidence: str = ""


class SceneShots(BaseModel):
    """`frame/shots.json`: the shots in order; the motion prompts may be edited (0027 §7)."""

    model_config = STRICT
    format_version: Version = "1"
    shots: list[SceneShot]


class Planned(BaseModel):
    """Stage 5 (`plan`): the project file written into the frame workspace, and the plan's numbers."""

    model_config = STRICT
    format_version: Version = "1"
    project: str  # the frame project's id in `<project>/frame/`
    sha256: str  # of the project file as written
    shots: int
    items: int
    problems: list[str] = []


class Scenes(BaseModel):
    """The scenes as the clips take them (stage 6 and `review_scenes`): the frame run's end, and per shot
    its scene's picture in use as a start frame, its prompt and its motion prompt."""

    model_config = STRICT
    format_version: Version = "1"
    run: str  # the frame run's status when the stage ended: done, waiting, ...
    reason: str = ""
    shots: Shots | None = None  # None until every scene has a picture in use
    stills: ShotFiles | None = None
