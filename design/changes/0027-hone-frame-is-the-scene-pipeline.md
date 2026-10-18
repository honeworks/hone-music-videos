# 0027: Hone Frame is the only scene pipeline

## Status

`accepted (experimental)`: requested by the owner on 2026-10-16, revised the same day (no dependency on
`hone-frame`: its behaviour is re-implemented here). It is built only on the branch
`exp/frame-scene-generation`, which is never merged to `main` and never pushed. It takes over 0026 (the
frame planner stays; 0026's maker is replaced by the re-implementation of Hone Frame) and removes what 0006,
0014, 0015, 0017, 0019, 0020 (the pictures part), 0021 (the references part), 0023 and 0025 §6 built
before the scenes. Its smaller choices will be D-161 onwards.

## Context

0026 showed that the frame plan works on a real song. *roostam-death* (5.4 min, 33 lines) was planned in
28 calls in 8 minutes, with no problems left over. Before, one `plan_shots` call ran 18 minutes and was
paused before it finished. The plan's prompts read like the stress-test files of Hone Frame. But 0026
runs beside the old pipeline:

- Its maker only looks like Hone Frame's. It remakes whatever changed, where Hone Frame makes only what is
  marked.
- It has no dashboard.
- It skips some of Hone Frame: `count`, scenes made from scenes, pose pictures, a model per item, and
  sheets.

The old pipeline still carries:

- the cast planner, sheets, packs and the cutter;
- the one-call shot planner, its repairs and the re-plan;
- the reference picking;
- the judges, the retries and best-of;
- the polish;
- the picture menu and uploads.

That is about half of `src/` for pictures the frame path makes better. The owner wants one pipeline, and
up to the scenes it should be exactly Hone Frame, re-implemented here without depending on it.

## Decision

### 1. Hone Frame re-implemented inside this library, not a dependency

The owner decided (2026-10-16) that hone-music-video does **not** depend on `hone-frame`. Its behaviour up
to the scenes is re-implemented here, exactly, in a package `hone_music_video/frame/`. Every module says
in its docstring which Hone Frame module and design section it follows, and which tests prove it
matches. The source is Hone Frame's `redesign/0008-owner-control` working tree of 2026-10-16 (its
`design/current.md`, change 0008, decisions D-042 to D-077, `src/hone_frame/`, `docs/`).

| `hone_music_video/frame/` | follows Hone Frame's | what |
|---|---|---|
| `records.py` | `records.py` (§4.2) | `ProjectState`, `ItemState`, `Version`, `RunRecord` (format `"2"`) |
| `project_file.py` | `project_file.py` (§5.2) | items in file order, `[defaults]`, `[demo]` (D-077), `prompts` (D-076), derived seeds (D-046) |
| `checks.py` | `checks.py` (§5.3) | validation, every problem naming its item: refs upward, ids, fields, sizes, inputs, refs within the model's limit, `file`, licence warnings |
| `writeback.py` | `writeback.py` (§5.4, D-042) | edits written with `tomlkit`, comments and order kept |
| `workspace.py`, `project.py` | `workspace.py`, `project.py` (§4.1, §5.1) | the folder, import, `sync` (new items marked, a changed `file` a new version), versions, `run.json`, events, locks (D-004, D-068, D-069) |
| `actions.py` | `actions.py` (§6) | edit, mark, unmark, dependants, accept, pick, use a version, replace with a file |
| `making.py` | `making.py` (§8.2) | one item: `count` images or one per prompt, seeds `seed + k`, refs in order, `made_with`, a sheet by Pillow; `next_up`, `rest_of` (D-075) |
| `runner.py` | `runner.py` (§8.1 to §8.5) | the queue, run, resume, pause, stop, accept, settle (D-074), recover |
| `estimates.py` | `estimates.py` (§9.1) | measured seconds per (model, size), 25th to 75th percentile |
| `notifications.py`, `events.py` | `notifications.py`, `events.py` (§8.6, §9.2) | `notifications.jsonl`, `events.jsonl`, the hub |
| `sheets.py` | `sheets.py`, `sheets_model.py` (§10) | the nine layouts composed by Pillow, byte-identical on recomposition |
| `views.py` | `views.py` (§12.3) | `ItemView`, `RunView`, `ProjectView`, with "changed since made" and "made from an older" ref |
| `api.py` | `dashboard_api.py` (§12.2) | the JSON API, mounted under `/api/projects/<id>/frame/` |
| `models.py` | `ports.py`, `models.py` (§7.2) | the frame's model port over this library's `Models`: `generate` with references, size, inputs and a cancel; `info` (max references, sizes, inputs, licence) from the registry |
| `dashboard_page/views/scenes*.js` | `dashboard_page/screens/*.js` | the items view (§6) |

