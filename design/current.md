# hone-music-video: the design (accepted, 0.1)

**Status:** accepted in [changes/0001](changes/0001-initial-design.md) (2026-10-10); being built in
milestones M1 to M6. M1 is built: the project folder (§4) and its records, the settings (§2.3), the
13 stages of §3.1 as one resumable hone-flow run with the four owner gates, the `Models` port with its
fake, the CLI and the dashboard shell (§13). M2 is built: hosted word times, the one-call lyrics
editor whose times the code takes from heard words, and `check_lyrics` (§5.1, §6). M3 is built: the cast
plan (§7.2), the sheets with their pick gate and the packs (§9) on the library's own registry entries
(D-020 to D-024). M4 is built: the shot plan in one call with at most two repairs, `check_shots` and the
shot gate (§5.2, §7.3, §7.4, §8; D-025 to D-028). M5 is built: the start frames (§10), the clips and
their finishing (§11) on local models, and redoing one shot with its takes (§11.2, D-030 to D-034). M6
is built: the assembly with ffmpeg and assembling again (§12, D-035, D-036). Change
[0007](changes/0007-operations.md) adds the edit for editors (§12.1), notifications (§13.4) and what a
video cost (§13.5; D-060 to D-064). Guarantees 1 to 13 are tested. [Change 0006](changes/0006-quality.md)
is built: face shots take the portrait first (§10.1), one vision call checks the start frames before the
clips with an optional gate, and optional extra takes are picked by it (§10.3, D-065 to D-069); the run
now has 14 stages and 5 gates. [Change 0014](changes/0014-prompt-and-reference-fixes.md) is built:
the limits of no speech and of motion (§8), fixed traits and the period anchor (§7), references by kind
of shot (§10.1), motion prompts rewritten by the check and anachronisms flagged (§10.3), the `speech` and
`no-anchor` warnings (§5.2) and the cutter's crop (§9; D-077 to D-081); guarantees 14 to 17 are
tested. [Change 0009](changes/0009-project-options.md) is built: the project's `pace` and `mood` and the
story's `world` reach the planners and the check as data (§2.3, §7, D-084, D-085).
[Change 0015](changes/0015-still-retries.md) is built: the drafts are checked inside stage 10 and a
start frame with a major flag is drawn again (§10.4), by a stricter judge (Claude Sonnet 5.5
since D-110, first Haiku 5.5; §10.3; D-086, D-087); motion prompts never name the mouth (§8.3, D-088). Guarantees 18 and 19 are
tested. [Change 0016](changes/0016-dashboard-bell-and-options.md) adds the dashboard's bell (§13.6), the
New video form's pace, mood, style presets and start-frame retries, and "Retry this frame" at
`review_stills` (§13.2; D-096 to D-099). [Change 0017](changes/0017-prop-sheets.md) is built: prop
sheets and packs and the reference budget (§9, §10.1; D-100 to D-109); guarantee 20 is tested.
[Change 0019](changes/0019-sheet-judge.md) is built: the judge checks every sheet take, flagged takes
are drawn again, unusual characters get more takes and a miscounted take is never cut (§9.1; D-120 to
D-127); guarantee 21 is tested. [Change 0020](changes/0020-owner-sheets-and-frames.md) is built: the
owner chooses how each picture is made from one menu of local models, hosted models and uploads; a new
project's packs are separate pictures reviewed at two gates; the run can stop after the scenes; a scene
can be changed while others are drawn (§2.3, §2.4, §9, §10, §11.2, §13.2, §13.5; D-128 to D-138);
guarantees 23 to 29 are tested.

**Since [change 0027](changes/0027-hone-frame-is-the-scene-pipeline.md)** (accepted as an experiment,
merged to `main` on 2026-10-18), Hone Frame's way is the only scene pipeline. The plan is made in several
calls and written as a Hone Frame project file; the scenes are made by Hone Frame's behaviour,
re-implemented in `hone_music_video.frame`; each shot's start frame is its scene's picture in use. The
run has 10 stages and 3 gates (§3.1). §7, §9, §10, §11.2 and §13.2 describe it; the cast, packs, judges,
retries, polish and picture menu of the sections' earlier text are gone (0027 §8), and the guarantees
they had are listed as removed in §14. [Change 0028](changes/0028-feeling-first-planning-and-overnight-queue.md)
(on the same branch) puts the feeling first in the plan (§7: the song's measured shape, the owner's
feeling, the arc, a review call), makes every take of a hard scene with its clip overnight (§9, §11.1)
and adds the overnight queue (§13.1: prepare, run all prepared, retries, a kept queue).
[Change 0031](changes/0031-clips-only-for-picked-takes.md) (same branch) makes clips only for the takes in
use unless `take_clips` is `"all"` (§2.3, §11.1). [Change 0032](changes/0032-lines-the-aligner-lost.md)
(same branch) times a line the aligner lost from its heard words (§5.1).
[Change 0029](changes/0029-prompt-guideline-for-stills.md) (same branch) adds the still models' guideline
from 100 hard cases: scene replies write their facts first, the shot list is planned around six facts no
prompt makes the still models draw (§8.2b), and an extreme camera or a creature fight gets the place in
words (§7). Section numbers are
stable; code comments refer to them
("design §5.3"). The evidence behind the defaults is
in [history/0000-research.md](history/0000-research.md); smaller choices are in
[decisions.md](decisions.md).

## 1. What it does

A person gives a song in the dashboard, with optional lyrics, optional reference sheets for characters
they already have, and the settings of the video (style, aspect ratio, resolution, frame rate, shot
limits). hone-music-video then:

1. times every sung line and word in integer milliseconds (§6);
2. plans the cast and writes the prompts for the reference sheets it still needs (§7.2);
3. makes a reference pack per character, and per prop with a look, on local models (§9);
4. plans every shot of the video in one call, within the written limits of the local models (§7.3, §8),
   and validates the plan against the timed lyrics (§5);
5. draws a start frame per shot (§10), checks them all in one vision call (§10.3), turns each into a
   clip (§11), finishes the clips (§11.3);
6. assembles the video: each clip cut to its exact window, the song under it (§12).

The owner approves the timed lyrics, the cast, the sheets and the shot list before the long local stages
run (and, when they ask, the flagged start frames before the clips), and can redo any single shot
afterwards.

### Goals

- Cuts land on the lyrics: every time comes from measured audio, is checked by code, and is kept in
  milliseconds until the last frame is chosen.
- Characters stay the same across shots: every shot with a character gets that character's reference
  pictures.
- The planner knows the local models' limits and plans shots they can deliver.
- One planning call per kind of plan (cast, shots), never one per shot.
- Every stage resumes after a crash; every generated file is kept with the prompt and settings that made it.
- Every model, setting and prompt is configurable; the defaults are the measured best on an 8 GB GPU.

### Non-goals (0.1)

Generating music, lip-sync, dialogue, an editing timeline (the edit is exported to editors instead,
§12.1), captions, several users, accounts, hosted
rendering, training.

### Responsibilities

hone-music-video owns the song-to-video domain: settings, timing, plans, validators, prompts, the local
generation recipes, assembly and the dashboard. It delegates every model call to **hone-models** and run
execution (resume, gates, progress) to **hone-flow**; both are core dependencies (decision D-001).

## 2. Inputs

### 2.1 The song

An audio file (WAV, FLAC, MP3, M4A, OGG). Its duration, measured with `ffprobe`, is the length of the
video: `duration_ms`.

### 2.2 Optional material

| Input | Meaning |
|---|---|
| `lyrics` | the lyrics as text, one line per sung line, blank lines between sections; biases and corrects the transcription (§6) |
| `story` | notes on the story, setting, era, characters' names and relationships; the planners treat it as the owner's intent |
| `sheets` | reference sheets or portraits the owner already has, each with a name (e.g. "Darvin") and an optional note; the cast planner decides what they cover (§7.2) |

### 2.3 Settings

Settings are data given with the song (a pydantic model, `extra="forbid"`); they never appear as words
the owner must write into a prompt. Settings stored before change 0006 read a missing `face_refs` as
`"front-first"` and a missing `quality_check` as `false`; settings stored before 0014 read a missing
`rewrite_motion` as `false` (and keep their `face_refs`); settings stored before 0009 and 0015 read a
missing `pace` as `"balanced"`, `mood` as `""` and `still_retries` as `0`, and keep their
`models.quality`; settings stored before 0019 read a missing `sheet_retries` as `0`, so an older
project keeps its behaviour; settings stored before 0020 read a missing `packs` as `"sheet"` and a missing
`models.views` as their `models.stills`, so an older project draws and cuts four-figure sheets as before
(D-128, D-135). `project.json` stores every setting, so a project made before 0021 keeps its models and its
`face_refs`: only a new project gets Qwen-Image-2.1 Turbo and `"one-body"` (0021). Settings stored
before 0025 read a missing `polish` as `"on"`, so their start frames stay polished (0025, D-155).
Defaults:

