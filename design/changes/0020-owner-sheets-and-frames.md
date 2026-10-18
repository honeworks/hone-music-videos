# 0020: The owner chooses how each picture is made

## Status

`implemented in 0.1` (2026-10-11; unreleased). `accepted` 2026-10-11: approved by the maintainer. Its smaller
choices are D-128 to D-138 in [decisions.md](../decisions.md).

## Context

In the last unattended run of *Isolde the forgotten wife 3*
(`projects/isolde-the-forgotten-wife-3/events.jsonl`, 2026-10-11) the local sheet model drew no usable
sheet. The sheet judge (0019) flagged every take major in both rounds: `sheets_checked` reports
`takes: 16, flagged: 16` twice, and the log has 32 `sheet_retry` events. The characters came back
with repeated side or back views and five or six figures; the prop's "detail" was the same crown again.

What the record of that run shows (`current/checks/sheet-retries.json`):

- **The retry limit held.** `sheet_retries` was 2, so each of the 16 takes was drawn three times: the
  first draw and two retries, 48 pictures. Nothing went past the limit.
- **Every retry had a new prompt.** The judge rewrote each one, for example "exactly four figures …
  figure 2 in three-quarter view … four different directions, no direction repeated".
- **It still failed because of the model.** Z-Image draws three to five figures whatever count is
  asked (design history). The scores did not improve between rounds and some got worse (4 figures
  became 6).
- **The last round was drawn and never judged.** The run stopped at 12:47, right after the 48th
  picture and before the last judge call; a resume judges it (`sheets_check.heal`).

The owner also tried a sheet made elsewhere: one picture with four standing figures, three face
close-ups and crops of the snakes, the belt, the ring and the boots. The cutter (`_cutter.py`, §9
step 2) found the four figures, but each cut runs the whole height of the picture, so every view also
holds slices of the faces and the details below it. It named the three-quarter view `side.png` and never
used the true profile. The scene model, Qwen-Image-Edit 2511 on the 8 GB card, takes at most three
pictures and reads each at about one megapixel, so one collage cannot carry all of that either.

Asked what a better local model would be: none fits this card. Qwen-Image-Edit 2511 at Q4 (what the
library runs) is the best scene model that fits in 8 GB; a heavier copy, or FLUX.2 Klein 9B, needs 16 to
24 GB. Better pictures come from hosted models (an OpenAI-compatible gateway) or from the owner's own work.

## Problem

1. Every picture is made by one fixed model per role: sheets by Z-Image, scenes by Qwen. When it
   cannot draw something, the only remedy is drawing again with the same model.
2. There is no way to use a hosted image model, or the owner's own picture, for one sheet or one scene.
3. A pack depends on a four-figure sheet and the cutter. A picture with another layout is cut wrongly.
4. A scene can be redone only once the run has stopped. While scene 23 is drawing, scene 12 cannot be
   changed.
5. The owner cannot make the run stop after the scenes are drawn, to look at them before the videos.

## Options

1. **Leave it as it is.** The owner asks for new takes from the same model, or prepares a given sheet
   before the run. Rejected: the run above spent 48 pictures and two judge calls and had nothing to cut.
2. **Uploads only** (the first draft of this record): a "provided sheets" setting and an upload button
   for scenes. Rejected by the owner: they want hosted models as well, sheets always reviewed, and packs
   as separate pictures, not a cut sheet.
3. **One menu for every picture, and packs as separate pictures (chosen).** Every sheet picture and
   every scene can be made with any local model, any listed hosted model (with its estimated cost) or an
   upload; the run waits for the owner at the sheets and, if chosen, after the scenes; a scene can be
   changed while others are drawing; only what depends on a changed picture is made again.

## Decision

### 1. The menu: how a picture is made

Every picture the owner can redo offers the same list:

```text
Local: Qwen-Image-Edit 2511                    free, about 2 min
Local: Z-Image Turbo (text only)               free, about 30 s
gateway: qwen-image-edit-plus                   about $0.03
gateway: seedream-5-0-260128                    about $0.035
...
Upload my own picture
```

- The list comes from the hone-models registry (rule 3): every `kind = "image"` entry the library
  ships or the user has, with its `max_references` and its price. The local entries are the ones in use
  today (`models.stills`, `models.sheets`). The hosted entries are new in `data/models.toml`, called
  through hone-models' OpenAI-compatible image client (`openai_media`: `/images/generations`, or
  `/images/edits` with the reference pictures). Their prices are recorded by hone-models and counted in
  `costs.json` (§13.5).
