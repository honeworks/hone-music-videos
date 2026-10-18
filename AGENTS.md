# AGENTS.md: hone-music-video

A brief for AI coding tools (Claude Code, Codex, Cursor and others) helping with this repository.
People follow the same rules; they are in [CONTRIBUTING.md](CONTRIBUTING.md).

## What this is

`hone-music-video` (import `hone_music_video`) turns a song into a music video: timed lyrics, a planned
cast and shot list (hosted planner), character reference packs, start frames and clips on local models,
and an assembly cut to the millisecond, with a web dashboard. Runs go through hone-flow, every model call
through hone-models. Read [design/current.md](design/current.md) before changing behaviour; its §14
lists the guarantees the tests check. Why the design looks like this:
[design/changes/](design/changes/) and [design/decisions.md](design/decisions.md).

**Status:** the design (0001) is `accepted` (2026-10-10); milestones M1 to M6 and changes 0002 to 0008, 0014, 0020, 0021, 0022, 0024 and 0025 are built (0.1, not released). 0026, 0027 (Hone Frame is the only scene pipeline, re-implemented in `hone_music_video.frame`), 0028 (feeling-first planning, takes overnight, the overnight queue) 0029 (the still models' prompt guideline) 0030 (the Scenes board, the planner's calls, line starts from the heard words) 0031 (clips only for the picked takes), 0032 (lines the aligner lost timed from the heard words) and 0033 (one prompt at a time) are built (experimental; merged to `main` on 2026-10-18).
Do not implement anything the owner has not accepted.

## Commands

```bash
uv sync --all-extras                 # install everything (dev included)
scripts/check.sh                     # all quality gates: lint, format, types, tests + coverage, build, wheel smoke test
uv run pytest                        # default suite (fast, offline, deterministic)
scripts/gpu-lock.sh uv run pytest -m gpu   # real-model tests, under the machine-wide GPU lock
```

## Layout

