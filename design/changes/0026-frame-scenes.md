# 0026: Scenes the Hone Frame way, planned in several calls (experimental)

## Status

`proposed (experimental)`: built on the branch `exp/frame-scene-generation` at the owner's request
(2026-10-16), to be tried on real songs before it is accepted. It is **not merged to `main`**. Nothing of
the 14-stage run changes: the frame path is its own command, `hone-music-video frame`, and starts from
a project whose timed lyrics are approved.

## Context

Two problems with how the scenes are made today:

1. **One planner call plans every shot.** On *roostam-death* (2026-10-13) the one `plan_shots` call ran 18
   minutes before it was stopped; on *this-too-shall-pass* it failed twice before a third attempt
   returned after 4.7 minutes; *raha*'s took 7.3 minutes. One reply carries every shot's timing, cast,
   still prompt and motion prompt for 45 to 67 shots: a long structured reply under many rules, all of
   it lost when any part of it fails, and repaired as a whole.
2. **The pictures are weaker than Hone Frame's.** Hone Frame (`../hone-frame`, change 0008 and its
   stress tests of 2026-10-14) makes every recurring character, object and place as a picture of its
   own first, and draws each scene from exactly the pictures it names, with a prompt that names each one
   by its number. Five test projects in five styles kept their look and their characters from the first
   scene to the last. Here a place is only words (weak point 21: the room changes from shot to shot), a
   costume change has no picture (the reference's costume wins), a scene's references are chosen by
   rules the planner cannot see, and the prompt it wrote is rewritten (placeholders, the polish).

Hone Frame itself does not plan: the owner (or an assistant in a chat) writes its project file by hand
from its prompt guide. The stress tests' files were written that way, and that is the quality to match.

## Decision

### 1. The frame plan, in four steps (`frame_plan.py`, `frame_calls.py`, `frame_prompts.py`)

1. **The bible** (one call, `data/prompts/frame_bible.md` + the guide's Hero, Objects and Places): the
   story; `kind`, the kind of picture as one sentence that begins every scene ("A still from a 1920s
   period drama shot on 35mm film."); `finish`, the closing texture words; `world`; the reference
   backdrop and light (mid-grey, one soft key light from a side); a demo of three to six prompts; every
   character with the whole visible look of its hero and its **variants** (another costume or state a
   scene must copy), every object, every place with its layout, light and **states** (night, dawn). The
   owner's given pictures are attached; one that is a subject's hero becomes Hone Frame's `file`.
2. **The shot list** (one call, `frame_shots.md` + the video limits): the shots that tile the song, each
   with its beat, framing, faces, camera, light, `hard`, and **which picture** of each character (variant
   and view: front, three-quarter, side, back, close), of the place (view: wide, reverse, high, low,
   close; and state) and which objects. **No prompts**: the reply is a fraction of today's. It is checked
   by `check_shots` (timing, lines, faces) and against the bible, and sent back up to twice.
3. **The pictures** (code, `frame_items.py`): from the shot list, the items each subject needs, with Hone
   Frame's ids (`darvin.hero`, `darvin.sleeping-side`, `oasis.dawn`), sizes (a hero 832x1248, an animal
   1536x1024, a close-up or an object 1024x1024, a place and a scene 1664x928 at 16:9), seeds (Hone
   Frame's derived seed) and references (each view, close-up and variant made from its hero; a place's
   views from its wide view, a state from its view). A scene's references are one picture per character,
   then the place's view, then the objects, at most four (Hone Frame's stress tests: three to five drew a
   character twice most often). A subject no shot uses gets no picture.
4. **The prompts**: one call per subject (`frame_assets.md` + the guide's stages for it: Hero, Views,
   Faces, Poses; Objects; Places) and one call per six shots for the scenes (`frame_scenes.md` + the
   guide's Scenes + the video limits), four at a time. Each reply is checked by code: the scene begins
   with `kind` word for word, names every picture by its number and no other, no words of a render
   ("photorealistic", "8k"...), within 1500 characters, two or three different shots of a hard moment;
   the motion prompt names no mouth or speech. Problems go back once; a picture still without a prompt
   gets one written by code, so the plan is always whole, and what is still wrong is listed in the
   plan's `problems` (shown, never refused).

Every reply is kept as it returns (`current/frame/calls/<label>-<key>.json`, the key the sha256 of the
model, system prompt, data and images): a plan made again after a failure calls only for what it lacks;
a note (`--note`) changes the data, so the calls are made again.

The guide is Hone Frame's own, copied word for word into `data/frame_guide/` (`SOURCE.md` says from
where), with its image model's notes (`models.md`).

### 2. The plan is a Hone Frame project file (`frame_toml.py`)

`current/frame/plan.json` keeps the whole plan (the bible, the shots, the items, the motion prompts, the
problems); `current/frame/project.toml` is its items in Hone Frame's stored format: `[project]`,
`[defaults]`, `[demo]`, every item in file order with its refs pointing upward, a cast sheet and a
storyboard. `hone-frame import project.toml` reads it as it is, so the owner can make and steer the
pictures in Hone Frame's dashboard instead.

### 3. The maker makes it as Hone Frame does (`frame_make.py`)

Items top to bottom, one picture per step, on the project's start-frame model (`models.stills`), one
model session: every prompt byte for byte, the current pictures of its refs as image 1, 2...; an item
with several prompts makes one picture each (seeds `seed`, `seed + 1`) and waits for a pick while the
run goes on (Hone Frame's D-075; `--auto-pick` takes the first); a `hold` (each hero, each place's wide
view) waits to be accepted and stops the run (`--no-holds` does not stop); an item made from a picture
that waits is held back; a failure stops the run; every version is kept
(`current/frame/items/<id>/vNNN.png` with its record). No polish. One difference from Hone Frame: the
maker makes what is missing or changed (the key of D-009), so a changed hero is made again with
everything made from it; `frame redo` gives an item new seeds.

### 4. To the video (`frame_video.py`)

`frame video` makes each shot's scene picture in use its start frame (`current/shots/<id>/`, with its
`Made` record), and stages 12 to 14 make the clips, the finished clips and the assembly as they are,
with the planned motion prompts. `frame import PROJECT FOLDER` takes the pictures in use from a Hone
Frame project made from the same file (its `state.json`), keyed as the maker keys them, so the owner can
do the pictures in Hone Frame and the video here.