- A model is listed only where it can do the job: a text-only model only for a picture with no
  reference pictures (a scene without a cast or a prop picture, or a first character picture).
- **The estimate** shown is the entry's price per picture plus its price per reference picture, from
  the gateway's published prices, marked "about"; the time is this project's measured time for local models,
  else §15's. The real cost is what hone-models records.
- The hosted image models to list, at the prices the gateway published (read 2026-10-11),
  for a 1024×1024-class picture:

  | Entry | References | About, per picture |
  |---|---|---|
  | `qwen-image-edit-plus` | yes | $0.03 |
  | `qwen-image-3.0` | yes | $0.04, plus $0.003 a reference |
  | `qwen-image-3.0-pro` | yes | $0.04, plus $0.003 a reference |
  | `seedream-5-0-260128` | up to 10 | $0.035 |
  | `flux.2-pro` | up to 8 | $0.03 the first megapixel, $0.015 each more, $0.015 a reference megapixel |
  | `flux.1-kontext-pro` | 1 | $0.04 |
  | `gpt-image-2.5-flare`, `gpt-image-2.5-sunburst` | yes | $0.053 at `high`, plus the references' input tokens |
  | `z-image-turbo` (hosted) | none | $0.015 |
  | `gemini-3.1-flash-image` (Nano Banana 2) | yes | $0.067 for a 1K–2K picture, plus its input |
  | `gemini-3-pro-image` (Nano Banana Pro) | yes | $0.134 for a 1K–2K picture, plus its input |

  `gpt-image-2` and `gpt-image-1-mini` have no published output price; `gpt-image-1.5` takes no
  references. They are not listed.
- **The Gemini models are a temporary exception to rule 3.** They answer on the gateway's chat endpoint, not
  the image endpoints, and hone-models has no client for that. Until it has one, a small in-library
  client (`adapters/hosted_gemini_image.py`, the same kind of stopgap as `adapters/hosted_speech.py`,
  D-002) makes these calls behind the same port as hone-models' images. It records each call's model,
  prompt, references (paths and sha256), time and price in the picture's version record, and §13.5
  counts those, as it counts transcription. Its module docstring and a `TODO(hone-models)` say to
  remove it when hone-models can call them, and a decision in `design/decisions.md` says the same.
