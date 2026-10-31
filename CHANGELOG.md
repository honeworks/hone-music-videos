# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow semantic versioning. Why the
design changed is in [`design/changes/`](design/changes/).

## [Unreleased]

### Added

- **Experimental: simple scenes for the story and the
  feeling** ([0035](design/changes/0035-simple-scenes-for-the-story-and-the-feeling.md)). Every shot
  is now one simple picture with one focus: a face, a figure in its place, a pair of people, the place
  alone, or one detail. The planner tells the song's story as a sequence of these, comes closer as the
  song grows stronger, and carries the feeling in the one thing each focus shows (the eyes, the posture,
  the distance between two, the light, the state of a thing). Fights, crowds and other moments the image
  models draw badly become a sequence of simple shots instead of one hard picture. Code checks each
  shot's focus, and the planner's instructions are shorter. Re-plan a project to use it.

- **Experimental: scene references made for an edit
  model** ([0034](design/changes/0034-scene-references-for-an-edit-model.md)). Qwen-Image 2.1 edits its
  first picture and takes the others as content, so every scene now gives the place first, then the
  characters, then the objects, and the scene writer says what changes from them. Measured on 100 hard
  cases ([results](design/research/scene-references-2026-10.md)): about four scene pictures in ten come
  out fully right where one in four did, with fewer figures that look pasted in from a studio portrait.
  A recurring arrangement opens on a wide or medium master and its closer shots are made from it; the
  review now sees which shots are. Size and aspect words in a prompt are sent back, and a subject prompt
  gets two repairs. Two parts of the proposal were measured and dropped: wide shots with their people
  in words (they lost the facts) and expression close-ups (they did not carry the feeling). Re-plan a
  project to use it.

- **Experimental: feeling first, takes overnight, and
  a night of videos** ([0028](design/changes/0028-feeling-first-planning-and-overnight-queue.md)).
  The planner now decides what the viewer should feel before the shots: the song's shape is measured
  from the audio (loudness, drops, the voice, words per second), the lyrics' notes are kept per section,
  and a new optional **Feeling** field says what the owner wants felt. The story call writes the arc
  over the song's parts and each character's presence and inner life; the shot list gives every shot
  its opening frame, one motion, what it leaves, its feeling and the visible evidence; a review call on
  Claude Haiku 5.5 reads it for the feeling and sends it back with notes; the camera must vary. Poses
  and details of a character get pictures of their own, variants and states are whole looks, and
  recurring two-person arrangements are declared once. A hard scene's takes never wait for a pick and
  each gets its clip overnight, so choosing another take in the morning only cuts the video again.
  **Prepare only** makes the hosted calls and stops before the scenes; **Run all prepared** runs every
  prepared video one after another, unattended and offline; the dashboard keeps its queue across a
  restart and resumes a failed run up to twice.

