# 0007: Operations: notifications, what a video cost, and an export for editors

## Status

`accepted` 2026-10-10 by the owner (the three improvements were approved together). The smaller
choices are in [decisions.md](../decisions.md) D-060 to D-064, awaiting coordinator review.

## Context

A 5-minute video runs for about 8 hours, mostly overnight, and stops four times for the owner (design
§3.1). The owner learns that a gate is waiting, that a stage failed or that the video is done only by
looking at the dashboard. After a video, nothing says what it cost: the hosted calls (an OpenAI-compatible gateway) have
recorded prices, and the run records every stage's time, but nobody adds them up. And the assembled
video is final: `edl.json` is this library's own format, which no editor opens, so polishing the cut in
DaVinci Resolve or Premiere means rebuilding it by hand.

## Decision

1. **Notifications** (design §13.4, D-060). The run notifies through hone-flow's notifications
   (hone-flow design §4.9): when it stops at a gate for the owner (`run.awaiting_review`, the gate
   named), when a stage fails (`run.failed`, the stage and its first error line), and when the video
   is done (`run.completed`). One destination, configured only from the environment (or the `.env` file
   hone-models reads): `HONE_MV_NOTIFY_URL` (the webhook URL) and `HONE_MV_NOTIFY_KIND` (`slack`, the
   default, `mattermost`, `discord`, `telegram` or `http`). Telegram is a plain POST to the Bot API's
   `sendMessage` with the chat in the URL, the same body as Slack's. The message names the project, the
   gate or stage, and the project's page on the dashboard (`HONE_MV_DASHBOARD_URL`, default
   `http://localhost:8794`). The URL is never written into a record, a project file or a log (hone-flow
   strips it); without `HONE_MV_NOTIFY_URL` nothing is sent.
2. **What a video cost** (design §13.5, D-061, D-062). `hmv.costs(project)` adds up, from what is
   already recorded: the hosted cost of every call (the planners' prices from hone-models' span store,
   the transcriptions' and listens' from `words.json`), and the time of every stage from the run's step
   records (each attempt, in integer ms), by where it ran (GPU, CPU, hosted). Each stage's time and cost
   is split into the first pass, reruns (a stage run again after a rejected gate or a failure) and redos
   (forks of the run: redone shots, assembling again). A call without a recorded price, a failed
   transcription and a planner stage whose calls are not found are counted as unknown, never guessed.
   To find the planners' calls, the adapter passes hone-flow's trace context to hone-models (D-061).
   The summary is written to `current/costs.json` after every start, resume and fork of the run, shown
   in the Video view ("This video cost $X of hosted calls and Y h of GPU") and printed by
   `hone-music-video costs`.
3. **An export for editors** (design §12.1, D-063). Next to `edl.json`, the assembly writes
   `current/edit.xml` (Final Cut Pro 7 XML, `xmeml` version 4, which DaVinci Resolve and Premiere Pro
   import) and `current/edit.edl` (CMX3600): every finished clip on video track 1 at its frames of
   `edl.json`, the song on audio track 1, at the project's frame rate, shot ids as clip names. The Video
   view offers both as downloads; `hone-music-video export PROJECT` (and `hmv.export`) writes them for a
   video assembled before 0007, with no model call (D-064).

## Consequences

- `HoneModels.plan` and `generate` pass `trace=hone_flow.current_trace() or None`: hone-models' spans
  carry `hone.run_id`, `hone.step` and `hone.item` from now on. Runs made before keep working: their
  planner calls are found by time instead (D-062).
- New files in `current/`: `costs.json`, `edit.xml`, `edit.edl`. The `assemble` step takes the run's
  `measure` (the song's `Song`) as a new input and writes two more files; its result (`Assembly`) does
  not change.
- New CLI commands `costs` and `export`; new API `hmv.costs`, `hmv.export`, `hmv.Costs`; new dashboard
  route `GET /api/projects/<id>/costs`.
- No new dependency: notifications use hone-flow's standard-library webhooks, the XML is written with
  `xml.etree.ElementTree`.

## Alternatives considered

- **Our own notifier** (a thread posting on each gate event): rejected; hone-flow already records each
  event and its delivery in the manifest, retries on request and keeps the URL secret.
- **Telegram through a custom adapter** (`chat_id` and `text` in a JSON body): not needed; the Bot API
  takes `chat_id` from the URL's query and `text` from Slack's body.
- **Prices computed here from token counts**: rejected; hone-models records the price it computed from
  the registry, so the summary reads it ("never invent numbers").
- **OpenTimelineIO** for the export: a dependency (with a compiled core) for two small text formats.
- **FCPXML (Final Cut Pro X)**: Premiere does not import it; FCP7 XML is the one both editors read.

## Compatibility

Additive. Records and settings are unchanged. The `assemble` step has a new input (`measure`), so it
runs again where a run reaches it with this version (assembling again and redos run it anyway).
Existing projects get the editor files with `export` or their next assembly, and `costs.json` after
their next run, resume, redo or assembly.
