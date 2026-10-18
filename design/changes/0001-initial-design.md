# 0001: Initial design: song in, music video out (v0.1)

## Status

`accepted` 2026-10-10 by the owner, with the answers recorded in [decisions.md](../decisions.md) D-002 to
D-007 (hosted speech through a temporary in-library client, D-002; no lyrics editor in 0.1, D-003).

## Context

The owner makes story-driven songs and wants their music videos made the same way: from the song, with
consistent characters, on open models running on one consumer GPU (an RTX 4060 Laptop, 8 GB). Over two
days (2026-10-09/10) the whole pipeline was tried by hand in a private playground on one real song, and
every model and setting was chosen in side-by-side tests the owner judged
([history/0000-research.md](../history/0000-research.md)). The owner then asked for an open-source
honeworks library that does it end to end, with a web dashboard, in their words:

- take a song, get its context, generate character sheets, plan the scenes under our constraints (shot
  length, no complicated actions, ...), generate the scenes, then the videos; style, resolution, aspect
  ratio and similar are inputs given with the song;
- time the lyrics (each line's exact time) with a strong LLM from the OpenAI-compatible gateway;
- plan the sheets with a strong hosted model, which also accepts sheets the owner already has and
  decides what is covered and what is still needed;
- plan the scenes with a strong hosted model, in detail, with prompts the local models use later; the
  prompt carries the style, the characters, the story of the song and **our limitations** (for example,
  avoid small faces), worded so the model understands them; research the models' limits and include
  them;
- write the prompts the local models need;
- never call the API per scene: one call with the transcript, limitations, roles and prompts, returning
  all scenes;
- exact timing to the millisecond ("this scene goes from 3:32.050 to 3:39.150"), checked by a Python
  validator against the transcript;
- then the local generation: images, videos.

Answers to the owner's questions (2026-10-10): name `hone-music-video`; lyrics optional (used when
given); standalone (not built on hone-frame); a run ends with the assembled video; design first, then
milestones; local git only until the owner says to publish; word times from Whisper plus an LLM;
`claude-opus-5-5` (hosted) as the planner.

## Problem

There is no tool that goes from a song to a timed, consistent, story-following music video on local
models, and the hand-made trial showed where such a tool fails if it is naive: guessed timing, drifting
faces, shots the video model cannot do, per-shot planning that loses the story, and long opaque runs.

## Options

1. **Extend hone-frame** (characters, sheets, scenes, dashboard). Rejected by the owner: hone-frame's
   larger model (requests, recipes, judging rounds) is more than this flow needs; coupling the two would
   slow both.
2. **A pipeline in the OneShotStudio research repositories** (storyboard, video-cut). Rejected: the owner
   wants an open-source honeworks library that stands on its own.
3. **A new standalone library on hone-flow and hone-models** (chosen): the stages of the trial, made
   resumable, with whole-song planning, written model limits and validators.

For timing: an LLM alone (imprecise times), Whisper alone (mishears sung words), local Whisper on
isolated vocals (offline, more setup), or **hosted Whisper word times plus an LLM that only fixes text
and structure, checked by code** (chosen).

## Decision

Build `hone-music-video` as described in [current.md](../current.md):

- the flow of §3 as one hone-flow workflow per project, with gates for the timed lyrics, the cast, the
  sheets and the shot list;
- integer milliseconds everywhere, validators for the lyrics and the shot plan, frame positions
  computed from absolute times (§5);
- three whole-song hosted calls (lyrics, cast, shots) plus at most two repairs; the planner prompt carries
  the written model limits of §8;
- the local stack the owner chose in the trial (§3.2), every part a setting;
- a standard-library web dashboard with a modern look (§13).

### Milestones

Each milestone ends with `scripts/check.sh` green, a review (simplicity and tests), an update of
`design/current.md`, and a short demo for the owner.

| # | Milestone | Done when |
|---|---|---|
| M1 | Project folder, settings, the workflow skeleton with fakes, the dashboard shell (projects, New video, live stages) | a song can be added in the dashboard and the stages run on fakes |
| M2 | Timed lyrics: speech model, lyrics editor, `check_lyrics`, the Lyrics view | a real song gets a validated timeline the owner can correct |
| M3 | Cast plan and character packs: `plan_cast`, sheets, the pick gate, cut, portraits, the Cast view | given sheets are reused and the missing ones are made |
| M4 | Shot plan: the prompts with the model limits, `plan_shots`, `check_shots`, repairs, the Shots view | a real song gets a valid shot list in one call |
| M5 | Stills, clips and finishing on local models, redo per shot, the Storyboard view | every shot has a finished clip |
| M6 | Assembly, the Video view, exports; a full real run on a test song | `video.mp4` plays with every cut on time |

## Consequences

- Better: timing is measured and checked; the planner plans what the models can do; characters keep
  their identity; every stage resumes; the owner approves before the expensive stages.
- Costs: three to five hosted calls per song (Opus with images is the largest; the prompts and images are
  recorded with their cost by hone-models); about 8 hours of local GPU per 5-minute song.
- Harder: the model limits in §8 must be kept true as models change; each new local model needs its
  limits measured and written down.
- **Dependency on hone-models:** a hosted speech provider (OpenAI-compatible `/audio/transcriptions`
  with word timestamps) does not exist yet. It needs its own change in hone-models (D-002). Until then
  a small in-library client calls the gateway's `whisper-1` behind the same port (D-002, owner's choice).

## Migration and compatibility

A new library; nothing to migrate. Record formats start at `format_version: "1"`.