- **Experimental: Hone Frame is the only scene
  pipeline** ([0027](design/changes/0027-hone-frame-is-the-scene-pipeline.md), after
  [0026](design/changes/0026-frame-scenes.md)). After the timed lyrics, the planner makes the plan in
  several calls (the story, the shot list, one call per character, object and place, one per six
  scenes), checks every prompt and writes a Hone Frame project file (`[demo]`, holds, counts, several
  prompts, references, given files and poses, per-item models, the sheets). The scenes are made by Hone
  Frame's behaviour, re-implemented in `hone_music_video.frame` with Hone Frame's own acceptance tests
  ported: marks, the demo first, holds, picks, accept, use, replace and redo with the dependants
  question, versions never deleted, edits written back keeping the file's comments, measured estimates,
  notifications, Pillow sheets, Pause and Stop cancelling the picture being made. The dashboard has a
  **Plan** view and a **Scenes** view (Hone Frame's items view, ported); `hone-music-video frame ...`
  does the same from the command line. Each shot's start frame is its scene's picture in use; a scene
  changed later, a motion prompt edited (`motion`) or a new clip seed (`redo`) makes again only that
  clip with `remake`. The run has 10 stages and 3 gates; `new --pose` gives pose pictures.
- **Removed on that branch:** the cast planner, sheets, packs, the cutter, prop sheets and details, the
  one-call shot planner with its repairs and re-plan, the sheet judge, the start-frame check, its gate,
  retries and best-of, motion rewrites, the polish, the picture menu with hosted image models and
  uploads, takes and the scene queue, and the commands `pick`, `retake`, `image-models`,
  `redo-picture`, `apply-queue`, `replan` and `use`. A project stored before keeps its lyrics; its
  retired settings are dropped and its `resume` continues into the new plan.
- A `polish` setting (`hone-music-video new --polish on|off`, a switch on the New video form and one in
  the project header). New projects leave start frames as drawn; a project stored without the setting
  keeps polishing. A redo that draws a new start frame remembers the setting at that moment
  ([0025](design/changes/0025-comfyui-server-per-model.md)).
- A blank picture or clip from a model is refused and not kept.
- Before a ComfyUI model that wants a plain server runs, the adapter reads the server's command line and
  refuses one started with `--use-sage-attention`.
- `HONE_COMFYUI_PYTHON`: ComfyUI's Python, so each clip's record can show the SageAttention version.
- The dashboard's Storyboard is split in two: **Storyboard** shows the start frames (tagged draft or
  polished) and the new **Clips** view the clips (tagged raw or finished), each with its own redo. A
  click on a shot opens the **scene viewer**: its draft against its polished frame (a wipe or side by
  side), its raw clip against its finished clip with the song, every version of the shot by take, and
  Redo right there. A new **Preview** tab plays the song with each shot's best file so far (draft,
  polished frame, raw clip or finished clip), from the first drafts on
  ([0024](design/changes/0024-scenes-clips-and-preview.md)).
- **Pause** and **Stop now** a running video from the dashboard (or `hone-music-video pause [--now]`):
  Pause finishes the picture or clip being made, Stop ends it too (it is made again on Resume); the run
  shows as paused and **Resume** goes on from what is made. A scene redone on a paused run is made at
  once and the run stays paused ([0022](design/changes/0022-pause-and-stop.md)).
- An open Redo on the Storyboard keeps its edited prompts while the page updates.
- The Lyrics view's timing has "Move the following lines too": a nudge or "Set … here" then moves the
  lines after it by the same amount (moving a start moves the whole line).

### Changed

- **Experimental: clips only for the picked takes**
  ([0031](design/changes/0031-clips-only-for-picked-takes.md)). A scene's other takes no longer get
  clips overnight (107 extra clips on one song); picking another take and remaking makes its clip when
  it has none. The setting `take_clips: "all"` brings back 0028 §5.
- **Experimental: one prompt at a time**
  ([0033](design/changes/0033-one-prompt-at-a-time.md)). An item with several prompts makes only the
  first (or the one in use); **Run prompt N** in the item panel (`hone-music-video frame run-prompt`)
  makes another beside the picture in use, without marking anything made from it; **Use this version**
  then asks about the dependants as before.

### Fixed

- **Experimental: lines the aligner lost**
  ([0032](design/changes/0032-lines-the-aligner-lost.md)). A line placed far from where it was heard
  and with a low score (an outro put 32 s early, inside a guitar solo) is timed from the heard words; a
  confident line more than 3 s from them is a lyrics error, so an unattended run stops at the lyrics.

- The dashboard showed a project made by `hone-music-video new` as "Starting" with a spinner, and
  could not start it: it now shows **Not started** with a **Start** button (D-179).
- The Plan view's Calls panel shows each planner call as it comes back; it had been hidden until the
  whole plan was made, so a 15-minute plan showed nothing.
- The Preview showed nothing while the scenes were made: a shot's start frame was kept only once every
  scene had a picture. It now shows each scene's picture in use as soon as it has one.
- The dashboard refuses a resume (409) while the project is running or waiting its turn; a second one
  had waited behind the run, shown it as `queued` for hours and would have run once more after it.
- Black start frames from a ComfyUI left running with SageAttention: the picture models are refused on
  that server, and a blank file is not kept.
- A scene redo that asks for nothing is refused when it is sent, and a queued redo that cannot be made
  is dropped with a note in the activity feed while the scenes go on; one such redo used to stop the
  scenes stage and every run after it (D-147). The Storyboard's redo waits for an edited prompt.