Copying Hone Frame's code where it fits, rather than writing it anew, is how "exactly" is kept. The
differences are only where this library's pieces stand in for Hone Frame's, each marked
`# Hone Frame: ...` in the code:

- **The model port.** It is this library's `Models` (hone-models on its `main` branch), not Hone Frame's.
  - hone-models `main` has no `cancel` on a call. Pause and Stop cancel the picture being made the way
    0022 already does: the call is abandoned and ComfyUI's `/interrupt` ends the job.
  - Sizes, max references and licence come from the registry entry. The library's
    `qwen-image-2.1-turbo` entry gets the size list Hone Frame's catalog has.
- **Where the runner lives.** Hone Frame's dashboard owns one `Runner` per workspace. Here each video
  project holds a workspace (§2), and its `Runner` is driven by stage 6 of the run (§5): in the stage's
  thread from the command line, by the dashboard's background runner in the dashboard.
- **The frame run's hone-flow record is kept as Hone Frame has it** (D-043): each frame run is a
  hone-flow run under `<project>/frame/flows/`, beside the video's run (whose step `scenes` drives it).
  Each picture is also in the frame project's `events.jsonl` and in hone-models' spans.
- **Two differences from Hone Frame**, both deliberate: a blank picture (one colour, 0025 §4) is refused
  as a failed item instead of kept, and a version's URL names its file as it is on disk (`v001.png`, not
  Hone Frame's `v1.png` that its own server maps).
- **Hone Frame's CLI, exports and model page are not ported.** The CLI is replaced by
  `hone-music-video frame ...`, and the menu of models becomes the per-item `model`.

**Tests that prove each part matches** are Hone Frame's own acceptance tests, ported to this
package: AC 1 to 9, 13, 14, 16 and 17 (`tests/frame/test_ac*_*.py`), and its unit tests of the project
file and estimates. Each ported test file names the Hone Frame test it comes from. AC 10 and 11 (the
guide and model pages) and AC 12 and 15 (mannequins, old workspaces) are covered where they apply: the
licence warning and the refusal of a `mannequin:` ref.

### 2. Inside the project: one frame workspace