| Setting | Default | Meaning |
|---|---|---|
| `style` | `"photoreal live-action film, 35mm film look, natural film grain"` | the look, as a phrase the planners weave into every prompt |
| `aspect_ratio` | `"16:9"` | also `9:16`, `1:1`, `4:5` |
| `resolution` | `1080` | the short side of the final video, in pixels |
| `fps` | `32` | final frame rate (Wan's 16 fps x2 by RIFE; decision D-004) |
| `min_shot_ms` / `max_shot_ms` | `2000` / `8000` | shot length limits (8 s is Wan's tested maximum, §8.3) |
| `still_takes` | `1` | start frames drawn per shot; the first goes on to its clip, the owner can use another (§10.2, D-031) |
| `face_refs` | `"one-body"` | each character in a scene gets one picture, a full body or in a face shot its portrait, then details and props up to the model's slots (D-145); a carrier's first picture gets its props, a view the character's details (§9, §10.1, 0021); `"by-shot"` (0014 to 0020): in a face shot the portrait first, in any other no portrait; `"portrait-first"` as 0006, `"front-first"` as before 0006 (D-065, D-079) |
| `quality_check` | `true` | one vision call checks every start frame before the clips (§10.3, D-066) |
| `rewrite_motion` | `true` | the check also rewrites each motion prompt to its start frame as drawn; only with `quality_check` (§10.3, D-080) |
| `quality_gate` | `"off"` | `"ask"`: the run waits at `review_stills` when a start frame in use has a major flag (D-067); `"always"`: it waits there once every scene is drawn and checked, flagged or not, so the owner can change scenes before the clips (§10.3, 0020, D-137) |
| `packs` | `"views"` | `"views"`: a character's pack is separate pictures (a front, a side, a back, a portrait and its details) and a prop's is one picture; `"sheet"`: the four-figure sheet and the cutter, as before 0020 (§9, D-135) |
| `pick_best_of` | `1` | 2 or 3: the chosen shots get that many start-frame takes, the check picks the best (D-068) |
| `pick_shots` | `"faces"` | which shots `pick_best_of` chooses: the shots with `faces`, or `"all"` |
| `sheet_takes` | `4` | turnaround takes per character (the owner picks); at least 4 for an `unusual` character (§9.1, 0019, D-125); only in a `"sheet"` project, a `"views"` project draws one picture each (§9) |
| `prop_sheet_takes` | `4` | sheet takes per prop with a `look` (the owner picks; §9, 0017, D-102); only in a `"sheet"` project |
| `language` | `None` | the sung language, when known (passed to the transcriber) |
| `pace` | `"balanced"` | `"calm"`: long shots (about 6.5 to 8 s), few cuts inside a verse, cuts on line or section starts; `"energetic"`: short shots (2 to 4.5 s); the shot planner gets the length it prefers, `check_shots` warns outside it (0009, D-084) |
| `mood` | `""` | free words in any language ("tragic", "tender, hopeful", "dark, دلهره‌آور"): the light, colour, camera speed, stillness and how open the faces are; the cast and shot planners and the check get it (0009) |
| `take_clips` | `"picked"` | `"picked"`: clips and finished clips only for each scene's take in use, another take's when it is picked and remade; `"all"`: every take's overnight (0028 §5, 0031); not given to the planners |
| `polish` | `"off"` | `"on"`: each start frame is polished after it is drawn; `"off"`: the start frame is its draft. A new project is `"off"`; settings stored without it read `"on"`. It does not reach a planner. A take can record its own choice (`Take.polish`); a redo that draws a new start frame stores the project's setting then (0025 §6, D-155) |
| `still_retries` | `2` | 0 to 5: a start frame whose draft has a major flag is drawn again from the check's corrected prompt, at most this many rounds (§10.4, 0015, D-087); not takes per shot (`pick_best_of`) |
| `sheet_retries` | `2` | 0 to 5: a sheet take with a major flag from the judge is drawn again from its corrected prompt, at most this many rounds (§9.1, 0019, D-121); needs `quality_check` |
| `models` | §3.2 | the model id per role; `models.sheets`, `models.views` and `models.stills` may name hosted entries (§3.2, D-128) |

### 2.4 The public API

`hmv.redo`, `hmv.use`, `hmv.replan` and the rest are in §11.2; what 0020 adds, with the command line's
equivalents:

```python
hmv.image_models(project, models, purpose="scene", shot="S012")  # [ImageModel(id, where, max_references, about_usd, about_ms)]
hmv.redo_picture(project, models, "morvane", "front", model="seedream-5-0-260128", note="two snakes")
hmv.redo_picture(project, models, "morvane", "ring", upload=Path("ring.png"))
hmv.redo(project, models, "S012", hmv.Redo(still=True, model="qwen-image-3.0"))
hmv.redo(project, models, "S018", hmv.Redo(upload=Path("frame.png")))
hmv.apply_queue(project, models, dry_run=True)   # the Preview; without dry_run, the fork's run state
```

```text
hone-music-video new isolde song.wav --stop-after-scenes --stills-model seedream-5-0-260128
hone-music-video image-models isolde --for scene S012     # the menu, with estimates
hone-music-video redo-picture isolde morvane front --model seedream-5-0-260128 --note "two snakes"
hone-music-video redo-picture isolde morvane ring --upload ring.png
hone-music-video redo isolde S012 --still --model qwen-image-3.0
hone-music-video redo isolde S018 --upload frame.png
hone-music-video apply-queue isolde --dry-run             # what would be made, how long, how much
hone-music-video apply-queue isolde
hone-music-video pause isolde                             # after the file being made (0022)
hone-music-video pause isolde --now                       # stop now: that file is made again on resume
```

`image_models` lists, for a scene or a picture, every `kind = "image"` entry of the hone-models registry
that can do the job, local ones first, then hosted ones by price, each with its reference limit and an
estimate marked "about"; a text-only model is listed only for a picture with no reference pictures
(D-129, D-133). `Redo` gains `model` and `upload` (one of them, never both; D-132). `hmv.redo` keeps its
behaviour when neither is given, except that a redo sent while the run is going is checked and queued
instead of refused (§11.2). `new` also takes `--sheets-model` and `--views-model`.

## 3. The flow

### 3.1 Stages

The whole video is one hone-flow workflow per project. Stages run in order; ⏸ marks a human gate (the run
pauses until the owner approves or edits in the dashboard). A project made to run unattended
(`approve: "auto"`, 0004) has each gate approved the moment it is reached, unless its check reports
errors: then it stops there as above (D-075, D-076).

| # | Stage | Where | Output |
|---|---|---|---|
| 1 | `measure` | local (ffprobe) | `song.json`: duration, sample rate, channels |
| 2 | `transcribe` | Demucs and the MMS aligner on the CPU + hosted speech model | `words.json`: every word heard in the song's vocals with start/end ms; given lines not heard listened for again; given lyrics aligned to the vocals (§6) |
| 3 | `lyrics` | hosted LLM, one call | `timeline.json`: sections, lines, words, instrumental spans (§6) |
| 4 | `check_lyrics` | Python | validation report; ⏸ `review_lyrics`: the owner reviews the timed lyrics |
| 5 | `plan` | hosted LLM, several calls (§7) | the frame project's file `frame/projects/<id>/project.toml` and the shots' sidecar `frame/shots.json`; `current/timeline.json` |
| 6 | `check_plan` | Python | `check_shots` on the planned shots (§5.2); ⏸ `review_plan`: the owner reviews the plan |
| 7 | `scenes` | local image models, Hone Frame's run (§9) | every marked item made in file order, the demo first; ⏸ `review_scenes`: the owner accepts, picks, edits and runs in the Scenes view |
| 8 | `clips` | local video model | a raw clip per shot from its scene's picture in use (§10, §11) |
| 9 | `finish` | local upscaler + interpolation | a finished clip per shot (§11.3) |
| 10 | `assemble` | local (ffmpeg) | `video.mp4` with the song (§12) |

The gates are `review_lyrics`, `review_plan` and `review_scenes`. An unattended project passes each on its
own unless its check reports errors; at `review_scenes` it accepts every hold and takes each pick's first
picture (0027 §5).

After the scenes gate the owner may remake any shot's clip (§11.2). Stages 8 and 9 run per shot, so the dashboard shows each shot's frame and clip as soon as it exists;
models load once per stage, not per shot (decision D-005).

### 3.2 Models (defaults; each is a setting)

| Role | Default | Why |
|---|---|---|
| speech (word times) | `scribe_v2` (ElevenLabs Scribe) on the OpenAI-compatible gateway | word-level timestamps; on the owner's song 42/43 lines on every run and line starts on the singing, where `whisper-1` varied from 40 to 42 (§6, D-002, D-049) |
| lyrics editor (`lyrics`), planner (`planner`) | `claude-opus-5-5` on the OpenAI-compatible gateway | strong at long structured plans under many constraints |
| the shot list's review (`review`) | `claude-haiku-5-5` on the OpenAI-compatible gateway | a check, not a planner: reads the shot list for the feeling, once per plan (0028) |
| the scenes' image models (`frame`, a list) | `["qwen-image-2.1-turbo"]` (local, ComfyUI) | the first is the project file's `[defaults] model`; the planner may give a picture another listed model (0027); Qwen-Image-2.1 Turbo drew all ten hard epic figures right (0021); its sizes are Hone Frame's catalog's |
| clips | Wan 2.2 I2V 14B fp8 + 4-step lightx2v LoRA, SageAttention | best that fits 8 GB; owner chose "fast" |
| finish | Real-ESRGAN x2 + Lanczos, then RIFE 4.9 x2, one job (D-032) | as good as SeedVR2 to the eye, ~14x faster; 16 → 32 fps |
| vocal isolation (`vocals`) | Demucs `htdemucs` on the CPU (the `separate` extra) | the first listen hears the song's vocals, isolated once (§6, D-045) |
| lyrics alignment (`align`) | Meta's MMS forced aligner, torchaudio's `MMS_FA`, on the CPU (the `align` extra); `null` turns it off | given lyrics placed on the vocals: every line, starts on the singing (median 38 ms from the vocals' onset on the owner's song: `scribe_v2` 60 ms, `whisper-1` 600 ms early; §6, 0005, D-055) |

hone-music-video ships the ComfyUI workflows and hone-models registry entries for its local roles
(`data/workflows/`, `data/models.toml`). They are defaults: merged over hone-models' catalog and under the
user's `~/.config/hone/models.toml` and the working folder's `hone-models.toml`, which win. In 0.1 so
far: the planner (`claude-opus-5-5` through the OpenAI-compatible gateway), the judge (`claude-sonnet-5-5`, D-110; `claude-haiku-5-5`, D-086), `scribe_v2`, `scribe_v1`, `whisper-1`, `groq.whisper-large-v3` and `groq.whisper-large-v3-turbo` through the OpenAI-compatible gateway (D-018, D-048),
`qwen-image-2.1-turbo` (0021: the int8 model, the int8 Qwen3-VL 8B encoder, the VAE and the Turbo LoRA, about
21 GB; ten reference slots of which six are used, `ref_resolution` 768, 8 steps; the Qwen research license,
`commercial_use = false`), `qwen-image-edit-2511-4step` and Z-Image (the local models allowed for commercial
use, on the menu), `z-image-turbo-polish`, `wan2.2-i2v-14b` (hone-models' entry with the
library's copy of its workflow and an 8 s limit, D-033) and `esrgan-rife-x2` (D-032); the sheets and the
start frames without a cast use hone-models' packaged `z-image-turbo` (D-022). Only a workflow that
loads the Wan 2.2 I2V 14B experts is started with `--use-sage-attention` (0025 §1; D-033 narrowed).
Before any other ComfyUI model runs, the adapter reads `/system_stats`: a server started with that flag
is refused, and one that does not answer is left for hone-models to start (0025 §2, D-156).

The hosted image entries and the Gemini client of 0020 are gone with the picture menu (0027 §8): the
scenes are drawn on local models only, each item on its own `model` when it names one.

## 4. The project folder

```text
<projects>/<project-id>/
  project.json            name, created, settings, inputs (song file name, lyrics, story, sheet names),
                          approve ("ask" or "auto": unattended runs, 0004)
  input/                  song.<ext>, lyrics.txt, sheets/<name>.<ext>
  vocals/                 <model>-<key>.wav + .json   the song's isolated vocals and their record, made
                          once per song and model (D-045)
  replan.json             a re-plan of a few shots waiting for the owner (0008), until applied or discarded
  events.jsonl            the progress log: the run's events, each stage's units and every file made
                          (`units`, `version_started`, `version_made`; 0003, D-050)
  runs/video/runs/<id>/   the hone-flow run folder: every stage's output record (song, words,
                          timeline, report, cast, sheets, packs, shots, the per-shot file lists,
                          assembly), inputs, reviews and spans
  current/                the latest accepted outputs, for the dashboard and for people:
    timeline.json  cast.json  shots.json  edl.json
    edit.xml  edit.edl    the edit for DaVinci Resolve and Premiere (§12.1)
    costs.json            what the video cost so far (§13.5)
    lyrics/               owner-timing.json                      the owner's timing at the lyrics gate (0018)
                          timeline-<key>.json                    every timeline it made, never overwritten
    packs/<character>/    front.png side.png back.png portrait.png   the views and the chosen portrait
                          sheet.png  figure-N.png                the sheet cut from (a copy), every figure
      takes/              sheets-<key>.png + .json, cut-<key>.png  every sheet take, never overwritten,
                                                                 and the preview of its cut
      versions/           portrait-<key>.png + .json,            every portrait drawn and polished
                          polish-<key>.png + .json
    packs/<character>/    (a "views" project, 0020)  front.png side.png back.png portrait.png <detail>.png
                          the accepted pictures, uncut; no sheet and no figures
      takes/              <view>-<key>.png + .json               every picture of a view, drawn or uploaded,
                                                                 never overwritten
    props/<prop>/         main.png detail.png sheet.png          a prop's views and the sheet cut from (0017, D-104);
                                                                 in a "views" project main.png only
      takes/              sheets-<key>.png + .json, cut-<key>.png  every prop sheet take and its cut preview
                          main-<key>.png + .json                 or every picture of a prop ("views" project)
    scene-queue.json      the redos and uploads of scenes waiting, with scene-queue.lock beside it (0020, D-138)
    live-takes.json       the takes stage 10 made from the queue while it ran (cleared when a fork starts)
    pause.json            the owner's pause or stop of the running video, while it is asked (0022)
    uploads/<sha>.<ext>   an upload as received, before its crop (0020, D-131)
    checks/               sheet-<key>.png                        the contact sheets the start-frame check saw
                          motion-prompts.json                    the motion prompts it rewrote (§10.3, D-080)
                          still-retries.json                     each frame's rounds drawn again (§10.4, D-087)
                          sheet-retries.json                     each sheet take's rounds and verdicts (§9.1, D-121)
      sheets/             take-<key>.jpg                         the sheet takes as the judge saw them (D-120)
    shots/<shot-id>/      still.png  clip-raw.mp4  clip.mp4      the version of each the video uses
                          prompt.json                            the prompts of the take in use
                          takes.json                             every take with its files (§11.2, D-031)
      versions/           <stage>-<key>.<ext> + <stage>-<key>.json   every version made, never overwritten
                                                                 (draw, stills, clips, finish; D-034)
    video.mp4
```

Records are JSON with `format_version: "1"`. Times are integer milliseconds (`start_ms`, `end_ms`).
Every generated file is a version named after the sha256 key of what made it, kept with a record of
the model, prompt, seed, inputs (files by path and sha256) and settings; a stage run again does not
make a version that exists (decision D-009).

0020 adds optional fields only, so `format_version` stays `"1"` and a record written before reads each
as its default:

- Settings: `packs`, `quality_gate: "always"` and `models.views` (§2.3).
- `cast.json`: a character's `details` (§4.2); in a `"views"` project `sheet_prompt` is the single-figure
  prompt of its first picture.
- `Packs`: a character's `details` (`{id: path}`), and `pictures`, every picture's takes by
  `"<subject>/<view>"` as `SheetTakes` rows with the one accepted; a prop's `detail` stays `None` in a
  `"views"` project. `SheetTakes` gains `models` (the model of each take, `None` for the project's) and
  `uploaded` (whether each is the owner's own picture).
- `Take`: `model` (the registry id; `None` is the project's `models.stills`), `source` (`"generated"` or
  `"uploaded"`) and `sha` (an upload's sha256). `Redo`: `model` and `upload`. Takes without them are the
  project's model, generated, so an older run's keys do not change and the redo guard (D-071) does not
  refuse its redos.
- `current/scene-queue.json` (the requests waiting: scene, what is asked, an upload as its sha256),
  `current/live-takes.json` (scene id to its takes, and the entries taken) and `current/scene-queue.lock`.

The queue is written safely (D-138): the HTTP thread and the CLI only add to it, under an exclusive
`fcntl.flock` on `scene-queue.lock`, the file written to a temporary name and renamed into place; the
runner thread alone takes from it and writes `live-takes.json` the same way; the lock is never held
during a model call. An upload's file is checked and kept before its queue entry, a taken entry is
recorded in `live-takes.json` before it leaves the queue, so a crash leaves nothing or a complete file,
or an entry taken again as a no-op. Two requests for one scene: the later wins and the earlier stays a
take to go back to.

### 4.1 `timeline.json`

```json
{"format_version": "1", "duration_ms": 214380, "language": "en",
 "sections": [{"id": "verse-1", "kind": "verse", "start_ms": 12040, "end_ms": 41210, "notes": ""}],
 "lines": [{"id": "L001", "section": "verse-1", "text": "She waits upon the balcony",
            "start_ms": 12040, "end_ms": 15385, "heard_first": 0, "heard_last": 4,
            "words": [{"text": "She", "start_ms": 12040, "end_ms": 12310}]}],
 "instrumental": [{"start_ms": 0, "end_ms": 12040, "kind": "intro", "notes": "[Intro: soft piano]"}],
 "owner_timed": []}
```

`owner_timed` lists the lines whose start and end the owner set by hand at the lyrics gate (0018, D-113);
their words moved with them.

### 4.2 `cast.json` (retired by 0027: the frame project file holds the cast)

```json
{"format_version": "1",
 "characters": [{"id": "celina", "name": "Celina", "kind": "person", "noun": "woman",
   "cue": "Queen Celina, a fair-skinned queen with long black braids",
   "source": "make",
   "sheet_prompt": "...", "portrait": true, "first_line": "L001",
   "traits": "a woman in her mid thirties, slender and tall, long black hair in one thick braid",
   "unusual": false}],
 "props": [{"id": "mohreh", "name": "the onyx armband", "carried_by": "loren", "note": "...",
   "look": "a gold armband set with one large black onyx", "source": "make"}],
 "story": "a short summary of the story the planner read in the lyrics and notes",
 "anchor": "A still from a historical epic film, real set, a legendary ancient kingdom.",
 "world": "A legendary ancient kingdom: clay oil lamps, torches, wool, leather, bronze and iron belong; no glass lanterns, printed cloth, zips, modern shoes or anything made by machine."}
```

`traits` (each character's fixed look) and `anchor` (the kind of film, the period and the place) came
with 0014, `world` (what belongs in the story's world and what must not appear) with 0009; a cast
written before reads them as `""` (D-077, D-085). A prop's `look` (the object alone in one phrase:
shape, material, colour, count, size; what its sheet is drawn from and what its `{id}` becomes) and
`source` (`"make"` or `"given:<sheet name>"`) came with 0017; a prop written before reads `""` and
`"make"`, and gets no sheet (D-100, D-108). A character's `unusual` (0019, D-125) marks a look that is
hard to draw the same in four views; a cast written before reads `false`. A character's `details`
(0020) are `[{id, look}]`, at most four (`"ring": "a gold ring with one red stone on his left hand"`):
what must stay the same and one full-body picture is too small to carry; each becomes one close-up
picture (§9). A cast written before reads `[]`.

### 4.3 `shots.json`

```json
{"format_version": "1",
 "shots": [{"id": "S001", "start_ms": 0, "end_ms": 6210, "lines": [],
   "beat": "establishing: the palace at dusk before the first line",
   "framing": "wide", "faces": false, "cast": ["celina"], "location": "palace balcony, Vellmoor",
   "camera": "slow push-in",
   "still_prompt": "Cinematic wide shot ... {celina} stands at the balustrade ...",
   "motion_prompt": "Slow push-in. Her veil lifts in the wind; torch flames flicker; mist drifts.",
   "refs": null, "props": []}]}
```

`props` lists the props the shot shows, each written as `{id}` in its still prompt (0017, D-105); a
plan written before reads `[]`.

In `timeline.json`, `heard_first` and `heard_last` are the heard words (indices into the transcription's
words) a line is sung over; its times are theirs (D-016).

`framing` is one of `extreme-wide`, `wide`, `medium`, `close-up`, `extreme-close-up`, `insert` (an object
alone). In `cast.json`, `source` is `"make"` or `"given:<sheet name>"`. `faces` is true when a face must be recognisable; it selects the clip resolution (§11.1).

## 5. Timing and its validators

All times are integer milliseconds from the start of the song. The dashboard shows `m:ss.mmm`.

### 5.1 Lyrics checks (`check_lyrics`)

Errors (the lyrics gate cannot be approved; the owner fixes the lines' times or runs the lyrics stage
again with a note, D-015, 0018):

- every line and word lies within `[0, duration_ms]`, with `start_ms < end_ms`;
- lines are in order and do not overlap; words of a line lie inside the line and are in order;
- every line's start is within 150 ms of its first word and its end within 150 ms of its last, the
  words it is timed from: the aligned words when the given lyrics were aligned, else the heard words
  (the LLM may fix text, not move time; D-003, D-059); a line not timed from those words is an error;
  a line the owner timed by hand at the gate (`owner_timed`, 0018) is not held to its words (D-115);
- sections cover the lines; instrumental spans do not overlap sung lines.

Warnings: words the transcriber heard that no line uses; given lyrics lines that were not found in the
audio; a listen that could not be made as designed (`not-listened`: the first listen on the mix because
the vocals could not be isolated, or windows past the cap of listens again; D-045, D-046); a given line still not heard
whose gap is marked instrumental (`line-in-instrumental`: the owner checks it by ear, D-040); given
lyrics that could not be aligned (`not-aligned`, with why), or were aligned on the mix
(`not-listened`); a given line whose aligned start is more than 750 ms from the start of the heard
words it was found in (`align-disagrees`: one of the two is off the singing), or that the aligner
placed with a score under 0.3 (`align-unsure`); the owner checks these by ear (D-058).
`start-from-heard` (0030 §3): a line whose first aligned word was stretched back into the pause before
it (the same word heard more than 750 ms later, at the line's first heard word or the one before it,
and the second word within 300 ms of the next heard word) starts, with that word, where it was heard;
the warning says by how much, and the line no longer disagrees. `timed-from-heard` (0032): a line the
aligner lost, more than 750 ms from where it was heard **and** under 0.3, has its words placed over the
heard words it was found in (their lengths in the same proportions), unless that puts it over a
neighbouring line; it no longer disagrees. An `align-disagrees` of more than 3 s is an **error**
(0032): an unattended project stops at the lyrics gate.

### 5.2 Shot checks (`check_shots`)

Errors (sent back to the planner for a repair, §7.4):

- the shots are in order and **tile the song exactly**: the first starts at 0, each starts where the
  previous ends, the last ends at `duration_ms`;
- every shot is within `[min_shot_ms, max_shot_ms]`;
- **no cut inside a sung word**: a boundary may not fall strictly inside any word of the timeline;
- every line listed by a shot overlaps the shot in time; every line is listed by at least one shot;
- every cast id exists in `cast.json`; every prop id a shot lists is a prop of the cast (`unknown-prop`);
  every `{placeholder}` in a prompt names a cast member or a listed prop of the shot (0017, D-105);
- `faces: true` only with `medium`, `close-up` or `extreme-close-up` framing (§8.3);
- prompts are non-empty and within the length limit of their model.

Warnings (shown, not sent back): a cut more than 120 ms away from a line start, section start or
instrumental boundary; three or more consecutive shots with the same framing; a character missing for
more than a third of the song after being introduced; `speech`: a still or motion prompt with a word of
speech (speak, say, sing, whisper, talk, call out, recite, chant, mouth the words, lips move or form
words; whole words, any case; expressions such as smile, laugh, shout, roar, gasp or cry never warn);
`no-anchor`: a still prompt without the cast's `anchor` (none when the cast has no anchor; D-078). In a
motion prompt `speech` also names the words of the mouth (mouth, lips, jaw, teeth, breath, breathing,
voice, words), negated or not (D-088). `pace`: a shot outside the length its pace prefers, the last
shot excepted (0009, D-084). `model-limit` (0029 §2): a beat naming a body's own side ("LEFT hand", any
case, a body part after left or right) in a shot wider than a close-up, or counting more than three of a
kind (four to twelve, a dozen, a number from 4); the frame planner sends these to the review call.

Each finding names the shot, the rule and what is wrong, by how much in milliseconds (D-026). The
prompt limits are 1500 characters for the still prompt and 1000 for the motion prompt (about 512
tokens of the text encoders, with room for the placeholders; D-026). `hone-music-video check-shots`
prints every finding of a project's latest plan. Errors that would break the video (tiling, cuts inside
words, cast, placeholders, shot ids, empty prompts) keep the shot gate from being approved; the others
(shot length, prompt length, faces on wide framing, a sung word longer than the longest shot, lines
listed wrongly) the owner may approve with an explicit acknowledgement. Either way the owner can plan
the shots again with a note (D-027).

### 5.3 From milliseconds to frames

A clip is generated a little longer than its shot (§11.1) and cut at assembly. Shot `i` gets the frames
`round(start_ms * fps / 1000)` to `round(end_ms * fps / 1000)` of the output: positions are computed from
the absolute times, never by adding durations, so rounding never accumulates. At 32 fps every cut is
within ±16 ms of its planned time.

## 6. Timed lyrics

1. `transcribe`: the song's vocals, isolated once with Demucs `htdemucs` on the CPU (the optional
   `separate` extra; kept in the project's `vocals/` by model and song sha256, so a run made again does
   not separate again), go to the speech model with word timestamps; the opening of the given lyrics
   (about 400 characters of sung lines) is passed as the prompt that biases the words (D-045). Without
   the extra, or when the separation fails, the mix is heard and `check_lyrics` warns how to install
   it. When more than a third of the given sung lines are not found in what it heard, this first listen
   is made once more and the one that found more lines is kept, one without an invented time or the
   prompt echoed preferred (D-047). Output: heard words with times.
   Until hone-models has hosted transcription, a small client in this library calls an OpenAI-compatible gateway and keeps
   every call in the record (D-002, D-017).
   1b. **Listening again** (D-040, D-046): the given sung lines (not the `[bracketed]` notes) are
   matched in order against the heard words, robust to Whisper's mishearings (letters without marks, ZWNJ
   or punctuation; a run of heard words scoring at least 0.6 on difflib's ratio; Latin transliterations
   in a non-Latin line are unknown letters, the script decided once for the song; a line begins within
   40 heard words of the one before, 40 more for each line missed in a row just before it, D-046). Each run of lines not found is a gap, from the end of the found
   line before it to the start of the found line after it. A gap is cut into the fewest equal windows of
   at most 30 s, each with the lines expected in it (the gap's lines spread over the windows in order, a
   line on a boundary in both). A window's slice of the mix (500 ms more each side, inside the song) is
   cut with ffmpeg and sent to the same transcriber with those lines as the prompt (the second listen);
   when the slice's words (margins included) do not have every expected line, the same slice of the
   song's vocals is sent (the third).
   The words the last listen heard inside the window, shifted by the slice's start, take the place of
   the first listen's words there and are tidied as in step 1. At most 16 listens again per song (in
   song order; the windows and vocals listens past it are named). A reply with a word longer than 5 s (an invented time) or
   with the given lines' own transliterations (the prompt echoed back) is not taken as heard. Each
   listen is kept in `words.json` (`listened_again`, with its call). Times are still only heard words'
   (D-003).
   1c. **Alignment** (change 0005, D-055 to D-058): when the owner gave lyrics, the given sung lines are
   aligned to the song's vocals (the mix when they could not be isolated) with Meta's MMS forced
   aligner, torchaudio's `MMS_FA` bundle (`models.align`), on the CPU: the `align` extra, in this
   library behind the `Models` port (`align`) until hone-models has an alignment client, its weights
   (1.2 GB) in torch's cache as `mms_fa.pt`. The song is read with ffmpeg at 16 kHz and heard in pieces of 30 s with
   2 s more on each side. Each word is romanised with `uroman` (no language code), lower case, only the
   aligner's letters kept: Latin transliterations stay as they are, a word with no letter left is not
   aligned (D-056). A star token between the words takes what is not the text; a word is not sung
   across a pause of the vocals: when 300 ms or more of 20 ms frames 50 dB below the loudest lie between
   two of its letters, the word keeps the side with more letters, the first on a tie (D-057). The
   aligned words, tidied as in step 1, are kept in `words.json` (`aligned`). Recognition (steps 1 and
   1b) is made as before and is the cross-check: a line whose aligned start is more than 750 ms from
   the start of the heard words it was found in (the matching of step 1b) is recorded, and so is a line
   the aligner is unsure of: each word has a score (the mean probability of its letters), and a line
   whose words' scores, weighted by their length, are under 0.3 is named (D-058). Aligned on the mix,
   `words.json` says so (`not_listened`). When the aligner is off, not installed or fails, `words.json`
   says why (`not_aligned`) and the lines are timed from the heard words. Settings stored before 0005
   (without `models.align`) read as alignment off, so a project keeps the timing it was made with
   (D-059).
2. `lyrics`: **one** call to the lyrics editor with: the words to time from (the aligned words when the
   given lyrics were aligned, flagged `aligned`, else the heard words; text and times), the given lyrics
   if any, the language, and the rules: keep every time from a word (a line starts at its first word,
   ends at its last); correct misheard words using the given lyrics (aligned words are the given words
   already: only split lines and sections); split lines as the song phrases them; group lines into
   sections (intro, verse, pre-chorus, chorus, bridge, outro); mark instrumental spans. Structured
   output (JSON Schema): the lines with the range of words each is sung over, the sections and where
   the instrumental spans fall, no times; the code builds the timeline of §4.1, every time from those
   words, measured from the audio (D-016, D-059).
3. `check_lyrics` (§5.1), then the owner reviews it in the dashboard and approves it or runs the lyrics
   stage again with a note for the editor (D-015). The words stay the editor's; the times can be fixed
   by hand (change 0018, D-113 to D-116): while the gate waits, the owner sets a line's start or end (to
   the play position, or by ±100 ms and ±500 ms) and saves it (dashboard, `lyrics-timing` in the CLI,
   `hmv.lyrics_timing`). Every save is checked (whole milliseconds, start before end, inside the song,
   lines in order without overlapping) and refused whole on any problem; the line's words move with it,
   scaled within it; a section holding it spans its lines again; an instrumental span beside it fills the
   new gap. The edits are kept by line id in `current/lyrics/owner-timing.json`, each timeline they make
   as a version, and `check_lyrics` runs again on it. Approving decides the gate with the edited
   timeline (hone-flow's `edit`), so every later stage uses the owner's times as they are. Rejected with
   a note after edits, the editor is asked to change the text only; the edits apply again where their
   line ids remain, and the dashboard and the approval say which were kept and which dropped.

## 7. Planning (0027 §3, 0028)

The planner (`frame_plan.py`, `frame_calls.py`, `frame_review.py`, the prompts `data/prompts/frame_*.md`)
works from the approved timeline (with the lyrics' notes per part), the song's measured shape
(`music.py`), the story notes, the owner's **feeling** (what the viewer should feel, an optional input),
the given sheets and poses, the settings (style, aspect, pace, mood) and the guides Hone Frame provides
(`data/frame_guide/`). Feeling comes first (0028): what the viewer should feel is decided before the
shots and carried into every prompt. It makes the plan in several calls, each reply kept in
`<project>/frame/calls/` and reused when its input is the same:

1. **The story** (one call): what the whole video should make the viewer feel and its **arc** (per part
   of the song: its feel, intensity 1–5, turn and visible evidence), the characters with their looks,
   their `presence` (what the viewer should feel about them and the visible traits that do it), their
   `inner` life (what they feel, show and leak) and their variants as whole looks (a pose picture where
   the owner gave one), the objects and the places (their states as whole looks). The song's shape it
   reads: per section and instrumental span, the loudness against the song, its change from the part
   before, the voice's loudness, the words per second and the lyrics' notes; the owner's feeling wins
   over the notes, the notes over the numbers.
2. **The shot list** (one call): every shot on the song's timeline in milliseconds with its lines, its
   **focus** (0035: `face`, `figure`, `pair`, `place` or `detail`, one simple picture whose feeling has
   one carrier; code checks the characters and framings each allows and gives a face its close-up and a
   detail its part; a shot planned before 0035 gets the focus its framing and cast imply), its
   opening frame (`beat`), its one `motion`, what it leaves for the next (`ends`), what the viewer should
   `feel` and the `evidence`, framing, faces, cast (a view, a `pose` or a `detail` of a part), place,
   camera, how many pictures it takes (`one`, `count` or `prompts`), the recurring arrangement it is in
   (`setup`, declared once with its layout by the people's own sides, its first shot a wide or medium
   **master**, 0034 §4) and a scene made from an earlier scene (`from_scene`, the setup's later coverage
   from its master); no prompts yet. `check_shots` (§5.2), the bible and the camera's variety (no
   move on more than 40% of the shots, never four in a row) check it.
2b. **The review** (one call on `models.review`, Claude Haiku 5.5): reads the arc and the shot list for
   the feeling (visible evidence, a mask with its leak, a sung action not contradicted, tension that
   grows, pictures that fit the shot, one instant per opening, hard moments with takes, the models'
   limits of §8.2b with the `model-limit` warnings code found in the beats, `place_in_words` where the
   camera or a fight needs it, 0029 §2); its notes go back to the shot list as one more repair.
3. **One call per character, object and place**: each of its pictures' prompts (hero, views, close-up,
   poses, details, variants), and an item's own model when the
   project lists several; repaired up to twice (0034 §5).
4. **One call per six scenes**: each scene's **facts** first (0029 §1: every thing with its count and its
   picture, each link between two things with both ends, what must be visible, the frozen moment; not
   sent to the image model), then its prompt written from them (the things and links naming each
   reference in order, "image 1 is…"; the framing and camera; the performance from the shot's evidence
   and its characters' inner life; the light; the finish; sides only as the picture's left or right,
   every link in frame and lit), and its motion prompt from the shot's motion and camera; each batch sees
   the shot before's `ends` and the setup's layout. A shot marked `place_in_words` (an overhead,
   straight-down or worm's-eye camera, or two creatures against each other) gets only its characters as
   pictures and its place's look, light and state in words (0029 §3). A creature's hero shows its size
   beside something of known size (0029 §4). **The references are made for an edit model** (0034): the
   image model edits image 1 and takes the others as content, so a scene's pictures are its place's view
   first, then its characters, then its objects, and the scene call is told to say what changes from
   them (where a figure stands and how large, its body and face in this instant, the light). A wide shot
   without faces keeps its characters' pictures behind the place (0034's J2, its people in words, lost
   the facts and was dropped, D-182).