- **Upload my own picture** is always last. The file is checked (PNG, JPEG or WebP by its bytes, at most
  25 MB, at least the picture's size on both sides), cover-cropped to the size (the crop recorded) and
  kept as a version under its sha256 (D-009). It is never checked by the judge and never drawn again.

### 2. Character packs: separate pictures, not a cut sheet

A new project's pack is separate pictures: `front` (full body, facing the camera), `side`, `back`,
`portrait` (the face, as today's portrait) and the character's **details**. An animal's first picture
is its `side`.

- **Details.** The cast planner lists for each character the details that must stay the same and that
  one full-body picture is too small to carry: `details: [{id, look}]` ("ring": "a gold ring with one
  red stone on his left hand"; "snake-head"). At most four. Each becomes one close-up picture. The
  owner redoes or replaces these; they cannot add another in 0.1.
- **Step one, stage 6 (`sheets`):** one picture per character, its first view (front, or side for an
  animal), from a single-figure prompt the cast planner writes in place of the four-figure template, on
  the project's `models.sheets` (Z-Image unless the project chose another, §7 below) or the model the
  owner picks. Given sheets of the project are attached as
  reference pictures when the model takes them. One picture per prop (below). One take each, not
  `sheet_takes`. The judge (0019) checks each and retries as today (§5 below). Then ⏸ `pick_sheets`.
- **Step two, stage 7 (`packs`):** from each accepted first picture, the side, back, portrait and each
  detail are drawn by a model that takes reference pictures (the project's `models.views`, Qwen unless
  the project chose another, or the model the owner picks), each its own picture: "The same man from
  image 1, exact side profile facing left, full body, same costume, plain light-grey studio backdrop".
  Judged and retried the same way. Then ⏸ `review_packs`, a new gate.
- **Before this is built**, a short GPU comparison on two characters (Morvane among them): their side and
  back views drawn by plain Qwen, and by Qwen with the multiple-angles LoRA the workflow already loads
  at strength 0 (`qwen-image-edit-2511-multiple-angles-lora`), at full strength. The owner picks; the
  result is a decision, and the views' workflow input `lora_strength` is set from it.
- **At either gate**, each picture has: Accept, Redo (a note and a model from the menu), Upload. Redo
  draws only that picture; every other picture is found, not drawn (D-009). Approve accepts what is
  shown. The views are drawn only after the first pictures are accepted, so a redone front gets new
  views from it.
- **Both gates always wait**, in an unattended project too (`approve: "auto"`): the owner asked that
  sheets are always reviewed. The run stops with `auto_stopped` and the usual notification (§13.4).
  Only when no character and no prop needs a picture (every one a given sheet, D-024) do they pass on
  their own.
- A given sheet at project creation is cut as today (§9 step 4) into the views it holds; any view can
  then be replaced at `review_packs`. The cutter stays for given sheets and older projects.
- No take is refused for its figure count any more (D-124): there is nothing to cut. The judge's flags
  are shown, never blocking.
- Sizes: a full-body picture 832×1248, the portrait and each detail 1024×1024 (about one megapixel, the
  size Qwen reads its references at).

### 3. Props: one picture each

A prop with a look gets one picture of the whole object on a plain light-grey backdrop, no people, no
hands, no text, from the library's prop prompt without its detail half (D-101), at 1024×1024. Accept,
Redo or Upload at `pick_sheets` like a character's first picture. Its pack is `main` only; it takes one
reference slot in a scene (§10.1).

### 4. Scenes

- **Redo with a model, or upload.** A scene's redo (D-031) gains a model from the menu, or an upload.
  The take records `model` (the registry id; none means the project's `models.stills`) and `source`
  (`generated` or `uploaded`, with the file's sha256). The scene's reference pictures go to the chosen
  model by the budget below, at most its `max_references`. Every scene, from any model and uploads too,
  is **polished by the local polish model** (`models.polish`, Z-Image image-to-image), then goes on to
  its clip as today. A take drawn by a model is checked and retried as today (§10.3, §10.4) with that
  model; an uploaded one is not checked and not retried.
- **Details in a scene.** The shot planner gets each character's details (id and look) and names in a
  shot's `refs` the details it shows (`"morvane/ring"`). The budget (§10.1, D-106) puts the named details
  first, then each character's views as today, then the props' pictures, until the model's slots are
  full: three on Qwen, more on a hosted model that takes them.
- **Stop after the scenes.** A choice on the New video form and `new --stop-after-scenes`:
  `quality_gate` gains `"always"`, so `review_stills` waits after every scene is drawn and checked. In
  an unattended project (`approve: "auto"`) it passes on its own like any other gate there (D-067,
  D-075): the automatic run wins. Off by default.
- **Changing a scene while scenes are being drawn.** A redo or an upload sent while stage 10 runs is
  written to the project's queue (`current/scene-queue.json`). Stage 10 reads the queue before each
  scene it draws and once more before its polish pass: a queued scene gets its new take in this same
  stage (a local model in its turn, between two scenes; a hosted call at once); the other scenes are
  drawn as planned. The taken entries move to `current/live-takes.json`, which stages 10, 12 and 13 read
  after the run's `takes` param, so the clip is made from the new picture without a fork. The next fork
  (a redo, a use, an apply) copies them into its `takes` param and empties the file.
- **Changing a scene later.** A redo or an upload sent once stage 10 is done (the clips are being made,
  or the video is finished) waits in the queue. When the run stops (it ends, or waits at a gate),
  everything queued is applied as **one** fork (0008, D-070): only those scenes are drawn, polished,
  animated and finished again, and the video is assembled once. Before it runs, the redo guard (D-071)
  refuses it, naming the scenes, if any other scene would be made again, and the estimate (D-072)
  shows its time and its hosted cost. "Make these now" on the Storyboard applies the queue at once when
  the run is stopped.

### 5. Retries

Unchanged in what they do (0015, 0019): the judge checks a drawn picture, a major flag gets the judge's
corrected prompt, the picture is drawn again with that prompt and the same model, up to
`still_retries` or `sheet_retries` rounds, and the best-scoring round is offered. No bug was found in
the limit (Context); the case of the last round drawn but not judged when the run stops gets a
regression test. A retry of a hosted picture is another hosted call and is counted in the estimate.

### 6. Unattended runs

- `pick_sheets` and `review_packs` always wait for the owner (§2).
- `review_stills` with "stop after the scenes" waits only when the owner approves by hand
  (`approve: "ask"`); in an unattended project it passes on its own (§4).
- Every other gate behaves as 0004 says.

### 7. Each project's default models

The models a picture is made with unless the owner picks another from the menu are settings, and may be
hosted entries:

| Setting | Makes | Default |
|---|---|---|
| `models.sheets` | a character's first picture, a prop's picture | `z-image-turbo` (local) |
| `models.views` (new) | a character's side, back, portrait and details | `qwen-image-edit-2511-4step` (local) |
| `models.stills` | the scenes | `qwen-image-edit-2511-4step` (local) |

They are chosen on the New video form (each a list from the menu, with its estimate per picture) and
with `new --sheets-model`, `--views-model` and `--stills-model`. A hosted default spends money on
every picture of its kind; the New video form shows the estimate for the whole video before Start (as
D-069 does for extra takes). A setting naming a model that takes no references is refused for
`models.views` and for `models.stills` when the plan has a cast. The polish stays local
(`models.polish`), always. Stored settings without `models.views` read it as their `models.stills`.

### How the owner uses it

```text
hone-music-video new isolde song.wav --stop-after-scenes --stills-model seedream-5-0-260128
hone-music-video image-models isolde --for scene S012     # the menu, with estimates
hone-music-video redo-picture isolde morvane front --model seedream-5-0-260128 --note "two snakes"
hone-music-video redo-picture isolde morvane ring --upload ring.png
hone-music-video approve isolde                           # pick_sheets, then review_packs
hone-music-video redo isolde S012 --still --model qwen-image-3.0
hone-music-video redo isolde S018 --upload frame.png
hone-music-video apply-queue isolde --dry-run             # what would be made, how long, how much
hone-music-video apply-queue isolde
```

```python
hmv.image_models(project, purpose="scene", shot="S012")    # [ImageModel(id, where, max_references, about_usd, about_ms)]
hmv.redo_picture(project, models, "morvane", "front", model="seedream-5-0-260128", note="two snakes")
hmv.redo_picture(project, models, "morvane", "ring", upload=Path("ring.png"))
hmv.redo(project, models, "S012", hmv.Redo(still=True, model="qwen-image-3.0"))
hmv.redo(project, models, "S018", hmv.Redo(upload=Path("frame.png")))
hmv.apply_queue(project, models, dry_run=True)
```

`hmv.redo` keeps its behaviour when no model or upload is given; while the run is going it now queues
instead of refusing.

### Dashboard

| View | Change |
|---|---|
| New video | "Stop after the scenes are drawn" (`quality_gate: "always"`; it says it does not stop an automatic run). The three default models (§7), each with its estimate per picture, and the estimate for the whole video when one is hosted. The sheet-takes setting is gone for new projects. |
| Cast | Per character: the first picture, then (after `pick_sheets`) the side, back, portrait and each detail, each with the judge's flags, Accept, Redo (note + model menu with estimates) and Upload. Per prop: its one picture, the same buttons. The gate card says what is still to accept. |
| Storyboard | Per scene: Redo opens the menu (models with estimates, Upload). A redo sent during stage 10 shows "will be drawn next"; sent later, "queued". **Make these now** applies the queue as one fork with its estimate. |
| Overview | The same gate controls as the views (D-111); `review_packs` is a new card. `review_stills` with "always" says the run waits so scenes can be changed. |

The page stays on `127.0.0.1` (§13.1). The menu is `GET /api/projects/<id>/image-models?for=…`.

### Records and folders

New data is optional; `format_version` stays `"1"`.

- Settings: `packs` (`"views"` for new projects; stored settings without it read `"sheet"`, the four-figure
  sheet and the cutter, as before). `quality_gate` gains `"always"`. `models.views` (new; read as
  `models.stills` when missing); `models.sheets`, `models.views` and `models.stills` may name hosted
  entries.
- Cast: a character's `details` (default `[]`). In `"views"` projects `sheet_prompt` is the
  single-figure prompt.
- Packs: a character's `details` (`{id: path}`, default `{}`); a prop's `detail` stays `None` in
  `"views"` projects.
- `Take`: `model` (default `None`), `source` (default `"generated"`), `sha` (an upload's). `Redo`:
  `model`, `upload`.
- The `Sheets` record's rows: per subject and view, the pictures made, each with its model and source,
  and the one accepted.

```text
current/packs/<id>/takes/<view>-<key>.png + .json    every picture of a view, drawn or uploaded
current/packs/<id>/<view>.png                         the accepted one (front, side, back, portrait, <detail>)
current/props/<id>/takes/main-<key>.png + .json       and main.png
current/scene-queue.json                              redos and uploads waiting, with a lock file beside it
current/live-takes.json                               the ones stage 10 took during the run
current/uploads/<sha>.<ext>                           an upload as received, before its crop
```

### Writing safely

- The HTTP thread and the CLI only write the queue: under an exclusive lock
  (`current/scene-queue.lock`, `fcntl.flock`), to a temporary file renamed into place. The runner
  thread is the only one that takes from it and writes `live-takes.json`, the same way. The lock is
  never held during a model call.
- An upload's bytes are checked and the version written before the queue entry, so a crash leaves
  either nothing or a complete file. A taken entry is recorded in `live-takes.json` before it is
  removed from the queue; a crash between the two takes it again, and its sha makes that a no-op.
- Two requests for the same scene: the later one wins and the earlier stays a take to go back to.
- A gate decision (Accept, Redo, Upload at a gate) happens while the run is stopped, through the gate
  calls that already refuse a run another process holds (D-031).

### Acceptance cases

Numbered after design §14 (the last there is 22).

23. In a `"views"` project, stage 6 draws one picture per character and per prop, and the run waits at
    `pick_sheets`, unattended too; a redo of one picture with a chosen model draws only that picture
    with that model; stage 7 draws each accepted character's side, back, portrait and details from its
    first picture and waits at `review_packs`; the pack is the accepted pictures, uncut. A project with
    stored settings without `packs` draws and cuts four-figure sheets as before.
24. The menu lists the local image models and the hosted ones with their estimates, only where they can
    do the job; a scene redone with a hosted model is one hosted call with the scene's references (at
    most the model's limit, the named details first), polished by the local polish model, and its cost
    is recorded.
25. An uploaded picture (a view, a prop, a scene) is cropped to its size with the crop recorded, kept as
    a version, never judged and never drawn again; a scene upload is polished. A file that is not PNG,
    JPEG or WebP, over 25 MB, smaller than the size, or for an unknown scene or picture is refused with a
    message that names the problem.
26. A scene redone or uploaded while stage 10 is drawing gets its new picture in the same stage, and
    every other scene's files are the ones it would have made. Scenes changed after stage 10, applied
    together, are one fork that makes only those scenes' still, clip and finished clip and the assembly;
    it is refused, before anything runs, when another scene would be made again.
27. With `quality_gate: "always"` a project that asks waits at `review_stills` once every scene is
    drawn, and the scenes changed there are the ones the clips use once it is approved; an unattended
    project goes on without waiting there.
29. A project whose default models name hosted entries makes each picture of that kind with that entry
    (the polish stays local), the New video form shows the estimate before Start, and a project stored
    without `models.views` draws its views with its `models.stills`.
28. A sheet or scene retry draws from the judge's corrected prompt with the same model, at most the
    setting's rounds; a round drawn but not judged when the run stopped is judged on resume, and no more
    is drawn.

### Tests

- `tests/e2e/test_ac23_picture_packs.py`: one picture per character and prop, the wait unattended, a redo
  of Morvane's front with another model (a second fake entry) drawing nothing else, the views drawn from
  the accepted front, `review_packs`, the pack files; an older project's four-figure sheet cut as before.
- `tests/e2e/test_ac24_image_menu.py`: the menu for a scene with a cast and for one without; a hosted
  redo through a fake hosted entry with four reference slots receiving the named detail first; the
  polish made locally; the recorded cost in `costs.json`.
- `tests/e2e/test_ac25_uploads.py`: the crop record, no judge call, no retry; each bad file refused with
  its message.
- `tests/e2e/test_ac26_scene_queue.py`: during stage 10 (a fake model that sends the request while
  scene 3 draws) scene 1 is drawn again and scenes 2 to 6 are unchanged; after the video, three queued
  scenes are one fork remaking only them and the assembly; a fourth scene whose key changed refuses it.
- `tests/e2e/test_ac27_stop_after_scenes.py`: the wait when the project asks, none when it is
  unattended. `tests/e2e/test_ac28_retries.py`: the limit, the last round judged on resume.
- `tests/e2e/test_ac29_default_models.py`: hosted defaults through fake hosted entries, the local
  polish, the estimate, the older settings.
- `tests/unit/test_hosted_gemini_image.py`: the in-library client against a recorded answer (no
  network): the request, the picture written, the price recorded, no key in any record.
- Unit tests: the queue under two writers and a crash between its two writes, the budget with details,
  the estimates, the settings' defaults, the planners' new fields.
- Real-model test (`tests/gpu`, and one hosted call per hosted entry before it is listed): each hosted
  entry answers on `/images/edits` with references.

### Milestones

Each ends with `scripts/check.sh` green and its own commit; decisions D-128 onward.

1. **The menu:** hosted image entries, the in-library Gemini client, `image_models`, a scene redo with a
   model or an upload while the run is stopped, the local polish on every scene, each project's default
   models.
2. **Picture packs:** first the Qwen multiple-angles comparison on the GPU (§2), then the planners' new
   fields, stages 6 and 7 in `"views"` projects, `review_packs`, props as one picture, details in the
   budget.
3. **Stop after the scenes:** `quality_gate: "always"`.
4. **The queue:** changes during stage 10, and the one fork afterwards.

## Consequences

- The owner can spend money on hosted pictures picture by picture; the estimate is shown before each
  choice and the cost is recorded after.
- Packs take more pictures (a front, three views, a portrait and up to four details per character)
  but no picture is wasted on a layout the cutter cannot read, and each can be fixed alone.
- Two gates always stop a new project, even unattended: the run no longer finishes without the owner.
  After them an unattended run goes on to the video.
- Pictures sent to the OpenAI-compatible gateway, the owner's references among them, leave the machine. The key stays in
  `OPENAI_COMPATIBLE_API_KEY`, never in a record.
- New modules are expected: `image_models.py` (the menu and estimates), `stages_views.py` (step two of
  the packs), `scene_queue.py` (the queue and live takes); each within the size limits.

## Migration and compatibility

- Stored settings without `packs` read `"sheet"`: older projects keep the four-figure sheet, the cutter,
  `sheet_takes`, the miscount refusal (D-124) and their packs.
- Stored settings with `quality_gate` `"off"` or `"ask"` behave as before.
- Takes without `model` and `source` are the project's model, generated: an older run's keys do not
  change, so the redo guard (D-071) does not refuse its redos.
- `review_packs` is a new workflow step. A run made before it is resumed as a fork for the new version
  (D-031), where the gate passes on its own for a `"sheet"` project.
- No step version changes for the stages a `"sheet"` project runs.

## Risks

- **Stored formats:** only optional fields with defaults that keep the old behaviour.
- **Crash halfway:** versions are written before the records that name them; the queue is renamed into
  place under a lock; a fork resumes like any redo (guarantee 11).
- **Two writers:** the HTTP thread and the CLI write the queue only; the runner thread alone takes from
  it; no lock is held during a model call.
- **Secrets:** the gateway key is read from the environment by hone-models, and by the in-library Gemini
  client the way `hosted_speech` reads it; upload paths and sha256 are logged, never the bytes.
- **Rule 3:** the Gemini client is a model call outside hone-models, a temporary exception like D-002,
  written down as a decision and marked `TODO(hone-models)` for removal.
- **Dependencies:** none new; hone-models' hosted image client and Pillow (D-020) are in use already.
- **Hosted endpoints:** each hosted entry must take references on `/images/edits` the way hone-models
  sends them; an entry is listed only after one real call proves it.
- **The smaller option:** uploads only (option 2) is less work but does not give the owner hosted models,
  separate pack pictures or changes during a run, which they asked for.

## The owner's answers (2026-10-11)

1. **Gemini (Nano Banana):** listed, through an in-library client with a `TODO(hone-models)` and a
   decision saying it goes when hone-models can call them (§1).
2. **Details:** only the ones the cast planner lists; the owner cannot add one in 0.1 (§2).
3. **Views from the front:** compare Qwen with and without the multiple-angles LoRA on the GPU before
   milestone 2 (§2).
4. **"Stop after the scenes" with an unattended run:** the automatic run wins; it stops there only when
   the owner approves by hand (§4, §6).
5. **Default models:** each project may set hosted defaults for the first pictures, the views and the
   scenes; the polish stays local (§7).

## Open questions

None left. Acceptance of the record is the maintainer's.