Each project holds a frame workspace at `<project>/frame/`, in Hone Frame's layout (format `"2"`:
`workspace.json`, `projects/<id>/project.toml`, `state.json`, `items/<item>/vNNN.png` and `.json`,
`thumbs/`, `events.jsonl`, `run.json`, `notifications.jsonl`). It holds one frame project, the video's
(its id is the video project's). So the folder can also be opened by Hone Frame itself.

Its `project.toml` is **the source of truth** for every picture up to the scenes:

- Edits come by hand or from the dashboard. They are read back by `sync` and checked as an import is
  before they are kept:
  - refs point upward;
  - ids are valid;
  - sizes, inputs and `negative` are ones the model takes;
  - the number of refs is within the model's limit;
  - a `file` exists and is a picture.
- They are written back with `tomlkit`, keeping comments and order.
- `tomlkit` becomes a dependency (as in Hone Frame, its D-042).

**What a project file cannot hold** goes in a sidecar, `<project>/frame/shots.json`: each shot's times,
lines, framing, faces and motion prompt, keyed by its scene's item id. Hone Frame refuses unknown fields,
so these cannot live in the file. The sidecar is checked against the project file:

- every shot names a scene item;
- the shots tile the song (`check_shots`).

### 3. The planner (0026's, extended)

The planner stays multi-call, and keeps every reply so a re-run only redoes what is missing:

- the bible;
- the shot list, without prompts;
- one call per character, object and place;
- one call per six scenes.

It uses Hone Frame's guides, the copy of 0026 in `data/frame_guide/` (`SOURCE.md` names the source).

The code check on written prompts stays, and replies are sent back once:

- every picture is named by its number;
- every scene begins with the shared opening sentence;
- no render words;
- no mouth or speech words in a motion prompt.

It is not a picture judge.

New in the plan, all things Hone Frame supports:

- **`count`**: several takes of one prompt. The shot list marks a shot `takes: "count"` when the moment is
  clear and only the draw varies. It marks `takes: "prompts"` (0026's hard shots) when different framings
  are the better bet.
- **A scene made from a scene**: the shot list may name `from_scene: "S012"`. That scene's only reference
  is that scene, and its prompt says "The same picture as image 1 … change only …". It waits for that
  scene's pick, as in Hone Frame.
- **Pose pictures**: when the owner gives a pose picture (`--pose NAME=FILE`, kept like a given sheet),
  the bible may use it for a variant. It becomes an item with `file`, given last in the variant's refs
  ("image 2 is only a pose guide …").
- **A model per item**: the planner writes `model` on an item only when the project names more than one
  image model (`models.frame`, a list; the first is `[defaults] model`). Otherwise `[defaults]` holds.
- **The whole file**:
  - `[project]`;
  - `[defaults]`: model, size, hold and inputs;
  - `[demo]`, with `hold`;
  - each item's `hold`, `count`, `prompt` or `prompts`, `refs`, `file`, `inputs`;
  - the sheets: a cast sheet, a turnaround per main character, a place board, and a storyboard of the
    scenes.

`hone-music-video frame plan` (and the stage) writes `project.toml` and `shots.json`. The workspace then
imports the file, so everything is marked, as at Hone Frame's import. A re-plan of a project that already
has pictures writes the new file over the copy (Hone Frame's `write_text`). An unchanged item keeps its
pictures and is not marked; a changed one is flagged "changed since made". The run marks only new items.

### 4. Making: Hone Frame's run, re-implemented

All of these follow Hone Frame's code (§1 says where):

- marks;
- the topmost marked item;
- redo, with or without dependants;
- the "changed since made" and "made from an older ref" flags (never marked by themselves);
- the demo first;
- `hold` stops the run until accepted;
- `count` and `prompts` wait for a pick while the run goes on with items not made from them;
- accept, pick, use an older version, replace with a file (with the dependants question);
- versions never deleted;
- Pause and Stop cancel the picture being made;
- estimates from measured times;
- `notifications.jsonl`;
- sheets composed by Pillow;
- prompts byte for byte;
- references in order;
- seeds `sha256("<project>:<item>")`, then `seed + k`.

Nothing is added between the file and the model. 0026's maker (`frame_make.py`), which remade whatever
changed, is replaced: here nothing is made unless marked.

### 5. The run's stages

```text
1 measure  2 transcribe  3 lyrics  4 check_lyrics  ⏸ review_lyrics     (unchanged, owner timing too)
5 plan     the frame plan (§3): project.toml + shots.json, imported     ⏸ review_plan
6 scenes   Hone Frame's run of the workspace, until nothing is marked   ⏸ review_scenes
7 clips    8 finish    9 assemble                                     (stages 12 to 14 as they are)
```

- **`review_plan`** shows the project file and the shot list. Approve, or reject with a note: the planner
  runs again with it, and the kept replies are reused where the data is the same.
- **`scenes`** drives the project's frame `Runner` (one per workspace, as in Hone Frame):
  - The stage runs the marked items (Run, or Resume of a paused frame run). It drains the queue in its
    own thread on the command line; in the dashboard the dashboard's frame runner does it, and the stage
    waits for the frame run to end.
  - Pause and Stop of the run (0022's request file, the CLI's `pause [--now]`, the dashboard) become the
    frame runner's pause and stop. Both cancel the picture being made, as in Hone Frame. The video's run
    then shows as paused, and `resume` continues the frame run.
  - When the frame run ends `waiting` (a hold, or picks left) or `done`, the stage ends and
    `review_scenes` waits. A failure fails the stage with the item's error.
  - During the gate the Scenes view acts as Hone Frame's dashboard does: an accept lets a waiting frame
    run go on by itself (D-074), and Run makes what is marked.
  - The owner works in the Scenes view (§6): accept, pick, redo, edit, replace, then Run.
  - `review_scenes` can be approved when every scene has a picture in use, none waits, nothing is
    marked and no frame run is active. Approving takes the scenes as they are at that moment (the
    gate's value is replaced through hone-flow's `edit`): each shot with its scene's picture in use and
    its motion prompt.
  - An unattended project (`approve: "auto"`) accepts holds and takes each pick's first picture.
- **The start frame of a shot** is its scene item's picture in use, copied as a kept version into
  `current/shots/<id>/`. The clips are then made as now, with the motion prompt from `shots.json`.

### 6. The dashboard

A **Scenes** view per project: Hone Frame's items view, ported. Its JSON API (`frame/api.py`, Hone Frame's
`dashboard_api.py`) is mounted under `/api/projects/<id>/frame/…` in this library's server, with the
same routes and answers. Its events (`item`, `run`, `event`, `notification`) come on the dashboard's
event stream. The view ports Hone Frame's `dashboard_page` screens (`items`, `item`, `fields`, `refs`,
`prompts`, `dependants`, `file`, `sheets`, `runbar`, `guide`) for one project:

- each item's status, current picture, versions, flags and estimate;
- accept, pick, redo (with the dependants question), use a version, replace with a file;
- editing a prompt or any field (written back, comments kept);
- the run's state, with Run, Pause and Stop;
- the demo first;
- the cast and storyboard sheets;
- the prompt guide.

As built: the screens are in `dashboard_page/frame/` (each names the Hone Frame file it is ported
from), with Hone Frame's stylesheet scoped under `.hf`; the view reloads the frame project on each
`frame` event of the page's stream (the frame project's `events.jsonl` lines) and every 3 s while its run
is busy. Hone Frame's notification panel, sounds and exports are not ported: the page's bell rings for
the video's gates, and the run bar says when the frame run waits.

