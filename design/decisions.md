# Implementation decisions

Choices too small for a change record. They are numbered in the order they were made, and code comments
refer to them by number. Entries marked **awaiting owner review** are proposals until the owner confirms.

## Awaiting owner review

Nothing is awaiting the owner. D-002 to D-007 were answered on 2026-10-10; D-009 to D-014 (milestone
M1) were accepted by the coordinator on 2026-10-10, D-015 to D-018 (milestone M2: timed lyrics) on
2026-10-10 with the changes written into them, D-020 to D-024 (milestone M3: cast and packs) on
2026-10-10, D-025 to D-028 (milestone M4: the shot plan) on 2026-10-10 with the review's changes.

D-030 to D-034 (milestone M5: stills, clips, finishing and redo) were accepted by the coordinator on
2026-10-10 with the review's changes written into them.

D-035 and D-036 (milestone M6: the assembly, assembling again) were accepted by the coordinator on
2026-10-10 with the review's changes written into them.

D-040 and D-041 (listening again, change 0002) were accepted on 2026-10-10 with the review's changes.

D-045 to D-049 (robust listening, change 0002's amendment, and the speech models) were accepted by
the coordinator on 2026-10-10 with the review's changes written into them.

D-050 to D-054 (live progress, change 0003) and D-075, D-076 (unattended runs, change 0004) were
accepted by the coordinator on 2026-10-10 with the review's changes written into them.

D-055 to D-059 (forced alignment of given lyrics, change 0005) were accepted by the coordinator on
2026-10-10 with the coordinator's answers written into them.

D-060 to D-064 (operations, change 0007: notifications, what a video cost, the edit for editors) were
accepted by the coordinator on 2026-10-10 with the review's changes written into them.

D-065 to D-069 (start-frame quality, change 0006) were accepted by the coordinator on 2026-10-10 with
the review's changes written into them.

D-070 to D-074 (batch redo and re-plan, change 0008) were accepted by the coordinator on 2026-10-10
with the review's answers written into them.

D-084 to D-089 (project options, change 0009; start frames that heal themselves and a cheaper judge,
change 0015; motion prompts that never name the mouth) were asked for by the owner on 2026-10-11.

## D-001: hone-flow and hone-models are core dependencies  (2026-10-10)

- **Question:** the family rule keeps another honeworks package out of a core; this library is a product
  whose runs and model calls are those packages.
- **Choice:** core dependencies (as hone-frame D-001), added in M1; model calls go through one small port
  so tests use fakes.
- **Status:** follows the owner's brief (the trial was built on them).

## D-002: hosted speech needs a hone-models change  (2026-10-10)

- **Question:** the owner chose Whisper word times from the OpenAI-compatible gateway; hone-models only has a local
  faster-whisper speech provider.
- **Options:** (a) call the gateway directly from this library, breaking "every model call through
  hone-models"; (b) propose a hone-models change adding an OpenAI-compatible transcription provider
  (`/audio/transcriptions`, `response_format=verbose_json`, `timestamp_granularities=["word","segment"]`);
  (c) use local faster-whisper.
- **Choice:** (b), and no local faster-whisper. Until the hone-models change lands, a small client in this
  library calls the gateway's `whisper-1` (`/audio/transcriptions`, `verbose_json`, word and segment
  timestamps, the lyrics as `prompt`). It has the same call shape as hone-models' `Transcriber`
  (`transcribe(audio, *, language, prompt, words)` returning segments and words) and sits behind the
  `Models` port, so switching to `mk.transcriber("whisper-1")` later changes one place. It writes the
  request, the reply and the time into the stage's records. This is the one temporary exception to
  "every model call goes through hone-models".
- **Owner's words:** "Don't use local. Propose the design change for hone-models. But for now, use a
  custom code for it. Make sure it's easy to change back to hone-models when we need it."
- **Status:** accepted by the owner 2026-10-10.

## D-003: the lyrics editor may not move times  (2026-10-10)

- **Choice:** the LLM fixes words, line breaks and sections; line and word times come from heard words,
  and `check_lyrics` rejects a line more than 150 ms from its heard words. The owner can still nudge
  times by hand in the Lyrics view (not in 0.1: see Scope).
- **Why:** LLMs are not reliable at timestamps; measured times are.
- **Scope (owner, 2026-10-10):** no hand editing of lyrics in 0.1: the Lyrics view shows the lines, words
  and validator results, plays a line, and has Approve (or rerun the lyrics stage); there is no waveform
  editor (edit, split, merge, nudge). "Let's get the most with what we have; if it is not good enough we
  will add a visual editor, but for now it is not part of the plan."
- **Status:** accepted by the owner 2026-10-10.

## D-004: 32 fps output  (2026-10-10)

- **Choice:** Wan's 16 fps doubled by RIFE: 32 fps, the setup the owner judged "looks great". 24, 25 and
  30 fps would need a frame-rate conversion after interpolation (judder) or a different RIFE factor; they
  can come later as a setting.
- **Status:** accepted by the owner 2026-10-10.

## D-005: models load once per stage  (2026-10-10)

- **Choice:** the per-shot stages run every shot of a stage inside one model session, then report each
  shot as it finishes, instead of one session per shot.
- **Why:** measured: Wan's load is ~6 s per session, but the image models' loads are 40–60 s.

## D-006: the image-to-text prompts are the motion prompts  (2026-10-10)

- **Question:** the brief asks for "prompts for our image to text model". The local pipeline has no
  image-to-text model; it has an image-to-video model (Wan), whose prompts are the motion prompts, and
  the planner itself describes the given sheets (a vision model reading images).
- **Choice:** read it as the motion prompts (§7.3, §8.3) and the planner's sheet descriptions (§7.2).
- **Status:** accepted by the owner 2026-10-10.

## D-007: minutes, seconds, milliseconds  (2026-10-10)

- **Choice:** records hold integer milliseconds; the dashboard shows `m:ss.mmm` (3:32.050) and accepts the
  same when editing.
- **Status:** accepted by the owner 2026-10-10.

## D-008: the workflows and model entries ship with the library  (2026-10-10)

- **Choice:** the ComfyUI workflows of the trial (Z-Image sheets and polish, Qwen-Image-Edit 4-step, Wan
  2.2 I2V, Real-ESRGAN + RIFE) and their hone-models registry entries live in `data/`, merged under the
  project's own `hone-models.toml`, as hone-frame does (its §7.3).
- **Why:** the library must work on a fresh machine with only ComfyUI and the model files installed.

## D-009: the run's shape, and where generated files live  (2026-10-10, M1)

- **Question:** design §3.1 names the stages and gates but not how they map onto hone-flow, nor where a
  per-shot stage keeps a finished shot while the stage is still running.
- **Choice (the run):** one hone-flow run per project with one item, `song`; the 13 stages are its steps
  under their §3.1 names, and the four gates are hone-flow gates after stages 4, 5, 6 and 9:
  `review_lyrics`, `review_cast`, `pick_sheets`, `review_shots`. Shots are not hone-flow items: a step
  that makes items must be a run-level step, and those cannot take item steps' outputs or be gated.
  Stages 10 to 12 loop over the shots inside one step and one model session per model (D-005).
- **Choice (storage):** every generated file is a version that is never overwritten, named after the
  sha256 key of what made it (model, prompt, seed, inputs with files by content):
  `current/shots/<id>/versions/<stage>-<key[:12]>.<ext>` for stills, clips and finished clips, and
  `current/packs/<id>/takes/sheets-<key[:12]>.png` for sheet takes (a reroll gets new seeds, so new
  versions). Beside each version a `Made` record (`<same name>.json`) holds the stage, the model, the
  prompt, the seed, the inputs (files by path and sha256) and the settings; it is written after the
  file, so a version with its record is finished, and a stage run again (a resume after a crash) does
  not make it again (guarantee 11). `still.png`, `clip-raw.mp4` and `clip.mp4` in the shot's folder are
  the chosen version, a copy of the latest made until the owner chooses (M5, §11.2), and
  `current/shots/<id>/prompt.json` holds the shot's prompts (§4). `current/timeline.json`, `cast.json`
  and `shots.json` are written by the stage after their gate, so they hold accepted plans; `edl.json`
  is the assembly's edit list. The project also keeps `events.jsonl`, the progress log the dashboard
  streams. The stage outputs in the run folder are records (`Song`, `Words`, `Report`, `Sheets`,
  `Packs`, `ShotFiles`, `Assembly`) that point at these files.
- **Status:** accepted by the coordinator 2026-10-10.

## D-010: settings and model roles in detail  (2026-10-10, M1)

- **Choices:** one setting per role, the three planners separate (`lyrics`, `cast`, `shots`), all
  defaulting to `claude-opus-5-5`. Ids that have no registry entry of their own yet are provisional
  until the library's `data/models.toml` ships (D-008): `qwen-image-edit-2511` (the 4-step LoRA
  variant), `real-esrgan-x2`, `rife`. `fps` accepts only 32 (D-004); `min_shot_ms` may not exceed
  `max_shot_ms`; shot limits are strict integers. The planners get every setting but the model ids
  (`Settings.for_planner()`). A shot with a cast is drawn by the `stills` role from the cast's front
  views; a shot without a cast is drawn from text by the `sheets` role (Z-Image Turbo, §10.2), and a
  cast member without a front picture fails the stage.
- **Open question:** §3.2 lists `upscale` and `interpolation` as two roles while §11.3 makes the
  finishing one ComfyUI job per clip; in M1 the `finish` stage makes one job on the `upscale` model and
  passes the `interpolation` id as an input. M5 should settle it.
- **Status:** accepted by the coordinator 2026-10-10.

## D-011: the command line and the dashboard's plumbing  (2026-10-10, M1)

- **Choices:** the CLI uses `argparse` (standard library; the CLI is core, so no Typer extra). Besides
  `dashboard`, `new`, `run`, `resume` and `status` it has `approve`, so every gate can be approved from
  the command line. `--fake-models` (on `dashboard`, `run`, `resume`) runs every stage on `FakeModels`,
  for demos and tests, until the real stages land (M2 to M6). The dashboard listens on `127.0.0.1`
  only (§13.1; there is no host option). Its runner does one project's run at a time (one GPU); a
  project waiting its turn shows `queued`. The New video form sends the song and the sheets as base64
  inside JSON (the standard library has no multipart parser since Python 3.13). The page uses the
  system sans-serif (works offline, no font host in the content security policy).
- **Status:** accepted by the coordinator 2026-10-10.

## D-012: what the run's state shows  (2026-10-10, M1)

- **Choices:** a run whose process died shows `interrupted` (hone-flow says `running` until a resume
  takes the lease over); a gate is offered for approval only once the run has let go of it (until then
  the run shows `running`, and `approve` refuses with `RunStateError`); a resume or approval while
  another process holds the run is a `RunStateError` saying what to do; a run folder whose manifest is
  not written yet is not a run yet. The `pick_sheets` gate pauses even when no sheet is to be made; M3
  decides whether it should then pass on its own.
- **Status:** accepted by the coordinator 2026-10-10.

## D-013: what the project views read and which files the dashboard serves  (2026-10-10, M1)

- **Question:** §13.2 gives each view what it shows but not where it reads it, nor which project files
  the server may hand out. M1 served only pictures under `current/`; the Lyrics view must play the song,
  the Cast view shows the given sheets, the Storyboard and Video views play clips and the video.
