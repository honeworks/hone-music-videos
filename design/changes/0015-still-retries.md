# 0015: Start frames that heal themselves, and a cheaper judge

## Status

`implemented in 0.1` (2026-10-11; unreleased). `accepted` 2026-10-11: asked for by the owner
2026-10-11. Its smaller choices are D-086 to D-089 in [decisions.md](../decisions.md). It builds on 0006
(the start-frame check), 0014 (the motion-prompt rewrite) and 0009 (the story's world, the mood).

## Context

In *The Long Night* the check found what was wrong (a wrong character in S034, a hurricane lantern in
S047, an extra person in S054), but only after the polish, and nothing acted on it: the owner redid the
shots by hand. The check runs on Claude Opus 5.5, which took 9 minutes and about 0.20 USD for 59 frames.

## Problem

1. A start frame with a major flag goes on to its polish and its clip (minutes of GPU each) unless the
   owner stops the run and redoes it.
2. The check's prompt is loose: no fixed list of what to look at, no evidence asked for, and a severity
   rule that depends on the clip.
3. The check costs more than it needs to.

## Options

- **More takes per shot (`pick_best_of`)**: draws every chosen shot two or three times whatever its
  quality. Stays as it is; not this change.
- **Check after the polish and redo through a fork**: the polish is made for every bad frame first, and
  a fork per round. Rejected: slower, and the redo guard would see other shots change.
- **Check the drafts inside stage 10 and draw only the flagged ones again (chosen).**

## Decision

1. **`still_retries`**: int 0 to 5, default 2, chosen when a project is made (CLI `--still-retries`, API
   `settings`). Not given to the planners.
2. Inside stage 10 (`stills`), once the drafts (and the stills of shots without a cast, drawn from
   text) are drawn, the start-frame check looks at them in **one** call (contact sheets, as §10.3).
   For each frame with a major flag its reply gives a corrected still prompt: the same `{id}`
   placeholders, the fixed traits stated, the problem named by its opposite. Only those frames are drawn
   again, with that prompt and a seed of their own (`retry` round), and checked again in one call; up to
   `still_retries` rounds. The best-scoring round goes on to the polish (from its corrected prompt); its
   flags stay recorded. Stage 11 (`check_stills`) then checks the polished frames as before: picks,
   motion-prompt rewrites (0014), flags and the `review_stills` gate. So the stage order is unchanged and
   no step version changes (D-087).
3. Every round is a kept version (D-009) and is recorded in `current/checks/still-retries.json` under
   the frame's first draft: a resume or a fork (a redo) finds each frame's rounds and its best version
   without a call, so only frames never checked are checked, and a redo's check sees only its shots. The
   redo guard (0008) works out the polish of the best round.
4. Events: `still_retry` (shot, take, round, flags) when a frame is drawn again; `still_retry_unfit` when
   the corrected prompt cannot be drawn (other placeholders, too long). The checks' calls are counted in
   the stage's cost (§13.5).
5. With `quality_gate: "ask"` the run still stops at `review_stills` when a major flag remains after the
   retries; an unattended project goes on (D-067). "Redo → New still" there runs the same loop for the
   redone shot.
6. **The judge** (D-086): a new registry entry `claude-haiku-5-5` (OpenAI-compatible gateway, vision, 0.10 / 0.50 USD per
   MTok) is the default `models.quality` of new projects; projects made before keep theirs. The judge's
   prompt (`data/prompts/quality.md`) is rewritten: a fixed list per frame (the cast's fixed traits,
   the number of people, faces where none should be, hands and limbs, the story's world, the mood, the
   composition asked for, text and style), concrete evidence per flag, one severity rule (major = the
   frame would mislead the viewer or contradict the cast or the story; a frame with a major flag scores
   at most 5). Two flag kinds are added: `off-mood` and `composition`.

## Consequences

- Stage 10 makes hosted calls when `still_retries` > 0 and `quality_check` is on: one per round, only
  when a frame has a major flag after the first.
- New record `current/checks/still-retries.json`; new settings key `still_retries`; new flag kinds.
- Guarantee **19** (design §14): a start frame with a major flag is drawn again from the check's
  corrected prompt before its polish and clip, at most `still_retries` rounds, the best round going on;
  a manual redo runs the same loop for its shot only; an older project draws nothing again.

## Tests

- `tests/e2e/test_ac19_still_retries.py`: a flagged draft drawn again twice, before the final check and
  polished once; an older project makes no draft check; with the gate "ask" the run stops after the
  retries, and a redo heals only its shot.
- `tests/unit/test_still_retries.py`: one call per round, seeds, the best round polished from its
  corrected prompt, a frame that heals stops, an unfit fix is not drawn, a stage run again asks nothing,
  a shot without a cast drawn again from text.
- `tests/integration/test_costs.py`: a check in `stills` counts in its cost; a `stills` attempt without
  one is not an unknown call.
- `tests/unit/test_prompt_rules.py`: the judge's list, evidence and severity rule.

## Migration and compatibility

Settings stored without `still_retries` read 0: nothing is drawn again and no draft is checked, so an
older project's start frames keep their keys, a redo remakes only the shot asked, and "assemble again"
still runs nothing else. Stored settings keep their `models.quality` (Opus for every project made
before; settings without one read Opus). Older check records load (the new flag kinds only add values).