The code checks every prompt (its references, its length, the words the limits of §8 forbid, a size or an
aspect ratio (0034 §5), a scene's
facts written and both ends of each link named in every prompt) and asks again for the ones that fail;
more than three of a kind in a scene's facts is kept as a `model-limit` problem, not asked again; what is left is kept in the plan's `problems` and shown. It is not a
picture judge: nothing looks at a picture. The result is written as one Hone Frame project file
(`frame_toml.py`): `[defaults]`, `[demo]` with `hold = true` (a few pictures from text before anything
else), every item with its `size`, `seed`, `refs`, `prompt` or `prompts`, `count`, `hold`, `model`,
`file` (a given sheet or pose, by its path in the project) and `inputs`, each with a `# used by` comment,
and the sheets (the cast, a turnaround per character, a board per place, the storyboard). The file is
imported as Hone Frame imports one (checked whole; refs point upward), and `frame/shots.json` keeps what
the file cannot hold: each shot's times, lines, framing, faces, cast, motion prompt and clip seed, keyed
by its scene's item id. A note at `review_plan` makes the plan again with it.

## 8. The model limitations (in the planner's prompt)

This text is part of the shot planner's system prompt (`data/prompts/limits.md`), written for a model to
act on. It is kept in sync with the measured behaviour (history), and every rule says why.