- A note typed at a review could be lost: the Lyrics view's note box sat in a collapsed "run again" box
  under a large Approve, which never sent a note, so "timing is not accurate" was approved with an empty
  note. Every review now has the same controls on its view and on the Overview's card: a note box
  always shown, **Approve** and **Reject with note** side by side with what rejecting does there, the
  reject disabled while the note is empty, and Approve with a note written asking first; the note
  survives live redraws ([0018](design/changes/0018-lyrics-gate-and-timing.md), D-111, D-112). The
  API's approve now keeps the note it is sent.

### Changed

- New projects are not polished by default. Only the Wan 2.2 I2V 14B workflow gets SageAttention.
  Closing the dashboard stops its run and waits for it first. The docs build SageAttention 2.2
  ([0025](design/changes/0025-comfyui-server-per-model.md)).
- New projects draw every picture (first pictures, views, scenes) on Qwen-Image-2.1 Turbo
  (`qwen-image-2.1-turbo`, local, about 50 s a scene against 141 s), with up to six references and one
  picture of each character in a scene (a full body, or its portrait in a face shot) (`face_refs: "one-body"`): a character's carried props go into its
  first picture, its details into its side view. The model is under the Qwen research license
  (no commercial use): `new` and the New video form say so. Projects made before keep their models
  ([0021](design/changes/0021-qwen-image-2.1-turbo.md)).
- New projects default to separate pictures (`packs: "views"`); projects made before keep the four-figure
  sheets and the cutter (`packs: "sheet"`) and their settings read as before. In a new project
  `pick_sheets` and the new `review_packs` always wait for you, also when it runs without stopping for
  approval; no take is refused for its figure count there.
- `redo` on a running project queues the change instead of refusing it.
- New projects' start-frame check is Claude Sonnet 5.5 (`claude-sonnet-5-5`, OpenAI-compatible gateway): in a bake-off on
  the first run's 59 frames it caught the wrong characters and the objects out of the story's world that
  Haiku 5.5 missed, at about 0.23 USD a check (D-110). Haiku stays in the registry.

### Added

- The owner chooses how each picture is made ([0020](design/changes/0020-owner-sheets-and-frames.md),
  D-128 to D-138):
  - **A menu for every picture**: the local image models, the hosted ones (Qwen, Seedream, FLUX,
    GPT Image, Gemini) with an estimate, and **Upload my own picture** (PNG, JPEG or WebP, checked, cropped
    to size, never judged). `hone-music-video image-models`, `hmv.image_models`,
    `GET /api/projects/<id>/image-models`.
  - **Separate pictures as the packs**: one picture per character (front, or side for an animal) and per
    prop, then each character's side, back, portrait and up to four details (`details` in the cast plan,
    named in a shot's `refs`) drawn from the accepted first picture, a new gate `review_packs`, and
    `redo-picture` / `hmv.redo_picture` / the Cast view's Redo (a note and a model) and Upload for any one.
  - **A scene with a model or an upload**: `redo --model ID`, `redo --upload FILE`; every scene is still
    polished locally.
  - **Default models**: `models.views` (new) beside `models.sheets` and `models.stills`, any of them
    hosted: `new --sheets-model`, `--views-model`, `--stills-model`, and the New video form, with the
    estimate for the whole video before Start. Hosted pictures are counted in `costs`.
  - **Stop after the scenes**: `quality_gate: "always"`, `new --stop-after-scenes`.
  - **Change a scene while the run is busy**: a redo or an upload sent during the run is queued; the
    start-frame stage takes it in the same stage, later ones are made as one fork by `apply-queue`
    (`--dry-run` for the estimate), `hmv.apply_queue` and the Storyboard's **Make these now**.

- The owner's timing at the lyrics gate ([0018](design/changes/0018-lyrics-gate-and-timing.md), D-113
  to D-119): set a line's start or end to the play position or nudge it by ±100/±500 ms in the Lyrics
  view, then **Save timing** (`POST /api/projects/<id>/lyrics-timing`, `hone-music-video lyrics-timing
  <project> L012=77300-81200`, `hmv.lyrics_timing`). Saves are checked (whole ms, in order, no overlap,
  inside the song) and refused whole on any problem; the words move with the line; `check_lyrics` runs
  again (an owner-timed line is not held to its heard words). The edits and each timeline they make are
  kept in `current/lyrics/`; approving makes the edited timeline the gate's output, used by every later
  stage. After a rerun with a note the edits apply again where their line ids remain, and the dropped
  ones are named. `Timeline` gains `owner_timed`.