### 5. The command

```text
hone-music-video frame plan PROJECT [--note TEXT] [--model ID] [--fresh]
hone-music-video frame make PROJECT [--no-holds] [--auto-pick] [--only ID ...]
hone-music-video frame accept PROJECT ITEM [N]
hone-music-video frame redo PROJECT ITEM ...
hone-music-video frame import PROJECT HONE_FRAME_PROJECT_FOLDER
hone-music-video frame video PROJECT
hone-music-video frame status PROJECT [--json]
```

## Options considered

- **Depend on hone-frame and run its runner.** The most literal, but hone-frame's 0008 is on a local
  branch and takes hone-models from a feature branch: the two libraries would ask for different
  hone-models. The project file keeps the two compatible instead; the maker is about 200 lines.
- **Split today's shot plan by sections.** Smaller calls, but the same kind of reply and the same
  pictures; it fixes only the first problem.
- **Replace stages 5 to 11 in the workflow.** The real integration, once this is tried: gates for the
  bible, the heroes and the scenes, the dashboard's views. Too large to try first; the command shows
  whether the pictures are worth it.

## Consequences

- A video's pictures are planned in about `2 + subjects + shots / 6` calls of a few minutes or less
  each, side by side, instead of one long one; a failure costs one call, not the plan.
- Places, costume changes and close-ups have pictures; every scene says which picture is which.
- More pictures are made before the scenes (heroes, views, places, states): about 15 to 40 for a
  video, at 20 to 50 s each on the reference machine.
- The dashboard does not show a frame plan yet; Hone Frame's does (import the project file).
- Not done: the dashboard, the run's gates, the start-frame check of 10.3 on frame scenes, a re-plan
  of a few shots, Hone Frame's Pillow sheets in the maker (Hone Frame composes them).

## Guarantees

AC-60 (`tests/e2e/test_ac60_frame_scenes.py`): the plan is made in a bible call, a shot-list call without
prompts, one call per subject and one per six shots; the project file is Hone Frame's, every ref
pointing upward; a plan made again calls for nothing it has, a note calls again; scenes with problems go
back once and a missing scene is written by code; the maker makes the demo first, stops at a hold, sends
prompts byte for byte with the references in order and seeds `seed + k`, waits for a pick without
stopping, and makes nothing unchanged; a changed hero is made again with what is made from it, every
version kept; pictures from Hone Frame come back and are not made again; the scenes in use become the
video with their motion prompts.