### 8.1 What the shots are made with

> Each shot is made in two steps. First a still image (the shot's first frame) is drawn from your still
> prompt, using reference pictures of the characters in it. Then a video model animates that still for
> the length of the shot, guided only by your motion prompt. The video model cannot add anyone or
> anything that is not in the still, and it works at a low resolution (about 832x480).

### 8.2 Limits of the still image

> - At most six reference pictures per shot (three on some image models). A shot can show at most two
>   characters with their own references; more people appear only as unnamed extras (soldiers, crowd)
>   without references.
> - Describe what is in the frame, not the story behind it. Say what changes from the reference
>   (age, clothes, hair, injuries) or the reference wins.
> - Unusual objects (a mace with an ox's head) are drawn as the nearest common object unless a
>   reference picture of the object exists. Prefer props that read clearly.
> - No text, letters or signs in the image.
> - Avoid overlapping bodies where motion happens, and tangled two-body contact poses (cradling,
>   embracing, grappling): the video model merges the bodies and adds hands. Show one body clearly and
>   the other beside it.
> - Size, aspect ratio and frame rate are parameters of the models: never write them in a prompt.

### 8.2b What no prompt makes the still models draw (0029 §2)

> Six kinds of fact failed under every prompt and every model tried (100 hard cases, 2026-10). Plan each
> shot around them, never ask for them:
>
> 1. **A body's own side** (his LEFT hand, her RIGHT leg, an eyepatch on the LEFT eye): a close-up of that
>    one hand or leg, or no side at all.
> 2. **A grip or a bite between two bodies** (jaws on a leg, a hand holding a wrist, a blade flat on a
>    shoulder): the moment just before or after (the recoil, the mark it left), or a close-up of only the
>    touching parts.
> 3. **More than three of a kind that must be counted** (seven candles, twelve guests, five wolves): three
>    or fewer, or a number that doesn't matter ("candles along the table").
> 4. **A tear, a cut or a swollen eye**: only in a close-up of the face.
> 5. **Eyes meeting**: a two-shot at eye level; eyes on a small thing: the thing large in the frame.
> 6. **A movement state** (diving, sliding, a blade passing through): its frozen position (wings folded,
>    head down, a hand's width above the water).

The frame planner's shot-list, scene and review calls get this section and §8.3 (`frame_calls.system`,
`limits=True`). Evidence: [design/research/prompt-guide-2026-10.md](research/prompt-guide-2026-10.md).

### 8.3 Limits of the video

> - One action and one camera move per shot. Combined moves (dolly and tilt) fail. If the camera does
>   not move, write "static camera", or the model invents a drift.
> - Describe motion and camera only; the picture is already in the still. Use concrete verbs: "she
>   lowers her eyes", "the horse gallops left to right", "the veil lifts in the wind".
> - Small, physical motion works best: wind, flames, a turn of the head, walking, riding. Fast
>   or complex body motion (fighting with contact, dancing, hands manipulating objects, many people
>   interacting) degrades into blur and melting limbs. Show a fight as a single clear move (a shield
>   raised, a blow landing) and let the cut carry the action.
> - **Faces must be large.** In a wide shot a face is only ~40 pixels tall and the eyes flicker and
>   vanish. Any shot where a face must be recognisable is a medium shot, close-up or extreme close-up
>   (set `faces: true`). Wide shots show people from behind, in silhouette, small in a landscape, or
>   with faces turned away.
> - The video model may turn a head towards the camera on its own. If a person must keep their back to
>   the camera or not look at it, say so in the motion prompt ("she keeps her back to the camera").
> - At most 8 seconds per shot; a single shot does not need to be split. Very short shots (under 2 s)
>   give the motion no time to read.
> - The video keeps the first frame's composition: the camera can push in, pull back, pan or track, but a
>   new place or a new person cannot appear. A change of place is a cut.
> - Hands holding small objects, reflections, mirrors and readable text are unreliable; avoid making
>   them the point of a shot.
> - No one speaks, sings, whispers or mouths the lyrics: there is no lip sync. The video model does not
>   follow negations ("she does not speak", "her lips stay closed" make the mouth move), and naming a
>   part of the face draws the motion there. So a motion prompt **never** names the mouth, lips, jaw,
>   teeth, breath or breathing, speaking, singing, whispering, words or a voice, not even negated. A face
>   that must not talk is described only through what does move, then "her face stays still": "her eyes
>   glisten, a single tear runs down her cheek, she slowly lowers her gaze; her face stays still". A
>   smile, a laugh, a roar or battle cry is one held moment in the still prompt, not a motion.
> - Negations do nothing in a motion prompt: say what happens and what stays still, never what does not
>   happen.
> - Name what moves, how and in which direction, and who or what stays still ("he lies completely
>   still", "the dagger lies still on the grass"): the video model moves anything left unsaid.
> - Inserts use a simple camera move: a straight push-in, a pull-back or a pan; never a move "along" or
>   "around" an object.
> - No hands, people or objects enter the frame unless the shot plans it; keep it so by saying what stays
>   still, never by a negation.
> - Fire and smoke only at their sources ("the torch flames flicker"). Describe light as light ("the warm
>   glow of the torches shifts on the helmet"), never attached to a person or object.
> - Every moving crowd or group of animals gets an explicit state and direction ("the horses stand
>   still, grazing", "riders walk slowly to the right"). A crowd of small figures gets a static camera,
>   never a pan across it.

These rules map to validator checks where they can (§5.2: `faces` and framing, shot length, cast ids,
words of speech and of the mouth); the rest stay advice in the prompt. The no-speech rule holds while
there is no lip-sync capability (0014). Why negations do nothing: the clip workflow runs Wan's 4-step
LoRA at cfg 1, where the negative prompt has no effect (D-088; NAG is an open option there).

## 9. The scenes: Hone Frame's workspace (0027 §1, §2, §4)

Each project holds one frame workspace in `<project>/frame/` with one frame project, and the package
`hone_music_video.frame` re-implements Hone Frame's behaviour on it exactly; each module names the Hone
Frame code it is ported from, and Hone Frame's own acceptance tests are ported to `tests/frame/`. The
project file is the source of truth: an edit (the Scenes view, `hone-music-video frame edit`, or the file
by hand) is checked like an import, refused whole when wrong, and written back with tomlkit keeping its
comments and order. Making follows Hone Frame: import marks everything; the run makes the demo first,
then the topmost marked item; `hold` stops the run until the owner accepts; `count` waits for a pick
while the run goes on with items not made from them, except a scene's takes, which never wait: the first
is used and the others are kept (0028 §5); an item with `prompts` makes one prompt at a time, the one in
use or the first, and another only through **Run prompt N**, which keeps the picture in use and marks
nothing made from it (0033); these two are the changes to Hone Frame's behaviour; accept, pick, use an older version,
replace with a file and redo ask whether the items made from it are marked too; an item whose fields
changed since it was made, or made from an older version of a reference, is flagged but never marked by
itself; versions are never deleted; Pause and Stop cancel the picture being made; estimates come from
measured times; `notifications.jsonl` is written; sheets are composed by Pillow; prompts go to the model
byte for byte, references in order, seeds `sha256("<project>:<item>")` then `seed + k`. Every image call
goes through the library's `Models` port (`frame/models.py`), so it is recorded by hone-models; a blank
picture is refused (0025 §4).

Stage 7 (`scenes`) drives the frame project's runner: on the command line in the stage's thread, in the
dashboard on the dashboard's runner for that project. When the frame run ends waiting or done the stage
ends and `review_scenes` waits; a paused or stopped frame run pauses the video's run; a failure fails the
stage with the item's error. `review_scenes` can be approved once every scene has a picture in use,
nothing waits, nothing is marked and no frame run is busy; approving takes the scenes as they are then.

## 10. Start frames (0027 §5)

A shot's start frame is its scene item's picture in use: copied as a kept version
`current/shots/<id>/versions/stills-<sha12>.png` (its record names the scene's version) and as
`current/shots/<id>/still.png`. The clips stage reads the scenes as they are when it runs, so a scene
picked, used, redone or replaced since gets a new start frame and only its clip is made again. The other
takes of a scene with several are kept as start frames too (not `still.png`), so their clips can be made
(0028 §5).

## 11. Clips and finishing

### 11.1 Clips

Wan 2.2 I2V 14B with the 4-step LoRA, SageAttention, from the shot's start frame and its motion prompt
(`frame/shots.json`), with the seed of the shot and its clip seed. Size by the
aspect ratio: 832x480 for 16:9; **960x544 when `faces` is true** and the clip has at most 110 frames
(6.81 s; longer face clips do not fit the 8 GB card at that size, D-082; the other aspect ratios in D-030).
Length: `ceil(duration_ms * 16 / 1000) + 1` frames, at least 33 and at most 129 (8.06 s at 16 fps); the
extra frame is cut at assembly. One model session for the stage (D-005). Only the takes in use get
clips (0031): choosing another take later and remaking makes its clip and finished clip when it has
none, and reuses them when it has. With `take_clips: "all"`, after the clips of the takes in use the
other takes of each scene with several get theirs, with the same seed and motion prompt, and the
finishing stage finishes them too (0028 §5): choosing another take later and remaking makes no clip,
only the cut.

### 11.2 Remakes (0027 §7)

A scene's picture in use changes in the Scenes view (a pick, a use, a redo, a replace); a shot's motion
prompt is edited from the Clips view or `hone-music-video motion PROJECT SHOT TEXT`; a shot gets a new
clip seed with `redo PROJECT SHOTS` (the dashboard's "New clip (new seed)"). `hone-music-video remake
PROJECT` (`hmv.remake`, the dashboard's **Remake changed clips**) then forks the run from `clips` with a
run parameter `remake` one higher, so every clip whose start frame, motion prompt and seed are the same
keeps its key and its file: only the changed shots' clips and finished clips are made, and the video is
cut again. Refused while the run runs, before `review_scenes` is approved, and while a scene has no
picture in use. `assemble` cuts the video again from the finished clips without a model call (D-036).
Every version is kept and listed in the scene viewer.

**Pause and Stop** (0022). `pause` (the dashboard's **Pause**) writes `current/pause.json`; the stages
check it before each model call, so the file being made is finished and kept, and the run reports
`paused`. **Stop now** (`--now`) also ends the call being made (ComfyUI's interrupt, a hosted call no
longer waited for). In stage 7 both become the frame runner's pause and stop, which cancel the picture
being made as Hone Frame does. Resume goes on from what is made.

### 11.3 Finishing

Real-ESRGAN x2, a Lanczos resize to the output size (1920x1080 for 16:9 at 1080), RIFE x2 to 32 fps, in
one ComfyUI job per clip: one `finish` role and one workflow (D-032).

## 12. Assembly

`ffmpeg` cuts each finished clip to its frame range (§5.3), concatenates the shots in order, and muxes
the original song (re-encoded to AAC 320 kb/s only when the container needs it). The result is
`video.mp4` (H.264, `yuv420p`, CRF 17) of exactly `duration_ms`, plus an edit list (`edl.json`: shot,
clip file, first and last frame) so any editor can rebuild it.

In detail (D-035): shot `i` is the output frames `first_frame = round(start_ms * fps / 1000)` to
`last_frame = round(end_ms * fps / 1000) - 1`, both included, taken from the start of the finished clip
of the take in use; each shot is encoded once with the same settings and the cuts are joined without a
second encoding; an AAC or MP3 song is copied. A clip shorter than its shot holds its last frame
(`held_frames` in the edit list, a `clip_short` event); clips of different sizes or another frame rate
are refused; a shot under half a frame gets none. `hmv.assemble` / `hone-music-video assemble` / "Assemble again" assembles the video again
from the finished clips as a fork of the run where only `assemble` runs, with no model call: for a run
assembled by an older version (D-036).

### 12.1 The edit for editors

Beside `edl.json`, the assembly writes the same edit in two formats editors import (D-063):
`edit.xml`, Final Cut Pro 7 XML (`xmeml` version 4), which DaVinci Resolve and Premiere Pro both open,
and `edit.edl`, a CMX3600 EDL. One sequence at the video's frame rate (`fps`, non-drop timecode from
`00:00:00:00`): video track 1 holds every finished clip of the edit list, named by its shot id, at
`first_frame` to `last_frame + 1` (the editors' end is excluded), from the clip's first frame; audio
track 1 holds the song from frame 0 to its last frame. Files are linked by `file://localhost/...` URLs (percent-encoded absolute paths)
on this machine (an editor relinks them when they move). A clip shorter than its shot ends at its own
last frame, so the frames the video holds (`held_frames`) are a gap there; a shot under half a frame
has no clip. `hmv.export` / `hone-music-video export` writes them again from `current/edl.json` with
no model call, for a video assembled before 0007 (D-064). The assembly writes them from the clips it
measured and the run's `measure`; if that fails once the video is made, it is an `editor_files_failed`
event, not a failed stage (D-063).

## 13. The dashboard

### 13.1 Server

A standard-library HTTP server (no web framework), a small JSON API and static files (HTML, CSS,
JavaScript without a build step), started with `hone-music-video dashboard`. It serves one projects
folder on `localhost`: of a project's files, only `current/`, the song and the given sheets, with byte
ranges so the song and the clips can be sought (D-013). Closing it (Ctrl-C or SIGTERM) stops the busy
run and waits up to 60 seconds for the runner, so a ComfyUI that session started is stopped; a second
interrupt exits at once (0025 §3, D-160). The New video form and the project header each have a switch
for the start frames' polish (0025 §6).

**A night of videos** (0028 §6). The New video form has a **Feeling** field (what the viewer should
feel) and a **Prepare only** switch (also on the project header until the scenes start): the run makes
every hosted call (the lyrics, the plan) and stops before the scenes, shown as *prepared*.
**Run all prepared** on the Videos page (`POST /api/run-prepared`) queues every prepared project, oldest
first, set to run without stopping; nothing after the plan needs the internet. The runner keeps its queue
in `<projects>/.queue.json` (the running project first), so a dashboard started again queues it again;
a run that failed (not paused) is resumed at the end of the queue, at most twice in a row; a resume of a
project already running or queued is refused (409).

### 13.2 Views

| View | What it shows and does |
|---|---|
| Projects | every project with its stage, thumbnail and length; **New video** |
| New video | drop the song; paste the lyrics; story notes; given sheets and pose pictures with names; the settings with their defaults from `GET /api/settings`: the pace, the mood, the style (free text or one of four presets naming no era), the scenes' image models (checkboxes, the first checked the default), the other models; above Start, the models whose licence forbids commercial use (`POST /api/estimate`, a notice, never a block); what will be sent; "Run without stopping for my approval" (0004); Start |
| Overview | the song's timeline, the current gate's card with its controls, the newest start frames and clips, the pipeline of the 10 stages with live progress and the overall estimate (0003), the activity |
| Lyrics | the lines with their start and end, and their words; play a line; validator results, each under its line; at the gate, a line's timing editor (0018, D-119); the gate's controls; **Calls**: the first listen and each listen again, with model, time, price and what was heard (0030 §2) |
| Plan | the planned shots on the song's timeline with framing, cast, camera, the scene's prompt and the motion prompt; the checks under each shot; what the planner's repairs left; Approve, or plan again with a note; "Open its scene"; **Calls** (0030 §2): every kept planner call in the order made with its model, time, the repairs it was asked for and the problems the code found in its reply; a row opens the data sent, the system prompt and the reply (`GET …/calls`, `GET …/calls/<name>`) |
| Scenes | a **board** first (0030 §1): one card per shot in time order like the Clips view (the scene's picture in use, its state, beat, time and length, cast, framing, versions) under the song's timeline, then the characters', objects' and places' pictures by subject; a card opens the scene viewer over the page: Hone Frame's item panel (the picture large, what made it, every version, accept, pick, mark to run, unmark, replace with a file, use a version, its fields) beside the shot (its times, beat, feel and evidence, the lines sung over it, camera, motion prompt), ←/→ and Esc, "Open in the workspace". Then, as a tab, Hone Frame's workspace for the frame project (§9): the run bar (Run, Pause, Resume, Stop, the item being made, n of m, the estimate and its end, the licence warnings), the items in file order with their status, marks, flags and versions, the open item (accept, pick, mark to run, unmark, replace with a file, use a version, each with the dependants question; its fields saved to the file), the activity; tabs for the sheets, the project file (edited and saved, checked like an import) and the guide; above it the `review_scenes` gate, approvable once every scene has a picture in use |
| Clips | every shot's clip as it arrives, raw while it is finished, hover to play; its motion prompt; per shot "New clip (new seed)" and "Remake with the edited prompt" (only that clip), "Change its scene"; **Remake changed clips**; a click opens the scene viewer |
| Preview | the song with, at each moment, the shot that covers it, from the best file it has: the finished clip, the raw clip, the start frame (while the scenes are made, the scene's picture in use), else a dark card (0024 §3) |
| Video | the assembled video with the song; download the video, the edit list and the edit for editors (§12.1); what the video cost (§13.5); assemble again |

Every gate's controls are the same on its view and on the Overview's card (0018, D-111, D-112): a note
box always shown, Approve and "Reject with note" side by side with what rejecting does at that gate, the
reject button disabled while the note is empty, and Approve with a note written asking first ("You
wrote a note. Reject with it instead?": Reject, Approve anyway, Cancel); a typed note survives the
view's redraws. The Lyrics view approves, fixes the lines' times or runs the lyrics again with a note
(M2, D-015, 0018); the Cast view picks the
sheet takes or asks for new ones (M3); the Shots view approves the shot list (with its acceptable errors
after a confirmation) or plans the shots again with a note, each finding shown under its shot (M4; no
shot editor in 0.1, D-027); the Storyboard redoes a shot or uses an earlier take (M5), or several shots
together, or re-plans a few with a note (0008); the Clips view redoes a clip, and the scene viewer
either (0024); the Video view
plays the video, offers the downloads, shows the edit list and assembles again (M6, D-036), and what
the video cost (0007). The Overview's cards carry the same gate controls (D-111); `review_packs` is a new
card, and `review_stills` with `"always"` says the run waits so scenes can be changed (0020). The menu
is `GET /api/projects/<id>/image-models?for=…` (and `GET /api/image-models` for the New video form, which
has no project yet), a picture's redo `POST …/picture-redo`, the queue's `POST …/apply-queue`. While
the run is going, the Project view and the Overview's card show **Pause** and **Stop now**
(`POST …/pause`, `{"now": true}` for Stop; 409 when the run is not running), then "Pausing after the
file being made…" or "Stopping…"; a paused run's card says what is made and offers **Resume** (0022). The page
stays on `127.0.0.1` (§13.1).

**The scene viewer** (0024 §2, 0027 §7) opens a shot from the Clips view or the Preview: its start frame,
raw clip and finished clip as the video uses them; Compare puts the raw clip against the finished one,
played together with the song; every kept version, newest first, with the scene version a start frame
was made from; and the redo of its clip, with the cards' rules. Keys: ←/→ the shots, C compare,
Esc close. Its versions come from `GET /api/projects/<id>/shots/<shot>/versions`, read only, built from
the version records (D-009) and `takes.json`: each version's stage, kind, URL, model, seed, prompt, time,
`from` (its `inputs.image` or `inputs.video`: a polished still's draft, a raw clip's still, a finished
clip's raw clip), `takes` (the takes whose files lead back to it) and `in_use`; an unreadable record is
left out; 404 for a shot not in the plan. The take in use also shows a file its stage has not listed
yet, made from its step before (D-153).

### 13.3 Look

Modern and calm: a dark and a light theme, one accent colour, generous spacing, a single sans-serif
type, thumbnails first, live updates without reloading (server-sent events), and every long action shows
real progress from the run (never an invented percentage). Progress is counted in units, one model-made
file each, from the progress log (or the folders, for a run from before 0003), and the time left from
this run's measured time per unit, else §15's times marked "estimate" (D-051 to D-053). What is being
made has a light CSS motion (opacity and transform only; none under reduced motion); every picture and
clip opens in a viewer over the page (D-054), a shot's in the scene viewer (0024).

### 13.4 Notifications

The run tells the owner, through hone-flow's notifications (hone-flow §4.9; D-060), when it stops at a
gate (`run.awaiting_review`: "1 item awaiting review at review_lyrics"), when a stage fails
(`run.failed`: the stage and its first error line) and when the video is done (`run.completed`), at
the end of every start, resume, redo or assembly that ends so. One destination, from the environment
only (or, for a variable not set, `$HONE_ENV_FILE` and `./.env`, read as hone-models reads them):
`HONE_MV_NOTIFY_URL`, the webhook, and `HONE_MV_NOTIFY_KIND`: `slack` (the default), `mattermost`, `discord`, `http` (hone-flow's
JSON with an `Idempotency-Key`) or `telegram` (the Bot API's `sendMessage` URL with `?chat_id=`; it
takes Slack's body). Each message names the project (the run's label), the gate or stage, and the
project's page (`HONE_MV_DASHBOARD_URL`, default `http://localhost:8794`, + `#/p/<id>`). The URL is read
when a message is sent and never written into a record, a project file or a log; each delivery's
outcome is kept in the run's manifest, and a failed delivery never fails the run. Without
`HONE_MV_NOTIFY_URL` nothing is sent. The message is hone-flow's text, which also gives the run's
folder on this machine (hone-flow has no message template).

### 13.5 What a video cost

`hmv.costs` / `hone-music-video costs` / the Video view ("This video cost $X of hosted calls and Y h of GPU")
add up what is recorded (D-062); `current/costs.json` is written after every start, resume and fork
of the run (reading it writes nothing):

- **Time:** every attempt of every stage in every run of the project, from hone-flow's step records, in
  integer ms; a stage a fork copied is not counted again. Totals by where the stage runs: GPU (`sheets`,
  `packs`, `stills`, `clips`, `finish`), hosted (`transcribe`, `lyrics`, `plan_cast`, `plan_shots`,
  `check_stills`: the time waiting for them) and CPU (the rest).
- **Transcription:** each `transcribe` attempt's `words.json` (D-002; a retired attempt's from
  `attempts/<n>/output/`), its call and every listen again with their price; a failed attempt is one
  unknown call. hone-models' spans of transcriptions are not read (never counted twice).
- **Planners** (`lyrics`, `plan_cast`, `plan_shots`, the start-frame check `check_stills`, the
  drafts' checks inside `stills`, §10.4, and the sheets' judge inside `sheets`, §9.1): hone-models' `hone.models.chat` spans
  (`hone.models.cost_usd`) in its store at `${HONE_HOME:-.hone}/models/spans.db` of the process, within
  the project's time. A span naming one of the project's runs is that run's stage's (the adapter passes
  hone-flow's trace context, D-061); its time only picks the attempt, else the stage's latest. A run
  that no span names (made before 0007) takes the spans without a run that started during one of its
  planner attempts. A `stills` or `sheets` attempt counts the spans that name it and is never an unknown call. A
planner attempt with no call found, or no store at all ("no hone-models records
  found at ..."), is one unknown call (not `check_stills`, which makes none when the check is off). A call without a price is unknown too, never guessed.
- **Hosted pictures** (0020, D-134): the price of each hosted picture of `sheets`, `packs` and `stills`
  (a first picture, a view, a scene, a retry), counted from where it was recorded: hone-models'
  `hone.models.image` spans by run and stage, as the planners' calls, or, for the Gemini models, the
  version's own record of the call (D-130), by its stage and time. The price is the registry's per
  picture, so a call is counted at least. An upload costs nothing. A picture redo's dry run and the redo
  guard show `hosted_usd`, without the pictures the start-frame check might draw again; the New video
  form shows the estimate for a hosted default before Start (D-133).
- **Parts:** each stage's `first` pass, its `reruns` (attempts after a rejected gate or a failure) and
  its `redos` (forks: a redone shot, assembling again); `added_usd` and `added_ms` are the last two.

### 13.6 The bell

While the page is open it asks for the projects every 4 s. When a project starts waiting for the owner
at a gate (seen on two polls in a row, so an unattended run's gates never ring), it plays a chime made
with the Web Audio API for 15 s and shows "Waiting for you: <project> — <gate>" with Stop; once per
wait, and again at the next gate. Browsers keep sound locked until the owner clicks on the page:
"Enable sound" unlocks it and is remembered (a later visit unlocks on the first click or key), the
banner says when the sound is locked, and the header's bell button mutes it (0016, D-097).

## 14. Guarantees (acceptance cases)

Each gets a test in `tests/e2e/` that runs offline with fake models (`test_ac<N>_<slug>.py`). On the
0027 branch the cases about the cast, packs, judges, retries, start-frame takes and polish are removed
with their code (3 to 5, 7, 8, 14, 16, 17, 19 to 21, 23 to 33, 36 to 39, 47 to 50 where they are about
start frames, 54 and 58 where they are about polish, and 59); 60 to 66 are new (end of this list).

1. A song with given lyrics yields a timeline whose line times come only from measured words: the
   given lyrics aligned to the vocals, or the heard words when they are not aligned (§5.1, §6).
2. `check_lyrics` rejects overlapping lines, times outside the song and moved lines.
3. The cast planner is called once per plan, with every given sheet as an image.
4. Given sheets that cover a character are not redrawn.
5. The shot planner is called once per plan (plus at most two repairs), never per shot.
6. `check_shots` rejects gaps, overlaps, cuts inside words, shots outside the length limits, unknown cast
   and `faces: true` on wide framing; a plan that passes tiles the song exactly.
7. A rejected plan is repaired with the list of errors; after two failed repairs the run stops at the
   shot-list gate with the errors shown.
8. Every shot with a cast gets at most three reference pictures, chosen by §10.1: in a face shot each
   person's portrait comes first; with `face_refs` "by-shot" (the default) a shot without faces gets no
   portrait (older projects keep their choice).
9. Clips use the larger size exactly when `faces` is true and the clip has at most 110 frames (D-082).
10. The assembled video lasts `duration_ms` (±1 frame), and every cut is within half a frame of its
    planned time.
11. A run killed during any stage resumes without redoing finished shots.
12. Redoing one shot regenerates only that shot and re-assembles the video.
13. Settings are validated (unknown keys rejected) and never appear as words the owner had to write
    into a prompt.
14. The shot planner's request carries each character's fixed traits and the story's anchor (§7.3).
15. `check_shots` warns on speech words in a prompt (in a motion prompt also on the words of the mouth,
    negated or not) and on a still prompt without the anchor, never on expressions (§5.2, D-088).
16. A clip is made from the vision check's rewritten motion prompt, unless the owner wrote the take's
    motion prompt; an older project's clips keep their prompts (§10.3, §11.1).
17. A cut figure holds no part of its neighbour (§9).
18. The project's options (`pace`, `mood`) and the story's `world` reach the planners and the start-frame
    check as data, never as words in a prompt; a project or a cast made before keeps its plans (§2.3,
    §7, 0009).
19. A start frame whose draft has a major flag is drawn again from the check's corrected prompt before
    its polish and clip, at most `still_retries` rounds, and the best round goes on; a manual redo runs
    the same loop for its shot only; an older project draws nothing again (§10.4, 0015).
20. A prop with a sheet is drawn from it: a start frame that shows it gets its pictures by the
    reference budget (at most three; first in a prop shot; after the portraits in a face shot), and its
    placeholder becomes its look word for word; a cast without prop sheets draws as before (§9, §10.1,
    0017).
21. Every sheet take is judged in one call per round; a take with a major flag is drawn again from the
    judge's corrected prompt, at most `sheet_retries` rounds, and its best round is offered; an
    `unusual` character gets at least four takes; a character's take the judge counted with other than
    four figures is never cut into a pack; unattended, the best-scoring take goes on; an older project
    redraws nothing (§9.1, 0019).
22. The owner's timing saved at the lyrics gate is checked (order, overlaps, inside the song), kept as a
    version, and is the timeline every later stage uses; a line's words move with it (§6, 0018).
23. In a `"views"` project, stage 6 draws one picture per character and per prop, and the run waits at
    `pick_sheets`, unattended too; a redo of one picture with a chosen model draws only that picture
    with that model; stage 7 draws each accepted character's side, back, portrait and details from its
    first picture and waits at `review_packs`; the pack is the accepted pictures, uncut. A project with
    stored settings without `packs` draws and cuts four-figure sheets as before (§9, 0020;
    `test_ac23_picture_packs.py`).
24. The menu lists the local image models and the hosted ones with their estimates, only where they can
    do the job; a scene redone with a hosted model is one hosted call with the scene's references (at
    most the model's limit, the named details first), polished by the local polish model, and its cost
    is recorded (§2.4, §10, §13.5, 0020; `test_ac24_image_menu.py`).
25. An uploaded picture (a view, a prop, a scene) is cropped to its size with the crop recorded, kept as
    a version, never judged and never drawn again; a scene upload is polished. A file that is not PNG,
    JPEG or WebP, over 25 MB, smaller than the size, or for an unknown scene or picture is refused with a
    message that names the problem (§9, §10.2, 0020; `test_ac25_uploads.py`).
26. A scene redone or uploaded while stage 10 is drawing gets its new picture in the same stage, and
    every other scene's files are the ones it would have made. Scenes changed after stage 10, applied
    together, are one fork that makes only those scenes' still, clip and finished clip and the assembly;
    it is refused, before anything runs, when another scene would be made again (§11.2, 0020;
    `test_ac26_scene_queue.py`).
27. With `quality_gate: "always"` a project that asks waits at `review_stills` once every scene is
    drawn, and the scenes changed there are the ones the clips use once it is approved; an unattended
    project goes on without waiting there (§10.3, 0020; `test_ac27_stop_after_scenes.py`).
28. A sheet or scene retry draws from the judge's corrected prompt with the same model, at most the
    setting's rounds; a round drawn but not judged when the run stopped is judged on resume, and no more
    is drawn (§9.1, §10.4, 0020; `test_ac28_retries.py`).
29. A project whose default models name hosted entries makes each picture of that kind with that entry
    (the polish stays local), the New video form shows the estimate before Start, and a project stored
    without `models.views` draws its views with its `models.stills` (§2.3, §3.2, 0020;
    `test_ac29_default_models.py`).
30. A new project's settings name `qwen-image-2.1-turbo` for `sheets`, `views` and `stills` and
    `face_refs: "one-body"`; a project stored before keeps its models and `face_refs` (§2.3, 0021;
    `test_ac30_qwen_turbo.py`, `test_settings.py`).
31. A character with a carried prop gets the prop's picture as a reference of its first picture, named
    in the prompt; a redone prop redraws its carriers and no other first picture; the details are drawn
    before the views that get them (§9, 0021; `test_ac30_qwen_turbo.py`).
32. In a `"one-body"` project every shot's references hold at most one full-body view or portrait per
    character and at most `max_references` pictures; a `"by-shot"` project's references are unchanged (§10.1, 0021;
    `test_ac30_qwen_turbo.py`, `test_prompt_assembly.py`).
33. `check_shots` reports `one-body` for a shot whose `refs` name two full-body views or portrait of one
    character,
    in a `"one-body"` project only (§5.2, 0021; `test_shots_check.py`).
34. The New video form and `new` list every role whose model forbids commercial use, with its licence
    (§13.2, 0021; `test_ac30_qwen_turbo.py`, `test_image_menu.py`).
35. Real model, through the GPU lock: one first picture and one two-character scene from its
    `"one-body"` references on `qwen-image-2.1-turbo`, each under 90 s (0021; `tests/gpu/test_qwen_turbo.py`).
36. Pause while stage 10 draws: the picture being made finishes and is kept, no other model call
    starts, the run is `paused`; Resume makes only the rest, no file twice (§11.2, 0022;
    `test_ac36_pause.py`).
37. Stop now while a local picture is made: ComfyUI is interrupted, nothing of that picture is kept, the
    run is `paused`; Resume draws it again and nothing else twice (0022; `test_ac36_pause.py`).
38. Stop during a hosted call returns within seconds; a pause during one takes effect when it answers;
    a pause of a run that is not running is refused (409, `RunStateError`) (0022; `test_ac36_pause.py`,
    `test_dashboard_pause.py`).
39. A scene redo on a paused run (CLI, API or dashboard) makes only that scene's new still, and its clip
    once past `review_stills`, and the run stays `paused`; Resume makes none of it again and the video
    uses the new take (0022; `test_ac36_pause.py`, `test_dashboard_pause.py`).
40. A pause request older than the run never stops it (0022; `test_ac36_pause.py`).

(41 to 46 are reserved by the proposed 0023.)

47. A shot's versions request lists every kept version with its stage, URL, model, seed, `from` and
    takes; a polished still names its draft, a clip its still; a version shared by two takes (a new
    seed keeps the still) names both; the take in use's chain is marked; a version no take leads to has
    no take; an unreadable record is left out; an unknown project or shot is 404; it writes nothing
    (0024; `test_dashboard_versions.py`).
48. The Preview shows each shot's furthest file of the take in use (finished clip, raw clip, polished
    frame, draft, nothing), and a file that arrives changes that shot's choice while the song plays
    (0024; `test_dashboard_preview_page.py`).
49. The Storyboard shows only start frames and the Clips view only clips, and every control of the
    Storyboard before 0024 is on one of them (0024; `test_dashboard_scene_page.py`).
50. A redo from the scene viewer sends the same request as the card's, so it is queued, made at once or
    refused under the same rules (0024; `test_dashboard_scene_page.py`).
51. A ComfyUI image model on a server started with `--use-sage-attention` is refused with the message of
    §2. Nothing is drawn or kept. A Wan model on the same server runs (0025; `test_ac51_server_check.py`).
53. Closing the dashboard during a session stops the runner, and the ComfyUI it started is stopped
    within 60 seconds (0025; `test_ac53_dashboard_close.py`).
54. A blank picture from a draft, a polish or a pack is refused, not kept and not put in use. A redo
    that gets one fails with the message. An upload is not checked (0025 §4, D-158;
    `test_ac54_blank_output.py`).
55. A blank clip is refused the same way. A dark picture that is not one colour is kept (0025;
    `test_ac54_blank_output.py`).
56. Only the Wan 2.2 I2V 14B workflow gets `--use-sage-attention`; another ComfyUI video model and every
    image model get a plain server (0025; `test_ac51_server_check.py`).
57. A clips session records the SageAttention version (`2.2.0`, `1.0.6` or `unknown`) on the clip's
    version, and a 1.x version runs as before (0025, D-157; `test_ac51_server_check.py`).
58. With polish = "off" no polish call is made, each start frame in use is its draft, and the clips are
    made from it. After the polish is switched on, a redo that draws a new start frame polishes only that
    shot; every other shot keeps its start frame and clip (D-155; `test_ac58_polish_off.py`).
59. Settings stored without `polish` read `on`: their start frames' keys do not change, and nothing is
    made again (0025; `test_ac58_polish_off.py`).

60. The plan is made in a story call, a shot-list call, one call per subject and one per six scenes; a
    run again calls only for what it lacks; a note calls again (0027; `test_ac60_frame_pipeline.py`).
61. The project file holds `[demo]`, `hold`, `count`, `prompts`, `refs`, `file`, `inputs`, a per-item
    `model` when the project names several, a scene made from a scene, a pose picture and the sheets;
    Hone Frame's import accepts it, its refs point upward.
62. The frame workspace behaves as Hone Frame's: its acceptance tests ported to `tests/frame/` pass.
63. An edit of the project file is checked like an import, refused whole when wrong, written back with
    its comments kept; a changed item is flagged, never remade until marked.
64. Pause and Stop in stage 7 cancel the picture being made, and the run shows as paused.
65. Each shot's start frame is its scene's picture in use; a change of one scene, or of its motion prompt,
    remakes only that shot's clip and finished clip, the video is cut again, every version is kept.
66. A project stored before 0027 opens, its retired settings dropped; its `resume` keeps the lyrics
    stages and continues into `plan` (`tests/integration/test_old_runs.py`).
67. The song's shape is measured per part (loudness, change, voice, words per second) with the lyrics'
    notes; the bible call gets it with the owner's feeling, and its arc must cover every part; the shot
    list's camera is varied; the review call's notes go back to the shot list; each scene call gets the
    shot's feel, evidence, motion, the shot before's end and its setup; poses and details are pictures of
    their own; variants and states reach the writers whole (0028; `tests/unit/test_feeling_plan.py`).
68. A scene's takes never wait for a pick; only the take in use gets a clip, and another take used and
    remade gets its clip when it has none (0031); with `take_clips: "all"` each take gets its clip and
    finished clip, and another take used and remade makes no clip, only the cut (0028 §5; `tests/e2e/test_ac60_frame_pipeline.py`,
    `tests/integration/test_overnight.py`).
69. A prepared project stops before the scenes with every hosted call made, also through approved
    gates, and goes on when resumed; "Run all prepared" runs every prepared project, oldest first, one
    after another, unattended; a failed run is resumed by the runner at most twice; the queue a stopped
    dashboard left is picked up when it starts (0028 §6; `tests/integration/test_overnight.py`).
70. A scene reply without its facts, or with a link whose end a prompt does not name, is asked again;
    more than three of a kind is kept as a problem; a beat naming a body's own side outside a close-up,
    or counting more than three, warns and reaches the review call; a shot with `place_in_words` gets
    only its characters as pictures and its place in words; the shot-list, scene and review calls carry
    the six limits (0029; `tests/unit/test_still_guideline.py`).
71. A line whose first aligned word was stretched into the pause before it starts where that word was
    heard, and the lyrics check names it; a line recognition heard otherwise is not moved (0030 §3;
    `tests/unit/test_alignment.py`). A planner call is kept with what was sent and the problems found
    in its reply, and the dashboard lists the calls in the order made and opens each; a call kept
    before 0030 still reads (0030 §2; `tests/unit/test_planner_calls.py`,
    `tests/integration/test_dashboard_calls.py`). The Scenes board and viewer are checked by hand in a
    browser (0030 §1).
72. A line the aligner lost (more than 750 ms from where it was heard, with a score under 0.3) is timed
    from its heard words unless that puts it over a neighbour; a confident line more than 3 s from where
    it was heard is a lyrics error (0032; `tests/unit/test_alignment.py`).
73. An item with several prompts makes one: the prompt of its picture in use, else the first; running
    another prompt makes only that prompt's picture beside the one in use and marks nothing made from
    the item (0033; `tests/frame/test_ac16_prompts.py`).
74. A scene's references are its place's view first, then its characters, then its objects, and the
    scene call gets them numbered in that order; a `place_in_words` scene has only its characters, a
    `from_scene` scene only that scene (0034 §1; `tests/e2e/test_ac74_scene_references.py`).
75. A `wide` or `extreme-wide` shot with `faces: false` keeps its characters' pictures behind the place
    (0034 §2 dropped, D-182; `tests/e2e/test_ac74_scene_references.py`).
76. (Removed with 0034 §3: expression close-ups lost the facts and did not carry the feeling, D-181.)
77. The first shot of every setup is `wide` or `medium`, or the shot list is sent back (0034 §4).
78. A `kind`, `finish`, demo prompt or any prompt that names a size or an aspect ratio is sent back; a
    subject prompt is repaired twice before what is left is kept (0034 §5).
79. The review call sees which shots are made `from_scene` (0034 §4, D-182;
    `tests/unit/test_still_guideline.py`).
80. Every planned shot has one of the five focuses; a shot whose cast, framing or faces its focus does
    not allow is sent back (0035 §1; `tests/unit/test_focus.py`, `tests/e2e/test_ac80_simple_scenes.py`).
81. A shot's references follow its focus: a `face` the place and the character's close-up, a `detail` the
    character's part (0035 §1; `tests/unit/test_focus.py`).
82. The scene and review calls are given each shot's focus (0035 §3; `test_ac80_simple_scenes.py`).
83. A shot list kept before 0035 reads, each shot given the focus its framing and cast imply (0035 §6;
    `tests/unit/test_focus.py`).
84. The shot list's, review's and scene call's instructions name every focus; the retired rules
    (`place_in_words`, hard moments, three-person casts) are not in the shot list's (0035 §4;
    `test_ac80_simple_scenes.py`).

## 15. Known limits (0.1)

- On 8 GB, faces in wide shots stay weak; true 720p needs a bigger GPU (§8.3 plans around it).
- About 8 hours for a 5-minute song on the reference machine (history). Measured in M5 through the
  library (RTX 4060 Laptop 8 GB, three 5 s shots, 2026-10-10): a start frame with a cast 103 to 125 s
  (Qwen 4-step at 1024x576, the first including the model load) plus 17 to 26 s of polish; a start
  frame from text 23 s; a 5 s clip 222 s at 832x480 and 318 s at 960x544 (Wan with SageAttention, load
  included); its finishing 73 to 95 s (Real-ESRGAN x2 + RIFE to 1920x1080 at 32 fps); ComfyUI starts in
  10 to 16 s per stage. Whole-GPU peaks: 7.3 GB for the stills, 7.7 GB for Wan, 1.6 GB for the finish.
  On Qwen-Image-2.1 Turbo (new projects, 0021) a first picture takes about 18 s at 832x1248 and a scene
  about 50 s at 1024x576 with four references read at 768 (the same card, 7.0 to 7.5 GB peak), against
  Qwen-Image-Edit's 141 s: stage 10 of a 60-shot video about an hour instead of two and a half, before
  retries. So a 5 s shot with a cast takes about 7 minutes on Qwen-Image-Edit, one with faces about 9; an extra start-frame take
  (`pick_best_of`) about 2 more (D-069). The start-frame check is one hosted call: 38 s and 0.10 USD for
  16 start frames, about 0.2 USD for 60, about 0.4 USD with best of 3 on the shots with faces; at most
  144 start frames per check (D-066). With Claude Sonnet 5.5 (new projects, D-110) a check of 59 start
  frames took 110 s and about 0.23 USD and found all 7 frames Opus flagged major; Haiku 5.5 took 41 s
  and 0.008 USD but found 3 of them (D-089); each round of
  the drafts' check (§10.4) is a call like it, and each frame drawn again about 2 minutes of GPU. The
  assembly of a 5-minute
  video (60 shots of 5 s at 1920x1080, 32 fps) takes about 77 s on the CPU (i9-14900HX, 32 threads; fewer cores take longer; D-035).
- Editors: 32 fps is not a standard timeline rate of DaVinci Resolve or Premiere Pro; the edit says 32
  (the video's frames), and how each editor takes it is not yet checked with the editors themselves
  (§12.1, D-063).
- When nobody needs to decide a gate (`pick_sheets` and `review_packs` when every character has a given
  sheet and no prop needs a picture, `review_packs` in a `"sheet"` project, `review_stills` unless
  `quality_gate` is `"always"` or `"ask"` and a start frame in use is flagged, and every gate of an
  unattended project except `pick_sheets` and `review_packs` of a `"views"` project) it passes on its own just after the run stops there, but that stop has
  already been notified as waiting for the owner, after every start, resume, redo, use and assembly
  (§13.4, D-060, D-067, D-075). With the defaults, every run and every redo sends one such message at
  `review_stills`.
- A run made before 0007 has its planner calls found by time: another tool's chat call recorded in
  the same store while one of its planner stages ran would be counted too (§13.5).
- Whisper mishears sung words; given lyrics improve it a lot; without them the owner should expect to
  correct some lines.
- hone-models has no hosted speech provider yet; an in-library client stands in (D-002). It has no
  vocal separation or forced alignment either; Demucs and the MMS aligner run in this library behind
  the same port (D-041, D-045, 0005).
- Forced alignment is late by 300 to 450 ms on a few soft onsets, and can misplace a word held at the
  end of the song (the owner's last "Lo-ren-am…"); the cross-check names a line only when recognition
  found it (D-055, D-058).