- The judge checks the sheets ([0019](design/changes/0019-sheet-judge.md), D-120 to D-127): with
  `quality_check` on, every sheet take (characters and props) is judged in one call per round by
  `models.quality`: the figures counted, each view's direction, each fixed trait in every view, the
  backdrop, a score and flags (`figure-count`, `wrong-trait`, `inconsistent-views`, `extra`). A take with
  a major flag is drawn again from the judge's corrected prompt, up to `sheet_retries` rounds (new
  setting, 0 to 5, default 2; `new --sheet-retries`, the New video form), every round kept
  (`current/checks/sheet-retries.json`) and logged (`sheet_retry`); its best round is offered. The Cast
  view shows each take's score, flags and retries; the best take is offered first (and goes on
  unattended); a character's take counted with other than four figures cannot be picked. The cast
  planner marks hard-to-draw characters `unusual`: they get at least four takes. Older projects read
  `sheet_retries` 0.
- Prop sheets ([0017](design/changes/0017-prop-sheets.md), D-100 to D-109): a prop gets a fixed `look`
  and `source`; each prop with a look is drawn on `prop_sheet_takes` sheets (default 4) beside the
  characters', picked at `pick_sheets` (`pick --take ruby-token=2`, the dashboard's Cast view) or given
  with `--sheet`, and cut into `current/props/<id>/main.png` and `detail.png`. Shots list their `props`;
  a `{prop-id}` becomes the prop's look word for word and brings its pictures within the reference
  budget (at most three; first in an insert or a close-up without faces; after the portraits in a face
  shot). A shot without a cast that shows a prop is drawn from its pictures. `check_shots` errors on
  `unknown-prop`; the start-frame checks flag `wrong-prop`. Casts made before have no looks and draw as
  before.