- **Choices:** one read-only route, `GET /api/projects/<id>/records`, answers every view: the plans and
  checks as their stages made them (the run's step outputs, so a gate shows the plan it is about before
  `current/` holds it), the given sheets, each pack's pictures and sheet takes found in
  `current/packs/<id>/`, each shot's chosen still, raw clip and finished clip with the count of versions
  kept, the edit list and the video, as URLs that change when the file does (`?v=<mtime>`). `/files/`
  serves `current/` (pictures, `.mp4`, `.json`), the song (`input/song.<ext>`) and the given sheets
  (`input/sheets/`), never `project.json`, `events.jsonl`, the lyrics file or the run folder. It
  answers one well-formed `Range: bytes=` range with 206 so audio and video can seek, a well-formed
  range the file cannot satisfy with 416 (`Content-Range: bytes */<size>`), and ignores any other
  `Range` header (another unit, several ranges, whitespace, last before first) by sending the whole
  file with 200 (RFC 9110 §14.2). It takes the size from the open file and streams it in chunks; a file
  removed meanwhile is a 404. `Stage` gains `started_at` (hone-flow's, when it has one; the page
  falls back to the run's `step_started` event while a step runs). The waveform is decoded in the
  browser (Web Audio API); nothing about audio runs on the server. The page is plain ES modules and two
  stylesheets, light and dark themes as CSS variables; the views are read-only (D-003; editing and
  redo arrive with M4 and M5).
- **Status:** accepted by the coordinator 2026-10-10.

## D-014: the sample project and its model set  (2026-10-10, M1)

- **Question:** the owner asked to see the dashboard with real material before the real stages exist.
- **Choice:** `scripts/sample-project.py` (a dev script, not in the wheel) makes a project from
  `samples/The Long Night/` and runs it through the real workflow and `runs` API on a sample model set
  (`scripts/sample_models.py`, `scripts/sample_plans.py`: a `FakeModels` subclass). The planners answer
  from the lyrics (lines spread evenly over the measured song: invented times, a believable shape) and
  the trial's `inputs/video-stills.toml` and `video-clips.toml`; every media call copies a trial file
  (a scene without a trial clip gets a slow push-in made from its still with ffmpeg, cached in
  `<projects>/.sample-cache/`). Two stand-ins for stages M1 stubs: when the shot planner is called, the
  trial packs' front, side, back and portrait views are copied into `current/packs/<id>/` (M3's cut and
  portrait), and after the run the script cuts `current/video.mp4` itself with ffmpeg (M6's assembly):
  each finished clip cut to its shot's frames (§5.3), concatenated, the song muxed (1280x720, 32 fps),
  and writes a `sample_video` event. `--live` serves the dashboard with the sample models slowed to
  0.5 to 2 s per call and stops at every gate for the owner. Nothing it copies or makes is committed.
- **Status:** accepted by the coordinator 2026-10-10.

## D-015: the lyrics gate and running the lyrics again  (2026-10-10, M2)

- **Question:** §5.1 says `check_lyrics` errors fail the stage and "the owner must fix or rerun", and
  §13.2 gives the Lyrics view "Approve or rerun". A failed `check_lyrics` step cannot be rerun into a
  different result: a resume runs only the failed step again, on the same timeline. Neither the API nor
  the CLI had a way to run the lyrics stage again.
- **Choice:** `check_lyrics` always returns its report, and the run stops at `review_lyrics` with it;
  while the report has errors, `approve` refuses that gate (`RunStateError` naming the count), and the
  dashboard hides Approve there. Running the stage again is hone-flow's reject-and-revise: `reject`
  (API `hmv.reject`, CLI `hone-music-video reject --note`, dashboard route
  `POST /api/projects/<id>/reject` with the Lyrics view's note box) sends the gate's stages back
  (`lyrics`, `check_lyrics`); `resume` runs them again, and the lyrics step passes the owner's note
  (`review_note`) and the previous lines (id, section, text, heard words) to the one lyrics call.
  `reject` needs a note (CLI `--note` is required; a blank note is `InvalidInput`) and is allowed only at
  gates whose stage reads it (`runs.RERUNNABLE`: `review_lyrics`, and `review_cast` since M3 makes
  `plan_cast` read it); any other gate is a `RunStateError` saying so (`pick_sheets` has its own
  retake; `review_shots` comes with M4). Events log `gate_rejected` and `gate_approved` with the note as
  hone-flow kept it (secrets stripped).
- **Status:** accepted by the coordinator 2026-10-10 ("errors block approval"; `reject` only where the
  note is read). Amended by 0018 (2026-10-11): the owner may set the lines' times by hand at this gate
  (D-113), and the dashboard's controls are D-111.

## D-016: the lyrics editor never writes a time  (2026-10-10, M2)

- **Question:** §6 makes the editor's structured output "the timeline of §4.1", times included, and
  D-003 says times come from heard words; an LLM asked to copy times copies them unreliably.
- **Choice:** the one lyrics call answers `LyricsEdit` (JSON Schema): `language`, `sections` (id, kind),
  `lines` (section, corrected text, `heard_first`..`heard_last`: the inclusive range of heard words, by
  index into `words.json`, the line is sung over) and `instrumental` (`after_line`: 1-based, 0 = before
  the first line; kind). The heard words are sent with their index `i`. The code builds the timeline:
  line ids `L001`.., a line from its first heard word's start to its last heard word's end, each written
  word timed from the heard words it lines up with (`difflib` over the words without marks: a matching
  word takes its heard word's times, the others share the heard words between their neighbours, a written
  word with no heard word takes the neighbour's), a section from its first to its last line (a section
  without lines is left out), an instrumental span from the end of the line before it (or 0) to the start
  of the line after it (or the song's end; left out when there is no room). A reply whose ranges are out
  of bounds, overlap or go backwards, name an unknown section, repeat a section id, or whose sections'
  lines are not each one run in the order of `sections` is sent back once with the problems (§7.1); a
  second such reply fails the stage. `check_lyrics` also reports overlapping sections (defence in depth).
- **Record:** `Line` gains `heard_first` and `heard_last` (optional, so older timelines still load), so
  `check_lyrics` can measure a line against its own heard words ("moved" > 150 ms; a line without them
  is an error).
- **Status:** accepted by the coordinator 2026-10-10.

## D-017: hosted transcription in detail  (2026-10-10, M2)

- **Measured on the OpenAI-compatible gateway (the sample song, 2026-10-10):** asked for `timestamp_granularities[]` `word` and
  `segment`, the gateway's `whisper-1` answers only the last one asked for (segments, no words), with the
  field spelled with or without `[]`; asked for `word` alone it answers the words. So the client asks for
  `word` only; `Words` keeps no segments anyway. The gateway also sends `estimated_cost`; Whisper gave 2 of
  315 words no length and, without `language`, overlapped two words by 20 ms.
- **Choices:** the client (`adapters/hosted_speech.py`, D-002) uses the standard library (`urllib`,
  multipart by hand; no new dependency) and the registry entry `whisper-1` (D-018) for its URL, key
  variable and model name. A file over 25 MB is sent as a mono 64 kbit/s MP3 made with ffmpeg next to
  it (deleted after; the encoder delay is in the MP3 header, so times are unchanged); the measured sample
  (6.8 MB MP3) is sent as it is. Each call is kept in `words.json` as `call`: the URL, the form fields
  and the file (name, bytes, sha256) but no headers, the reply as sent, `took_ms` and `cost_usd`
  (0.0001 USD per second of audio, whisper-1's list price: 0.0313 for the sample; the gateway's own estimate
  matched). The key is only in the request header; an error message has it replaced by `***`.
  Heard words become integer ms and are tidied (`timed_lyrics.tidy`): each ends at the next word's start
  at the latest and lasts at least 1 ms, so lines timed from them cannot overlap or lack length; the
  `transcribe` stage then keeps them inside the song (`measure`'s length): a word starting at or after
  the end is left out, a word running past it ends there. The service's own times stay in `call.reply`.
  The prompt is the opening of the given lyrics' sung lines (blank lines and `[bracketed]` notes left
  out): whole lines up to 400 characters (a longer first line is cut at a word), because Whisper keeps
  only the last ~224 tokens of a prompt and non-Latin scripts tokenise densely, so the opening is what biases it.
  `language` is sent only when the settings have it (else `Words.language` is what the service named,
  e.g. `english`). The client is one plain function returning the transcript and the call.
- **Status:** accepted by the coordinator 2026-10-10 (with the prompt cap and the clamp to the song).

## D-018: the library ships its hosted model entries  (2026-10-10, M2)

- **Question:** `claude-opus-5-5` and `whisper-1` on the OpenAI-compatible gateway are in no registry hone-models reads; D-008
  ships the local entries in `data/models.toml` but nothing loaded it yet. hone-models has no gateway
  source of truth (its change 0019 proposes `OPENAI_COMPATIBLE_BASE_URL` in a project file).
- **Choice:** `data/models.toml` holds `whisper-1` (transcription, `openai_compatible` at
  `base_url_env = "OPENAI_COMPATIBLE_BASE_URL"`, `api_key_env = "OPENAI_COMPATIBLE_API_KEY"`),
  next to the planner `claude-opus-5-5` and the local entries of M3; the file is loaded by
  `load_registry()` in the order of D-022 (catalog, library, user, working folder), for the planner, the
  media jobs and the transcriber alike. The key comes from the environment or a `.env` file (hone-models
  reads `./.env` and `$HONE_ENV_FILE`).

## D-020: numpy and Pillow are core dependencies, for the sheet cutter  (2026-10-10, M3)

- **Question:** the packs stage cuts a turnaround sheet into its figures (design §9 step 2); the trial's
  cutter (pipeline-demo `split_figures`, `name_views`) uses numpy and Pillow, neither a dependency yet.
- **Choice:** both are core dependencies (`numpy>=1.26`, `pillow>=10.4`); the trial's cutter is reused
  as `_cutter.py`, unchanged in what it finds. The packs stage is core, so they cannot be an extra.
- **Status:** accepted by the coordinator 2026-10-10.

## D-021: how a sheet becomes a pack  (2026-10-10, M3)

- **Question:** design §9 says how a turnaround is cut and that "a single portrait or figure is used as
  given", but not when that applies, what a portrait is drawn from then, or what a recut keeps.
- **Choices:** the cut finds the figures as the trial did; a picture where it finds fewer than two
  figures (a portrait, a single figure, a plain picture) is the front view as it is, and has no side or
  back. A portrait is drawn only for a character with `portrait: true` that has front and side views
  (so never for a single given picture: it is used as given). The longest-figure rule for the side view
  applies to `kind: "animal"` (design §9 says "an animal"); people and creatures take the second figure.
  The cut is made again each time the stage runs (deterministic, a second): `figure-N.png`, `front`,
  `side`, `back` and `sheet.png` (the source, as PNG) are replaced, so a new pick leaves no figure of the
  old one; the portraits are kept versions (`packs/<id>/versions/portrait-<key>.png` from the start-frame
  model, `polish-<key>.png` from the polish pass, `portrait.png` the chosen copy), so a rerun on the same
  views draws nothing. A character id names its pack's folder, so the record only accepts lowercase
  letters, digits and dashes.
- **Status:** accepted by the coordinator 2026-10-10.

## D-022: the library's registry entries, and one client per session  (2026-10-10, M3)

- **Choices (D-008, D-010):** `data/models.toml` holds the planner `claude-opus-5-5` (the gateway's
  OpenAI-compatible gateway, `OPENAI_COMPATIBLE_BASE_URL`, key from `OPENAI_COMPATIBLE_API_KEY`;
  Anthropic's list price, $4 / $20 per million tokens, so the recorded cost is an estimate), the trial's
  `qwen-image-edit-2511-4step` (portraits and start frames) and `z-image-turbo-polish`, with their
  workflows in `data/workflows/`. The sheets use hone-models' packaged `z-image-turbo` as it is, as the
  trial did. The registry is hone-models' catalog, then these entries, then the user's
  `~/.config/hone/models.toml`, then `./hone-models.toml` of the working folder; each later file wins,
  so the library's entries are defaults and never override the user. (`mk.registry.load` always merges
  the two user files before the paths it is given; the adapter gives them again after the library's
  file, which is what makes them win: a file merged again changes nothing it already set.) The two
  image entries declare `vram_gb` near the whole card (7.6 and 7.2, as hone-frame does), so hone-models'
  GPU scheduler unloads other models first. The polish denoise (0.3, design §3.2) is the registry
  entry's default and is not repeated in code. The role defaults become
  `stills = "qwen-image-edit-2511-4step"` and `polish = "z-image-turbo-polish"`; `real-esrgan-x2` and
  `rife` stay provisional, and the Wan and finishing entries are left to M5 (the finish is one job or
  two, D-010's open question).
- **Fix:** M1's adapter made a new hone-models client for every `generate`, so a call inside
  `session(model)` did not use the session (hone-models then loads and frees the model per call). The
  adapter now keeps the session's client and sends the session's calls through it (D-005).
- **Status:** accepted by the coordinator 2026-10-10.

## D-023: sheet and portrait sizes, the cut preview  (2026-10-10, M3)

- **Question:** design §9 gives 2048x1024 "for 16:9 projects" and no other size.
- **Choices:** the sheet is a reference of four full figures in a row, not a frame of the video, so it is
  2048x1024 for every aspect ratio; the portrait is 1024x1024 (the trial's). Each take's preview of its
  cut (design §9 step 1) is the figures side by side, 512 px high, kept as `takes/cut-<key>.png` beside
  `takes/sheets-<key>.png`; the `sheets` record lists the previews with the takes (`SheetTakes.previews`),
  each derived from its take (and made when missing), so the two lists never drift.
- **Status:** accepted by the coordinator 2026-10-10.

## D-024: picking the sheets, and the cast plan's checks  (2026-10-10, M3)

- **Choices (the pick):** at `pick_sheets` the owner picks a take per character (`runs.pick`, the
  dashboard's `POST /api/projects/<id>/pick` with `{"picks": {character: index}}`, the CLI's
  `pick --take CHARACTER=N` counting from 1 as the Cast view shows them); it is a hone-flow gate edit
  of the `Sheets` record, so the decision and the chosen takes are in the run. "New takes with a note"
  (`runs.retake`, `POST .../retake`, `retake --note`) is hone-flow's reject-and-revise: the `sheets`
  stage runs again with a new seed and the note added at the end of every sheet prompt it draws; the
  earlier takes stay on offer before the new ones, and the first new take is the one offered. When no
  character needs a sheet, `pick_sheets` passes on its own (approved with `automated=True` and a note,
  and a `gate_approved` event with `automated: true`), settling D-012's open question.
- **Choices (the cast plan, §7.1):** a reply that names a given sheet that does not exist, has a
  character to make without a sheet prompt, or uses an id twice is sent back once, in one more
  whole-plan call with the problems and the previous reply in the data; if the second reply still has
  problems, the stage fails with them and the owner reruns it. When the owner sends the cast back at
  `review_cast` with a note (reject and revise), the stage's call carries `review_note` and the rejected
  plan as `previous_plan`.
- **Status:** accepted by the coordinator 2026-10-10.

## D-025: what "one call" is, where the repairs run, and how the calls are counted  (2026-10-10, M4)

- **Question:** §3.1 puts "one call (+ repairs)" on stage 8 and "errors trigger a repair call" on stage
  9; §7.1 said an invalid reply is retried once. hone-models' structured output already sends a
  schema-invalid reply back inside one `complete` call, up to twice (`MAX_RETRIES = 2`).
- **Choices:** a planner call is one `Models.plan`, which is one hone-models `complete`. Inside it,
  hone-models may resend a schema-invalid reply up to twice, with the validation error (each a
  `structured_retry` event; `hone.models.structured.attempts` and the summed `usage` on the call's span);
  that is §7.1's retry of an invalid reply, now worded "retried up to twice inside the call". The library
  adds no schema resend of its own; the lyrics and cast calls work the same way, their own one resend
  being for replies that fit the schema but break their rules (D-016, D-024). The repairs run inside
  `plan_shots` (stage 8), because a repair is a model call: the plan, then `check_shots`, then while
  errors remain at most two repair calls, each with the whole data again plus `previous_reply` (the
  plan) and `problems` (every error as `rule`, `where`, `message`); the last plan is the stage's output
  even with errors. Stage 9 (`check_shots`) checks that plan again, and its report is what the gate
  shows. Each whole-plan call writes a `shots_planned` event (`call` 1 to 3, `shots`, `errors`,
  `warnings`) to `events.jsonl`, so the count is in the project's records: at most 3 calls a plan (9
  requests in the worst case, when every reply also needs hone-models' retries), never one per shot.
- **Status:** accepted by the coordinator 2026-10-10.

## D-026: the shot checks in detail  (2026-10-10, M4)

- **Question:** §5.2 lists the rules but not how a finding is named, where a cut is measured, what
  "the length limit of their model" is, how "missing" and "three in a row" are counted, or what makes a
  shot id safe.
- **Choices:** `check_shots(shots, timeline, cast, settings)` (public, `hmv.check_shots`) returns the
  `Report` of `check_lyrics`: each `Problem` has `where` (the shot id; `plan` for an empty plan), `rule`,
  a `message` with the amount in milliseconds and the times as `m:ss.mmm`, and `acceptable` (D-027).
  Error rules:
  - break the video (block the gate): `song-start`, `gap`, `overlap`, `song-end` (tiling);
    `cut-in-word` (a shot's start strictly inside a word, `start < cut < end`; a cut at a word's edge or
    between words is fine); `unknown-cast`; `placeholder` (`{name}` not in the cast, or not in the
    shot's cast); `shot-id` (an id used twice, or not `S` and three or more digits); `empty-prompt`;
  - acceptable (the owner may approve with them): `length`; `prompt-length`; `faces`;
    `word-longer-than-max-shot` (a sung word longer than `max_shot_ms`, reported at the shot it starts
    in: the song or the setting makes the limit impossible to keep there); `unknown-line`,
    `line-outside`, `line-unlisted` (the lines a shot lists are information, not picture).
  `Shot.id` itself must match `^[A-Za-z0-9][A-Za-z0-9-]*$` (it names the shot's folder), so a reply
  with a path in an id fails validation. The prompt limits are 1500 characters for the still prompt and
  1000 for the motion prompt: the text encoders read about 512 tokens (Z-Image's Qwen3 for shots without
  a cast, Wan's umT5), at worst ~3 characters a token, with room for the placeholders to grow ("the
  woman from images 1 and 2"); the trial's prompts were 330 to 600 and 280 to 380 characters. The shot
  planner's prompt states both limits (a test keeps them equal). Warnings: `far-cut` (a cut more than
  120 ms from the nearest line start or end, section start, instrumental edge, or the song's start or
  end), `same-framing` (once per run of three or more, at its first shot), `character-missing` (the
  longest stretch without the character after their first shot, the song's end included, when over a
  third of the song; at the first shot of the stretch), `faces-without-cast` (`faces: true` with an
  empty cast: no reference pictures keep that face the same). `hone-music-video check-shots <project>`
  checks the run's latest plan against the approved lyrics and cast and prints one line per finding
  (kind, shot, rule, message), then the counts; it exits 1 when there are errors.
- **Status:** accepted by the coordinator 2026-10-10.

## D-027: the shot gate, the planner's data, and no shot editor in 0.1  (2026-10-10, M4)

- **Question:** §13.2 gives the Shots view "edit; Approve"; §7.4 says what remains after the repairs
  "goes to the owner with the errors shown"; §7.3 lists the planner's inputs without their shape.
- **Choices:** errors that would break the video (D-026: tiling, cuts inside words, cast, placeholders,
  ids, empty prompts) block `review_shots`, as the lyrics' errors do (D-015). When every error left is
  `acceptable` (a shot outside the length limits, a prompt over its limit, a face on wide framing, a
  word longer than the longest shot, a line listed wrongly), the owner may approve anyway with an
  explicit acknowledgement: `approve(project, accept_errors=True)`, `hone-music-video approve
  --accept-errors`, or the Shots view's "Approve with N errors" behind a confirmation (the API takes
  `"accept_errors": true`). The acceptance is kept: the gate's note ends with `(accepted N errors:
  S001 length, ...)` and the `gate_approved` event has `accepted_errors`. Without it, `approve` refuses
  with what to do. `review_shots` is in `runs.RERUNNABLE`, so `reject` with a note (API, CLI, the Shots
  view's note box) plans the shots again, the call carrying `review_note` and the rejected plan as
  `previous_plan` (then the repairs as usual). There is no shot editor in 0.1: the view shows the shots
  on the timeline, their framing, cast, both prompts and each finding under its shot; editing a shot by
  hand waits, as the lyrics editor does (D-003, D-013). The planner's data: `timeline` (sections, lines
  with `[start_ms, end_ms, text]` for every word, so it can cut between words of a long line, and the
  instrumental spans), `story` (the cast plan's summary), `cast` (each character's id, name, kind, noun,
  cue and first line, and the props; not the sheet prompts), `settings` (`Settings.for_planner()`) and
  `pictures` (each character's front view and portrait, labelled with the character, the view and the
  image number, the images attached in that order). The Shots view's logic (which buttons the gate
  shows, the confirmation) is tested only through the JSON API it calls, as the Lyrics and Cast views
  are (M2, M3): there is no JavaScript test framework.
- **Status:** accepted by the coordinator 2026-10-10.

## D-028: the planner's registry entry has time for a whole-song plan  (2026-10-10, M4)

- **Question:** hone-models gives a hosted model without a measured `speed_tok_s` a 120 s timeout; the
  first real shot plan (61 shots) timed out after 120 s, and its reply is ~26k tokens, close to the
  entry's `max_tokens = 32000`.
- **Choices:** the library's `claude-opus-5-5` entry declares `speed_tok_s = 40`, a conservative figure
  below the 47.8 tokens/s measured on the real plan, and `max_tokens = 64000`, so the timeout is
  `min(max_timeout_s, 2 * 64000 / 40)` = `min(1800, 3200)` = 1800 s and a long plan is not cut. A user's
  own measured speed (`hone-models models check`) wins, as every entry of the user's file does (D-022).
- **Status:** accepted by the coordinator 2026-10-10.

## D-030: start-frame prompts, references and sizes  (2026-10-10, M5)

- **Question:** design §10.1 gives the naming and the reference preferences for people and animals, and
  §10.2 / §11.1 give the 16:9 sizes; not a creature's preference, what a character gets when the three
  slots are full, what a bad `refs` does, or the other aspect ratios.
- **Choices:** the trial's code (pipeline-demo `video_stills`) ported as `prompt_assembly.py`: one
  character after another, each takes its next preferred view that exists, until three slots are full;
  a shot's own `refs` (`character/view`) replace that and must name up to three existing views of the
  shot's cast, else the stage fails naming the shot. A **creature** is drawn like a person (front,
  portrait, side). A character that gets no picture (a fourth one, or a third after two took all
  slots) is named by its `cue` in the image prompt too. A placeholder naming someone outside the shot's
  cast, or a cast member without a pack, fails the stage naming the shot. Sentences start with a
  capital after the substitution (the trial's rule). Sizes per aspect ratio, all multiples of 16, at
  about the pixels of the 16:9 ones (start frame ~0.59 MP; clip ~0.4 MP; clip with faces ~0.52 MP):

  | aspect | start frame | clip | clip with faces | finished (`resolution` 1080) |
  |---|---|---|---|---|
  | 16:9 | 1024x576 | 832x480 | 960x544 | 1920x1080 |
  | 9:16 | 576x1024 | 480x832 | 544x960 | 1080x1920 |
  | 1:1 | 768x768 | 624x624 | 720x720 | 1080x1080 |
  | 4:5 | 704x880 | 576x720 | 640x800 | 1080x1350 |

  The finished size is the aspect ratio with `resolution` as its short side, rounded to even; Lanczos
  stretches the clip to it (832x480 is 1.733:1 against 1.778:1, about 2.5%; the trial did the same,
  and the coordinator kept it: no crop, no pad). The 9:16, 1:1 and 4:5 sizes are untested on the GPU.
  A shot id names a folder, so the stages refuse one that is not letters, digits and dashes (defence in
  depth; M4's shot checks refuse it first).
- **Status:** accepted by the coordinator 2026-10-10.

## D-031: takes, redo and "use this version"  (2026-10-10, M5)

- **Question:** design §11.2 says any shot can be redone (a new seed, an edited motion prompt, a new
  still) with the old versions kept and the owner choosing which one the video uses, and §2.3 that the
  owner picks when `still_takes` > 1; not how a redo runs on hone-flow, what "a version" is when a
  still, a clip and a finished clip each have versions, or whether the run waits for the pick.
- **Choices (takes):** a shot's **take** (`Take`) is its still prompt, motion prompt, a still seed number
  and a clip seed number; a shot has takes and uses one (`ShotTakes`). Until the owner redoes it a shot
  has `still_takes` takes that differ in the still seed, the first in use. A **redo** adds a take copied
  from the one in use and uses it: `seed` gives a new clip seed (same still), `still` a new still seed,
  an edited `still_prompt` a new still seed with the new prompt, an edited `motion_prompt` a new clip;
  they combine, and a redo that changes nothing is refused. **Use** puts an earlier take back. The
  stills stage draws the still of every take (so `still_takes` > 1 draws them all; the run does not
  wait: the first goes on to its clip and the owner can use another from the Storyboard, which then
  animates it); clips and finish make only the take in use. Every file stays a version named after its
  key (D-009), so going back to a take makes nothing but the assembly. A redo is a `Redo(seed, still,
  still_prompt, motion_prompt)`, the same for the API, the CLI and the dashboard.
- **Choices (the run):** the owner's takes are the run's `takes` param (shot id to `ShotTakes`, the
  decisions only), read by `stills`, `clips` and `finish` (their step versions become 2). A redo or a
  use is a **hone-flow fork** of the project's run with the new `takes` (`runs_redo.remake`): the fork
  copies everything up to the shot list and runs `stills` to `assemble` again, where every version that
  exists is found, not made; so only that shot's new files are made, and the edit list is written again
  (guarantee 12). Forks inherit the run's seed. The fork is the project's run from then on: the latest
  run is the one no other run forks from (run ids sort only to the second). A redo needs the shot list
  approved (`review_shots` done) and the run stopped; a redo while it runs, or while the dashboard has
  the project queued, is a `RunStateError` (409), and so is a fork refused because another process holds
  the run. The seeds: `seed_for(run seed, shot, "still", still seed number)` and `(…, "clip", clip seed
  number)`.
- **Choices (records and surfaces):** each per-shot stage builds the job of every take whose source
  file exists, makes only the take in use, and lists every take's file it finds made (`ShotFiles.takes`,
  each `ShotFile` with its `take`; `shots` stays the files the video uses). From that, each stage writes
  `current/shots/<id>/takes.json` (`TakesMade`: the takes, the one in use, and `files[n]` with take n's
  still, clip and finished clip), derived and never read back by the stages; the finish step therefore
  also takes the stills' record. The Storyboard lists it; `prompt.json` holds the prompts of the take in
  use. API `hmv.redo(project, models, shot, hmv.Redo(...))` and `hmv.use(project, models, shot, take)`
  (index); CLI `redo PROJECT SHOT [--seed] [--still] [--still-prompt T] [--motion-prompt T]` and `use
  PROJECT SHOT N` (from 1); dashboard `POST /api/projects/<id>/redo` (`{shot, seed, still,
  still_prompt, motion_prompt}`) and `.../use` (`{shot, take}`), checked at once and run by the runner
  as a remake job. Events `shot_redo` and `shot_take_used` are written once the fork has started.
- **Status:** accepted by the coordinator 2026-10-10.

## D-032: the finish is one role  (2026-10-10, M5)

- **Question:** D-010's open question: §3.2 lists `upscale` and `interpolation` as two roles, §11.3
  makes the finishing one ComfyUI job per clip.
- **Choice:** one role, `finish = "esrgan-rife-x2"`: one registry entry and one workflow (Real-ESRGAN
  x2plus, a Lanczos resize to the finished size, RIFE 4.9 x2, saved at 32 fps), called once per clip
  with `video` and `size`. `upscale` and `interpolation` are gone. Reading stored settings (a
  project's `project.json`, a run's `settings` param) drops the two keys, so a project or run made
  before M5 still loads (they named provisional ids that never had entries); new settings
  (`parse_settings`, `create_project`, the New video form) that name them are refused with
  "models.upscale: replaced by models.finish in 0.1 (D-032)", and any other unknown key is still refused
  (guarantee 13).
- **A project this version cannot read** (a `project.json` made by a newer version, such as one with
  `settings.models.finish` opened by an older one, or a damaged file) no longer breaks the projects
  list: `Project.record()` raises `ProjectUnreadable` with the reason ("made by a newer version of
  hone-music-video: settings.models.finish" when every problem is an unknown key, else the problems),
  the list shows the project as `unreadable` with that reason and the others as usual, and opening it is
  a 422 JSON error, not a 500 (found by the coordinator). Settings keep `extra="forbid"`. The list
  reads each `project.json` once.
- **Status:** accepted by the coordinator 2026-10-10.

## D-033: the clip model's entry and SageAttention  (2026-10-10, M5)

- **Choices:** the clips use hone-models' packaged `wan2.2-i2v-14b` (fp8 high and low noise experts,
  lightx2v 4-step LoRA on both, shift 5, 2 + 2 steps: the trial's "fast" setup) with the library's copy
  of its workflow (`data/workflows/wan2.2-i2v-14b.json`, so a catalog change cannot move node ids),
  `max_duration_s = 8` (the trial's override; the catalog says 5), `max_timeout_s = 7200` and a measured
  `vram_gb`, merged per D-022. The stage asks for `duration_s = (frames - 1) / 16`, which the entry's
  `{per_second = 16, add = 1}` mapping turns back into exactly `frames` (no new input mapping that
  could fight the catalog's `duration_s` default). **SageAttention** is ComfyUI's own start flag, as
  the trial passed it: while a session of a ComfyUI video model whose workflow runs a diffusion model
  (Wan) starts the server, the adapter adds `--use-sage-attention` to `HONE_COMFYUI_START` (once; put
  back after), so ComfyUI's Python environment is not touched and the image models keep their tested
  setup. The finish gets no flag: Real-ESRGAN and RIFE have no attention to speed up. It needs the
  `sageattention` package in ComfyUI's Python; when ComfyUI does not start with the flag, the stage
  fails with "ComfyUI did not start with --use-sage-attention (added for video models, D-033): install
  sageattention in ComfyUI's Python, or start ComfyUI yourself". SageAttention applies only when the
  library starts ComfyUI: one already running is used as it is (accepted by the coordinator).
- **Measured (the M5 real run, hone-models' spans):** the second and third Wan clips of the session did
  not load the model again (`hone.models.media.loaded` false, `hone.models.gpu.released` empty), and a
  5 s clip took 222 s as the first (load included) or the third: the model stays resident for the stage
  (D-005), so the `vram_gb` lease needs no change. Whole-GPU peak 7.7 GB for Wan (`vram_gb = 7.6`),
  1.6 GB for the finish (`vram_gb = 2.0`).
- **Status:** accepted by the coordinator 2026-10-10.

## D-034: what the stills stage keeps  (2026-10-10, M5)

- **Choices:** a shot with a cast is drawn by the start-frame model (`draw-<key>.png`, a version with
  its `Made` record) and polished (`stills-<key>.png`, the still); a shot without one is drawn by the
  `sheets` model from text, which is the still (`stills-<key>.png`, no polish: the trial's choice). The
  stage loads each model once: the start-frame model for every drawing, then the polish and text models
  for every still (D-005). Progress events (`shot_finished`) count the stills, not the drawings (since
  0003: `version_made` events count both, D-050). The
  start frames live in `stages_stills.py`; what stages 10 to 12 share in `_shot_jobs.py`.
- **Status:** accepted by the coordinator 2026-10-10.

## D-035: how the assembly cuts  (2026-10-10, M6)

- **Question:** design §5.3 and §12 give the frame ranges and the encoding, not the edit list's
  convention for the last frame, which frames of a clip a shot takes, what a clip shorter than its shot
  does, how the clips are joined without a second encoding, or what clips that do not match do.
- **Choices:** the edit list keeps M1's convention: `first_frame = round(start_ms * fps / 1000)` and
  `last_frame = round(end_ms * fps / 1000) - 1`, both included (rounded half up, `frame_at`), so the next
  shot starts at this one's end frame and the frames tile the video; a shot takes its clip's frames from
  the clip's first. `Cut` gains `held_frames` (default 0, so earlier edit lists still read) and
  `Assembly.video` is `current/video.mp4`. **A clip shorter than its shot** holds its last frame for the
  missing frames: every cut pads its last frame without limit (`tpad=stop_mode=clone:stop=-1`) and
  `-frames:v` sets the exact count, so a clip that shows fewer frames than it has packets (an MP4 edit
  list) still gives its shot's exact frames; each cut's frames are counted after cutting and a
  difference fails the stage. `held_frames` is the estimate from the clip's packets, with a
  `clip_short` event; the Video view marks the shot. Holding rather than failing: clips are made a frame longer (§11.1),
  so only a shot longer than the clip model's 8 s (an acceptable error the owner approved, D-027) is
  short, and an overnight run should end with a video. **One encoding:** each shot is cut and encoded
  once (libx264, `medium` preset, CRF 17, `yuv420p`, timestamps `N/fps`), every cut with the same
  settings, and the cuts are joined by ffmpeg's concat demuxer with `-c:v copy` (no second encoding);
  one ffmpeg pass over every clip would hold a decoder per clip open at once (60 to 100 at 1080p). The
  song is copied into the MP4 when it is AAC or MP3, else encoded to AAC 320 kb/s; all of it is kept
  (it lasts `duration_ms`; the pictures last `round(duration_ms * fps / 1000)` frames, within half a
  frame). The clips are measured first (ffprobe, packets counted): they must share one size and be at
  the video's frame rate, else the stage fails naming every clip and saying what to do (redo the odd
  shots or put their files back, then resume; scaling would hide a finish that went wrong); a clip
  ffprobe cannot read is named by its shot. The clips are measured one after another; up to 4 cuts run
  at once. ffmpeg or ffprobe missing is a `ToolMissing` ("ffmpeg is not installed", "ffprobe is not
  installed", "ffmpeg and ffprobe are not installed"). **Timestamps (test audit):** each cut gives frame
  n the time n / fps itself (`settb=1/fps,setpts=N`) and does not pass `-r`: with `-r`, ffmpeg makes the
  output constant-rate from the clip's own timestamps, so a gap in them became copies of one frame
  instead of the clip's next frames (`test_a_gap_in_a_clips_timestamps_takes_its_next_frames` fails
  with `-r`). **A shot under half a frame** (e.g. 1000 to 1010 ms) gets no frame (`last_frame =
  first_frame - 1`) and no cut; the video still lasts the song (simpler than a new blocking rule in
  `check_shots`). **Crash safety:** the video is written in a work folder `.assemble-*` in the project
  and renamed over `current/video.mp4` only when whole, so a killed assembly leaves the old video or
  none; the stage removes a dead assembly's work folders when it starts (AC-11 kills one after its first
  cut).
- **Fakes:** `FakeModels` now writes a small real video (64x36, one colour from the call) for an `.mp4`:
  a clip of `duration_s` at 16 fps and one frame more, a finished clip of its `video` at 32 fps (twice its
  frames), so the default suite runs the real assembly. `testing.make_clip` makes such a clip.
- **Measured** (i9-14900HX, 32 threads, 2026-10-10; fewer cores take longer; synthetic 1920x1080 32 fps clips of `testsrc2`, 60
  shots of 5 s, a 5-minute WAV song): 9600 frames exactly, 300.000 s; measuring 2.8 s, cutting 79 s one
  at a time or 55 s four at once, joining 20 s (most of it encoding the WAV to AAC; an MP3 or AAC song is
  copied): about 77 s in all. The default suite went from about 55 s to about 160 s with the real
  assembly on fakes (ffmpeg starts about 40 times per fake run).
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes.

## D-036: assembling again, and runs made before M6  (2026-10-10, M6)

- **Question:** a run assembled by M1's stub (an edit list, no video), like the owner's run that started
  before M6, must get its video without making any still, clip or finished clip again. hone-flow's
  resume refuses a run whose pending step changed its version, and a fork reruns any step whose
  version, source or params changed.
- **Choices:** the `assemble` step keeps its version ("1"), signature and source text (the new code is
  in `stages_make.assemble`, which the step calls), and no other step's text changes, so a run started
  before M6 resumes under M6 (its pending `assemble` runs the new code) and its step hashes match.
  `hmv.assemble(project, models)` / `hone-music-video assemble PROJECT` / **Assemble again** in the Video
  view (`POST /api/projects/<id>/assemble`, a runner job) is a hone-flow fork of the latest run with
  `refresh=["assemble"]`: every other step is reused, only the assembly runs, no model is called; the
  fork is the project's run from then on (D-031), and an `assemble_again` event is logged. It needs the
  `finish` stage done and the run stopped (a `RunStateError`, 409 in the dashboard, also while the
  project is queued). Before forking it plans the fork (`dry_run`) and refuses, naming each step and why,
  when any other step would run (a run made by a version whose stage has changed since): assembling
  again never calls a model. The dashboard runs the same check (`check_assemble(project, models)`, with
  the runner's models) before it queues the job, so a refusal is a 409 at once. The redo and use forks
  share the fork code (`runs_redo._fork`). A run assembled by the stub that is only resumed (it is
  complete, so resume does nothing) never gets its video until someone runs `assemble`.
- **For the owner's run** (`projects/the-long-night`, started on main 6d3376d, whose 17 step versions
  and source hashes equal this branch's): once its GPU stages end, with this version installed:
  `hone-music-video assemble projects/the-long-night` if the run completed with the stub, or
  `hone-music-video resume projects/the-long-night` if it stopped before `assemble` (the new assembly
  runs). Tested by `tests/integration/test_assemble_again.py` (a run completed with the stub assembles
  again with no model call and only `assemble` run).
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes.
## D-040: the second listen  (2026-10-10, lyrics)

Change record: [0002](changes/0002-listen-again.md).

- **Question:** on the owner's song Whisper heard no words between 67 280 and 90 820 ms (the drum drop
  before Verse 1), so the first line of Verse 1 was never heard; under D-003/D-016 the line was
  dropped, the whole gap was marked an instrumental `break`, and `check_lyrics` only warned
  `lyrics-not-found`. The owner chose a second listen of just that part of the song.
- **Where:** inside the `transcribe` stage (it has the song and the given lyrics), after the first
  call and its tidy: `lyrics_match.py` (matching, gaps) and `second_listen.py` (slices, listens).
- **Matching:** the given sung lines (`sung_lines`: no blank lines, no `[bracketed]` notes, which are
  never missing) are matched in order against the heard words. A line is compared without marks
  (harakat), ZWNJ, punctuation or spaces (`plain`). In a line with non-Latin letters, the Latin words
  are transliterations (Noh, Darvin, Kaa-ra-van) that Whisper writes in the song's script with fewer
  letters: they count as unknown letters, about 2/3 as many (Darvin->دروین, Kaa-ra-van->کاروان), matching
  heard letters left over (at most as many as the known letters matched). Whether the song is written
  in Latin letters is decided once, from all its sung lines (review): in a song in another script even an
  all-Latin line ("Lo-ren-am…") is transliterations. The score of a run of heard words is difflib's ratio with those unknown
  letters; a line whose known letters are less than 60% in the run scores 0. A line is found at the
  first run scoring at least `FOUND = 0.6` that begins within `SEARCH = 40` heard words after the
  previous found line (review: on the owner's song a line began at most 3 words after the one
  before; so a missed line is not matched to a repeat far on, dragging the alignment past the lines
  between; a line not found there is missing and the cursor stays), moved to the best run beginning
  up to `LOOK = 3` words later. A run with fewer letters than 60% of the line's known letters cannot
  reach `FOUND` and is not scored, and a given line of more than `LONGEST_LINE = 200` letters (a
  paragraph pasted as one line; the owner's longest has 46) is not matched, so it is never missing
  (test audit: a 600-letter line took 13 s; the owner's song now matches in 0.04 s, was 1.9 s). Measured on the owner's song (the first listen of 2026-10-10):
  the 41 heard lines score 0.80 to 1.00 (Celina->صلینا, اسب->عصف, چاه->شاه, کشتی->گشتی all
  match); the line under the drum drop and the last line ("آخ" not heard) score 0; matching takes
  about 2 s for 305 words. The `lyrics-not-found` warning keeps its own exact check on the edited
  timeline (the editor has corrected the words by then).
- **Gaps:** consecutive lines not found share one gap, from the end of the found line before them
  (or 0) to the start of the found line after them (or the song's end); a gap without room is skipped.
  One listen per gap, at most `MAX_LISTENS = 5` per song (the first gaps in song order), none longer
  than `MAX_GAP_MS = 30 000` (review: a longer gap is more than a line or two missed; the real re-run
  had a first listen missing 1:45.920-3:11.740); the others are named, with their times, in
  `Words.not_listened`, which `check_lyrics` turns into `not-listened` warnings.
- **The listen:** the slice is the gap with 500 ms more each side, inside the song, cut with ffmpeg as
  a mono 16 kHz PCM WAV (what Whisper hears; PCM starts exactly at the cut) in a temporary folder next
  to the song, deleted after. It goes to the same transcriber (`Models.transcribe`, the D-002 client)
  with the missing lines as the prompt (`transcription_prompt` of them) and the settings' language.
  Its words are shifted by the slice's start; those starting inside the gap (not the margins, which
  re-hear the neighbours) replace the first listen's words in the gap, when it heard any; then the
  whole list is tidied with the song's length (D-017). A listen that hears nothing in the gap changes
  nothing.
- **Record:** `Words.listened_again` keeps each listen (`ListenAgain`: the lines, the slice, the gap,
  how many words it kept, and the hosted call as `Words.call` keeps it, never the key); events log
  `listened_again`. Both fields default to empty, so older `words.json` files load.
- **Still not heard (coordinator's change):** the editor's instrumental spans are kept. `check_lyrics`
  computes the gaps again on the final heard words and warns `line-in-instrumental` for each gap that
  overlaps an instrumental span (overlap > 0 ms): "'…' may be sung in 1:07.280-1:30.820, which is
  marked instrumental; listen to it", so the owner checks it by ear at the gate; `lyrics-not-found`
  warns as before. (The first version left such spans out; the coordinator chose a warning.)
- **Steps:** the `transcribe` and `lyrics` steps are version 2, so runs made before do them again
  (as D-034).
- **Echoes and invented times (coordinator, 2026-10-10):** Whisper may echo its prompt on a slice
  with little singing. The real check's second listen of the last line ("آخ… Lo-ren-am…") came
  back as the prompt itself, Latin transliteration included, with a 10 440 ms "am…"; a re-run gave
  "اوہ! Lo-ren-am" with a 9 660 ms "am", and its vocals "Ah, Lo-ren-am…". So a listen's reply is
  taken as not heard (its words are dropped, `ListenAgain.rejected` says why, and the next listen is
  tried: second, then third; after the third the line stays missing with its warning) when
  (a) a word lasts more than `LONGEST_WORD_MS = 5000`: the longest of the 305 words of the owner's
  first listen was 3 460 ms (a held "کاروان"; the next 2 340 ms), the echoes 9 660 and 10 440 ms; or
  (b) it contains one of the prompt's own transliterations letter for letter (at least 3 letters,
  compared without marks or punctuation: "Lo-ren-am" -> `lorenam`). Whisper writes what it hears
  in the song's script (Darvin->دروین, Kaa-ra-van->کاروان, Celina->صلینا on the first listen), so the
  given Latin spelling in its reply is the prompt echoed, however much of the rest is the prompt. This
  is the coordinator's "essentially the prompt, with script the language cannot produce", measured on
  the transliterations rather than the whole text: the vocals' "Ah, Lo-ren-am…" is only 0.82 alike
  to its prompt by difflib, yet copies the given spelling.
- **Known limits:** a line missed the first time that matches a later repeat (a chorus) is matched
  there, and the lines between become one gap. A line whose known letters are very few (mostly
  transliterations) may match a neighbouring line sharing them; the unknown letters can at most
  double the known letters matched.
- **Status:** accepted 2026-10-10 (the owner chose the second listen; the coordinator with the review's
  changes written in).

## D-041: the third listen: the slice's vocals, isolated on the CPU  (2026-10-10, lyrics)

Change record: [0002](changes/0002-listen-again.md).

- **Question:** the owner decided a third listen: when the second listen of a gap still does not find
  its missing lines, isolate the vocals of that slice and send them to the transcriber again.
- **Choice:** Demucs `htdemucs` (MIT; the setting `models.vocals`, default `htdemucs`, review) through the `demucs` package (4.1: torch, no torchaudio; its
  `demucs.api.Separator` takes a file and a device), not `audio-separator` (a wrapper over many
  models with onnxruntime and more dependencies, for the same Demucs model). In this library for now,
  like D-002 (a temporary exception to "every model call through hone-models"), behind the `Models`
  port: `separate_vocals(model_id, audio, *, out) -> Path`, in `adapters/vocals.py`, with
  `FakeModels.separate_vocals` (copies the slice) and `testing.check_separate` in the contract. Moving
  it to hone-models needs a change there (a separation client); then `HoneModels.separate_vocals` is
  the one place that changes.
- **When:** after the second listen of a gap, when not every missing line of the gap is found in the
  words it kept (`all_heard`). The slice (same bounds) is cut again as 44.1 kHz stereo (what htdemucs
  takes), separated, and the vocals WAV goes to the transcriber with the same prompt and shift. Its
  words in the gap replace the second listen's when it heard any. At most one per gap, so at most 5
  per song. When the separation cannot run, the third listen is skipped and one `not-listened`
  warning per reason names every gap it was not made for (review): without the extra (`ToolMissing`)
  or when it fails (`ModelFailure`: the first download offline, out of memory; test audit). The
  `transcribe` stage never fails for it.
- **CPU only, a slice only:** the adapter forces `device="cpu"` (the GPU belongs to the image and video
  models, D-005), and only the slice is separated, never the whole song. Measured: a 24.5 s slice
  of the owner's song took 34.8 s on this machine's CPU (weights cached), the transcription of its vocals
  5.2 s.
- **Optional extra `separate`** (`demucs>=4.1`, `torch>=2.5`; on Intel macOS demucs' own torch
  bound applies): the core never imports it; `adapters/vocals.py` imports it only when called. Without
  it the adapter raises `ToolMissing` ("install hone-music-video[separate] for a vocal-isolation
  listen"; a failure says the first run downloads the weights), the listen is skipped and named in
  `Words.not_listened`, so the lyrics report warns (`not-listened`); never a crash. pip users get
  torch's CPU build with `--extra-index-url https://download.pytorch.org/whl/cpu` (README). Development and CI take torch's CPU build (`[tool.uv.sources]`,
  the `pytorch-cpu` index), since the extra runs on the CPU.
- **Weights:** downloaded by demucs on first use to the Hugging Face cache (`~/.cache/huggingface/hub`,
  or `$HF_HOME`; about 80 MB), never into a project or the repository.
- **Record:** the third listen is a `ListenAgain` with `vocals`: `Separation` (model, `took_ms`,
  `input_sha256` of the stereo slice, `output_sha256` of the vocals); events log `listened_again` with
  `listen: third`.
- **Tests:** the default suite fakes the separation (first and second listen miss, the vocals are
  heard); `tests/separate/` runs the real Demucs on the CPU (marker `separate`, skipped by default).
- **Status:** accepted 2026-10-10 (the owner chose the in-library third listen; the coordinator with
  the review's changes written in).

## D-045: the first listen hears the song's isolated vocals  (2026-10-10, lyrics)

Change record: [0002](changes/0002-listen-again.md) (amendment 2026-10-10).

- **Question:** the owner decided that the first listen hears the song's vocals, isolated once, because
  `whisper-1` on the mix varied from run to run on the owner's song (once 16 of 43 lines missing, "موسیقی"
  heard from 1:07 to 3:11). The coordinator's experiment: Demucs `htdemucs` on the whole song on the CPU in
  94 s; whisper on the vocals heard 315 words, 42 of 43 lines.
- **Choice:** in the `transcribe` stage (`first_listen.py`), the whole song goes to
  `Models.separate_vocals` (D-041's adapter, CPU, the setting `models.vocals`), then its vocals to the
  transcriber with the same prompt and language as before. Without the `separate` extra (`ToolMissing`),
  or when the separation fails (`ModelFailure`), the first listen hears the mix and `Words.not_listened`
  says "first listen on the mix, not the isolated vocals: <why>" (the message says how to install the
  extra), so `check_lyrics` warns `not-listened`; the stage never fails for it.
- **Kept, not made again:** the vocals are written to the project's `vocals/` as
  `<model>-<key>.wav`, `key` = sha256 of "model|song sha256" (12 hex), with their `Separation` record
  beside them as `.json` (model, `took_ms`, `input_sha256` = the song's, `output_sha256`). The separation
  writes a hidden `.partial.wav` that is renamed when done (and deleted when the separation fails;
  review), and the record is written last: vocals with
  their record are finished, and a run made again (or another run of the project) reuses them without a
  separation. Not in a run folder: a new run would separate again. Not in `current/`: they are not an
  approved output. Events log `vocals_isolated` (model, `took_ms`) when they are made.
- **Record:** `Words.vocals` is the separation the first listen heard (`None`: the mix). The real
  separation measured here: 91.6 s for the 5:13 song (weights cached, `nice -n 10`, 32 cores).
- **The port:** `separate_vocals` now takes the whole song, never a slice; the slices for the listens
  again are cut from the stored vocals (D-046), so a song is separated once. The per-slice separation of
  D-041 is gone (one way to do it).
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes written in.

## D-046: long gaps are listened to in windows; the order of the listens again  (2026-10-10, lyrics)

Change record: [0002](changes/0002-listen-again.md) (amendment 2026-10-10).

- **Question:** a gap longer than 30 s was not listened to again (D-040), so the run where whisper heard
  only "موسیقی" from 1:07 to 3:11 kept 16 lines missing. The owner decided: listen to it in consecutive
  windows of at most 30 s, each with the lines expected in it as the prompt, capped per song.
- **Windows:** a gap is cut into the fewest equal windows of at most `WINDOW_MS = 30 000`
  (`ceil(length / 30 000)`; a gap of up to 30 s is one window, as before). The slice is the window with
  `MARGIN_MS = 500` more on each side, inside the song. The lines expected in window `n` of `count`
  (the gap's `m` lines spread evenly in order) are `lines[floor(m·n/count) : ceil(m·(n+1)/count)]`: a
  line that falls on a boundary is expected in both windows, so every window has at least one line. This
  is the simplest honest estimate; it is wrong where the gap begins with a long instrumental (on the
  owner's song the 1:07-3:11 gap starts with the spoken part and the drum drop, so the first windows'
  prompts were the lines of the windows after them). A wrong prompt still lets Whisper hear what is sung;
  the window's words are kept by time (those starting inside the window), whatever line they are.
- **The listens of a window:** the second listen is the slice of the mix; when its words in the whole
  slice (the margins included; review: a line on a window's edge is heard whole there, and should not
  force the vocals listen of both windows) do not have every line expected in the window, the third is
  the same slice of the song's vocals (cut from the vocals of D-045, no second separation). Only the
  words starting inside the window are kept. Without the vocals the mix slice is the one listen. The last listen that
  heard any words in the window replaces the first listen's words there (as D-040); the echo and
  invented-time guard (D-040) applies to every listen.
- **Which first (measured, 2026-10-10):** the real first listen on the vocals (40/43 lines) with its
  words from 1:07 to 3:11 dropped (20/43: the bad run rebuilt), then each window's slice of the mix and
  of the vocals sent alone (7 windows), twice (the replies were the same both times): mix alone 32/43,
  vocals alone 34/43, mix then vocals 36/43 in 13 calls, vocals then mix 35/43 in 14 calls. So the mix
  first, as D-040 and D-041 had it: second listen on the mix, third on the vocals.
- **Cap:** `MAX_LISTENS = 16` listens again per song (second and third counted), windows in song order;
  the windows not listened to are named in one `Words.not_listened` entry ("windows 0:17.700-0:18.000,
  … not listened to again (at most 16 listens per song)"). The owner said "e.g. 12"; 16 because the
  rebuilt bad case needs 13 or 14 listens (7 windows), at about 0.3 cents each (whisper-1, 30 s); the
  coordinator kept 16. A window whose vocals listen is still needed but would pass the cap is named
  too (review): "the vocals listen of window 4:44.586-5:13.200 not made (at most 16 listens per song)".
- **Matching after a long hallucinated run (review):** D-040 looked for a line within `SEARCH = 40`
  heard words after the line before; 62 "موسیقی" words over two minutes hid every later line. Now, after
  `missed` lines in a row not found, the next line is looked for within `SEARCH * (1 + missed)` words
  (`find_line`'s `limit`), back to `SEARCH` once a line is found. A test has 62 such words before a
  real line, found again. The rebuilt whisper-1 bad case was not measured again: its replies were not
  kept (scratch deleted); the matching change only widens the search after misses. `MAX_LISTENS = 5` gaps and
  `MAX_GAP_MS` are gone.
- **Record:** each listen is a `ListenAgain` as before, `gap_start_ms`/`gap_end_ms` being the window's,
  `lines` the lines expected in it; a listen of the vocals has `vocals` = the song's `Separation` (the one
  of D-045, so `input_sha256` is the song's, no longer a slice's). Events log `listened_again` with
  `listen: second|third`.
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes written in.

## D-047: a poor first listen is made once more  (2026-10-10, lyrics)

Change record: [0002](changes/0002-listen-again.md) (amendment 2026-10-10).

- **Question:** whisper varies from run to run; the owner decided that a first listen missing more than a
  third of the given sung lines is made again once, keeping the better.
- **Choice:** after the first listen (on the vocals or the mix), the given sung lines are matched as for
  the gaps (`lyrics_match.lines_found`: lines that can be matched, D-040). When more than a third are not
  found (`3 · missing > lines`; exactly a third missing is not made again), the same call is made once
  more. Both are checked by D-040's guard on the whole song (review): a word longer than
  `LONGEST_WORD_MS`, or, in a song not written in Latin letters, the prompt's transliterations copied.
  A listen that passes is preferred; then the one that found more lines; the first on a tie. Without given lyrics there are no
  lines and no retry. The gaps of the kept listen are then listened to again (D-046).
- **Record:** `Words.call` is the kept listen's call; `Words.retried` (`Retry`: `lines`, `first_found`,
  `again_found`, `kept_again`, `other`: the call not kept, `first_rejected`, `again_rejected`: why the
  guard did not trust each). Events log `first_listen`
  (`found`, `lines`, and `again: true` for the second).
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes written in.

## D-048: other speech models on the OpenAI-compatible gateway, through the same client  (2026-10-10, lyrics)

- **Question:** the owner asked to compare the speech models the gateway lists (`scribe_v1`, `scribe_v2`,
  `groq.whisper-large-v3`, `groq.whisper-large-v3-turbo`) with `whisper-1`, and to support the winners
  through the same port (at most one small adapter per request shape).
- **Measured (a 10 s slice of the owner's song):** all four take `whisper-1`'s request as it is (D-017:
  `/audio/transcriptions`, `verbose_json`, `timestamp_granularities[]=word`, `language`, `prompt`) and
  answer `words` with `word`, `start`, `end` in seconds, so none is dropped and no other shape is
  needed. Scribe's reply adds `speaker_id` per word, gives the language as `fas` and has no `duration`;
  the Groq replies have no cost estimate. Whether Scribe uses the `prompt` is not known: the gateway accepts
  the field, and Scribe never echoed it. Details: [history/0001](history/0001-speech-models.md).
- **Projects made before (review, Q4):** a project keeps the speech model stored in its settings; a
  lyrics run made again with Scribe (a new project, or the setting changed) moves line starts about
  0.5 s later, onto the singing (D-049).
- **Choice:** a registry entry per model in `data/models.toml`, the same as `whisper-1`'s (the same URL,
  key variable, `kind = "transcription"`, `word_timestamps = true`); the client is unchanged but for the
  price: `HostedCall.cost_usd` is the gateway's own `estimated_cost.unit` (USD) when the reply has it (it
  matched `whisper-1`'s list price, D-017), else `whisper-1`'s list price for `whisper-1`, else `None`
  (the Groq models: their price is not `whisper-1`'s).
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes written in.

## D-049: the default speech model is `scribe_v2`  (2026-10-10, lyrics)

- **Question:** which model should be `models.speech` by default (D-002 chose `whisper-1`)? The
  coordinator: the winner only if it clearly wins on lines found and stability.
- **Measured (the whole song, two or three runs per model, on the mix and on the vocals,
  [history/0001](history/0001-speech-models.md)):** `scribe_v2` found 42 of 43 lines on every run (the
  last line, "آخ… Lo-ren-am…", is missed by every model), its words the same run to run; `whisper-1`
  40 to 42; the Groq models 28 to 41, and they copy the prompt's transliterations. Scribe's line starts
  land where the vocals begin (22 to 26 of 42 lines, `whisper-1` 6 to 10): Whisper runs its words
  together, so its line starts fall in the pause before the singing. Scribe costs 0.019 USD for the
  song (`whisper-1` 0.031) and answers in about 20 s (`whisper-1` about 27 s). On the bad run rebuilt
  (D-046), the windows brought `scribe_v2` from 6 to 42 lines, `whisper-1` from 5 to 26.
- **Choice:** `models.speech` defaults to `scribe_v2` (`scribe_v1` gave the same words; v2 is the newer
  name). `whisper-1` stays a setting. Projects made before keep the speech model stored in their
  settings.
- **Consequences:** the approved timeline of the owner's project was timed by `whisper-1`; a lyrics
  stage made again with Scribe moves line starts later by about half a second (onto the singing). The
  real checks of the stage with Scribe (on the vocals, twice): 42/43 lines, 3 transcription calls,
  2.2 cents, 0 errors.
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes written in.

## D-050: the progress events  (2026-10-10, live progress)

Change record: [0003](changes/0003-live-progress.md). **Status:** accepted by the coordinator 2026-10-10.

- **Unit:** one model-made file. Kinds by version prefix (`_jobs.KINDS`): `draw` -> `draft`, `stills` ->
  `still` (a polish or a still from text), `clips` -> `raw_clip`, `finish` -> `clip`, `sheets` ->
  `sheet_take`, `portrait` -> `portrait_draft`, `polish` -> `portrait`.
- **Events:** `units` (`stage`, `totals` and `made` per kind) once when a unit stage starts making;
  `version_started` (`stage`, `kind`, `shot` or `character`, `n`, `total`) and `version_made` (the
  same with `file`, `took_ms` measured with the monotonic clock, `first`, `done`) around every file.
  `first` marks the first file of its model in this stage run: it carries the model load (D-005).
- **One way:** `version_made` replaces `shot_finished`, `sheet_take` and `pack_picture` (the tests that
  read them read it now); the activity feed still describes the old ones in older logs.
- **Made at the start:** what exists with its record. A polish is known only from its draft's content
  (its key, D-009), so it is counted as made only when its draft is; on a resume after a crash in the
  polish pass the bar starts where it stopped. `stills` draws every take of every shot, so it counts
  every take; `clips` and `finish` make only the takes in use, so they count those (D-031). The folder
  count of an old run (D-053) sees only the take in use.
- **No new thread:** the stage writes the events where it makes the files (`_jobs.Units.make`).

## D-051: the time left of a stage  (2026-10-10, live progress)

**Status:** accepted by the coordinator 2026-10-10.

- The time per unit of a kind is the mean of this stage run's units of that kind that loaded no model
  (`first: false`), or of all of them when only first units exist. The model load is the first units'
  time over their kind's warm mean, shown when at least one second.
- Time left = the remaining units of each kind at that mean (a kind not measured yet: §15's time, and
  the result is marked "estimate"), less the time already spent on the unit being made (never below
  zero, never more than one unit). Shown only once 2 units of this run are made ("estimating..."
  before).
- `progress.py` is pure (no clock, no files): `stage_progress(work, now_ms)` and `overall(works,
  now_ms)`; `_run_progress.py` reads the log and the folders. The page counts the time left down
  between updates (`data-until`) and computes no number itself.

## D-052: the overall estimate and §15's times  (2026-10-10, live progress)

**Status:** accepted by the coordinator 2026-10-10.

- Covers the long local part, `stills` to `assemble`, once the shot list is planned (before it, the
  number of shots is unknown and gates wait for the owner, so there is none). Each stage not done
  adds its remaining units at the times this run measured for the kind (in any stage), else §15's.
- §15's times per unit (`progress.DEFAULT_MS`): draft 110 s, still 22 s, raw clip 222 s (318 s with
  faces, weighted by the shots with faces), finished clip 84 s, assembly 77 s per 60 shots; sheet take
  50 s, portrait draft 90 s, portrait 26 s (from the M3 runs). A 5 s shot is assumed; a measured mean
  replaces each one as soon as this run has made one of its kind.
- The overall bar's share is weighed by time (made units at their times over made plus remaining).
  The end clock time is shown while the run runs; at a gate it says "once it runs".

## D-053: runs from before the progress events  (2026-10-10, live progress)

**Status:** accepted by the coordinator 2026-10-10.

- A stage whose latest run has no `units` event is counted from the folders: per shot, a
  `versions/draw-*.png` (shots with a cast), `still.png`, `clip-raw.mp4`, `clip.mp4`; per character,
  its `takes/sheets-*.png` (up to `sheet_takes`), a `versions/portrait-*.png` and `portrait.png`.
  The folders cannot tell a character whose sheet had no side view (so no portrait, D-021): it is
  counted as two units not made; such an old run's `packs` bar can end short of its total.
- Its times are the gaps between the file times (mtime) since the stage started, the first of each
  kind marked `first`. The unit being made is not known, so none is named and no card moves: never
  invented.
- The owner's run of 2026-10-10 (started before 0003) shows this way, labelled "counted from the files".

## D-054: the page  (2026-10-10, live progress)

**Status:** accepted by the coordinator 2026-10-10.

- A shot's newest file is its furthest stage's (`finish`, `clips`, `stills`, then the newest draft by
  mtime). Its state is what is being made for it (`drafting`, `polishing`, `animating`, `finishing`; a
  still from text is "drafting"), `failed` when its stage failed on it, else from its files.
- Motion only on what is being made: the card's ring (opacity), a sweep over its picture (transform),
  the stage's bar sweep (transform), a dot (opacity); 1.8 to 2.4 s cycles, no JavaScript timer for it,
  none under `prefers-reduced-motion`. Measured on the fake run: 50 ms of main-thread work in 10 s with
  three moving items (the 1 s clock tick and the live updates).
- The viewer (`lightbox.js`) is a modal dialog over the view's pictures and clips in the order shown
  (`ctx.gallery`): arrow keys, Esc, a click outside, a link to the file, focus kept inside and given
  back. A shot's clip there plays with its slice of the song, as a click on it did before.
- The overall estimate is in the pipeline and the Storyboard; the "Working on" card shows the stage's
  bar. Durations are m:ss (h:mm:ss from an hour), the end a clock time.

## D-055: the aligner is torchaudio's `MMS_FA`, read with ffmpeg, heard in pieces  (2026-10-10, lyrics)

Change record: [0005](changes/0005-forced-alignment.md).

- **Question:** which implementation of Meta's MMS forced aligner, and how to run it on a whole song on
  the CPU.
- **Measured (2026-10-10):** `ctc-forced-aligner` on PyPI (1.0.2) is Deskpai's fork under its own
  licence (DOSL), published as a source package with a C++ extension to build, on onnxruntime and
  librosa: not simpler. torchaudio 2.11 (the last release) still has `pipelines.MMS_FA` and
  `functional.forced_align`; its wheel is built on torch's stable ABI and declares no torch pin, and it
  runs on the locked torch 2.14 CPU build. The extra pins `torch>=2.11` and `torchaudio>=2.11,<2.12`
  (review): the versions checked; a later torchaudio may drop `MMS_FA` or `forced_align` (its 2.9
  release moved much of the library out), so it is a step to check, not taken on its own. Since
  torchaudio 2.9 `torchaudio.load` needs torchcodec, so the audio is decoded with ffmpeg (already required). A whole 5:13 song in one pass would need the
  wav2vec2 model's attention over 15 650 frames (about 15 GB): the song is heard in pieces of 30 s with
  2 s more on each side, and only each piece's own 30 s kept.
- **Choice:** the adapter `adapters/aligner.py` (the `align` extra: torch, torchaudio, uroman; torch
  and torchaudio from torch's CPU index, like `separate`), behind `Models.align(model_id, audio,
  lines) -> list[list[AlignedWord]]` (each line's words; `models.align` names the torchaudio bundle, default
  `MMS_FA`, `null` off). The weights (1.18 GB) download on first use to torch's cache (`$TORCH_HOME`,
  by default `~/.cache/torch/hub/checkpoints/`), torchaudio's own place, under a name of their own,
  `<bundle id in lower case>.pt` (`mms_fa.pt`): torchaudio's default name for them is a bare
  `model.pt`, which another model could take; `get_model`'s `dl_kwargs` passes `file_name` to torch's
  download (coordinator, 2026-10-10). Only torch's, torchaudio's and the download's errors
  (`RuntimeError`, `OSError`, `URLError`) and a `models.align` that names no torchaudio pipeline are a
  `ModelFailure` (the lyrics then timed from the heard words); any other error is a bug and is raised
  (review). There is no `language` argument: uroman is used without one (D-056).
- **Real check (the owner's song, isolated vocals, `nice -n 10`, 32 cores):** the first run 144 s with
  the download, then 46 to 57 s; all 43 lines placed.
- **Status:** accepted by the coordinator 2026-10-10 with the coordinator's answers written in.

## D-056: the given words are romanised with uroman, as written  (2026-10-10, lyrics)

Change record: [0005](changes/0005-forced-alignment.md).

- **Question:** the MMS aligner knows 27 Latin letters and the apostrophe; the owner's lyrics are
  in Arabic script with vowel marks, and Latin transliterations ("Celina", "Kaa-ra-van").
- **Measured (the owner's song, line starts against the vocals' onsets, 21 lines with a clear onset):**
  uroman on the text as written: median 38 ms, all within 456 ms. With the language code `fas`: the
  same line starts, a lower mean letter score (0.58 against 0.66). With the vowel marks taken out
  first: a higher score (0.74), but two lines after a break started 5 to 6 s early (their first word
  lost its vowels and was cut in two by D-057's pause, one letter each side).
- **Choice:** each word of the given sung lines (split at spaces) goes through `uroman` without a
  language code, as the owner wrote it (marks kept); lower case; only the aligner's letters are kept
  (hyphens, punctuation, digits and other marks dropped: "Kaa-ra-van" is "kaaravan", Latin words stay
  as they are). A word with no letter left ("—", "…") is not aligned and not in the aligned words.
- **Status:** accepted by the coordinator 2026-10-10 with the coordinator's answers written in.

## D-057: a word is not sung across a pause of the vocals  (2026-10-10, lyrics)

Change record: [0005](changes/0005-forced-alignment.md).

- **Question:** how to keep words from stretching across long instrumental passages.
- **Measured (the owner's song):** aligning the whole song at once places every line in order. But the
  aligner's letters are spikes: the first letter of a line after a break was put on the last breath
  of the line before it, so three lines started 1.5 to 5.2 s early, in the silence (L025 after the
  2 s stop, L033, L034 after the outro's break), with words of 2 to 6 s. Lowering the letters'
  probability in quiet frames changed nothing (the stray letter sits on the line before's tail, which
  is not quiet). The star token between words (MMS_FA's `with_star`, which takes what is not the text)
  kept the last word from running to the song's end (9.9 s down to 2.8 s) and moved no line start.
- **Choice:** a 20 ms frame of the vocals is quiet when its loudness is 50 dB or more below the loudest
  frame's (the vocals' silence is at -70 to -75 dB, singing above -30); 15 quiet frames in a row
  (300 ms) between two letters of a word are a pause, and the word keeps the side with the most
  letters (the first on a tie). A star token sits before, between and after the words. Line by line
  alignment in windows, or windows from the recognised words, was not needed.
- **Measured with it:** those three lines start 20 to 128 ms after the vocals' onset; line starts of
  the 21 lines with a clear onset: median 38 ms from it (approved timeline by `whisper-1`: median
  600 ms early; `scribe_v2`: 60 ms), all within 456 ms. Worse places: two soft onsets (L005, L007)
  start 322 to 456 ms late; the last word of the song ("Lo-ren-am…" held to the end) is placed at
  303.8 to 306.6 s with a letter score of 0.05, where the vocals suggest it begins at 296.2 s. The last
  line's start (292.8 s, its "آخ…") lands on a loud vocal onset at 292.7 s that recognition never
  heard (`whisper-1` put the line at 297.8 s, Scribe missed it).
- **Status:** accepted by the coordinator 2026-10-10 with the coordinator's answers written in.

## D-058: recognition stays, and is the cross-check  (2026-10-10, lyrics)

Change record: [0005](changes/0005-forced-alignment.md).

- **Question:** what recognition does when the lyrics are aligned, and when to warn that the two
  disagree.
- **Choice:** the first listen and the listens again (0002) are made as before, and their words are
  kept in `words.json` `words`: without given lyrics, with the aligner off, not installed or failing,
  the lines are timed from them. With aligned lyrics, each given line is looked for in the heard words
  as for the listens again (`lyrics_match.found_starts`); a line found more than `DISAGREE_MS` = 750 ms
  from its aligned start is recorded (`Alignment.disagree`) and `check_lyrics` warns
  `align-disagrees` ("aligned at …, heard at … (N ms apart …); listen to it"). A line recognition did
  not find is not named.
- **Why 750 ms (one `scribe_v2` listen of the owner's vocals, 1.9 cents):** 39 of the 42 lines Scribe
  found start within 467 ms of their aligned start (median 25 ms); the other three are 982, 1796 and
  2595 ms apart, and 750 ms lies in that gap. In each of the three one of the two is off the singing by
  450 ms or more: Scribe in two (L036, L037: 1040 and 2639 ms late), both in one (L005: aligned 456 ms
  late, Scribe 1340 ms early).
- **Lines the aligner is unsure of (coordinator, 2026-10-10):** the port's words carry a score
  (`AlignedWord.score`: the mean probability of the word's letters over their frames, 0 to 1). A
  line's score is its words' scores weighted by their length; a line under `UNSURE` = 0.3 is recorded
  (`Alignment.unsure`: line, start, score) and `check_lyrics` warns `align-unsure` ("aligned at … with
  a low score (…); listen to it"). Measured on the owner's song: 41 of 43 lines score 0.49 or more; the
  two under 0.3 are the whispered outro line "«یِک سال…" (0.17, its start right, its words unsure) and
  the last line (0.12: its held "Lo-ren-am…" at 0.05, placed seconds late). Single short words
  ("و", "اَز") score low on lines that are right, so a line's weighted score is used, not its worst word.
- **Aligned on the mix (coordinator, 2026-10-10):** when the vocals could not be isolated (the first
  listen heard the mix, D-045), the mix is still aligned and `Words.not_listened` gains "the given
  lyrics were aligned on the mix (no isolated vocals); their timing may be less exact", so
  `check_lyrics` warns `not-listened`.
- **Status:** accepted by the coordinator 2026-10-10 with the coordinator's answers written in.

## D-059: the lines are timed from the aligned words  (2026-10-10, lyrics)

Change record: [0005](changes/0005-forced-alignment.md).

- **Question:** how the aligned words reach the timeline while the editor still never writes a time.
- **Choice:** `Words.aligned` (`Alignment`: model, `took_ms`, the aligned words tidied as in D-017,
  `disagree`) and `Words.not_aligned` (why not) are new, both `None` by default so older files load.
  `Words.timing()` is the aligned words when there are any, else the heard words; the lyrics stage
  sends them to the editor as `heard_words` with `aligned: true` (the prompt says they are the given
  words: keep their text, split lines and sections only), `build_timeline` takes every time from them,
  and `check_lyrics` checks lines against them (the 150 ms rule of D-003, words no line uses, given
  lines not found). Events log `lyrics_aligned` (model, `took_ms`, words, disagree). The `transcribe`
  step is version 4, `lyrics` 3, `check_lyrics` 2.
- **Projects made before (coordinator, 2026-10-10):** a project or run keeps the timing it was made
  with. Stored settings (`project.json`, a run's `settings` param) are read through `settings.stored`
  (as for D-032's retired roles): stored models without `align` mean `align: null`, so a lyrics stage
  made again is timed from the heard words as before; new projects default to `MMS_FA`. Stored
  settings hold every role, so the speech model stays as stored: the owner's `project.json` reads
  `speech: whisper-1`, `align: null` (checked; a test keeps it so).
- **Status:** accepted by the coordinator 2026-10-10 with the coordinator's answers written in.

## D-060: notifications through hone-flow, one webhook from the environment  (2026-10-10, operations)

Change record: [0007](changes/0007-operations.md).

- **Question:** how the owner hears that a gate waits, a stage failed or the video is done, and where
  the webhook comes from.
- **Choice:** hone-flow's notifications (hone-flow §4.9), declared on the workflow
  (`notify.destinations`, `build_workflow`): its three events are exactly the owner's three cases
  (`run.awaiting_review` names the gate, `run.failed` the stage and its first error line,
  `run.completed`), sent at the end of every start, resume or fork call that ends so. hone-flow
  records each delivery in the manifest, never raises from the run for one, and keeps the URL out of
  every record (it reads `os.environ[url_env]` at delivery). One destination named `owner`:
  `HONE_MV_NOTIFY_URL`, and `HONE_MV_NOTIFY_KIND` = `slack` (default), `mattermost`, `discord`, `http`
  or `telegram`; an unknown kind is an `InvalidInput` wherever the workflow is built (start, resume,
  redo, use, assembling again). The message is hone-flow's: its label is the project's name (every run
  and fork is labelled so already), its summary the gate or stage, its link `browse_url` =
  `HONE_MV_DASHBOARD_URL` (default `http://localhost:8794`, the dashboard's default port; a trailing
  `/` is dropped) + `/#/p/<project id>`, made per project (the workflow is), braces doubled for
  hone-flow's template.
- **The run's folder in the message:** hone-flow's text always has the run's location (an absolute
  local path) and has no message template (only `browse_url` is one), so the path stays; it tells
  where the run is on the owner's machine, nothing secret. Leaving it out needs a hone-flow change.
- **Telegram:** the Bot API's `sendMessage` takes `chat_id` from the URL's query and `text` from a JSON
  body, so `telegram` is the Slack format (`{"text": ...}`) posted to
  `https://api.telegram.org/bot<token>/sendMessage?chat_id=<chat>`. No adapter, and the token lives
  only in the one secret URL (no separate `TELEGRAM_BOT_TOKEN` / `CHAT_ID` variables to keep secret).
  Not yet sent to a real bot (a check for the coordinator).
- **`.env`:** hone-flow reads only the environment, so `destinations` first reads the three variables
  (and only those) from the files hone-models reads, `$HONE_ENV_FILE` then `./.env`, the same way
  (`KEY=value`, `export `, quotes taken as they are, ` #` comments), never over a variable already set
  (`notify.load_env_files`). Library callers get it too. hone-models' own reader is private, so these
  few lines repeat it for three names. The tests stub it (`conftest.no_notifications`), so a `.env` in
  the folder they run from never makes them notify.
- **Not notified:** a run whose process dies (`interrupted`) sends nothing (no process is left to send
  it). When every character has a given sheet, `pick_sheets` passes on its own (D-024) just after the
  run stops there; that stop is notified as waiting (hone-flow sends at the end of the call, before
  the library passes the gate). Merged with 0004 and 0006 (2026-10-10) the same holds for every gate
  that passes on its own: `review_stills` on every run and every redo, use or assembly that reaches it
  (unless `quality_gate` is `"ask"` and a start frame in use is flagged, when it really waits), and
  every gate of an unattended project. hone-flow's webhook has no per-gate filter; muting these needs
  a hone-flow change (not proposed yet).
- **Tests:** hone-flow's `WebhookServer` shaped like Telegram (the planted token in the path, the chat
  in the query): every gate and the end are told with the project, the gate and the page; a planted
  planner failure is told with its stage and error; each kind's body; the token and the URL are in no
  file of the project; a bad kind stops resume, redo and assembling again; `.env` read, the
  environment winning; a trailing slash on the dashboard's address.
- **Status:** accepted by the coordinator 2026-10-10.

## D-061: hone-models' records name the run and the stage  (2026-10-10, operations)

Change record: [0007](changes/0007-operations.md).

- **Question:** hone-models records each planner call's price in its span store, but the spans of the
  owner's run carry no run or stage: nothing ties a call to a project.
- **Choice:** `HoneModels.plan` and `generate` pass `trace=hone_flow.current_trace() or None` (inside
  a step: `traceparent`, `hone.run_id`, `hone.step`, `hone.item`); hone-models copies those keys onto
  every span (its §8.3, §8.5), and the span joins the step's trace. Outside a step it is `None`, so
  hone-models uses its own context as before. The in-library transcription (D-002) and Demucs (D-041)
  record their own calls in `words.json` and need nothing.
- **Status:** accepted by the coordinator 2026-10-10.

## D-062: what a video cost: read, never estimated  (2026-10-10, operations)

Change record: [0007](changes/0007-operations.md).

- **Time:** every run of the project with hone-flow (`open_runs`, every step record and its earlier
  `attempts`, times from `started_at` / `ended_at`, ms); a step with `reused_from` was copied by a fork
  and is skipped. In a fork every attempt is a `redo` (redone shots, assembling again); in the run,
  attempt 1 is the `first` pass and later ones `reruns` (a gate rejected, a failure retried).
- **Where:** from design §3.1: GPU = `sheets`, `packs` (the cut is CPU, the portrait GPU), `stills`,
  `clips`, `finish`; hosted = `transcribe` (its Demucs listen on the CPU included), `lyrics`,
  `plan_cast`, `plan_shots`; CPU = the rest. Stage wall time, model loads and ComfyUI starts included.
- **Transcription** (its only source: hone-models' `hone.models.transcribe` spans are not read, so
  nothing is counted twice): each `transcribe` attempt's `words.json`, `call` and every
  `listened_again[].call` with their `cost_usd`: the current one's from `output/`, a retired one's from
  `attempts/<n>/output/`. An attempt without one (failed) is one unknown call.
- **Planners:** only `hone.models.chat` spans, only for `lyrics`, `plan_cast`, `plan_shots`, read with
  one read-only SQL query on hone-models' store (its `spans` table, §8.2) limited to the project's
  time (its first attempt's start to its last attempt's end, a minute either side). A span naming one
  of the project's runs (`hone.run_id`, D-061) is that run's stage's (`hone.step`); its time only
  picks the attempt (the one running then, else the stage's latest), so it is never dropped. A run no
  span names (made before 0007) takes the spans without a run that started during an attempt of its
  planner stages. Every other span (another run; another tool's call during a run that is named) is
  not this video's. A planner attempt with no call found (no store, or no span) is one unknown call.
- **Unknown:** a call without a recorded price, a failed transcription, a planner attempt without a
  found call: `unknown_calls`, never a number; `hosted_usd` is then a lower bound. `store` names the
  store read and `store_found` says whether it was there; the command line and the panel then say "no
  hone-models records found at ...".
- **Record:** `current/costs.json` (`Costs`), written after every start, resume and fork of the run
  (`video_costs.write_costs`, from `runs` and `runs_redo`); `hmv.costs`, the `costs` command and the
  API only read.
- **Known limits:** the store is the one of the process (`${HONE_HOME:-.hone}` of its working folder):
  ask from the folder the runs ran in. Time lost to a killed attempt is not recorded by hone-flow, so it
  is not counted. A run made before 0007 takes another tool's chat call made during its planner stages.
- **Status:** accepted by the coordinator 2026-10-10, with the review's items 1 to 4.

## D-063: the edit for editors: FCP7 XML and CMX3600  (2026-10-10, operations)

Change record: [0007](changes/0007-operations.md).

- **Choice:** FCP7 XML (`xmeml` version 4), the one interchange format both DaVinci Resolve and
  Premiere Pro import (FCPXML is Final Cut Pro X's, which Premiere does not read; AAF and OTIO need
  libraries). Written with `xml.etree` (no dependency). One `sequence` (the project's name, `rate` =
  the video's fps, `ntsc` FALSE, timecode from `00:00:00:00` non-drop), a video `format` with the
  clips' size, video track 1: a `clipitem` per cut named by its shot (`start` = `first_frame`, `end` =
  `last_frame + 1`, `in` 0, `out` = the length; its `file` with `pathurl` = `file://localhost` + the
  percent-encoded absolute path, the form both editors write, the clip's own frame count and size),
  audio track 1: the song (0 to its length in frames, `round(duration_ms * fps / 1000)`, its sample
  rate and channels, `sourcetrack` audio 1). Plus a CMX3600 EDL (`edit.edl`): an event per shot (reel =
  the shot id, source from 00:00:00:00, record its frames; `* FROM CLIP NAME:` the file's name, which
  Resolve matches media by, and `* SOURCE FILE:` its path), then the song (`AA` when stereo).
- **No second measuring:** the assembly hands the clips it measured for the cut and the run's `measure`
  (`Song`, a new input of the `assemble` step) to `editor_files.write`; only `export` measures them.
- **After the video:** the video and `edl.json` are written first; a failure of the editor files is an
  `editor_files_failed` event (a warning), never a failed assembly; `export` writes them again.
- **Held frames:** an editor's clip cannot run past its media, so a clip shorter than its shot ends at
  its own last frame and the held frames are a gap (the video holds the last frame, D-035). An edit
  list without shots is a `RunStateError`; a missing clip at `export` an `InvalidInput` naming the shot.
- **Frame rate:** the video's (32 by default) as it is; 32 fps is not a standard timeline rate in
  either editor, so how each takes it is a check for the coordinator, with the real files.
- **Tests:** the files of a fake run in a folder with spaces and non-ASCII letters, parsed back
  (ElementTree; the EDL's timecodes), every clip's and the song's frames checked against `edl.json`;
  stereo `AA`; no second ffprobe; a failure only a warning; a deleted clip; an empty edit list.
- **Status:** accepted by the coordinator 2026-10-10.

## D-064: where the new things are  (2026-10-10, operations)

Change record: [0007](changes/0007-operations.md).

- **Choice:** the assembly writes `edit.xml` and `edit.edl` after `edl.json` (stage 13, so assembling
  again and every redo write them too); `hmv.export` / `hone-music-video export PROJECT` writes them
  again from `current/edl.json` (for a video assembled before 0007; no run, no model call; refused
  without an assembled video). `hmv.costs` / `hone-music-video costs PROJECT [--json]` and `GET
  /api/projects/<id>/costs` only read; `current/costs.json` is written after the run's calls (D-062).
  The dashboard serves `.xml` and `.edl` from `current/` (as `application/xml`, `text/plain`); the Video
  view lists them as downloads and draws the cost panel from the API. Modules `editor_files.py` and
  `video_costs.py` (not `export.py`, `costs.py`: the package's `hmv.export` and `hmv.costs` are the
  functions).
- **Status:** accepted by the coordinator 2026-10-10.

## D-065: a face shot gives the portrait first  (2026-10-10, quality)

Change record: [0006](changes/0006-quality.md).

- **Question:** in the first real run a close-up of Celina came out younger and softer than her
  portrait: design §10.1 gave every shot the front view first, a full-body figure whose face is small,
  so the start-frame model took the face from it.
- **Choice:** a **face shot** is a shot with `faces: true` framed `medium`, `close-up` or
  `extreme-close-up` (`prompt_assembly.face_shot`; an `insert` with faces is not one). In a face shot a
  person or a creature prefers portrait, front, side; in any other shot front, portrait, side (D-030);
  an animal keeps side, front everywhere. The round robin and the three slots are unchanged, and a
  shot's own `refs` still win. A face shot's start-frame prompt ends with one sentence per character
  whose portrait it got: "The woman from images 1 and 2 keeps the face of image 1: same age, same
  features." (the character named as everywhere else, so two women stay apart; "same age" because the
  fault was a younger face). It costs nothing (no call, a few words) and the polish prompt is
  unchanged.
- **A setting, so old projects keep their keys (coordinator):** `face_refs: "portrait-first" |
  "front-first"`, default `"portrait-first"` for a new project. Settings stored before 0006 (a
  project's `project.json`, a run's `settings` param) have no `face_refs`; `settings.stored` reads a
  missing one as `"front-first"` (as D-032 drops retired keys), so an old project's start frames keep
  their references, prompts and version keys (D-009) and a redo on it remakes only the shot asked.
  `"front-first"` also drops the identity sentence.
- **Real check left for the owner:** `tests/gpu/test_faces.py` (skipped by default) draws the same
  close-up with the portrait first and with the front first (same seed), from a real pack
  (`HONE_TEST_PACK`), for the owner to compare.
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes.

## D-066: the start-frame check: one vision call over contact sheets  (2026-10-10, quality)

Change record: [0006](changes/0006-quality.md).

- **Choices:** a new stage `check_stills` (stage 11, `stills_check.py`) after `stills`. It makes **one**
  `Models.plan` call (role `models.quality`, default `claude-opus-5-5` on the OpenAI-compatible gateway; the system prompt
  `data/prompts/quality.md`) for the whole video, never one per shot. What it shows: the start frame in
  use of every shot, and every take of a shot the check picks for (D-068). **Contact sheets**
  (`_contact_sheet.py`): 4 x 3 tiles, each tile's long side 480 px (a 16:9 sheet is 1944 x 946, about
  what a vision model reads whole), an 8 px gap, the label burnt in white on a 40 px black band above
  the tile: the shot id, or `S012 #2` when the shot has several takes. A sheet is named after its
  content (`current/checks/sheet-<sha12>.jpg`) and never overwritten. The images, in order: each
  character's front view and portrait (as the shot planner gets them, `stages_plan.pack_pictures`),
  then the sheets. The data: the style, the cast (id, name, kind, noun, cue), the pictures and sheets
  with their image numbers, and per still its label, sheet image, shot, take, framing, `faces`, cast,
  location and still prompt (with each character's cue, as the polish pass reads it).
- **The reply** (`StillsReview`): per label a `score` 1 to 10 and `flags`, each a `kind` (`anatomy`,
  `wrong-character`, `missing-character`, `extra-people`, `text`, `unwanted-face`, `off-style`), a
  `severity` (`minor`, `major`) and a one-sentence `reason`. A label the reply invents is dropped; one
  it leaves out is listed in `unreviewed` (no score, no flags, never picked). An invalid reply is sent
  back by hone-models' structured output like the planners' (D-025); a failed call fails the stage
  (resume runs it again), as a planner call does.
- **The record** (`StillsCheck`, the stage's output): the model, `took_ms` (the call, measured around
  it; hone-models records the cost and tokens in its spans), the sheets, each still's verdict (`shot`,
  `take` index, `score`, `flags`), `unreviewed`, `picked` (D-068) and `flagged`: the shots whose start
  frame in use has a major flag (D-067). `StillsCheck`, `StillCheck` and `StillFlag` are exported. An event `stills_checked` logs the counts and the time. The stage then
  makes each shot's `still.png` the take it uses and writes its `takes.json`.
- **Surfaces:** `GET .../records` gains `stills_check`; the Storyboard shows the flags of the start
  frame in use on each card (major first, with the reason), each take's score ("picked" for the
  check's pick) and how many shots were flagged.
- **Off:** with `quality_check: false` the stage makes no call and returns an empty record (no flags,
  no picks); the gate after it passes on its own. Settings stored before 0006 have no `quality_check`;
  `settings.stored` reads a missing one as `false` (coordinator), so an old project makes no call.
- **Size (review):** the sheets are JPEG at quality 85 (`sheet-<sha12>.jpg`, a few hundred kB). At most
  `MAX_TILES = 144` start frames (12 sheets) go in one check; more is a typed `InvalidInput` that says
  to set `pick_best_of` lower or `pick_shots` to `"faces"` (or `quality_check` to false) and resume. 60
  shots with best of 3 on the 33 with faces are 126 tiles (11 sheets, about 0.4 USD); best of 3 on
  every shot of 60 (180) is refused.
- **Measured** (one real call on 16 of the owner's first start frames, two sheets and 8 pack pictures,
  2026-10-10): 37.9 s, 16 731 input and 1 567 output tokens, 0.098 USD. It flagged the one start frame
  with a second woman (`extra-people`, major) and two faces turned towards the camera in shots planned
  without faces (`unwanted-face`, minor). So about 0.2 USD for 60 shots.
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes.

## D-067: the `review_stills` gate waits only when asked  (2026-10-10, quality)

Change record: [0006](changes/0006-quality.md).

- **Choices:** `GATES` gains `check_stills: review_stills`, an ordinary hone-flow gate whose output is
  the check's record (`clips` and `finish` read it, so they follow it). After every start, resume and
  fork (a redo, a use, assembling again) the run passes on its own (approved as automated, with an
  event `gate_approved` that has `automated` and the reason as `note`) every gate with nothing to
  decide: `pick_sheets` without sheets (D-024, unchanged) and `review_stills` unless the setting
  `quality_gate` is `"ask"` and `flagged` is not empty. With `"ask"` and a flag the run waits; the
  owner redoes flagged shots from the Storyboard or the CLI (each redo runs the check again and stops
  at the gate again while a start frame in use has a major flag) or approves to go on. **Only a major
  flag stops the run** (coordinator); minor ones are shown on the Storyboard, not blocking. Anything that approves gates (`hmv.approve`, the
  CLI, the dashboard, an automatic approval) treats it like the other gates; it cannot be run again
  with a note (`reject`): a redo is the way to change a start frame.
- **With unattended runs (0004, merged 2026-10-10):** a gate with nothing to decide passes as above
  first, in either mode; in an unattended project a waiting `review_stills` is then approved as `auto`
  like any other gate (a flag is not a check error, D-076), so "run without stopping" wins over
  `quality_gate: "ask"`. A fork (a redo, a use, assembling again) passes the gates the same way after
  it runs; applying a re-plan decides its own gate first (D-074).
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes.

## D-068: best of N takes, picked by the check  (2026-10-10, quality)

Change record: [0006](changes/0006-quality.md).

- **Choices:** settings `pick_best_of` (1 to 3, default 1) and `pick_shots` (`"faces"`, default: the
  shots with `faces: true`; or `"all"`). A shot it chooses (`takes.picks_best`) has `max(still_takes,
  pick_best_of)` planned takes that differ in the still's seed (D-031), each drawn and polished by the
  `stills` stage. `pick_best_of` above 1 needs `quality_check` (refused otherwise: nothing would pick).
  The check shows every take of such a shot and picks the take with the highest score, the earliest on
  a tie, none when no take of the shot was reviewed (take 1 stays). The pick is `StillsCheck.picked`
  and the take each shot uses unless the owner chose one (the run's `takes` param wins); only that take
  gets a clip and a finished clip.
- **Picks stay picked:** a redo or a use runs the check again, and a new reply could score the takes
  differently and so make another shot's clip again. So once a check exists, a redo or a use first
  writes the take in use of every best-of-N shot the owner has not chosen into the run's `takes` param,
  as if the owner had chosen it: the check's pick, or the first take when it picked none (a shot it
  did not review; review) (`runs_redo._picks_kept`). From then on those shots show only their take in
  use to the check, and a redo makes only its own shot again (guarantee 12).
- **A redo that would remake other shots is refused (coordinator):** before forking, a redo or a use
  works out what the fork would make for every shot (the run's settings and each step's seed, this
  version's code) and refuses with a `RunStateError` naming each other shot whose still, clip or
  finished clip the run had but the fork would make again, before any model call. A shot whose file
  the run never made (unfinished work, as at a waiting `review_stills`) is not counted. (hone-flow's
  dry-run fork lists steps, not shots: every redo reruns the per-shot steps, so the check is per shot.)
  When 0006 and 0008 were merged (2026-10-10) this became one guard, 0008's `runs_redo.guard` (D-071)
  with this rule for unfinished work (`_remade.remade_others`); the separate `_remake_check.py` went.
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes.

## D-069: the estimate of extra takes  (2026-10-10, quality)

Change record: [0006](changes/0006-quality.md).

- **Choices:** the numbers live in `estimates.py` only: `TAKE_S = 125` (a start frame with a cast drawn
  in about 100 s with the model loaded, 103 to 125 s with the load, plus 17 to 26 s of polish: §15),
  `TEXT_TAKE_S = 23` (a start frame from text, §15), `SHOT_MS = 5200` and `FACES_SHARE = 0.55` (the
  owner's first real shot plan: 60 shots over 5:13, 33 with faces). An extra take never adds a clip.
  The formula: `extra = pick_best_of - max(still_takes, 1)` takes per chosen shot (no warning when it
  is 0: `still_takes` already draws them); `extra seconds = extra x` the sum over the chosen shots of
  `TAKE_S` (a shot with a cast) or `TEXT_TAKE_S` (without) when the shot plan is known, else `extra x
  TAKE_S x shots` with `shots = ceil(duration_ms / SHOT_MS)`, times `FACES_SHARE` for `"faces"`,
  rounded (shown with `~`). Without ffprobe or a length, only the time per shot. Text: "Best of 2 on shots with faces: about +54 min of GPU (≈ +2 min per shot × ~26 shots)"
  for a 4-minute song; without a length, only "≈ +2 min per shot of GPU".
- **Where:** the CLI prints it as a `warning:` on stderr after `new` and before `run` (the song measured
  with ffprobe; the shot plan when there is one). The New video form asks the server
  (`POST /api/estimate` with the settings and the song's length, which the browser reads from the
  dropped file), shows it under the settings and asks to confirm it on Start. The quality call itself is
  hosted (no GPU time) and runs with `quality_check` whatever `pick_best_of` is.
- **Status:** accepted by the coordinator 2026-10-10 with the review's changes.

## D-070: a batch redo is one fork  (2026-10-10, batch redo)

Change record: [0008](changes/0008-batch-redo.md). **Accepted by the coordinator, 2026-10-10.**

- `runs_redo.redo_takes(project, {shot: Redo})` adds a take to every shot asked for in one new value of
  the run's `takes` param (D-031); one `remake` forks the run once, so the stages make only those shots'
  new versions and `assemble` runs once. One shot still logs `shot_redo` (`shot`, `take`); several log one
  `shots_redo` with `takes` (shot -> its new take's number).
- `hmv.redo(project, models, shots, redo)` takes one id or a list; an item that is not an id but
  `A-B` with both ends in the plan is the range in plan order, either way round (`S015-S012` too). Each
  shot is listed once, in plan order. Unknown ids are `NotFound` naming the shots.
- The CLI's `redo` takes `SHOT...`; one `Redo` for all (the prompts too, checked against each shot's
  cast). The API's `POST /redo` takes `{shot, ...}` as before or `{"shots": [{shot, seed, still,
  still_prompt, motion_prompt}, ...]}`: each shot its own redo, which the Storyboard's prompt list uses.
  It answers `{redo: [ids], made, left_ms, estimate}`; `"dry_run": true` answers without queueing.
  A shot listed twice in `shots` is refused (`InvalidInput` naming it): its two redos would conflict.
  The CLI's and Python's ids and ranges are a set: overlapping ranges name each shot once.
- While a re-plan proposal waits (`replan.json`), a redo or a "use this version" is refused ("apply
  or discard the proposal first"): it would be made against the plan the proposal replaces.
- The approved plan and takes are read once per redo (`stopped_plan`) and carried in the `Remake`.

## D-071: the guard works out each shot's jobs  (2026-10-10, batch redo)

**Accepted by the coordinator, 2026-10-10.**

- Before a redo or a "use this version" (and a re-plan, D-073) the fork is planned twice, making
  nothing: hone-flow's dry run (any step to run other than `stills`, `check_stills`, `review_stills`,
  `clips`, `finish`, `assemble`, and `review_shots` for a re-plan, is refused with its reason, as D-036 does for assembling again), then
  `_remade.to_make`: for every shot and take, the stills stage's draw and polish jobs (`StillMaker`, the
  stage's own class), and for the take in use the clip and finish jobs (`clip_task`, `finish_task` and
  `take_job`, which `stages_make` uses too: one seed rule), each keyed as the stage keys it (the step's `ctx.seed` is hone-flow's
  `step_seed(run seed, item, step)`; `stills`, `clips` and `finish` are never refreshed or rejected, so
  it has no salt: were one ever refreshed, its keys would change and the guard would show it as
  refusals, never as a silent remake). A unit
  whose version is not on disk would be made; a polish is known only once its draft is, so a missing
  draft means a draft and a still.
- Any unit for a shot not asked for refuses the redo when the run has that kind of file of the shot
  (`_remade.made_before`; work the run has not done yet is not refused, D-068): "this would also remake
  S004 (finished clip): their files are not on disk under the keys this version gives them (made with
  other settings or by an older version, or removed); select those shots too". Every best-of-N shot
  keeps the take it uses (D-068), so a check's new scores never remake another shot. The owner's earlier runs therefore cannot silently remake the
  whole video after a code change to how keys are made.
- **Settled (coordinator, 2026-10-10):** refusing, with the explanation, is the honest fallback for
  runs whose keys changed (old projects mostly keep their keys once stored settings get defaults).
- It hashes the inputs it keys (stills, raw clips), as the stages do: a few seconds for 60 shots.

## D-072: the time a redo should take  (2026-10-10, batch redo)

**Accepted by the coordinator, 2026-10-10.**

- The units of D-071, each at this project's measured time per kind (`progress.averages` over every
  `version_made` event in `events.jsonl`, warm units preferred), else §15's (`DEFAULT_MS`, then
  `estimate` is true), plus the assembly at §15's time scaled by the shot count. A raw clip's §15 time is
  the 832x480 one when unmeasured (faces are not weighed: the measured time takes over after one clip).
- Shown as whole minutes ("7 shots ≈ 55 min of GPU"), and by `redo --dry-run`.
- Only the shots asked for are counted (merged with 0006, 2026-10-10): at a waiting `review_stills`
  the other shots' clips are the run's remaining work, not the redo's, and are not in the estimate.

## D-073: re-plan: the call, the check, the proposal  (2026-10-10, batch redo)

**Accepted by the coordinator, 2026-10-10.**

- One `plan` call with the shot planner's usual data (timeline, story, cast, settings, the pack
  pictures), `previous_plan` (the approved plan) and `replan: {shots, note}`; the prompt's new rule says
  to return every unlisted shot exactly and keep the listed ones' ids and times unless the note asks.
- The code's check: the same shot ids in the same order (a re-plan never adds, removes or renumbers a
  shot, so takes and folders stay put); every unlisted shot equal field by field; no `check_shots` error
  the current plan does not have (`(where, rule)` pairs; errors the owner accepted before stay accepted).
  Problems go back once with `previous_reply` and `problems` (`keep_shot`, `same_shots`, or the check's
  rule); a second failure is a `ModelFailure` naming the problems and the fields that differ, and nothing
  is kept. Each call is logged as `shots_replanned` (`call`, `problems`).
- A reply that changes none of the listed shots is refused ("say more in the note").
- **Settled (coordinator, 2026-10-10):** a re-plan keeps the shot ids, count and order, and the
  changed shots' takes start again (D-074); that is fine as it is.
- **Cost:** each call's cost as recorded: `HoneModels.plan` keeps `last_plan_cost_usd` (hone-models'
  `cost_usd` of the registry's price and the call's usage; None without a price or usage), and the
  re-plan reads it after each call. A call without a recorded cost counts at $0.6 (docs/shots.md), and
  the proposal's `cost_estimate` says so ("$0.60 (an estimate)"). The port is unchanged: a `Models`
  without the attribute reads as unknown. `FakeModels(plan_cost_usd=...)` reports one for tests.
- The proposal, `<project>/replan.json` (`Replan`: run id, shots asked, note, each change before and
  after, the whole plan, calls, `cost_usd` and `cost_estimate` as above, and D-071/D-072's `made`,
  `left_ms`, `estimate`), is replaced by a new one. Events: `replan_asked`, `replan_proposed`,
  `replan_failed`, `replan_discarded`, `replan_applied`; the dashboard shows "re-planning…" while the
  last of them is `replan_asked`. A proposal is applied only to the run it was made from.
- The planner call runs in the dashboard's runner (it takes minutes), as a `replan` job; the page says
  "re-planning" while the runner has that job queued or running (`Runner.replanning`), never from the
  log alone. Any stop while the planner works (an error, Ctrl-C) writes `replan_failed`; an ask whose
  process was killed outright is cleared by `discard_replan`, which writes `replan_discarded` then.

## D-074: applying a re-plan  (2026-10-10, batch redo)

**Accepted by the coordinator, 2026-10-10.**

- A fork with `refresh=("review_shots",)` and the run's takes without the changed shots: the gate runs
  again and waits; it is then decided by hone-flow's `edit` with the new plan (actor `replan`,
  `automated`), and the run resumes: `stills`, `clips`, `finish` make only the changed shots, `assemble`
  runs once. `plan_shots` and `check_shots` are reused: they keep the planner's original reply and its
  check (the edit is the record of the change, as an owner's edit would be). The workflow's steps are
  not changed, so no step's source hash changes for runs made before.
- **What the views check (coordinator, 2026-10-10):** the Shots view's findings, the records'
  `shots_check` and `check-shots` are of the applied plan: `runs_replan.shot_plan` gives the approved
  plan (`review_shots`) once there is one, else `plan_shots`, and when the approved plan differs from
  `plan_shots`' reply it runs `check_shots` on it (a pure check, milliseconds) instead of showing the
  stored check of the first reply.
- **Picked up after a stop:** when the latest run is the re-plan's fork waiting at `review_shots`
  (the process stopped between the fork and the edit), `apply_replan` makes the edit and resumes
  instead of refusing. The edit (`edit_gate`) turns another process holding the run (`_gates.busy`), or a
  gate no longer waiting (hone-flow's `ReviewError`), into a `RunStateError`; `_gates.decide` is left as it
  is, since the unattended approval relies on its `ReviewError` passing through.
- The changed shots' takes start again from the new plan's prompts (their old take lists would hold the
  old prompts); every earlier version stays in `versions/`.
- The records' `shots`, `shot_files` and `shots_check` read the approved plan and its check
  (`shot_plan`, above).
- A project in auto mode (0004) applies a proposal as soon as it is made; otherwise the Storyboard shows
  it (old and new fields and prompts per shot) with Apply and Discard, and the CLI has `--apply` and
  `--discard`.

## D-075: where the unattended mode lives and when it is read  (2026-10-10, unattended runs)

Change record: [0004](changes/0004-unattended-runs.md). **Status:** accepted by the coordinator 2026-10-10.

- **Where:** `project.json` `approve` (`"ask"` default, `"auto"`), beside `settings`, not inside them:
  the settings are the run's parameter (D-009), so a setting would not reach a run already started and
  switching would need a new run. A missing key reads as `"ask"` (older projects), and the key is
  written only for `"auto"`: a project that asks stays readable by a version from before 0004
  (`ProjectFile.as_stored`, review).
- **When:** `runs.start`, `runs.resume` and every fork of a redo, a use or assembling again (not a
  re-plan's, D-074) pass the gates after the run stops (`_gates.pass_on_its_own`, which first passes a
  gate with nothing to decide, D-024, D-067, then asks `_auto_approve.approve_unattended`): they read
  the mode from `project.json` each time the run waits.
  So the CLI's `run`/`resume`, the dashboard's runner and the Python API behave alike, and switching a
  waiting project to `"auto"` takes effect at its next `resume` (the dashboard submits one).
- **How:** hone-flow `approve(gate, note=..., actor="auto", automated=True)`, then a
  `gate_auto_approved` event, then the run resumes. `pick_sheets` approves the takes on offer as they
  are (`picked` = the first new take of each character, D-024). `Stage.gate_auto` is true when the
  gate's last decision is an approval by the actor `auto`.
- **A decision first:** when the owner (or another process) decides the gate between the run stopping
  and the unattended approval, hone-flow refuses the second decision (`ReviewError`); the run stops
  quietly and the owner's decision stands (review).
- **Switching:** `set_approve_mode(project, mode)` rewrites `project.json` atomically; the dashboard's
  `POST /api/projects/<id>/approve-mode {approve}` then resumes a waiting run (unless it is queued).
  Changing the mode while the run is running is safe: it is read at the next gate.

## D-076: auto-approval never accepts errors  (2026-10-10, unattended runs)

**Status:** accepted by the coordinator 2026-10-10.

- At `review_lyrics` and `review_shots`, any error in the check's report stops the unattended run there,
  including the shot list's *acceptable* errors (D-027): accepting those is the owner's decision (the
  conservative reading of the request). Warnings do not stop it.
- The stop writes `auto_stopped` (`gate`, `reason`) once: not again while it is the newest stop and
  nothing decided the gate since (review). The gate waits as in "ask" mode, and the page says
  "Stopped: needs you" on the gate card when the check has errors or that stop stands, else "Continuing
  on its own…". After the owner fixes it (a rerun with a note) the run, still in
  `"auto"`, continues on its own once the check is clean.
- **Settled (coordinator, 2026-10-10):** the conservative reading stays: auto-approval never accepts
  acceptable shot errors; the owner approves those by hand (`approve --accept-errors`, or the Shots
  view's confirmation, D-027).


## D-077: the fixed traits and the anchor come from the cast planner  (2026-10-11, 0014)

Change record: [0014](changes/0014-prompt-and-reference-fixes.md). **Status:** accepted (owner delegated
acceptance overnight; answers as recommended), 2026-10-11.

- `Character.traits` (one phrase: age, build, hair, beard; for an animal its colour and markings) and
  `Cast.anchor` (one sentence: the kind of film, the period and the place) are new cast-planner fields
  (open questions 1 and 2), both `""` by default so an older `cast.json` loads.
- The shot planner's request carries `traits` in each of `cast.characters` and `anchor` at the top
  level. A character without `traits` (a cast made before 0014) sends the description part of its
  `sheet_prompt` instead: the text from "plays" up to "The costume is identical" when the sheet prompt
  follows the cast planner's template, else the whole sheet prompt; nothing for a given sheet without
  one. The rest of the sheet prompt still never reaches the shot planner (D-027).
- The step versions of `plan_cast` and `plan_shots` stay: their records only gain optional fields, and
  0008's guard must not refuse the redo of an older run.

## D-078: the `speech` and `no-anchor` warnings  (2026-10-11, 0014)

**Status:** accepted (owner delegated acceptance overnight), 2026-10-11.

- `speech`: a still or motion prompt with a word of speech, matched as whole words in any case, with
  their usual inflections: speak/spoke, say/said, sing/sang/sung, whisper, talk, call out, recite,
  chant, "mouth(s) the words", "lips move", "lips form words" (and "-ing" forms). Expressions (smile,
  laugh, shout, roar, gasp, cry) never match. One warning per prompt, naming the words found.
- `no-anchor`: a still prompt that does not contain the cast's `anchor` (compared without case and with
  runs of spaces as one, a final full stop ignored). No warning when the cast has no anchor (an older
  cast): there is nothing to compare with.
- Both are warnings: they never reach a repair call and never stop an unattended run (D-076). The
  `check_shots` step version stays "1" (a step version change would make 0008's guard refuse a redo of
  an older run); a re-plan or the CLI's `check-shots` checks with the new rules.

## D-079: references by kind of shot (`face_refs: "by-shot"`)  (2026-10-11, 0014)

**Status:** accepted (owner delegated acceptance overnight; open question 3 as recommended),
2026-10-11.

- `face_refs` gains `"by-shot"`, the default of a new project. A face shot (`faces` and medium or
  closer) orders a person's or creature's views portrait, front, side, one character after another
  (as `"portrait-first"`); any other shot (`faces: false`, or a wide shot marked `faces: true`, which
  `check_shots` already reports) gets no portrait: a person or creature front then side, an animal side
  then front. No-face shots stay on Qwen with these views (experiment D may later move them to Z-Image
  from text).
- The identity sentence ("keeps the face of image N") is added in a face shot for each portrait it got,
  unless the project is `"front-first"` and the shot has no `refs` of its own: a re-plan's refs (below)
  bring it with them.
- A project whose settings are older (`"portrait-first"` or `"front-first"`) keeps them. A re-plan
  (0008) on such a project writes the by-shot references into the changed shots' own `refs` when the
  planner left them `null`, so only those shots get the new references and no other shot's key changes.

## D-080: the vision check rewrites motion prompts  (2026-10-11, 0014)

**Status:** accepted (owner delegated acceptance overnight), 2026-10-11.

- The `check_stills` call also gets each start frame's beat, camera and planned motion prompt (each
  character named by its cue), the cast's `anchor` and the limits of the video (`limits.md` follows
  `quality.md` in the system prompt). The reply may give each start frame a `motion_prompt` and flag
  `anachronism`.
- A rewrite is kept in `current/checks/motion-prompts.json` under the start frame's file and the planned
  motion prompt it was written from, so a start frame keeps the rewrite first written for it: a later
  check (a redo's fork) asks only for start frames without one, and the clips of the other shots keep
  their keys (0008's guard). An empty or missing rewrite, or one over the motion prompt limit (1000
  characters), is kept as the planned prompt with a `motion_rewrite_dropped` event: the start frame is
  asked only once, so a later redo of another shot never changes its clip's key (review).
- The clip uses the rewrite when `rewrite_motion` is on and the take's motion prompt is the planned one;
  a take whose motion prompt differs from the shot's was written by the owner (`redo --motion-prompt`)
  and is used as it is.
- `rewrite_motion` (default `true`, stored settings without it read `false`) has an effect only when the
  check runs (`quality_check`); with the check off it is not an error, nothing is rewritten and the clips
  use their own prompts (rewrites kept earlier are not used while it is off).
- Step versions stay (`check_stills` "1", `clips` "3"), unlike the record's plan: an older project has
  `rewrite_motion: false`, so its check and clips do what they did, and a version change would make
  "assemble again" refuse every older run.

## D-081: the cutter keeps only what is joined to the figure's head  (2026-10-11, 0014)

**Status:** accepted (owner delegated acceptance overnight), 2026-10-11.

- In a figure's slice (between the halfway points to its neighbours' heads) the foreground above the
  bottom fifth of the sheet is split into connected parts by runs of pixels row by row, joined with a
  union-find (NumPy and plain Python, no new dependency; about 0.3 s for a 2048x1024 sheet). A part
  that reaches the slice's edge without being joined to the figure's head (the column of the top third
  where its head and neck are thickest) belongs to a neighbour: it is painted with the backdrop colour,
  grown by 3 pixels to take its soft edge, and the box is narrowed to what is left. A part inside the
  slice that the threshold cuts off from the head (a pale shirt between head and trousers) is the
  figure's own and stays (review). Below that line feet, shadows and the floor join every
  figure (on the real Ember sheet a floor shadow runs under all four horses), so there everything
  under the figure's own columns is kept and nothing is painted.
- Checked on the five sheets of *The Long Night*: the Ember side view and the other horses' views lose
  their neighbour's rump and tail, the people's views are unchanged but for narrower boxes.
- A neighbour's part that touches the figure itself above the floor cannot be told apart and stays.
- Existing packs are not cut again (open question 4): the Ember pack of *The Long Night* keeps its
  side view; the fix applies to new projects and new sheet takes.

## D-082: long face clips are made at the smaller size  (2026-10-11)

**Status:** accepted (owner delegated decisions overnight), 2026-10-11.

- On the 8 GB RTX 4060 Wan 2.2 ran out of memory three times on S003 of *The Long Night v2*, a face shot
  of 7786 ms (126 frames at 960x544), in its first sampler (`Allocation on device 0 would exceed allowed
  memory`), also with ComfyUI started fresh and with `--reserve-vram 3` (dynamic VRAM ignores it). The
  longest face clip of the first run, 110 frames at 960x544 (S049, 6760 ms), was made without trouble.
- So a face clip uses 960x544 only up to `FACE_MAX_FRAMES` = 110 frames; a longer one is made at 832x480
  (51.4 M pixel-frames at 129 frames, below the 57 M that worked). The finish upscales both to 1920x1080.
  Clips without faces are unchanged; so is every clip key of a face shot of at most 110 frames.
- The run-time estimate (`progress.clip_default`) still times every face shot at the larger size, a small
  overestimate for the few long ones; left as it is.
- Guarantee 9 changes to say so. The limit is for this card; a larger card could raise it (a setting
  later, if wanted).

## D-083: a failed stage made again shows running  (2026-10-11)

**Status:** accepted (owner delegated decisions overnight), 2026-10-11.

- hone-flow keeps a step's record of its failed attempt until the next attempt ends. After a resume the
  clips stage of *The Long Night v2* read `failed` while it made clip after clip, and the dashboard
  showed each shot being animated as "failed".
- `status` now shows a failed stage as `running` while the run is live, without the failed attempt's
  error, start and duration (the page then times it from the resume's `step_started`, review): the
  workflow is one line of stages and a failure ends the run, so in a live run a failed step is the one
  being made again.

## D-084: the pace is a preferred shot length, warned, never an error  (2026-10-11, 0009)

**Status:** accepted (asked for by the owner 2026-10-11).

- `pace` maps to a preferred shot length (`pace.SHOT_MS`): calm 6500 to 8000 ms, energetic 2000 to
  4500 ms, balanced none; the range is clamped into `min_shot_ms` .. `max_shot_ms`, so a project's own
  limits always win. The shot planner gets it as `pace_shot_ms` beside the settings, and the prompt
  says what each pace means (calm: few cuts inside a verse, cuts on line or section starts, a shot may
  carry two short lines).
- `check_shots` warns `pace` on a shot outside the range, never on the last shot (it ends where the
  song ends). A warning, not an error: a sung line can force a shorter shot, and an error would send
  the plan back to the planner for something the owner may accept.
- The pace and the mood go to the planners in `settings` (they are the project's options);
  `still_retries` joins the check's settings, which no planner sees.

## D-085: the story's world is written by the cast planner; the flag keeps its name  (2026-10-11, 0009)

**Status:** accepted (asked for by the owner 2026-10-11).

- `world` is a new optional field of `cast.json`, written in the same whole-song cast call as `anchor`
  (no extra call): the period and place, what belongs (materials, clothing, light sources,
  technology), what must not appear. The cast planner's prompt gives an ancient and a modern example and
  says both come from the story.
- The shot planner and both start-frame checks get it as data; an older cast reads `""` and they fall
  back to the anchor and the story (as the prompts say).
- The check's flag stays `anachronism` (stored check records and the Storyboard read that name); its
  meaning is widened to "out of the story's world". Renaming it would need a migration of every check
  record for no gain.

## D-086: Claude Haiku 5.5 is the new projects' judge, with a stricter prompt  (2026-10-11, 0015)

**Status:** accepted (asked for by the owner 2026-10-11).

- Registry entry `claude-haiku-5-5`: the Opus entry's gateway and key (OpenAI-compatible gateway, `OPENAI_COMPATIBLE_API_KEY`),
  vision, 1M input, `max_tokens` 32000 (a reply is a score, flags and at most two prompts per frame),
  600 s timeout, 0.10 / 0.50 USD per MTok (Anthropic's list price for prompts up to 100K tokens).
- It is the default `models.quality` of a new project. Settings stored before keep theirs (every
  project stores its whole `models`); stored settings with a `models` table but no `quality` read
  Opus.
- The judge's prompt lists what to check in every frame, in order (fixed traits, number of people,
  unwanted faces, hands and limbs, the story's world, the mood, the composition asked for, text and
  style), asks for the evidence in each flag's `reason`, and fixes the severity rule: major when the
  frame would mislead the viewer or contradict the cast or the story; a frame with a major flag scores
  at most 5. New flag kinds `off-mood` (never when the mood is empty) and `composition` (a wide shot
  drawn close, a silhouette lit from the front, a figure that should be turned away facing the camera:
  S007, S057 of the first run). Before, a composition other than asked was "not a flag".
- The same prompt serves the drafts' check (0015) and the final check; `drafts` in the data tells the
  judge a slightly glossy look before the polish is expected.

## D-087: the drafts are checked inside the stills stage, rounds recorded per first draft  (2026-10-11, 0015)

**Status:** accepted (asked for by the owner 2026-10-11).

- The check of the drafts runs inside stage 10, between the drafts and the polish, not as a new stage:
  the stage list, the gates and every step version stay, so a run made before forks nothing new, the
  redo guard and "assemble again" keep working, and the dashboard's stages are unchanged. Stage 11 still
  checks the polished frames (the picks, the motion-prompt rewrites and the gate are its own); with
  Haiku the second call costs under a cent.
- A frame is a take's first draft (for a shot without a cast, its still from text). A retry is the take
  with the corrected still prompt and the seed `seed_for(stage seed, shot, "still", still_seed,
  "retry", round)`; it is a kept version like any other (D-009).
- `current/checks/still-retries.json` holds every frame's rounds (prompt, file, score, flags, the
  corrected prompt) under its first draft's file. Rounds are written as soon as they are drawn and as
  soon as they are checked, so a resume goes on; a fork finds a frame's best round from it and makes
  nothing for a frame already checked (the redo guard does the same, `_remade`). Takes that share a
  first draft share its rounds.
- The best round is the highest score, the earliest on a tie (a reply that leaves a frame out scores
  it 0); it is polished with its own corrected prompt. The clip's motion prompt is the take's (or the
  rewrite of stage 11), unchanged.
- A corrected prompt is drawn only when it names exactly the original's `{id}` placeholders and is
  within 1500 characters; otherwise the frame is not drawn again and `still_retry_unfit` says so.
- A project stored without `still_retries` reads 0 and its drafts are not checked: its start frames keep
  their keys. `still_retries` above 0 needs `quality_check`; with the check off nothing is checked or
  drawn again (no error, as `rewrite_motion`).
- The costs count a span naming the `stills` stage as that stage's call; a `stills` attempt with no
  call is not an unknown call (most make none).

## D-088: a motion prompt never names the mouth  (2026-10-11)

**Status:** accepted (asked for by the owner 2026-10-11).

- In *The Long Night v2* S003's clip shows Celina talking, although its motion prompt said "keeps her
  lips closed … her breath trembling … She does not speak". Our Wan workflow
  (`data/workflows/wan2.2-i2v-14b.json`) runs the 4-step lightx2v LoRA at cfg 1 in both
  KSamplerAdvanced nodes: at cfg 1 the negative prompt has no effect, Wan does not follow negations,
  and naming the lips, mouth or breath draws the motion to the mouth.
- The rule, in `limits.md` (shot planner), `shots.md` and the judge's rewrite (`quality.md`): a motion
  prompt never names the mouth, lips, jaw, teeth, breath or breathing, speaking, singing, whispering,
  words or a voice, not even negated; a face that must not talk is described by what does move (the
  eyes, a tear, the gaze) and "her face stays still"; negations are useless, say what happens. 0014's
  advice "lips slightly apart at rest" and "breathing" as good motion are removed.
- `check_shots`' `speech` warning (0014) is extended rather than a new `mouth-words` rule: in a motion
  prompt it also warns on those words of the mouth (`shots_check.MOUTH`), negated or not, and says to
  show the face through what moves. A still prompt warns only on words of speech, as before (a still is
  drawn, not animated).
- A rewritten motion prompt (0014) that names speech or the mouth is dropped like one that is too long:
  the planned prompt stands for that start frame (`motion_rewrite_dropped`).
- cfg and the LoRA stay as they are. An open option for later: NAG (normalized attention guidance),
  which gives a negative prompt an effect at cfg 1 with distilled LoRAs; it would need a ComfyUI node
  and a test on the 8 GB card.

## D-089: what Haiku flagged on the first run's contact sheets  (2026-10-11, 0015)

**Status:** accepted (asked for by the owner 2026-10-11); a measurement.

- One real call: `claude-haiku-5-5` through the OpenAI-compatible gateway with the new judge's prompt, on the five contact
  sheets of *The Long Night v2*'s check (59 frames, read-only), its cast without `world` (made before
  0009), no mood. The gateway accepted the model with images. 41 s, 0.0079 USD (Opus: 538 s, about 0.20 USD).
- Opus's major flags: S003 (hurricane lamp), S033 (extra people), S034 (wrong character, twice), S040
  (unwanted face), S047 (hurricane lantern), S052 (a steel chain), S054 (an extra man, a lantern).
- Haiku's major flags: S033 (extra robed figures), S040 (Loren's face in an arm insert), S054 (a
  second, bearded person beside her); minor: S029 (a face in profile), S055 (no chainmail visible).
  It missed S034's wrong characters and every object out of the period (S003, S047, S052, S054's
  lantern).
- So Haiku finds extra people and unwanted faces as Opus does, at 4 % of the cost and 8 % of the time,
  but misses wrong characters and out-of-world objects, the flags 0015 most needs to heal. A cast with
  `world` (new projects) names what must not appear, which should help the second; it was not measured.
  A project can set `models.quality` to `claude-opus-5-5` (about 0.2 USD a check, plus the drafts'
  rounds). Kept the owner's choice as the default; the comparison goes to the owner.

## D-096: the New video form's pace, mood, style presets and retries  (2026-10-11, 0016)

**Status:** accepted (asked for by the owner 2026-10-11).

- Pace is three radio cards (calm, balanced, energetic) with one line each; the choices come from
  `GET /api/settings`' `paces` (a list of names; the page holds what each means) when the server sends
  it, else these three.
- Mood is one text field with `dir="auto"` and `unicode-bidi: plaintext` (right-to-left scripts read right to left);
  ten chips add their word at the end or take it out (commas, Arabic-script ones too, separate the words; a
  chip is pressed while the mood holds its word). "dreadful (دلهره‌آور)" adds "dreadful".
- Style presets fill the style text with a concrete look that names no era, and stay editable; the
  pressed preset is the one the text still equals. The lyrics, story and style fields read `dir="auto"`
  too.
- Start-frame retries is a 0 to 5 choice (default 2, or the server's default); it is not part of the
  extra takes' estimate.
- "What will be sent" shows the settings as JSON, rebuilt on every input.

## D-097: the bell rings once per wait, after two polls  (2026-10-11, 0016)

**Status:** accepted (asked for by the owner 2026-10-11).

- `bell.js` asks `GET /api/projects` every 4 s; a wait is the pair project and gate (`waiting`, or
  "review" for an `awaiting_review` status without one). An unattended run passes its gates within the
  same process step, so a wait rings only once two polls in a row see it; it rings once, and is
  forgotten when it ends, so the next gate rings. The waits rung are kept in `localStorage`
  (`bell.rung`, every access in try/catch): reopening the page does not ring again.
- `chime.js` makes the sound with the Web Audio API: a two-note bell (A5 then F5, four sine partials
  each, fading over about 1.8 s) every 2.5 s from 0 to 15 s, so it lasts about 17 s. Stop disconnects it
  and closes the banner; a project that stops waiting leaves the banner, and the sound stops with the
  last one.
- Autoplay: no AudioContext exists until a click. **Enable sound** creates and resumes it inside the
  click and remembers the choice (`bell.enabled`); on a later visit the first click or key anywhere on
  the page resumes it. Until then the banner says the sound is locked, with the button. The header's
  bell button mutes (`bell.muted`); unmuting is a click, so it unlocks too. A later visit keeps trying on
  each click or key until the context runs (a touch or Escape may not count as a gesture).

## D-098: "Retry this frame" and the automatic retries on the Storyboard  (2026-10-11, 0016)

**Status:** accepted (asked for by the owner 2026-10-11).

- A start frame the check flagged (`stills_check.flagged`) is outlined, keeps its flags list, and has a
  primary **Retry this frame** while the shot can be redone: the existing redo with `still: true`
  (design §11.2), so nothing new on the server.
- The automatic retries come from `still_retry` events; a round 1 starts a new series (a redo of the
  shot, or a resumed run, makes the retries anew; the events carry no run), the last event of each round
  counts, in round order, for the take in the video (`take`, from 1), as "retry {round} of
  {still_retries}: {flag kinds} → redrawn"; flags may be kinds or flag objects. The project view keeps these events apart from the 400
  latest it holds, so a long run never drops them, and redraws when one arrives.

## D-099: the page's logic is tested in Node  (2026-10-11, 0016)

**Status:** accepted (asked for by the owner 2026-10-11).

- The page modules touch the DOM only when called, so `tests/unit/test_dashboard_page.py` imports them
  in `node --input-type=module` and checks pure functions (`nextWaits`, `waitsOf`, `toggleWord`,
  `paceChoices`, `readSettings` over a stand-in form, `retryNotes`). No browser and no npm package;
  skipped with a reason where Node is missing (GitHub's Ubuntu runners have it).

## D-100: a prop's fixed look, apart from its note  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- A prop gains `look`: the object alone in one phrase (shape, material, colour, how many of each part,
  size against a hand or a body), written by the cast planner. It is what a `{prop-id}` becomes, word for
  word, and what its sheet is drawn from. `note` keeps where it is worn, who has it and what happens to
  it: *The Long Night v2*'s armour note ("after his death it is torn open") would draw a torn shirt on
  every sheet.
- A prop gets a sheet only when it has a look (or a given sheet, D-103): a cast made before 0017 has
  none, so it draws nothing new (D-108).
- A prop's id is a placeholder like a character's: `cast_problems` asks it to be unique among both, and a
  prop with a pack to be a plain lowercase name (it names its folder). An older prop keeps any id.

## D-101: the prop sheet prompt is the library's  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- The library builds the prop sheet prompt (`stages_props.PROP_PROMPT`): the object twice on one wide
  studio photograph (whole on the left, a close-up of its most telling detail on the right), the look,
  the story's `anchor` (else `world`), a plain light-grey backdrop, no people, no hands, no text. The
  cast planner writes only the look: one tested template, and no sheet prompt per prop to go wrong.
- Drawn by the `sheets` model (Z-Image) at 2048x1024, in the same model session as the characters'
  sheets; a retake's note is added to the props' prompts too, with new seeds.
- The template is untested on the GPU (no GPU in this change); the first real run checks it by eye.

## D-102: prop takes are picked at the same gate  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- `Sheets` gains `props: [SheetTakes]` (the row's `character` field holds the prop id, so the record
  shape, the pick and the dashboard's take rows are shared). `prop_sheet_takes` (default 4, like
  `sheet_takes`) sets the takes per prop; stored settings without it read 4, harmless since an older
  cast draws no prop.
- `pick` takes prop ids as it takes character ids; `pick_sheets` passes on its own only when no
  character and no prop was drawn (the note now says "no character or prop has a sheet to draw"); an unattended project uses the first take, as for characters.
- The cut preview of a prop take is the object crop's (D-104).

## D-103: a given prop sheet comes through `--sheet`  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- No new flag: a picture given with `--sheet name=file` reaches the cast planner with the others, and
  the planner sets a prop's `source` to `"given:<name>"` when it shows that object. A prop gains
  `source` (default `"make"`), checked like a character's. A given prop sheet is never redrawn; it is
  cut by the object crop.

## D-104: a prop pack is cut by the object crop  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- `split_objects` in the cutter: the foreground's column runs over the whole height (an object has no
  head in the top third to find: a dagger lies across the middle), each cropped to its box with the
  figure margin on every side (its slice reaches halfway to the next object, as a figure's does;
  review). The first object is `main.png`, a second `detail.png`; a picture with no separate
  object is `main.png` whole. More than two objects: the first two.
- Files in `current/props/<id>/` (`main.png`, `detail.png`, `sheet.png`, `takes/`), apart from the
  characters' `packs/`; `Packs` gains `props: [{prop, main, detail, sheet}]`. No portrait, no model call.

## D-105: shots list their props; `{prop-id}` is the look word for word  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- A shot gains `props: [ids]`. For the image model `{prop-id}` becomes the look followed by its
  pictures' numbers, "(image 2)" or "(images 2 and 3)"; without a picture the look alone; for the polish
  pass and the check the look alone. An older cast's prop becomes its note.
- `check_shots`: `unknown-prop` for an id not in the cast's props, `placeholder` for a `{prop-id}` the
  shot does not list. A redo's prompt may name the shot's props.
- A shot without a cast that shows a prop with a pack is drawn by the start-frame model from the prop's
  pictures and polished (S007 of *The Long Night v2*, an insert of the armband alone); without one it
  stays the text model's. The text model's prompt is expanded only when it has a placeholder, so no
  older still prompt changes.

## D-106: the reference budget  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- Still at most three pictures a start frame (the model's slots, §8.2).
- A **prop shot** is an `insert`, or a `close-up` or `extreme-close-up` without faces, that shows a
  prop: each prop's main view first, then the characters' views by §10.1, then the props' detail views.
- **Any other shot**: the characters' round robin (§10.1) is split after its first round, each
  character's first view (the portrait in a face shot); then each prop's main view; then the rest of the
  characters' views; then the props' detail views. So in a face shot every portrait keeps its slot and
  a prop gets one only when one is free after them: a one-person close-up gets portrait, prop, front
  view; a two-person face shot both portraits and the prop; three people, no prop.
- A prop without a pack takes no slot; a shot's own `refs` may name `prop-id/main` or `/detail` and
  override the rule. A shot without props gets exactly the pictures it got before (tested).

## D-107: the check flags `wrong-prop`  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- Both checks (the drafts' and the start frames') get the cast's props with their looks, each prop's
  main view among the pictures, and per frame its shot's `props`. The prompt adds a step: compare each
  listed prop with its look and picture; `wrong-prop` `major` for another shape, count or colour (three
  emeralds for one ruby), `minor` for size or a detail. A major one counts like any other: the drafts
  are drawn again (`still_retries`), the gate waits when asked.

## D-108: older projects draw as before  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- Every new field is optional (`look` `""`, `source` `"make"`, a shot's `props` `[]`, `Sheets.props`
  and `Packs.props` `[]`). An older cast has no look: no prop sheet, pack or picture; no older start
  frame changes its key. Step versions stay, as in 0014 (D-080): a version change would make "assemble
  again" refuse every older run.
- An older project gets prop sheets only from a new run (a new cast plan); a re-plan keeps its cast.
- One predicate says whether a shot is drawn from pictures (`prompt_assembly.from_pictures`: a cast, or
  a prop with a pack); the progress read from folders (older runs, D-053) asks the same of the cast's
  props. The best-of estimate, which sees only the shot plan, counts any shot with props as drawn from
  pictures: an overestimate of a few seconds for a prop without a pack.
- The prompt functions take the props as a required argument (`NO_PROPS` for none), so no caller can
  leave them out silently: a re-plan on a project with an older `face_refs` writes the changed shots'
  `refs` by the budget, the prop's picture among them (review).

## D-109: the props in the Cast view  (2026-10-11, 0017)

**Status:** accepted (asked for by the owner 2026-10-11).

- The Cast view's props panel becomes a card per prop, after the characters: its name, look, note and
  who carries it, where its sheet comes from, its takes with their cut previews (radio buttons at
  `pick_sheets`, the same pick as the characters') and its main and detail views once cut. The project
  record gains `prop_packs` (from `current/props/`), and `sheets` lists the props' rows after the
  characters'.

## D-110: Claude Sonnet 5.5 is the new projects' judge  (2026-10-11)

**Status:** accepted (the owner's choice), 2026-10-11.

- A bake-off on *The Long Night v2*'s five contact sheets (59 frames) with the 0015 judge prompt:
  Sonnet 5.5 flagged every major problem Opus 5.5 had (S034's mixed-up characters, the lamps in S003 and
  S047, S052's chain under `composition`, the extra people in S033 and S054, S040's face) in 110 s for
  about 0.23 USD; Haiku 5.5 missed S034, S003, S047 and S052, and with a `world` text still missed S034
  and S052 and lost its extra-people flags (run to run it varies).
- So `models.quality` defaults to `claude-sonnet-5-5`; Haiku stays in the registry. Retry rounds check
  only the flagged frames, so a video's judge costs about 0.25 to 0.35 USD. Stored settings keep their
  model.

## D-111: one set of gate controls, and a note is never lost  (2026-10-11, 0018)

**Status:** accepted (asked for by the owner 2026-10-11).

- The bug: on *isolde-the-forgotten-wife-2* the owner typed "timing is not accurate" into the collapsed
  "Run the lyrics again with a note" box and pressed the big Approve above it; the dashboard's Approve
  sent `{gate}` only, so the gate was approved with an empty note and no reject was ever sent.
- Every gate a page decides uses `dashboard_page/decide.js` (`gateControls`), on the gate's own view and
  on the Overview's card alike: a note box always visible, Approve and the gate's reject button side by
  side, and one line saying what rejecting does (D-112). The reject button is disabled while the note is
  empty (except new sheet takes, which need none). Approve with text in the box opens a `<dialog>`: "You
  wrote a note. Reject with it instead?" with Reject, Approve anyway, Cancel. Approve anyway sends no
  note and clears the box: a note written for a reject is not an approval's note.
- The note is kept per project and gate in memory and in `localStorage` (`note:<project>:<gate>`, every
  access in try/catch) from each keystroke until a decision is sent; a redraw (every server-sent event)
  builds the box again with it and gives back the focus and the caret when the owner was typing there.
- The API's `approve` now passes the note it is sent to `runs.approve` (before, only the CLI could).
- `approveButton` and `rerunBox` in `parts.js` go; `gateBar` draws the controls, and `actionButton`
  posts through the controls' `send`. The Shots view's
  "Approve with N errors" (D-027) is the Approve of its controls, still behind its confirmation.

## D-112: what reject does at each gate  (2026-10-11, 0018)

**Status:** accepted (asked for by the owner 2026-10-11).

- `review_lyrics`: the lyrics editor runs again with the note (words, lines, sections); it never moves a
  time, so the help text points at the timing editor. `review_cast`: the cast is planned again in one
  call. `review_shots`: every shot is planned again in one call with the rejected plan. `pick_sheets`:
  "New takes with note" (`retake`, D-024), the note optional; Approve there is "Use these takes" (`pick`)
  on the Cast view and approves the takes on offer from the Overview. `review_stills`: no reject (its
  stage would only check again); the controls show Approve with "This gate takes no note: retry a frame
  on its card", as the Storyboard already offers.

## D-113: the owner's timing is a gate decision with an edited output  (2026-10-11, 0018)

**Status:** accepted (asked for by the owner 2026-10-11).

- **Question:** where the owner's line times live before and after the gate, so that every later stage
  uses them as they are, and older runs and forks are untouched.
- **Choice:** while `review_lyrics` waits, `runs.lyrics_timing` (API `POST
  /api/projects/<id>/lyrics-timing`, CLI `lyrics-timing`) saves the edits by line id in
  `current/lyrics/owner-timing.json` (`OwnerTiming`: `edits`, `saved_at`, `timeline`) and the edited
  timeline as a kept version `current/lyrics/timeline-<sha256[:12]>.json`, never overwritten (D-009). The
  edits are applied to whatever the lyrics stage made last, on every read: the Lyrics view, the check,
  `approve`. `Timeline.owner_timed` lists the owner's lines. `approve` at `review_lyrics` with edits
  that apply decides the gate with hone-flow's `edit` (the gate's output becomes the edited timeline,
  label `edited`, as `pick` does at `pick_sheets`), so `plan_cast`, `plan_shots`, `check_shots` and,
  through the shots, the assembly read the owner's times; `current/timeline.json` is written from it.
  The `gate_approved` event gains `timing_kept` and `timing_dropped`. Once the gate is decided the
  record is marked `decided` and kept as the gate's record; it is never applied again (review).
- hone-flow's `edit` keeps no note, so `approve` with a note and saved edits is refused
  (`InvalidInput`) rather than dropping the note silently.
- Rejected: a new owner-edit step in the workflow (a new shape: every older run would have to be
  forked to resume, 0006); keeping the edits inside the run folder (hone-flow owns it).

## D-114: checking and applying the owner's times  (2026-10-11, 0018)

**Status:** accepted (asked for by the owner 2026-10-11).

- An edit is `{start_ms, end_ms}`, strict whole milliseconds from 0 (a float, a string, a bool or a
  negative is refused), on a line that exists, with `start_ms < end_ms <= duration_ms`. After applying,
  neighbours must not overlap where one of them was edited. A save is refused whole, every problem named
  (`InvalidInput.problems`, HTTP 400), and writes nothing. `null` takes a line's edit back.
- A line's words move with it: each time is moved from the line's start and scaled by the new length
  over the old (from the lyrics stage's line, never compounding), rounded, kept inside the line, each
  word at least 1 ms long and in order.
- A section holding an edited line spans its lines again (first start to last end). An instrumental span
  next to an edited line fills the new gap: its start becomes the edited line before it's end, its end
  the edited line after it's start; a span with no gap left is left out. Spans and sections away from
  edited lines stay as made.

## D-115: an owner-timed line is not held to its words  (2026-10-11, 0018)

**Status:** accepted (asked for by the owner 2026-10-11).

- `check_lyrics` skips `moved` and `not-heard` for the lines in `owner_timed`: the owner moved them on
  purpose, often because the words are what is off. Every other rule applies to them (inside the song,
  order, overlaps, words inside the line, sections, instrumental spans). The check runs again on every
  save, and its report is what the view shows and what `approve` goes by while the gate waits; after the
  gate, the dashboard checks the approved timeline again when it has owner-timed lines.

## D-116: running the lyrics again after timing edits  (2026-10-11, 0018)

**Status:** accepted (asked for by the owner 2026-10-11).

- A reject at `review_lyrics` with saved edits adds to the note sent to the editor: "(The owner set the
  times of L001, L003 by hand; they are kept where these line ids remain. Change the text only: keep
  every line, its order and its heard words.)" The editor never wrote times anyway (D-016); this asks
  it not to re-cut the lines the owner timed. The API's reject answer adds `timing_kept_for`.
- After the rerun the saved edits apply again by line id. An edit whose line is gone, or that would now
  have no length, fall outside the song or overlap a neighbour, is dropped with why; the others stay.
  The records (`lyrics_timing`: `kept`, `dropped`), the next save's answer, `approve` and its event say
  which. A save after a rerun keeps only the edits that still apply.

## D-117: the timing in the API and the CLI  (2026-10-11, 0018)

**Status:** accepted (asked for by the owner 2026-10-11).

- `POST /api/projects/<id>/lyrics-timing` takes `{line_id: {start_ms, end_ms} | null}` and answers
  `timeline`, `lyrics_check` and `lyrics_timing` (`kept`, `dropped`, `measured`: the kept lines' times as
  the lyrics stage made them, `errors`, `warnings`); the run is not
  resumed. A decided gate is a 409, as any decision at a gate not waiting.
- `hone-music-video lyrics-timing <project> L012=77300-81200 L013=-` saves the same way, prints the
  check's findings and the dropped edits, and exits 1 when the check finds errors. Each save writes a
  `lyrics_timed` event (`lines`, `dropped`), so the dashboard follows it live.
- Python: `hmv.lyrics_timing(project, {"L012": {"start_ms": 77300, "end_ms": 81200}})` returns the
  `hmv.Reviewed`: the timeline, its check, the edits kept and dropped, and the kept lines' measured times.

## D-118: older runs and forks  (2026-10-11, 0018)

**Status:** accepted (asked for by the owner 2026-10-11).

- No `owner-timing.json`: every read, check and approval is as before. `Timeline.owner_timed` defaults to
  `[]`, so every stored timeline loads; no step version changes. A fork (a redo, assembling again, a run
  forked for a new version) reuses the decided gate's output, edited or not. The edits apply by line id
  to the lyrics stage's last output, so a run forked while the gate waits keeps them.

## D-119: the Lyrics view's timing editor  (2026-10-11, 0018)

**Status:** accepted (asked for by the owner 2026-10-11).

- Every line shows its start and end. While `review_lyrics` waits, a clock button beside a line opens
  its timing: Start and End, each with −500, −100, +100, +500 ms and "Set start here" / "Set end here"
  (the song's play position, rounded to the millisecond, kept inside the song; a change that would leave
  no length is refused with a toast), "Play the line" and "Back to the measured times".
- Changes are a draft per project in memory (they survive redraws, not a reload), shown at once on the
  line, its play slice and the song panel, marked "changed"; a bar says how many lines changed, with
  Discard and **Save timing**. Saved lines are marked "your timing"; edits dropped after a rerun are
  listed with why above the song. The words' own times are the server's (D-114) and show after the save.
  "Back to the measured times" on a saved line shows the measured times at once (from `measured`) and
  sends `null` on save. Approve with unsaved times asks first ("L002: new times not saved. Approve
  without them?"), on the Lyrics view and the Overview alike (review: the same silent loss as the note).

## D-120: one judge call per round over every new sheet take  (2026-10-11, 0019)

**Status:** accepted (asked for by the owner 2026-10-11).

- Stage 6 calls `models.quality` once over every new take of the characters and props, never once per
  take (design §7): the judge compares a character's takes and scores the best highest. Each take goes
  as one JPEG 1536 px wide with its label above it (`_contact_sheet.labelled`): a 2048 x 1024 PNG is
  several MB, and a 4 x 3 contact sheet would shrink four figures past reading a snake's head. At most
  60 takes a call (each is one picture); more is refused with what to lower.
- The data per take: the subject (a character's `id`, `name`, `kind`, `noun`, `cue`, `traits`; a prop's
  `look`), the figures and views asked for, the prompt it was drawn from, and, as 0015, `fix`, `round`
  and `earlier_flags`. The prompt is its own file, `sheets_check.md`: a fixed list (the number of
  figures, the views, each fixed trait in every view, the backdrop and anything extra), evidence per
  flag, one severity rule (major: a pack cut from it would be wrong).
- It runs whenever `quality_check` is on, so a project with `sheet_retries` 0 still gets scores and
  flags; a project made before 0006 (`quality_check` false) is never judged.

## D-121: sheet takes that heal themselves  (2026-10-11, 0019)

**Status:** accepted (asked for by the owner 2026-10-11).

- As 0015 for the start frames: a take with a major flag and a corrected prompt is drawn again (same
  model, size and folder, the judge's prompt, the seed `seed_for(take seed, "retry", round)`), judged
  again with the takes still flagged, up to `sheet_retries` rounds (0 to 5, default 2; stored settings
  without it read 0). The round with the highest score is offered, the earliest on a tie.
- `current/checks/sheet-retries.json` keeps every take's rounds under its first file, written as soon as
  a round is drawn and as soon as it is judged: a stage run again (a resume) draws a round recorded but
  not drawn and judges only what was never judged. A corrected prompt that is missing or over 2500
  characters is not drawn (`sheet_retry_unfit`); the planner's sheet prompts run about 1800.
- The rounds are counted as `sheet_take` units; `sheet_retry` and `sheets_checked` events are written.
  The judge's spans count in the `sheets` stage's cost, as the drafts' checks count in `stills` (§13.5).

## D-122: the judge's verdicts on the Sheets record and in the Cast view  (2026-10-11, 0019)

**Status:** accepted (asked for by the owner 2026-10-11).

- `SheetTakes.checks` lists each take's `SheetCheck` (its rounds, the round offered, the retry limit)
  in the order of `takes`, `null` for a take the judge never saw (an earlier take of an older run, the
  check off). `takes` holds the offered round's file, so the preview, the pick and the cut need no
  change. The types live in `records_sheets.py` (records.py was at its size limit).
- The Cast view shows under each take its score and figures, its flags (major first) and one line per
  retry ("retry 1 of 2: 5 figures → redrawn"); a take still flagged is outlined and says so.

## D-123: the take offered first is the judge's best  (2026-10-11, 0019)

**Status:** accepted (asked for by the owner 2026-10-11).

- `picked` (the take offered first, the one an unattended run uses) is the best-scoring new take that
  the judge did not miscount, the earliest on a tie; the first new take when none was judged (as
  before). The owner still picks at `pick_sheets`.

## D-124: a miscounted take is refused, the cutter stays  (2026-10-11, 0019)

**Status:** accepted (asked for by the owner 2026-10-11).

- The simplest safe way: the judge's count decides, at the points where a take is chosen. `pick`
  refuses a character's take counted with other than four figures (with the flag's evidence), approving
  `pick_sheets` with one is refused, and an unattended run stops at `pick_sheets` (`auto_stopped`). A
  take never judged is not refused (an older run, the check off).
- Not the cutter's own count: on fake and given sheets it finds no figures or too few when figures
  touch, and a refusal there would come after the gate, with no way back but a new run.
- A prop's objects are not views (a picture with one object is the main view whole, D-104): its count
  is flagged and retried, never refused.

## D-125: an unusual character gets at least four takes  (2026-10-11, 0019)

**Status:** accepted (asked for by the owner 2026-10-11).

- `Character.unusual` (default false; older casts read false) is set by the cast planner for a look
  that is hard to draw the same in four views: non-human anatomy, creatures, attached animals, extra
  limbs or heads, masks. Such a character gets `max(sheet_takes, 4)` takes.

## D-126: older projects  (2026-10-11, 0019)

**Status:** accepted (asked for by the owner 2026-10-11).

- Every new field is optional (`sheet_retries` 0 when stored without it, `unusual` false, `checks` `[]`),
  no step version changes, and a run whose `sheets` stage is done is not judged again. An older
  project's retake is judged (when `quality_check` is on) and drawn again never.

## D-127: the judge on Morvane's takes  (2026-10-11, 0019)

**Status:** accepted (a measurement), 2026-10-11.

- One real call (Claude Sonnet 5.5 on the OpenAI-compatible gateway) on *Isolde the forgotten wife 2*'s two Morvane takes:
  28.7 s, 0.051 USD. Take 1: 3 figures (front, side, back), score 3, major `figure-count` (the
  three-quarter view missing), `wrong-trait` (one snake, behind the left shoulder) and
  `inconsistent-views` (no snake in the side view). Take 2: 5 figures (front, side right, side left,
  back, front again), score 4, major `figure-count`, `inconsistent-views` and `wrong-trait` (the snakes
  draped over the shoulders in three figures, one rising in two). Both corrected prompts (about 2100
  characters) ask for exactly four figures and two separate snakes, one rising from the top of each
  shoulder, visible in every view. Each trait (crown, hair, beard, costume) was listed and found the
  same in every view. Not yet drawn on the GPU.

## D-128: default models that cannot do their job are refused  (2026-10-11, 0020)

**Status:** accepted (record 0020 §7); the details below are mine, awaiting owner review.

- `models.views` is new and, for a project stored before 0020, is the project's `stills` model
  (`settings.stored`), so an older project's keys and files do not change. `models.sheets` may be a
  text-only model (a first picture is drawn from text); `models.views` and `models.stills` must take
  reference pictures. `image_menu.check_defaults` refuses a default that is not an image model or takes no
  references, with the role and model in the message, before `new` and `POST /api/projects` make anything.
- Naming: the record's `image_models.py` is `image_menu.py`, because `image_models` is also the public
  function of `scene_menu.py` and a module and its function of one name shadow each other in the package.

## D-129: who may draw what  (2026-10-11, 0020)

**Status:** accepted in the record (§1); the rule below is mine, awaiting owner review.

- A picture with reference pictures needs a model with `capabilities.max_references > 0`; a picture with
  none (a character's or prop's first picture) may be drawn by a text-only model or any hosted one (hosted
  entries call `/images/generations`). The menu lists, local models first, then hosted ones by price, each
  with `where`, its reference limit and an estimate; a hosted entry that no real call has proved stays
  `disabled` in `data/models.toml`, so it is not on the menu. A take records the model that drew it
  (`Take.model`, `None` for the project's) and whether it was generated or uploaded.

## D-130: Gemini pictures through an in-library client  (2026-10-11, 0020)

**Status:** accepted in the record (§1: temporary, like D-002); details mine.

- `adapters/hosted_gemini_image.py` calls the two Gemini image models on the gateway's chat endpoint
  (`modalities`, `imageConfig.aspectRatio`, the picture as a data URL in the reply), because hone-models'
  media client cannot. It refuses more references than `max_references`, never writes the key anywhere,
  and returns the recorded request (references by name, bytes and sha256), the reply's id and usage, and
  the price (`price.per_image`) as `Generated.call`; the version's `Made.call` keeps it so the costs find it.
  It is removed when hone-models can make the call.

## D-131: an uploaded picture  (2026-10-11, 0020)

**Status:** accepted in the record (§1); details mine.

- The bytes decide the type (PNG, JPEG or WebP; at most 25 MB), never the name; a picture smaller than the
  one asked for is refused with both sizes. It is kept as `current/uploads/<sha256><ext>`, cut to the frame's
  size by a centred cover crop (the crop is recorded in the version's inputs), then polished by the local
  polish model like a generated one. An uploaded take is never checked, never drawn again and never shown to
  the start-frame check. The dashboard decodes an upload into a throw-away folder under the project with a
  name made safe; nothing of the sender's name is used on disk.

## D-132: a redo with a model or an upload  (2026-10-11, 0020)

**Status:** accepted in the record (§2); details mine.

- `Redo.model` / `Redo.upload` (a model or an upload, never both) make a new take: it records the model or
  the upload's sha256 and its note ("new still, model X" / "new still, uploaded picture"). The model must be
  on the shot's menu (`scene_menu.require`), or the redo is refused naming `image-models PROJECT --for scene
  S001`. A new still after an upload is drawn by the project's model again. The reference slots a hosted
  model gets are its own `max_references` (`prompt_assembly.references(..., slots=...)`); three for any other.
- CLI `redo --model ID | --upload FILE`; dashboard `POST /redo {shot, model}` or `{shot, upload}`.

## D-133: the menu's estimates  (2026-10-11, 0020)

**Status:** mine, awaiting owner review.

- A hosted picture's estimate is `price.per_image` plus a fixed `REFERENCE_USD` per reference picture for the
  two Qwen models that bill them (0.003 each); the other entries bill the picture only. A local scene's
  time on the menu is the draft plus the still time (`DEFAULT_MS` unless the project's records have
  measured them). A new video's estimate counts only the scenes (a hosted `models.stills`): a shot every
  5.2 s of the song (a shot's mean length, D-069), times the takes a shot gets (the larger of `still_takes`
  and `pick_best_of`), with three typical references; the first pictures' and views' are added with the
  packs (milestone 2). The text always says "about", names the model and says how many pictures. The New
  video form's `/api/estimate` adds it to the extra-takes warning.

## D-134: what hosted pictures cost, counted  (2026-10-11, 0020)

**Status:** mine, awaiting owner review.

- A hosted picture's price is counted from the place it was recorded: hone-models' `hone.models.image`
  spans (by run and stage, like the planners' calls), or a version's `Made.call` (the Gemini client), by
  the stage in `Made.stage` and the time. The price is the registry's per picture, so a call is counted at
  least. A pictures redo's dry run and guard show `hosted_usd`, without the pictures that the start-frame
  check might draw again.

## D-135: separate pictures as the packs, reviewed at `review_packs`  (2026-10-11, 0020)

**Status:** mine, awaiting owner review.

- `Settings.packs` is `"views"` for new projects and `"sheet"` for stored settings without it (`BEFORE_0020`
  in `stored()`), so an older project draws and cuts four-figure sheets as before. A project of `"views"`
  has stage 6 draw one picture per character (its front; an animal's side) and per prop, stage 7 draw the
  other views, the portrait and the details from the accepted first picture, and a new gate `review_packs`
  after stage 7. `pick_sheets` and `review_packs` always wait in such a project, unattended too
  (`_auto_approve.must_wait`); in a `"sheet"` project `review_packs` passes on its own.
- A redo of one picture is a rejection of the waiting gate whose note carries the request
  (`_pictures.encode`: subject, view, note, model, an upload's sha). The stage runs again and every picture
  already drawn is found (D-009); only the one asked for gets a new take, in use. A picture's seed is
  `seed_for(0, picture, n)`, not the stage's, because hone-flow gives a rejected step a new seed and every
  other picture would otherwise get new version keys and be drawn again.
- The sheet judge's rounds are reused for pictures: a picture is a `SheetTakes` row with one figure
  expected (`SheetCheck.expected`), kept as `Packs.pictures`, keyed `"<subject>/<view>"`.
- A close-up (a character's detail) named in a shot's `refs` is the first reference and is not counted
  among the character's own pictures when the prompt names "the man from images ...".

## D-136: the views are drawn without the multiple-angles LoRA  (2026-10-11, 0020)

**Status:** mine, awaiting owner review.

- Measured with `scripts/compare_views_lora.py` under the GPU lock: a front drawn by Z-Image, then the side
  and back views by Qwen Image Edit with the workflow's LoRA at strength 0 and at 1, for Morvane and
  Isolde. The two were practically the same; the LoRA's back view of Morvane merged his two snakes into
  one arc. So the views use plain Qwen (the workflow's own strength 0) and no `lora_strength` input is
  passed. The comparison pictures are in `.hone/test-media/views-lora/` (not committed).

## D-137: stop after the scenes  (2026-10-11, 0020)

**Status:** mine, awaiting owner review.

- `quality_gate: "always"` makes `review_stills` wait once every scene is drawn and checked, flagged or
  not (`off` and `ask` as before, D-067). `new --stop-after-scenes` and the New video form set it. An
  unattended project (`approve: "auto"`) passes the gate on its own like any other gate there (D-075): the
  automatic run wins, and the form says so. A scene changed at the gate is a fork's new take, in use, so
  its clip is made from it once the gate is approved.
- Not changed: the retries (0015, 0019) stop at their limit, and a round drawn but not judged when a run
  stopped is judged on resume with nothing drawn after it. `tests/e2e/test_ac28_retries.py` pins both for
  sheets, pictures and start frames (the Isolde run's last picture had only been left unjudged).

## D-138: the scene queue  (2026-10-11, 0020)

**Status:** mine, awaiting owner review.

- **The files and who writes them.** A redo or an upload sent to a running project is checked at once
  (`runs_queue.queue_redos`: the scene exists, its model is on the menu, the file's type and size) and added
  to `current/scene-queue.json` (`scene_queue.add`), an upload as the sha256 of the file `uploads.receive`
  kept. The HTTP threads and the CLI only add (and `remove`, `discard`); the runner thread alone takes
  (`scene_queue.take`) and writes `current/live-takes.json`, the scenes' new takes and the ids of the entries
  taken. Both files are written to a temporary name and renamed into place, under one exclusive
  `fcntl.flock` on `current/scene-queue.lock`; the lock is never held while a model is called. A later
  request for a scene replaces its earlier one in the queue (the earlier stays a take to go back to).
  `take` records an entry in `live-takes.json` before it leaves the queue, so a crash between the two takes
  it out again without applying it twice.
- **Stage 10 absorbs the queue** (`Scenes.absorb`) between two files, as `make_all`'s `between` hook, and
  once before the polish pass. It only works out the new take (nothing is drawn there): the draft jobs of the
  new takes come back and `make_all` draws them in the same stage, the counts and the takes in use follow.
  A scene without a cast is drawn from text and made with the polish pass at the end, so a changed scene of
  a text-only scene is made with the final stills, not between two files. Stages 10, 12 and 13 read
  `live-takes.json` after the run's `takes` param, so the clip is made from the new picture without a fork.
- **After stage 10, one fork.** A request that arrives once stage 10 is done waits in the queue. Once the run
  stops (it ends, or waits at a gate) `apply_queue` makes everything queued as one fork (0008, D-070): the
  redo guard (D-071) runs first (`preview_queue`, `apply-queue --dry-run`) and refuses it, naming the
  scenes, if another scene would be made again. `stopped_plan` is the plan it starts from: the run's
  `takes` param with `live-takes.json` over it, only while the run is not running. The dashboard's runner
  applies it at the end of a job, once, when the run has stopped (`Runner._apply_waiting`); a refusal is a
  `queue_refused` event and the queue stays, and a failed `apply-queue` job is not tried again at once.
- **`remake` clears the files when the fork starts**, not before, so a refused or failed start loses
  nothing: `live-takes.json` is emptied (the fork's `takes` param holds those takes now) and the entries
  the fork applied leave the queue. A fork of a redo (not of the queue) empties the live takes in the same
  way. `hmv.redo` on a running project queues instead of refusing; `hmv.use` still waits for the stop.

## D-139: 0021's pack references only in a "one-body" project  (2026-10-11, 0021)

**Status:** mine, awaiting owner review.

A carrier's props in its first picture, the details in the side and back, and the props drawn as their own
batch before the characters are on only when `face_refs` is `"one-body"` (`settings.one_body`). A project
stored before 0021 keeps `"by-shot"` or older, so its pictures keep their references, their keys (D-009) and
the judge's one call for stage 6: a resume or a fork redraws nothing it has. One setting rather than a
second one: `"one-body"` is what makes the extra references safe in scenes, and a project gets both or
neither.

## D-140: Qwen-Image-2.1 Turbo draws from text too  (2026-10-11, 0021)

**Status:** mine, awaiting owner review.

`image_menu.can_draw` lets a local model that takes references draw a picture without any only when its id
is in `FROM_TEXT_TOO` (`qwen-image-2.1-turbo`): hone-models drops its empty reference slots with their links
and the graph still runs (0, 3, 4, 6 and 10 references drawn on the GPU). Qwen-Image-Edit 2511 stays
references-only (D-129). A list of one id, not a registry capability: hone-models has no field for it yet.

## D-141: `one-body` is an acceptable error  (2026-10-11, 0021)

**Status:** mine, awaiting owner review.

`check_shots`' new rule is an error, so the planner's repair (§7.4) fixes it, but acceptable (D-027): two
full bodies of one character make a worse scene, not a broken video, so the owner may approve the shot list
with it. A shot's `refs` that name a view without a slash are left to `references`, which refuses them.

## D-142: a carrier's props before the given sheets  (2026-10-11, 0021)

**Status:** mine, awaiting owner review.

A first picture's references are the pictures of the props the character carries (`carried_by`), then the
owner's given sheets of other characters (0020 §2), cut at the model's `max_references`: the prop is the
character's own, the sheets only set the style. Each prop that got a slot is named by its number: "The
Ruby token in image 1 is the one this character carries: <look>; keep it exactly." Only props stage 6
draws (a look, no given sheet) are given; a prop from a given sheet has no picture until stage 7. A redone
prop changes its carriers' references and so their keys: stage 6 draws them again in the same run, and
nothing else.

## D-143: the details in the views, named by number  (2026-10-11, 0021)

**Status:** mine, awaiting owner review.

In a "one-body" project stage 7 draws the details first (one batch, judged), then the side and back with
the first picture and every detail of the character, up to the views model's slots, each detail named
("Image 2 is a close-up of <look>: keep it exactly."); the portrait gets the front, the side, then the
details. The detail prompts and their references (the first picture) are as in 0020.

## D-144: the licence warning is a notice  (2026-10-11, 0021)

**Status:** mine, awaiting owner review.

`image_menu.not_commercial` reads each role's entry through the port's new `licence` (hone-models'
`capabilities.license` and `commercial_use`) and lists those with `commercial_use = false`, and those that
record nothing as "licence not recorded"; `vocals` and `align` name no registry entry and are left out.
`new` prints it to stderr (stdout stays the project's path, which scripts read); the New video form shows it
above Start from `POST /api/estimate`'s `not_commercial`, without asking to confirm. Every entry of
`data/models.toml` now records both, so the list is empty unless a model really forbids commercial use.

## D-145: no portrait beside a body in a "one-body" scene  (2026-10-11, 0021)

**Status:** accepted by the maintainer (2026-10-11): 0021 §3 amended.

As built, a "one-body" shot without faces also got each character's portrait after the bodies; case 35's
scene drew Morvane twice. The same medium two-character scene on three seeds (7, 11, 42): from the two
fronts, two men every time; from the fronts and drawn portraits, a third man in two of the three. So a
character gets one picture of its body or face: a full body, or its portrait in a face shot (as before);
the named details and the props follow. `check_shots`' `one-body` rule counts a portrait with the
full-body views. Case 35 draws the scene from the two fronts (32 s).

## D-146: the back view gets no detail pictures  (2026-10-11, 0021)

**Status:** accepted by the maintainer (2026-10-11): D-143 and 0021 §2 amended.

Given Isolde's pendant close-up ("at the centre of her chest: keep it exactly"), her back view had the
pendant painted on her back, and the circlet's pearl on the back of her head; two redos with the note
"no necklace on her back" drew it again, the picture outweighing the note. A back view shows neither the
chest nor the face, so it gets the first picture only; the side keeps the details, and a detail that does
show from behind (Morvane's snakes) is in the first picture.

## D-147: a queued redo asks for something, and one refused leaves the queue  (2026-10-11, 0020)

**Status:** accepted by the maintainer (2026-10-11).

A redo of S006 sent with nothing chosen was queued while stage 10 drew; stage 10 refused it, failed after
42 of 129 pictures, and the entry stayed, so every later run (two forks for S006 and S043) failed the same
way. Now `takes.one_way` refuses a redo that asks for nothing when it is sent ("say how to redo shot
S006 ..."), so it is never queued; and `scene_queue.take` drops an entry its apply refuses
(`InvalidInput`) as a `queue_refused` event with the shot, and the stage goes on (any other error still
leaves the entry, as before). The Storyboard's "Redo with the edited prompts" waits for an edit and says
what it will make; the activity feed shows a refused redo.

## D-148: Pause is a wrapper on the models, asked through a file  (2026-10-11, 0022)

**Status:** accepted by the maintainer (2026-10-11), as 0022 §1 and §2.

`pause.Stoppable` wraps the `Models` port the workflow's stages get: before each model call it reads
`current/pause.json` and, if asked, writes `run_paused` and raises `Paused` ("paused by the owner").
The step fails with that message, and `status` reports the run and that stage as `paused`; Resume is the
resume of a failed run, so hone-flow needs nothing new. The dashboard and the CLI only write the file
(`runs_pause.pause`, refused unless the run is `running`). A pause asked during a call takes effect at
the next call; when the next thing is a gate (every planner is followed by one), the run waits there.

## D-149: local calls stay on the stage's thread; a hosted one is waited for on a helper  (2026-10-11, 0022)

**Status:** accepted by the maintainer (2026-10-11), as 0022 §2.

hone-models' GPU lease is per thread, so a local `generate` must run on the stage's own thread: Stop
cannot abandon it, it interrupts it (D-150) and the call's failure becomes `Paused`. A hosted `plan` or
`transcribe` runs on a daemon thread with the stage's context copied (the trace's ContextVars), and the
stage polls the request every 0.5 s; Stop no longer waits for it (its answer is dropped, and paid for).

## D-150: Stop interrupts ComfyUI directly  (2026-10-11, 0022)

**Status:** accepted by the maintainer (2026-10-11), as 0022 §2. `TODO(hone-models)`.

hone-models has no cancel call, so `pause.interrupt` posts ComfyUI's `/interrupt` at `HONE_COMFYUI_URL`
(default `http://127.0.0.1:8188`), ignoring a ComfyUI that is not there; the provider's wait then fails
and it cancels its job. This is the one request that bypasses hone-models; it goes once hone-models can
cancel a call. The tests replace `interrupt` with a stand-in that fails the fake's call.

## D-151: a paused run's redo makes the clip only past the start frames' gate  (2026-10-11, 0022 §5)

**Status:** mine, awaiting owner review.

`runs_pause.make_queued` takes the queued scenes into `live-takes.json` and draws them with stage 10's
`draw` given only those shots (so `shots.json` keeps the whole plan); once `review_stills` is decided it
also makes their clips and finishes with stages 12 and 13. Before that gate a scene's clip is made on
Resume like the others, from the pick the check makes. Stage 10's output is fixed once its step is done,
so stage 12 also takes a start frame from the scene's `takes.json` when stage 10's output lacks that take
and the take there is planned the same (`_shot_jobs.stills_of`). The dashboard's runner makes the
queue as a `paused-redo` job and does not apply it as a fork while the run is paused.

## D-152: a pause request older than the run is ignored  (2026-10-11, 0022)

**Status:** accepted by the maintainer (2026-10-11), as 0022 case 40.

The request records when it was asked; `Stoppable` clears one older than its own start, so a request
left by a crash, or asked as the run reached a gate, never pauses the next start or resume.


## D-153: the take in use shows the files its stage has not listed yet  (2026-10-12, 0024 §2)

**Status:** accepted (implementation detail of 0024, approved with it).

A stage writes a take's files into `takes.json` only once it is done, so while the clips stage runs, a
raw clip already made belongs to no take in the versions request. The scene viewer counts, for the take
in use only, the newest version no take leads to that was made from that take's step before (a raw clip
from its still, a finished clip from its raw clip; a draft while the take has no still). The server
stays a plain reading of the records; the page makes the one guess, and only for the take it is making.

## D-154: the viewer's Redo follows the step shown, not the view it was opened from  (2026-10-12, 0024 §2)

**Status:** accepted (implementation detail of 0024, approved with it).

0024 said the Storyboard's viewer redoes the frame and the Clips viewer the clip. A viewer opened on a
frame that then shows the raw clip would offer the wrong redo; so the panel follows the step shown: a
picture (draft or polished) offers the frame's redo, a clip the clip's. The requests are the cards'.

## D-155: the polish is chosen per take  (2026-10-12, 0025 §6)

**Status:** accepted (implementation detail of 0025, approved with it).

`Take.polish: Literal["on", "off"] | None = None`; `None` means the run's `settings.polish`. A redo that
draws a new start frame writes the project's current setting into the new take. Why: a fork keeps the
run's settings, and changing the setting for the whole run would change every shot's start frame and its
clip, which D-071 refuses. Polishing drafts already made, without drawing them again, is left for the
owner's later polish modes.

## D-156: without Part B, an image model on a SageAttention server is always refused  (2026-10-12, 0025 §2)

**Status:** accepted (implementation detail of 0025, approved with it).

The table's "leftover, idle → replaced" row needs Part B. Until then the adapter does not read `/queue`
or the GPU leases: every ComfyUI model that wants a plain server is refused when `/system_stats` shows
`--use-sage-attention`. A server that does not answer is left to hone-models to start, as today.

## D-157: the SageAttention version is kept in each clip's version record  (2026-10-12, 0025 §5)

**Status:** accepted (implementation detail of 0025, approved with it).

hone-flow has no API to add an attribute to a span, so the version goes into the clip version's `Made`
record as `inputs.sage_attention` (through `Generated.recorded`). It is read once per Wan session with
`HONE_COMFYUI_PYTHON` when set, else with the start command's first word when that is a Python
interpreter, else it is `"unknown"`.

## D-158: a blank file fails its step; retries do not catch it yet  (2026-10-12, 0025 §4)

**Status:** accepted (implementation detail of 0025, approved with it).

The refusal raises `ModelFailure` like any other model failure, the file is deleted, and the run stops
with the message (resumable). Drawing a blank start frame again inside 0015's retry rounds is left for
later: with §2 in place a blank picture should not happen, and this check is the safety net.

## D-159: the fake models draw pictures with a gradient and clips with a corner box  (2026-10-12, 0025 §4)

**Status:** accepted (implementation detail of 0025, approved with it).

The fake models draw pictures with a gradient and clips with a corner box, so the blank check passes
them; the colour of the top-left pixel stays the digest colour it was.

## D-160: the dashboard's runner takes no new job once closing  (2026-10-12, 0025 §3)

**Status:** accepted (implementation detail of 0025, approved with it).

`Runner.closing` is set by `Dashboard.close()`; jobs still queued are dropped (they are runs the owner
can resume). SIGTERM is handled like Ctrl-C while `Dashboard.wait()` runs.

## D-170: the song's shape is measured with ffmpeg and numpy  (2026-10-16, 0028 §1)

**Status:** accepted (implementation detail of 0028, approved with it).

The song (and the first listen's vocals, when kept) is decoded by ffmpeg to mono at 8 kHz; each part's
loudness is its RMS against the whole song's, in dB rounded to 0.1, never below -60 (silence). The voice's
loudness is against the vocals' own RMS. Words per second count the timeline's words that start in the
part. No new dependency: numpy and ffmpeg are already required.

## D-171: one review per plan, on Haiku, its notes as one more repair  (2026-10-16, 0028 §2)

**Status:** accepted (implementation detail of 0028, approved with it).

The review reads the shot list once its code repairs are done; when it has notes, the shot list is sent
back once more with the notes and the code's remaining problems (label `shots-review`), and the result
is checked by code again but not reviewed again. The review runs on `models.review`, Claude Haiku 5.5 by
default (the owner's rule: checks and judges on a cheap model).

## D-172: the camera check: no move on more than 40% of the shots, never four in a row  (2026-10-16, 0028 §2)

**Status:** accepted (implementation detail of 0028, approved with it).

A move is the camera field's first clause, lower case. A list of fewer than eight shots is not checked.
The 0027 run had 34 static shots and 31 slow push-ins of 73.

## D-173: a scene's takes never wait, as a workspace option  (2026-10-16, 0028 §5)

**Status:** accepted (implementation detail of 0028, approved with it).

`frame.Workspace(scene_picks=False)` (the video's workspace) makes an item of the `scenes` group with
`count` or `prompts` done at once with its first picture in use; Hone Frame's behaviour stays the default,
so the ported Hone Frame tests keep testing it.

## D-174: a scene's other takes are its latest `count` pictures but the one in use  (2026-10-16, 0028 §5)

**Status:** accepted (implementation detail of 0028, approved with it).

They are kept as start-frame versions (not `still.png`); their clips and finished clips use the shot's
seed and motion prompt, are made after the clips of the takes in use, and are carried from the clips
stage to the finishing stage in `ShotFiles.takes`.

## D-175: prepare is a check at the start of the scenes stage  (2026-10-16, 0028 §6)

**Status:** accepted (implementation detail of 0028, approved with it).

`project.json`'s `prepare` makes the `scenes` step raise `Paused` before it makes anything, so the run is
`paused` with every earlier stage done. A resume of a run paused there clears `prepare` and goes on; a
resume after a gate decision (before the scenes) keeps it. The owner's feeling is read from
`project.json` in the plan step, not added to the run's item, so a run made before 0028 stays the same.

## D-176: the dashboard keeps its queue and retries a failed run twice  (2026-10-16, 0028 §6)

**Status:** accepted (implementation detail of 0028, approved with it; replaces D-160's dropped jobs).

The runner writes `<projects>/.queue.json` whenever its queue changes: the running project first (as a
resume), then the jobs waiting. A dashboard started again queues them again (a project that is gone is
skipped). A run that ends `failed` is resumed at the end of the queue, at most twice in a row; a run
that ends otherwise resets the count. A resume of a project already running or queued is refused.

## D-177: how 0029's checks are made  (2026-10-18, 0029)

**Status:** accepted (implementation detail of 0029, approved with it).

- A link in a scene's facts has a `sentence` and its two `ends`; an end counts as named when a prompt
  holds it in any case without its first article or possessive (the, a, an, his, her, its, their, one).
  Every prompt of the scene must name it: each take is a whole shot of the same moment.
- `facts` is optional in the reply's schema, so a reply kept before 0029 still reads; a reply without
  it is asked again like any other problem.
- More than three of a kind in the facts is a `model-limit` problem kept in the plan, never sent back to
  the scene call, which cannot change the shot.
- The shot list's `model-limit` warnings come from the beat's words only (a regular expression, no
  model); they are not repaired by code but go to the review call as `code_found`, which decides whether
  the count or the side matters.
- Who gets `place_in_words` is the shot-list call's choice (it knows the camera and the beat), checked
  by the review call; code does not guess it from the words.
- The scale rule prefers a known object or a plain standing figure far smaller than the creature, since
  a full person in a reference picture can come back as an extra in a scene.

## D-178: how 0030 is built  (2026-10-18, 0030)

**Status:** accepted (implementation detail of 0030, approved with it).

- **No price per planner call.** The `Models` port reports a call's price only as the adapter's last one
  (`last_plan_cost_usd`), which the scene and subject calls, made four at a time on helper threads,
  would mix up. The Calls panel shows each call's model, time and problems; the plan's price stays in
  "What the video cost" (§13.5), from hone-models' records. The lyrics' calls have their own price.
- A kept call's file gains `at` (its start, to the microsecond, which orders the calls made side by
  side), `request` (the data, the images' names, the schema, the system prompt's file) and `problems`;
  the system prompt is written once per text as `frame/calls/system-<sha12>.md`. The key and the file
  name do not change, so the replies kept before 0030 are reused; they show without what was sent.
- The board and the viewer use Hone Frame's item panel as it is (its actions, the dependants dialog,
  its fields), so nothing of Hone Frame's behaviour is copied; the workspace stays a tab, and links to
  `…/scenes/i/<item>` still open it there.
- A line's start comes from the heard word only through the rule of 0030 §3; the heard word may be the
  line's first heard word or the one before it, since the matching can find a line from its second
  word (*This too shall pass*, L015 and L016). The three lines of that song move; no line of
  *Isolde (feeling)*, *Isolde (frame)* or *Roostam* moves.


## D-179: a project made by `new` starts from the dashboard  (2026-10-18)

**Status:** accepted (a fix: restores what a project made on the command line needs).

A project made by `hone-music-video new` has no run. The dashboard showed it as "Starting" with a
spinner and Pause and Stop, and offered no way to start it; the resume route failed in the runner's
thread for want of a run. It now shows **Not started** with a **Start** button, which posts to the same
resume route; the route starts the run when there is none (queued behind a running video, like any job).
No new route.

## D-180: how 0034 is built  (2026-10-19, 0034)

**Status:** accepted (implementation detail of 0034, approved with it); its bullets on the wide rule and
on expressions are superseded by D-181 and D-182 (2026-10-31).

- **`place_in_words` wins over the wide rule.** An overhead camera or a creature fight keeps its
  characters as pictures and has its place in words (0029 §3), even when it is wide without faces: the
  research measured that case, the wide rule was not.
- **The wide rule reads `faces` and `framing` only.** A wide shot with `faces: true` keeps its people's
  pictures; the shot list's check already warns on faces in a wide shot. The limit of pictures for people
  and place counts no character for a wide shot without faces.
- **An expression needs the neutral close-up.** It is made even when no shot uses the neutral face,
  since every expression is made from it (the Faces guide).
- **An expression the bible lacks is sent back, then dropped** from the kept shot list as an unknown
  variant is (`_kept_to_bible`), so a plan whose repair still names one is whole: the shot takes the
  neutral close-up.
- **Expression ids** are made safe and unique per character, like variants'; an item is
  `<character>.close-<expression>` or `<character>.<variant>-close-<expression>`.
- **Size words** are the usual aspect ratios (`16:9`, `9:16`, `1:1`, `4:5`, `4:3`, `3:2`, `2:3`,
  `21:9`), a size of three or four digits each way (`1664x928`, also with `×`), and "aspect ratio". A
  clock time (`10:30`) and a lens (`50mm`) are not.
- **The guide stays word for word** (0026); its "Photorealistic" examples are disclaimed in the scene
  and subject instructions instead.

## D-181: 0034's expression close-ups are dropped  (2026-10-31, 0034 §3)

**Status:** accepted (the measurement 0034 asked for decides it).

On the 17 face cases of the harness an expression close-up as the face shot's reference passed 66% of
the checks against 73% with the neutral close-up, and the cases' feeling checks did not gain (70%
against 72%): the close-up reference pulled the scene's scale and camera toward a head on a backdrop.
The bible's `expressions`, a cast use's `expression`, their items, checks and instructions are removed;
the face is written in the scene prompt as before (0028). A reply or plan kept with those fields still
reads: the records ignore fields they do not know. Guarantee 76 is removed.

## D-182: a wide shot keeps its character pictures; the review sees `from_scene`  (2026-10-31, 0034 §2, §4)

**Status:** accepted (the measurement 0034 asked for decides it).

- **J2 is dropped.** On its 22 wide cases, people in words passed 68% of the checks against 82%, and a
  quarter of the pictures were fully right against half, although they looked less posed. The place
  first with the characters' pictures kept matched the control's checks and had more pictures fully
  right, so a wide shot without faces now gets its place, then its characters, then its objects, like
  any shot. Guarantee 75 says so.
- **The review sees `from_scene`** (guarantee 79). It is told to check that a setup's later shots are
  made from the master, but its data left the field out: in the batch re-plans it said so, and one
  repair dropped a `from_scene` it could not see.
- **The shot list's wording.** "A wide shot without faces gets no picture of its people" was read as
  "lists no people": 77% of those shots came back with an empty cast (38% before). With J2 gone the
  sentence is gone too.

## D-183: the encoder's `<image1>` tags are not used  (2026-10-31, 0034 Verification J4)

**Status:** accepted (the measurement 0034 asked for decides it).

On the pilot's 20 cases, the same prompts with `<image1>` for "image 1" passed 78% of the checks, as
"image 1" did, with as many pictures fully right. The prompts keep "image 1".
