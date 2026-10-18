# 0008: Redo many shots at once, and re-plan a few shots with a note

## Status

`accepted` 2026-10-10 by the owner ("select several shots and regenerate only those, then get the
final video re-assembled once"). Implemented on `feat/batch-redo` (unreleased), built on
`feat/live-progress`. The details are in [decisions.md](../decisions.md) D-070 to D-074, accepted by
the coordinator on 2026-10-10.

## Context

After a run the owner watches the video and finds several weak shots: some need a new seed, some a new
start frame, a few in a row need a different idea ("S012 to S015: show the duel from a distance"). A
redo today is one shot at a time (D-031): each is a fork of the run that remakes the shot and assembles
the whole video again (about 77 s on the CPU for a five-minute song, §15), and the next redo waits for
it. Seven redos are seven assemblies, and nobody can say beforehand how long the GPU will be busy.
Changing what a shot shows needs the planner, but the planner only plans the whole song (§7.1), and
sending the shot list back with a note is possible only at the gate, before anything is made.

## Problem

1. There is no way to redo several shots in one go with one assembly at the end.
2. Nothing says what a redo will remake, or how long it will take, before it starts; and a redo of a run
   made by an older version can remake far more than the shots asked for (its files' keys changed).
3. There is no way to change the plan of a few shots after the shot list was approved without planning
   the whole song again (and remaking every shot).

## Options

- **One fork with every selected shot's new take (chosen).** The run's `takes` param already holds a
  take plan per shot (D-031): a batch is one new value of it with many shots changed, so the stages make
  only those shots and the video is assembled once. No new machinery.
- A queue of single redos, assembling only after the last: the queue would need its own state and
  failure rules; one fork already does it. Rejected.
- **Re-plan: one whole-song planner call that may change only the selected shots, proposed first
  (chosen).** The call keeps §7.1 (never one call per shot). The code checks the reply (every other shot
  exactly as before, the song still tiled, no new check error), the owner approves the difference, and
  the new plan reaches the stages as an edit of the shot-list gate in a fork of the run.
- Re-plan by asking the planner per shot: breaks §7.1 and loses the story's continuity. Rejected.
- Re-plan by sending the whole shot list back at the gate (reject-and-revise in a fork): the planner
  could change any shot, and every changed shot would be remade. Rejected.

## Decision

1. **Batch redo.** `hmv.redo(project, models, shots, redo)` takes one shot id or a list, where an item
   may be a range (`"S012-S015"`, in plan order); every listed shot gets a new take as `redo` asks, in
   one fork of the run, with one `shots_redo` event. The single-shot form keeps working (it is a list of
   one). The CLI: `redo PROJECT S003 S007 S012-S015 --seed` (any of `--seed`, `--still`,
   `--still-prompt`, `--motion-prompt`: one redo, the same prompts for every listed shot, each checked
   against the shot's cast), and `--dry-run`. The API: `POST /api/projects/<id>/redo` takes
   the old `{shot, ...}` or `{"shots": [{shot, seed, still, still_prompt, motion_prompt}, ...]}` (each
   shot its own redo), and `"dry_run": true` answers without running.
2. **What it will make, and how long.** Before any redo or "use this version" forks the run, the
   stages' own jobs are worked out for every shot without making anything: which shots would get a new
   draft, start frame, raw clip or finished clip. The answer, with the time it should take (each unit at
   this project's measured time per unit, else §15's, marked as an estimate) and the assembly, is what a
   dry run returns and what the Storyboard asks the owner to confirm ("7 shots ≈ 55 min of GPU").
3. **The guard.** A redo (one shot or many) is refused, with what and why, when the fork would run
   anything else: a stage before `stills` (its code or parameters changed since the run was made), or a
   file of a shot that was not selected (its key changed: made by an older version, or removed). Like
   assembling again (D-036), nothing runs that the owner did not ask for.
4. **Re-plan these shots.** `hmv.replan(project, models, shots, note)` makes one whole-song call to the
   shot planner with the whole current plan, the selected ids and the note, and the rule "change only
   these shots; keep every other shot exactly; keep their times unless the note asks". The code checks
   the reply: the same shot ids in the same order, every other shot identical, no `check_shots` error the
   current plan does not have (so the song is still tiled). A reply that fails goes back once in a repair
   call with the problems; one that fails again is refused with the difference. The proposal (each
   changed shot old and new, the calls and their recorded cost (else about $0.6 each, an estimate), what
   would be remade and how
   long) is kept in `<project>/replan.json` and shown for approval; `hmv.apply_replan` makes it, and
   `hmv.discard_replan` drops it. A project in auto mode (0004) applies it at once.
5. **Applying a re-plan** is one fork of the run where the shot-list gate is decided again as an edit
   with the new plan, and the changed shots' takes start again from the new prompts; then only the
   changed shots are made (still, clip, finish) and the video is assembled once. The same guard applies.
   The CLI: `replan PROJECT S012-S015 --note "..."`, then `replan PROJECT --apply` or `--discard`. The
   API: `POST /api/projects/<id>/replan {shots, note}`, `.../replan/apply`, `.../replan/discard`.
6. **The Storyboard** gets a checkbox on every card, shift-click for a range and a drag over the shots
   on the song's timeline; a bar with the count, "New seed for all", "New start frame for all", the
   selected shots' prompts to edit in a small list, and "Re-plan these shots" with a note; each asks for
   confirmation with the estimate. A re-plan proposal shows as old and new prompts and framing per shot,
   with Apply and Discard.

## Consequences

- One assembly per batch: seven redos cost one 77 s assembly instead of seven.
- A redo of a run made by an older version may now be refused where it used to remake everything
  silently; the message names those shots and why, and selecting them too lets the redo run.
- The planner sees the whole plan for a re-plan, so a proposal costs one whole-song call (two with the
  repair), about $0.6 each (docs/shots.md); the proposal shows the calls' recorded cost.
- After a re-plan, the shot-list gate's output (the plan the stages use, `current/shots.json`) differs
  from `plan_shots`' reply; the dashboard and `check-shots` read the approved plan and check it.

## Migration and compatibility

No record changes format. Runs made before keep working: a batch is a new value of the `takes` param
they already have, and the workflow's steps are unchanged (so no stage's code key changes). The
single-shot API, CLI and Python forms keep working. `replan.json` is new and optional.