The Lyrics view and the clip views (Clips, Preview, scene viewer) stay. The Cast, Packs, Storyboard
(start frames) and shot-list views go. The Storyboard becomes the storyboard sheet and the scene items.

### 7. From the scenes on: per-scene remakes

A scene's picture in use can change by a pick, a use, a redo, or a replace. A shot's motion prompt can be
edited in `shots.json`, from the clip view or `hone-music-video motion PROJECT SHOT TEXT`. Either way
`hone-music-video remake PROJECT` (the dashboard's Remake) forks the run from `clips` with a run
parameter `remake` (one more each time) rather than refreshing the stage, so every clip's seed and key
stay what they were. The clips stage
reads the scenes as they are now (the pictures in use, `shots.json`), so it makes again **only that
shot's** clip and finished clip, then re-cuts the video:

- A clip's key is the sha256 of its start frame's bytes, its motion prompt and its seed (D-009), so other
  shots keep their files.
- Every clip version is kept and listed in the scene viewer with the scene version it was made from.
- `takes`, forks and the queue of 0008, 0020 and 0022 are no longer needed for this, and go.
- Redo of a clip with a new seed stays (`redo PROJECT SHOT --seed`, clips only).

### 8. What goes

| Removed | Modules |
|---|---|
| cast planner, sheets, packs, cutter, prop sheets, details | `stages_cast`, `stages_firsts`, `stages_views`, `stages_props`, `_pictures`, `runs_pictures`, `_cutter`, cast and pack records, `data/prompts/cast.md` |
| one-call shot planner, repairs, re-plan, reference picking | `stages_plan.plan_shots`, `runs_replan`, `prompt_assembly`, `data/prompts/shots.md` |
| sheet judge, start-frame check and gate, retries, best-of, motion rewrites | `sheets_check`, `records_sheets`, `stills_check`, `_contact_sheet`, `still_retries`, `motion_rewrites`, `estimates` (extra takes), `data/prompts/quality.md`, `sheets_check.md` |
| polish | `z-image-turbo-polish` entry and workflow, the `polish` setting |
| picture menu and uploads of the old pipeline | `image_menu`, `scene_menu`, `uploads`, `image_costs`, `adapters/hosted_gemini_image.py` (Hone Frame's per-item model and "replace with a file" stay) |
| takes, forks for scenes, the scene queue, a paused run's scene redo | `takes`, `records_takes`, `runs_redo` (scene parts), `_remade`, `scene_queue`, `runs_queue`, `runs_pause` (scene parts), `_cli_queue`, `_cli_pictures`, `_dashboard_redo` (scene parts) |
| 0026's own maker and writer | `frame_make`, `frame_toml`, `frame_video` (replaced by `frame/` and the stages) |
| settings | `packs`, `face_refs`, `sheet_takes`, `prop_sheet_takes`, `sheet_retries`, `still_retries`, `still_takes`, `pick_best_of`, `pick_shots`, `quality_check`, `quality_gate`, `rewrite_motion`, `polish`, and the roles `cast`, `sheets`, `views`, `stills`, `polish`, `quality`; new: `models.frame` (list), `models.planner` |

**Stored projects:**

- A project stored before 0027 opens. Its retired settings are read and dropped (`settings.stored`).
- Its lyrics and finished video stay viewable.
- Its `resume` forks: hone-flow keeps the stages whose code and inputs did not change (the lyrics
  stages, with the approved timeline) and continues into `plan`, so the old scenes are replaced by a
  frame plan without refusing anything (built and tested so; this replaces the refusal first proposed).

**Acceptance cases:**

- **Removed:** 3 to 5, 7, 8, 14, 16, 17, 19 to 21, 23 to 33, 36 to 39, 47 to 50 where they are about
  start frames, 54 and 58 (polish), and 59.
- **Kept:** 1, 2, 6 (on `shots.json`), 9 to 13, 15 (on the motion prompt), 18 (pace and mood reach the
  planner), 22, 34 (the licence notice, from Hone Frame's warning), 40, 51 to 53, 55 to 57.

### 9. New guarantees (each an AC test)

60. The plan is made in a bible call, a shot-list call, one call per subject and one per six scenes; a
    re-run calls only for what it lacks; a note calls again.
61. The project file holds `[demo]`, `hold`, `count`, `prompts`, `refs`, `file`, `inputs`, a per-item
    `model` when the project names several, a scene made from a scene, a pose picture, and the sheets.
    Hone Frame's import accepts it, and its refs point upward.
62. The frame workspace behaves as Hone Frame's: its acceptance tests 1 to 9, 13, 14, 16 and 17, ported
    to `hone_music_video.frame` (`tests/frame/`), pass: import marks everything; the run makes the demo
    first and then the topmost marked item; a hold stops it; a pick waits while the run goes on; accept,
    pick, use, replace and redo with dependants; versions kept; estimates; a failure notifies; sheets
    byte-identical.
63. An edit of `project.toml` (by hand or through the mounted API) is checked like an import, refused
    whole when wrong, and written back with comments kept; a changed item is flagged, never remade until
    marked.
64. Pause and Stop in stage 6 cancel the picture being made (Hone Frame's AC 4), and the run's stage
    shows as paused.
65. Each shot's start frame is its scene's picture in use; a new pick, use, redo or replace of one scene,
    or an edit of its motion prompt, remakes only that shot's clip and finished clip, and the video is
    re-cut; every version is kept and listed.
66. A project stored before 0027 opens, its retired settings are dropped, and its `resume` keeps the
    lyrics stages and continues into `plan`.

## Options considered

- **Depend on `hone-frame`** (the first draft of this record). It would be exact by construction, and
  there is no hone-models conflict: Hone Frame's hone-models branch is `main` plus 14 commits. But Hone
  Frame's 0008 is not on GitHub yet. **The owner chose not to depend on it.**
- **Re-implement from the design alone.** That would drift in details: the order of `next_up`, when a
  hold stops the run, what a cancel restores. Copying the code with notes, and porting Hone Frame's own
  tests, keeps the details.
- **Keep the old pipeline as an option.** It doubles every test and view. The owner asked for one
  pipeline.

## Consequences

- About 40 modules and their tests go. The picture side of the library becomes the planner and a thin
  bridge to Hone Frame.
- About 4,000 lines of Hone Frame are re-implemented here and must follow Hone Frame's changes by hand.
  Each module names its source.
- No hosted picture models (Hone Frame offers local ones only).
- More pictures before the clips: heroes, views, places and states. On *roostam-death* that was 51
  reference pictures and 5 demo pictures before 76 scenes; 22 of the scenes have two or three prompts.

## Open questions for the owner

1. Was there more after the picture menu and uploads in your list of what to remove? (The list ended
   there.)