- Project options ([0009](design/changes/0009-project-options.md), D-084, D-085): `pace` (`calm`,
  `balanced`, `energetic`) and `mood` (free words, any language), chosen when a project is made (`new
  --pace --mood`, the API's `settings`), given to the planners as data; `check_shots` warns `pace` on a
  shot outside the pace's length. The cast planner writes the story's `world` (what belongs in it and
  what must not appear); the shot planner and the start-frame check read it, and `anachronism` now
  means "out of the story's world". The planners' prompts no longer suggest a period: the anchor and
  the world come from the story. `GET /api/settings` lists the paces.
- Start frames that heal themselves ([0015](design/changes/0015-still-retries.md), D-087): with
  `still_retries` (0 to 5, default 2) the drafts are checked before the polish, and a frame with a major
  flag is drawn again from the check's corrected prompt, up to that many rounds; the best round goes on.
  Every round is kept (`current/checks/still-retries.json`) and logged (`still_retry`); a redo's new
  still goes through the same loop; the checks' calls count in the costs.
- A registry entry for Claude Haiku 5.5 (`claude-haiku-5-5`, OpenAI-compatible gateway), the start-frame check of new
  projects (D-086, D-089).

### Changed

- The start-frame check's prompt is a strict judge: a fixed list per frame, evidence for every flag,
  one severity rule; new flag kinds `off-mood` and `composition` (D-086).
- A motion prompt never names the mouth, lips, jaw, teeth, breath, speech or words, not even negated:
  the clip model runs at cfg 1 and moves the mouth it is told about (D-088). The planner's limits and
  the check's rewrite say so, `check_shots`' `speech` warning names those words in a motion prompt, and
  a rewritten motion prompt with them is dropped.
- The dashboard rings a bell (15 s, made in the browser) and shows "Waiting for you: <project> —
  <gate>" with Stop whenever a project starts waiting for you; once per wait, with "Enable sound" for
  the browser's audio lock and a mute button
  ([0016](design/changes/0016-dashboard-bell-and-options.md), D-097).
- The New video form sets the pace, the mood (any language, words to add by a click), a style preset to
  start from and the start-frame retries, and shows what it will send (D-096).
- At Review the start frames, each flagged frame has "Retry this frame", and every frame shows its
  automatic retries (D-098).

### Fixed

- A failed stage that a resume makes again shows `running`, not `failed`, while the run is live: the
  dashboard showed every new clip as failed after a resumed failure (D-083).

### Changed

- A face clip longer than 110 frames (6.8 s) is made at 832x480 instead of 960x544: longer ones ran
  out of memory on the 8 GB card (D-082).
- Prompt and reference fixes from the first real run ([0014](design/changes/0014-prompt-and-reference-fixes.md),
  D-077 to D-081). The shot planner's limits say that no one speaks or sings (no lip sync), what stays
  still, that nothing enters the frame unplanned, where fire is, how crowds move, and to avoid tangled
  contact poses. The cast plan gains each character's `traits` and the story's `anchor` (the kind of
  film, the period and the place); the shot planner gets both and begins every still prompt with the
  anchor (an older cast sends its sheet prompts' descriptions as traits). A new project chooses the
  references by kind of shot (`face_refs: "by-shot"`, the new default): the portraits first in a face
  shot, no portrait in any other. The start-frame check also rewrites each motion prompt to its frame
  as drawn (`rewrite_motion`, default on; the clip uses the rewrite unless the owner wrote the prompt)
  and flags `anachronism`; the Storyboard shows both prompts. `check_shots` warns `speech` and
  `no-anchor`. Projects made before keep their `face_refs` and rewrite nothing; a re-plan on one gives
  only the changed shots the new references.


- The default speech model is ElevenLabs' `scribe_v2` on the OpenAI-compatible gateway (D-049): on the owner's song it found
  42 of 43 lines on every run, with line starts on the singing, where `whisper-1` varied from 40 to 42
  (design/history/0001). New registry entries `scribe_v1`, `scribe_v2`, `groq.whisper-large-v3` and
  `groq.whisper-large-v3-turbo` use the same client; a call's cost is the gateway's own estimate when the
  reply has one (D-048).
- Start-frame quality (change 0006). A shot whose faces must be recognisable (`faces`, medium or
  closer) gives each person's portrait as the first reference and says the face is the portrait's
  (D-065), so its start frame is drawn again in a run that makes it again. A new stage `check_stills`
  (stage 11; the run has 14 stages and 5 gates) checks every start frame in one hosted vision call
  with JPEG contact sheets (at most 144 start frames): scores and flags (anatomy, wrong or missing character, extra people, text, an
  unwanted face, off-style) are stored as its record and shown on the Storyboard (D-066). A new gate
  `review_stills` waits only with `quality_gate: "ask"` and a flagged start frame in use (D-067).
  `pick_best_of` (2 or 3, off by default) draws more takes of the chosen shots (`pick_shots`) and the
  check picks the best; the New video form and the CLI warn with the GPU time it adds (D-068, D-069).
  New settings `face_refs`, `quality_check`, `quality_gate`, `pick_best_of`, `pick_shots` and
  `models.quality`. Projects and runs made before keep their behaviour: their stored settings mean
  `face_refs: "front-first"` and `quality_check: false`, resuming such a run forks it and reuses every
  finished stage (`run_forked_for_new_version`), and a redo or a use that would make another shot
  again is refused, naming the shots (the one guard of 0008, D-071). Only a major flag stops the run
  at `review_stills`. A project that runs unattended (0004) approves `review_stills` like any gate; a
  fork (a redo, a use, assembling again) passes the gates nobody needs to decide, as a start does.
  The start-frame check's call counts in what a video cost (0007).
- The finishing roles `models.upscale` and `models.interpolation` are replaced by one `models.finish`
  (`esrgan-rife-x2`, D-032). New settings that name the old ones are refused with what replaced them;
  projects and runs made before keep opening (the two keys are dropped when stored settings are read).

### Added

- Given lyrics are timed by forced alignment to the vocals (change 0005, D-055 to D-059): Meta's MMS
  aligner (torchaudio's `MMS_FA`, new extra `align`: torch, torchaudio, uroman) places every given sung
  word on the isolated vocals on the CPU, and the lines are timed from the aligned words; recognition
  stays and is the cross-check (`check_lyrics` warns `align-disagrees` when a line's aligned and heard
  starts are more than 750 ms apart, `align-unsure` when the aligner placed a line with a low score,
  `not-aligned` when the lyrics could not be aligned, `not-listened` when they were aligned on the
  mix). New setting `models.align` (default `MMS_FA`, `null` turns it off; projects made before read
  as `null`, so they keep their timing), new port method `Models.align` (words with a score,
  `AlignedWord`); `words.json` gains `aligned` and `not_aligned`; the `transcribe`, `lyrics` and
  `check_lyrics` steps are versions 4, 3 and 2. The weights are kept as `mms_fa.pt` in torch's cache. A run stopped before
  `check_lyrics` finished (its `transcribe` or `lyrics` step of the older version) continues as a fork
  after upgrading, reusing its finished steps; its stored settings without `models.align` keep
  the lyrics timed from the heard words.
- Robust listening (change 0002's amendment, D-045 to D-047): the first listen hears the song's vocals,
  isolated once by Demucs on the CPU and kept in the project's `vocals/` (without the `separate` extra
  it hears the mix and `check_lyrics` warns `not-listened`); a first listen that misses more than a
  third of the given lines is made once more and the better kept (`words.json` `retried`); a gap
  longer than 30 s is no longer skipped but listened to in windows of at most 30 s, each with the
  lines expected in it, the mix slice first, then the same slice of the vocals (no per-slice
  separation any more), at most 16 listens again per song. `words.json` gains `vocals` and `retried`;
  the `transcribe` step is version 3; `Models.separate_vocals` takes the whole song.
- Batch redo and re-plan ([0008](design/changes/0008-batch-redo.md), D-070 to D-074): several shots are
  redone in one fork with one assembly (`hmv.redo` with a list or ranges like `S012-S015`, `redo PROJECT
  S003 S012-S015 --seed`, `POST /api/projects/<id>/redo {shots: [...]}`); `redo --dry-run` and
  `"dry_run": true` say what each shot would get and how long, from this project's measured times; a
  redo that would remake any other shot is refused with the shots and why. `hmv.replan` /
  `replan PROJECT S012-S015 --note ...` asks the shot planner (one whole-song call) to change only
  those shots, checks the reply and keeps the proposal in `replan.json`; `hmv.apply_replan` makes only
  the changed shots, `hmv.discard_replan` drops it. The Storyboard picks shots (checkboxes, shift-click,
  a drag on the timeline) and shows a re-plan's proposal for approval, with the calls' recorded cost
  (`HoneModels.last_plan_cost_usd`). The records gain `replan` and `replanning`; their `shots` and
  `shots_check`, and `check-shots`, are of the approved plan.
- Unattended runs ([0004](design/changes/0004-unattended-runs.md), D-075, D-076): a project can run
  without stopping for approval (`project.json` `approve: "auto"`, written only for unattended
  projects so the others stay readable by the previous version; "Run without stopping for my
  approval" on the New video form and the project page, `new --auto-approve`,
  `create_project(..., approve="auto")`, `hmv.set_approve_mode`, `POST /api/projects/<id>/approve-mode`).
  Each gate is approved by hone-flow as `automated` with the actor `auto` (`gate_auto_approved`), never
  over check errors (`auto_stopped`); the run state marks each such gate (`gate_auto`).
- Live progress ([0003](design/changes/0003-live-progress.md), D-050 to D-054): every picture shows as it
  lands (drafts, stills, raw clips, finished clips, sheet takes, portrait drafts) with each shot's state;
  each stage shows its units done of total, the unit being made, elapsed, the time left from this run's
  measured times and the model load; an overall estimate with its end clock time; a light CSS motion on
  what is being made; every picture and clip opens in a viewer. `events.jsonl` gains `units`,
  `version_started` and `version_made`, which replaces `shot_finished`, `sheet_take` and `pack_picture`;
  runs from before are counted from their folders. The project JSON gains `progress`; the records gain
  each shot's `draft` and `newest` and each pack's `portrait_draft`.
- Operations (change 0007, D-060 to D-064): **notifications** through hone-flow when a gate waits, a
  stage fails and the video is done, to one webhook from `HONE_MV_NOTIFY_URL` (Slack, Mattermost,
  Discord, Telegram's `sendMessage`, or plain HTTP; `HONE_MV_NOTIFY_KIND`), naming the project, the gate
  or stage and its dashboard page; the URL is never recorded. **What a video cost**: `hmv.costs`,
  `hone-music-video costs` and a panel in the Video view add up each hosted call's recorded price and
  each stage's time (GPU, CPU, hosted), split into the first pass, reruns and redos, into
  `current/costs.json`; `HoneModels` now passes hone-flow's trace context to hone-models, so its records
  name the run and the stage. **The edit for editors**: the assembly writes `current/edit.xml` (FCP7
  XML) and `current/edit.edl` (CMX3600) for DaVinci Resolve and Premiere, offered in the Video view;
  `hmv.export` / `hone-music-video export` writes them for a video assembled before.
- Milestone M6 (design §5.3, §12): the assembly cuts every finished clip to its shot's frames from the
  absolute times with ffmpeg, joins the cuts in order without a second encoding (H.264, CRF 17,
  `yuv420p`) and lays the song under them (copied when AAC or MP3, else AAC 320 kb/s) as
  `current/video.mp4`, with the edit list `current/edl.json`; a clip shorter than its shot holds its
  last frame (`held_frames`, a `clip_short` event), clips of another size or rate are refused (D-035).
  `hmv.assemble`, `hone-music-video assemble` and "Assemble again" in the Video view cut the video again
  from the finished clips without calling a model, as a fork of the run where only the assembly runs,
  so a run assembled before M6 gets its video (D-036). The Video view shows the held frames. Guarantee 10
  is tested; every guarantee now has its test. `FakeModels` writes small real videos for clips
  (`testing.make_clip`), so fake runs end with a real video. New guides in `docs/`, runnable examples in
  `examples/`, and a rewritten README.
- Listening again for given lyrics lines Whisper did not hear (design §6 steps 1b and 1c, D-040,
  D-041): the `transcribe` stage matches the given lines against the heard words (robust to
  mishearings and transliterations), sends each gap's slice of the song to the transcriber with the
  missing lines as the prompt, and, when that is not enough, the slice's vocals isolated by Demucs
  `htdemucs` on the CPU (new optional extra `separate`; without it `check_lyrics` warns
  `not-listened`). The words heard in the gap replace the first listen's there; `words.json` keeps
  every listen (`listened_again`, `not_listened`). A reply that echoes its prompt or has a word longer
  than 5 s is not taken as heard; gaps longer than 30 s are not listened to again; a line still not
  heard where an instrumental span is marked gets a `line-in-instrumental` warning. The `Models` port
  gains `separate_vocals`, the settings `models.vocals`; the `transcribe` and `lyrics` steps are
  version 2 (change 0002).
- Milestone M5 (design §10, §11): start frames by Qwen-Image-Edit 2511 4-step from up to three pack
  pictures chosen by §10.1 (the shot's own `refs`, else each character's preferred views in turn), the
  `{id}` placeholders named by their pictures for the image model and by the cue for the Z-Image polish;
  shots without a cast drawn by Z-Image from text; clips by Wan 2.2 I2V 14B (4-step LoRA, SageAttention
  through ComfyUI's start flag) at 832x480, 960x544 when `faces`, sized for every aspect ratio; one
  finishing job per clip (Real-ESRGAN x2, Lanczos to the output size, RIFE x2 to 32 fps) on one new
  `finish` role, replacing `upscale` and `interpolation` (projects that still have them load). Any shot
  can be redone (a new seed, a new still, edited prompts) or an earlier take used again, from the
  Storyboard, `hmv.redo` / `hmv.use` or `hone-music-video redo` / `use`: a fork of the run that makes
  only that shot and assembles again. The library ships the Wan and finishing entries and workflows
  (D-030 to D-034). Guarantees 8, 9 and 12 are tested, and 11 now kills the real stills, clips and
  finish stages.
- The projects list shows a project this version cannot read (e.g. made by a newer version) as
  unreadable with the reason, instead of failing as a whole; opening it is a 422.
- Milestone M4 (design §5.2, §7.3, §7.4, §8): every shot is planned in one call to the shot planner
  with the timed lyrics (every word's times), the story, the cast with each pack's front view and
  portrait as images, the settings as data and the model limits of §8 in the prompt; `check_shots`
  (`hmv.check_shots`, `hone-music-video check-shots`) reports every error and warning with its shot,
  rule and amount; errors go back in at most two whole-plan repair calls, and what remains is shown at
  the shot gate: errors that would break the video block it, the others can be approved with an explicit
  acknowledgement (`approve --accept-errors`, `accept_errors=True`, a confirmed "Approve with N errors"
  in the Shots view, kept in the gate's note); the owner can send the plan back with a note (`reject`,
  the Shots view). Each planner call is logged as a `shots_planned` event. The planner's
  registry entry gives a long plan the time it needs (D-025 to D-028). Guarantees 5, 6 and 7 are
  tested.
- Milestone M3 (design §7.2, §9): the cast is planned in one call with every given sheet as an image
  (prompt from the tested turnaround template; a plan that breaks the rules is sent back once); the
  sheets are drawn by Z-Image Turbo, `sheet_takes` per character, each with a preview of its cut; the
  owner picks a take or asks for new takes with a note (`hone-music-video pick` / `retake`, the Cast
  view), and the gate passes on its own when every sheet is given; the packs are cut from the picked
  take or the given sheet (never redrawn) into `figure-N.png`, front, side and back, with a portrait
  for people by Qwen-Image-Edit 2511 4-step and the Z-Image polish. The library ships its registry
  entries and workflows (`data/models.toml`, `data/workflows/`); numpy and Pillow are new dependencies
  (D-020 to D-024). Guarantees 3 and 4 are tested.
- Milestone M2 of [0001](design/changes/0001-initial-design.md), timed lyrics: word times from
  the gateway's `whisper-1` through a small in-library client behind the `Models` port (D-002, D-017), one
  structured call to the lyrics editor that corrects the words, lines and sections while the code takes
  every time from the heard words (D-016), and `check_lyrics` with every error and warning of design
  §5.1. Timed lyrics with errors cannot be approved; `reject` (API, `hone-music-video reject --note`,
  the Lyrics view) runs the lyrics stage again with the owner's note (D-015). The Lyrics view shows
  each finding under its line. The library ships its hosted model entries (`data/models.toml`, D-018);
  the key comes from `OPENAI_COMPATIBLE_API_KEY` (or a `.env` file).
- Milestone M1 of [0001](design/changes/0001-initial-design.md): the project folder and its records in
  integer milliseconds, validated settings, every generated file kept as a version with what made it,
  the 13 stages as one resumable hone-flow run with the four owner gates (all on fake models for now),
  the `Models` port with `FakeModels` and a hone-models adapter, the `hone-music-video` command
  (`dashboard`, `new`, `run`, `resume`, `status`, `approve`) and the dashboard shell (projects, New
  video, live stages, Approve).
- The dashboard's look (design §13.3): an app shell with the projects in a sidebar, a project's views
  as tabs; the Overview shows the song as a waveform timeline (decoded in the browser) with sections and
  shots, the gate waiting with a preview of what it approves, the 13 stages as a pipeline with real
  per-shot progress, the newest pictures and the activity; read-only Lyrics (play a line), Cast, Shots,
  Storyboard (hover plays a clip) and Video views; light and dark themes. New API route
  `GET /api/projects/<id>/records`; the song and given sheets are served, with byte ranges (D-013).
- `scripts/sample-project.py`: a sample project from the sample song and the trial's real pictures
  and clips, on a sample model set, run to the end or live in the dashboard (D-014).
- Repository created with the design ([0001](design/changes/0001-initial-design.md), accepted 2026-10-10).

### Fixed

- The sheet cutter no longer keeps a neighbouring figure's part that reaches into a figure's box (a
  horse's rump in the next horse's side view): only what is joined to the figure's head is kept (0014,
  D-081). Packs cut before are not cut again.
- The assembly gives each frame its time itself instead of asking ffmpeg for a rate, so a gap in a
  clip's timestamps no longer repeats a frame; a killed assembly's work folder is removed when the stage
  runs again, and the video is only ever replaced whole (D-035).
- A model call inside a stage's session now uses that session, so the model loads once per stage
  (D-005, D-022).
