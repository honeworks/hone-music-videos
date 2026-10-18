# 0003: Live progress: every picture as it lands, and a real progress bar

## Status

`accepted` 2026-10-10 by the owner's request (implemented on `feat/live-progress`, unreleased) ("It needs better status show. Even the draft images
should be shown. A proper progress bar is needed. This should be part of a change."). The details are
in [decisions.md](../decisions.md) D-050 to D-054 (accepted by the coordinator 2026-10-10).

## Context

On the owner's first real run (*The Long Night*, 60 shots, 50 with a cast) the `stills` stage first
draws every shot's draft with Qwen (about 100 s each, so about 80 minutes), then polishes them, then
draws the shots without a cast (D-034). The Storyboard showed only a finished `still.png`, and the
stage's count only counted stills, so for about 1.5 hours the owner saw nothing but "Start frames:
running" and "0 of 60 shots". The drafts were on disk (`versions/draw-*.png`) the whole time.

## Problem

1. The pictures a stage makes before its last step (drafts, raw clips, sheet takes and portrait drafts
   while their stage runs) are not shown.
2. There is no real progress: no count of the work a stage has done, no current step, no time left and
   no idea when the whole video will be done.

## Options

- **Show the files as they appear, count them from the folders.** Works for every run, but cannot
  tell what is being made now, and the time per picture is only the gap between file times.
- **Events for every model-made file, with a pure progress function over them (chosen).** The stages
  already write `events.jsonl` and the page already streams it. One event before and one after each
  model-made file give the current unit and its measured time; the folders remain the fallback for
  runs made before this change.
- A progress thread or a percentage from the model servers: a second source of truth, and ComfyUI's
  step counter says nothing about the stage. Rejected.

## Decision

1. **Units.** A stage's work is counted in units: one model-made file each. `stills`: a draft and a
   polish per shot with a cast (2 units), a still from text per shot without one (1); `clips`: a raw
   clip per shot; `finish`: a finished clip per shot; `sheets`: a sheet take per take to draw;
   `packs`: a portrait draft and its polish per character with a portrait. `stills` counts every take
   it draws; `clips` and `finish` the takes in use, which are all they make (D-031). The single-call stages have no units: they show their elapsed time.
2. **Events** (D-050). When a stage starts making, it writes `units` (`stage`, `totals` and `made` per
   kind: what it will have made at the end, and what was made already). Around every model-made file
   it writes `version_started` (`stage`, `kind`, `shot` or `character`, `n`, `total`) and
   `version_made` (the same, plus `file`, `took_ms`, `first`: the first file of its model session,
   which includes the model load). `version_made` replaces `shot_finished`, `sheet_take` and
   `pack_picture`; the dashboard still reads those in older logs.
3. **Progress** (D-051, D-052). A small pure function (`progress.py`) turns a stage's units and the
   timed units of its current run into: done and total, the current unit ("drafting S007, 3 of 110"),
   the elapsed time, the time per unit of each kind measured in this run, the model load (the first
   unit's time over the average, when known), and the time left: the remaining units at the measured
   averages, minus the time already spent on the current unit. Until two units of this run are done it
   says "estimating". A kind not measured yet in this run uses the measured default of design §15
   and the result is marked "estimate". The overall estimate covers the long local part (`stills` to
   `assemble`) once the shot list exists: each stage's remaining units at the measured averages, or
   the §15 defaults (marked "estimate"), and the clock time it should end. Nothing is invented: every
   number is a count of files or events, or a measured or published time.
4. **Old runs** (D-053). A run without `units` events is counted from its folders (drafts, stills,
   clips, finished clips; sheet takes and portraits), and its times per unit are the gaps between the
   file times since the stage started.
5. **The API** exposes it in the project JSON the page already reads (`GET /api/projects/<id>` and
   the project list): `progress` with each stage's numbers, the overall estimate and the unit being
   made. No new thread: it is computed when asked.
6. **The page** (D-054). The Storyboard and the Overview's filmstrip show each shot's newest file
   whatever its stage (draft labelled "draft", still, raw clip "raw clip, 16 fps", finished clip) with
   its state (waiting, drafting, draft ready, polishing, still ready, animating, clip ready, finishing,
   finished, failed). The Cast view shows sheet takes and portrait drafts as they are drawn, with the
   character being drawn. The pipeline, the Overview's "Working on" card and the project's card in the
   sidebar show the bar: done of total, the current unit, elapsed, time left (m:ss) and the overall
   end clock time. Every picture and clip opens in a viewer over the page (full size, the video with
   controls, its label, previous and next through the same list with the arrow keys, Esc or a click
   outside to close, a link to the raw file); focus stays inside it.

## Consequences

- `events.jsonl` gets two lines per model-made file instead of one; a 60-shot video writes about 500
  more lines (a few hundred kilobytes).
- The project JSON gains `progress`; the project records gain each shot's `draft` and `newest` file
  and each pack's `portrait_draft`.
- Scripts that read `shot_finished`, `sheet_take` or `pack_picture` read `version_made` instead.
- The ETA of the first minutes of a stage is "estimating"; the overall estimate before the clips have
  run uses the §15 times of the reference machine, labelled as an estimate.

## Migration and compatibility

Old event logs keep working: their progress comes from the folders (point 4), and the activity feed
still describes the old events. No stored record changes.