| Module | What it holds |
|---|---|
| `settings.py` | `Settings` and `ModelRoles` (design §2.3, §3.2); the settings and roles retired by 0027 dropped on read |
| `project.py` | the project folder: `create_project`, `open_project`, `list_projects` (§4); given sheets and poses |
| `records.py`, `records_timeline.py`, `records_frame.py` | the JSON records, integer milliseconds (§4.1 to §4.3, D-009); stages 1 to 4 and the shared field types in the second; the planner's replies, the frame plan, the shots' sidecar and the scenes in the third (0027) |
| `ports.py` | the `Models` port (with `image_info`, `image_models`, `image_guide`, 0027); `adapters/hone_models.py` is the real one, `testing/` has `FakeModels` |
| `adapters/hosted_speech.py` | the in-library transcription client for an OpenAI-compatible gateway, until hone-models has one (D-002, D-017) |
| `adapters/vocals.py` | Demucs vocal isolation on the CPU (the optional `separate` extra), until hone-models has one (D-041) |
| `adapters/aligner.py`, `aligned_lyrics.py` | given lyrics aligned to the vocals by the MMS forced aligner on the CPU (the optional `align` extra), until hone-models has one; the cross-check with the heard words (0005, D-055 to D-059) |
| `first_listen.py` | the first listen: the song's isolated vocals heard once, made once more when it finds too few lines (§6 step 1, D-045, D-047) |
| `lyrics_match.py`, `second_listen.py` | given lines matched against heard words and their gaps; listening again to a gap's slice and its vocals (§6 steps 1b, 1c; D-040, D-041) |
| `timed_lyrics.py`, `lyrics_check.py` | the lyrics editor's reply and the timeline built from heard words (§6, D-016); `check_lyrics` (§5.1) |
| `owner_timing.py` | the owner's line times at the lyrics gate: checked, applied by line id, kept in `current/lyrics/` (§6, 0018, D-113 to D-116) |
| `shots_check.py`, `prompt_words.py` | `check_shots` (§5.2): the shot plan's errors and warnings, each with shot, rule and amount (D-026); the words a prompt must not use |
| `pace.py` | the pace's preferred shot length and its `pace` warning (0009, D-084) |
| `stages_plan.py`, `stages_make.py` | stages 1 to 3 as plain functions (§3.1); clips, finishing and assembly |
| `frame/` | Hone Frame's behaviour re-implemented (0027 §1): the project file and its checks, write-back with tomlkit, marks, the runner (holds, picks, the demo first, pause and stop), actions with dependants, versions, estimates, notifications, Pillow sheets, the views and the JSON API the Scenes view calls, the guide; `frame/models.py` puts the library's `Models` behind it; each module names the Hone Frame code it is ported from |
| `frame_plan.py`, `frame_calls.py`, `frame_prompts.py`, `frame_facts.py`, `frame_items.py`, `frame_toml.py` | the planner (0027 §3): the plan in several calls (story, shot list, one per subject, one per six scenes), each reply kept and checked; the prompts' checks; a scene's facts checked against its prompts (0029); the items each subject needs (poses and details too, 0028), worked out by code; the plan as a Hone Frame project file |
| `music.py`, `frame_review.py` | the song's shape measured per part with ffmpeg and numpy (0028 §1); the arc and camera checks and the review call that reads the shot list for the feeling (0028 §2) |
| `frame_stages.py` | stage 5's install of the plan, stage 7 (`scenes`: the frame run driven, paused, stopped), the scenes in use as start frames, the dashboard's frame runners |
| `_shot_jobs.py` | what stages 8 and 9 share: a shot's folder, its job, making them (D-005) |
| `_video.py` | ffmpeg for the assembly: a clip measured, cut to its frames, the cuts joined under the song (§12, D-035) |
| `_jobs.py` | what the stages share: `Job`, and making a generated file as a kept version (D-009) |
| `_blank.py` | a blank picture or clip refused before it is kept (0025 §4) |
| `adapters/comfyui_server.py` | the ComfyUI command line and the SageAttention version a Wan session records (0025 §2, §5) |
| `workflow.py` | the 10 stages and 3 gates as one hone-flow workflow |
| `runs.py`, `_gates.py`, `_auto_approve.py` | `start`, `resume`, `approve`, `reject`, `lyrics_timing` (0018), `status`; the latest run (forks, D-031); the gates of an unattended project, `review_scenes` accepted as the scenes are (0004, 0027) |
| `runs_redo.py` | after the scenes: new clip seeds, a motion prompt, `remake` (a fork from `clips` that makes only what changed), `assemble` (0027 §7, D-036) |
| `pause.py`, `runs_pause.py` | Pause and Stop: the owner's request file, the models wrapped so the stages stop at their next call (0022) |
| `events.py` | the project's progress log (`events.jsonl`) |
| `progress.py`, `_run_progress.py` | how far each stage is and when the run should end (0003, D-050 to D-053) |
| `notify.py` | notifications through hone-flow to one webhook from the environment (§13.4, D-060) |
| `video_costs.py` | what a video cost: the hosted calls' recorded prices and every stage's time (§13.5, D-062) |
| `editor_files.py` | the edit for editors: FCP7 XML and a CMX3600 EDL beside `edl.json` (§12.1, D-063) |
| `_dashboard_runner.py` | the dashboard's runner: one project at a time, the queue kept in `<projects>/.queue.json`, a failed run resumed twice (0028 §6) |
| `dashboard.py`, `_dashboard_api.py`, `_dashboard_frame.py`, `dashboard_page/` | the dashboard (§13): server, JSON API (prepare, run all prepared, 0028), the frame API mounted under `/api/projects/<id>/frame/` (0027 §6), the page; `views/scenes.js` mounts the board (`views/scene-board.js`, the viewer `views/scene-frame.js`, 0030) and Hone Frame's screens ported in `dashboard_page/frame/`, `views/calls.js` the calls (0030), `views/plan.js` the Plan view, `decide.js` every gate's controls (0018), `views/timing.js` the Lyrics view's timing editor (D-119), `views/clips.js`, `views/board.js`, `views/scene-parts.js` and `views/scene.js` the clips and the scene viewer, `views/preview.js` the Preview (0024) |
| `_dashboard_calls.py` | the hosted calls for the Plan and Lyrics views: the kept planner calls with what was sent, the transcriptions (0030 §2) |
| `_dashboard_records.py`, `_dashboard_files.py`, `_dashboard_versions.py` | what the project views read; which files are served (the frame's pictures and thumbnails too), byte ranges; a shot's versions for the scene viewer (0024) |
| `cli.py`, `_cli_redo.py`, `_cli_frame.py` | the `hone-music-video` command; `remake`, `redo`, `motion`, `pause`; `frame` (Hone Frame's actions) |
| `data/frame_guide/` | Hone Frame's prompt guide, copied word for word, and its image model's notes (0026) |
| `data/prompts/` | the planners' system prompts, the model limits of §8 among them |
| `data/models.toml`, `data/workflows/` | the library's hone-models entries and ComfyUI workflows (D-008, D-018, D-022, D-032, D-033) |

## Rules

1. **Simple first** ([CONTRIBUTING.md](CONTRIBUTING.md#keep-it-simple)): the plainest code that meets the
   guarantees; complexity ≤ 10, functions ~40 lines, modules ~300 lines.
2. **Design before code:** a new need or change starts as `design/changes/NNNN-<name>.md` with status
   `proposed`; the maintainer accepts it before it is built. Small choices go into `design/decisions.md`.
3. **Every model call goes through hone-models**, local and hosted alike (temporary exceptions: hosted
   transcription, D-002, vocal isolation, D-041, and forced alignment, 0005), so prompts, costs and
   times are recorded; tests use fakes, never a real model by default.
4. **Planner calls are few and whole:** the story and the shot list are whole-song calls, and one review
   call reads the whole shot list (0028); the prompts are one call per subject and one per six scenes,
   never one per picture (0027 §3).
5. **Times are integer milliseconds** everywhere in records; only the dashboard formats them.
6. **The default suite is offline and deterministic**; real-model tests run only through
   `scripts/gpu-lock.sh` (one machine-wide GPU lock) and unload their models.
7. Never commit secrets (the gateway key comes from `OPENAI_COMPATIBLE_API_KEY`), model weights or generated media.
