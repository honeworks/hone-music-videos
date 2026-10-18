# 0004: Unattended runs: "don't wait for my approval, just do it"

## Status

`accepted` 2026-10-10 by the owner's request ("don't wait for my approval, just do it", chosen when a
project is started). Implemented on `feat/live-progress` (unreleased). The details are in
[decisions.md](../decisions.md) D-075 and D-076 (accepted by the coordinator 2026-10-10).

## Context

A run stops at four gates (design §3.1): the timed lyrics, the cast, the sheet takes and the shot list.
For a long song the owner may start a project in the evening and want the video in the morning, trusting
the plans, without coming back four times. The gates exist because the hours of GPU time after them are
wasted on a bad plan; the checks (`check_lyrics`, `check_shots`) catch the plans that are certainly bad.

## Problem

There is no way to say "go on without me". The owner must approve each gate by hand, and a run left
alone stops at the first one.

## Options

- **A per-project mode, approve "ask" or "auto" (chosen).** Kept in `project.json` beside the
  settings, not inside them: the settings are the run's parameter, and changing them would not reach a
  run already started (and must not change what it made).
- A setting inside `settings`: it would be a run parameter, so switching an existing project would mean
  a new run. Rejected.
- Approving with errors too: hours of GPU time spent on a plan that is known to break the rules.
  Rejected.

## Decision

1. **The mode.** `project.json` gains `approve`: `"ask"` (the default, as before) or `"auto"`. It is
   chosen on the New video form ("Run without stopping for my approval"), with `hone-music-video new
   --auto-approve`, or `create_project(..., approve="auto")`, and it can be switched later from the
   project page (a toggle), the API (`POST /api/projects/<id>/approve-mode`) or
   `hmv.set_approve_mode(project, "auto")`. The key is written only for `"auto"`; a project without it
   reads as `"ask"`.
2. **Auto-approval.** In `"auto"`, every gate is approved the moment the run reaches it, by hone-flow's
   `approve` with `automated=True` and the actor `auto`, with a `gate_auto_approved` event: the timed
   lyrics, the cast, the sheet takes (the take on offer, the first of each character), the shot list.
   The run then continues as if the owner had approved.
3. **Never over errors.** When `check_lyrics` reports errors, or `check_shots` reports any error
   (blocking or acceptable, D-027), the gate is not approved: the run stops there and waits for the
   owner as today, with an `auto_stopped` event and the notice "stopped: needs you". Acceptable shot
   errors are not accepted automatically: accepting them is the owner's decision (the conservative
   reading, D-076).
4. **Switching an existing project to auto** that waits at a gate approves that gate (under the same
   rule) and continues the run. Switching back to "ask" stops at the next gate.
5. **The page** shows "auto" on the project and "approved automatically" on each gate approved so.

## Consequences

- `project.json` of an unattended project has one more key; a version from before cannot read that
  project (it says it was made by a newer version, D-032). A project that asks is written as before.
- A run in auto mode can reach the end without anybody looking at the plans; the checks are the only
  guard. The owner can still redo any shot afterwards (D-031).

## Migration and compatibility

Projects made before have no `approve` key and keep asking; projects that ask are still written
without it, so the previous version reads them. Runs are unchanged: the mode is read when
the run reaches a gate, from `project.json`.
