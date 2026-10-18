# 0022: Pause and Stop a running video from the dashboard

## Status

`implemented in 0.1` (accepted by the maintainer 2026-10-11, built 2026-10-11), with Stop also abandoning
a hosted call and §5 asked for by the owner. Its smaller choices are D-148 to D-152 in
[decisions.md](../decisions.md).

## Context

A run, once started, goes on until a gate, an error or its end. The dashboard has no control to halt
it; the only way is Ctrl+C on the dashboard's terminal, which kills every project's runner and leaves
the picture being drawn half made. Resuming then works (every finished file is a kept version, D-009),
but the owner has to know that, and has to restart the dashboard. On *isolde-the-forgotten-wife* the
owner asked for both: to pause (let the current picture finish) and to stop (now).

Neither library helps: hone-flow has no way to cancel a running step, hone-models none to interrupt a
call from another thread. hone-models does cancel a ComfyUI job when its wait fails (`comfyui.py`).

## Problem

1. The owner cannot halt a run from the dashboard.
2. Halting it by killing the process loses the picture or clip being made (a clip is 4 to 5 minutes)
   and looks like a crash.

## Options

- **Leave it as it is** (Ctrl+C, then Resume). Works, but is neither in the UI nor gentle. Rejected.
- **Pause only:** the run stops before its next generated file. Simple; but a 5-minute clip or a
  10-minute planner call still has to end first.
- **Pause and Stop (chosen).** Pause as above; Stop is Pause plus ComfyUI's `POST /interrupt`, so the
  local picture or clip being made ends within seconds, and a hosted planner or transcription call is
  abandoned (its answer, still paid for, is dropped when it comes).
- *Killing the runner thread* (an async exception): unsafe mid-write. Rejected.

## Decision

### 1. One request file, read between files

`POST /api/projects/<id>/pause` with `{"now": false}` (Pause) or `{"now": true}` (Stop) writes
`current/pause.json` (`{"now": ..., "at": ...}`, written atomically). `_jobs.make`, the one place every
generated file passes through, reads it before each model call: when it is there, the stage raises
`Paused`. Between stages the workflow's steps start with the same check, so a pause asked during a
planner call takes effect when the call returns, before the next stage.

### 2. Stop interrupts the local job and abandons a hosted call

The stages' `Models` is wrapped (`pause.Stoppable`, in `build_workflow`): every call first checks the
request. A hosted planner or transcription call runs on a helper thread the stage waits on, checking the
request every half second; on Stop the stage stops waiting and raises `Paused`, and the answer is dropped
when it comes (hone-models still records its cost). Local calls stay on the stage's thread, which holds
the model's GPU lease (hone-models' leases are per thread). With `now`, the request also sends ComfyUI
`POST /interrupt` (the URL hone-models uses). The job ends;
hone-models' wait fails and cancels it; the stage sees the pause file and raises `Paused` instead of the
model error. Nothing of the interrupted file is kept: a version is recorded only after its file is
complete (D-009). This one HTTP call is an in-library exception to rule 3 until hone-models has an
interrupt, marked `TODO(hone-models)`.

### 3. A paused run

`Paused` ends the step as hone-flow's `failed` with the message "paused by the owner"; the progress log
gets `run_paused` (`now`, the stage, the file it stopped before). `status` reports `paused` for a run
whose last failure is a pause, and the dashboard shows "Paused" with **Resume**, not an error. Resume
deletes `pause.json` and resumes as today: every finished file is reused by its key, so only what was
not finished is made.

### 4. The dashboard

While a run is busy, the progress card has **Pause** ("finishes the picture being drawn, then stops")
and **Stop now** ("stops the picture or clip being made; it is drawn again on Resume"). After either,
the card says "Pausing… after the current picture" (or "Stopping…", or "waiting for the planner's
answer" during a hosted call) until the run has stopped; then "Paused" with Resume. A queued scene redo
(0020 §4) stays queued and is made on Resume.

### 5. A redo while paused is made at once, the run stays paused

Today a redo on a stopped run is a fork that runs on from its stage, so a redo on a paused stage 10 would
draw every scene not drawn yet. In a paused run instead (asked by the owner 2026-10-11), a scene redo
(new still, new clip, edited prompts, another model, an upload) is recorded as the scene's new take the
way stage 10 takes a queued one (`live-takes.json`, 0020 §4), and the runner makes just that scene's
files at once: its start frame (draft and polish) through stage 10's own function given only that
scene, and its clip and finish through stages 12 and 13's once the run is past the start frames' gate
(before it, the clip is made on Resume like every other scene's; D-151). No hone-flow step runs; the run stays `paused`. On Resume the stages
find those files by their keys (D-009) and make nothing of that scene twice. A redo of a picture at a
gate (0020) is unchanged.

### 6. The CLI

```bash
hone-music-video pause projects/<slug>          # finish the current file, then stop
hone-music-video pause projects/<slug> --now    # interrupt the local job too
hone-music-video resume projects/<slug>         # as today
```

## Acceptance cases (§14)

36. Pause while stage 10 draws: the picture being made finishes and is kept, no other model call
    starts, the run is `paused`; Resume makes only the rest, no file twice.
37. Stop now while a local picture is made: ComfyUI is interrupted, nothing of that picture is kept,
    the run is `paused`; Resume draws it again and nothing else twice.
38. A pause asked during a hosted call takes effect when the call returns, before the next model call
    or stage; a pause of a run that is not running is refused (409, `RunStateError`).
39. A scene redo on a paused run makes only that scene's new still (and clip when asked) and the run
    stays `paused`; Resume makes none of it again.
40. Resume clears the pause request; a pause file left by a crash is cleared by the next start or
    resume, never stopping it.

Tests: e2e with `FakeModels` asking for the pause during a call for 36 to 40
(`test_ac36_pause.py`, the interrupt replaced by a stand-in, D-150; the CLI there too); the dashboard API
in `tests/integration/test_dashboard_pause.py`.

## Consequences

- One more file in `current/` and one event; no record changes. A paused run is a failed hone-flow run
  with a known message, so older tools see a failed run, which resumes the same way.
- Stop drops a hosted call's answer, which is still paid for.
- Pause acts within one file: a few seconds to a minute for pictures, up to 5 minutes for a clip
  (Stop: seconds).

## Migration and compatibility

Nothing stored changes; old projects have no `pause.json`. Crash halfway: the request file is either
written whole or not at all; a leftover one is removed at the next start or resume (case 40). Two
processes: the dashboard and the CLI only write the file; the runner only reads it, and Resume removes
it, under the run lock that already keeps one run per project.

## Answered

1. Stop also abandons a hosted call (the maintainer, 2026-10-11).
2. A paused run offers Resume only, no "Discard the run" in this change.
