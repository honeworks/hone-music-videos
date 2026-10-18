# 0019: The judge checks the sheets

## Status

`implemented in 0.1` (2026-10-11; unreleased). `accepted` 2026-10-11: asked for by the owner 2026-10-11.
It builds on 0015 (the judge's retries of the start frames), 0017 (prop sheets) and D-110 (Claude Sonnet
5.5 is the judge). Its smaller choices are D-120 to D-127 in [decisions.md](../decisions.md).

## Context

In *Isolde the forgotten wife 2*, Morvane's cast entry asks for "two thick black snakes growing out of
the tops of his left and right shoulders" and a four-view turnaround. The project had `sheet_takes: 2`:

- take 1 draws three figures, with one snake rising from behind one shoulder and none in the side view;
- take 2 draws five figures, and the snakes differ in each (draped around both shoulders, one rising, one
  only).

Nothing checks a sheet: the judge sees only start frames. A take with the wrong number of figures also
breaks the cutter's view naming (§9 step 2 takes the first figure as the front, the next as the side, the
last as the back), and every shot of the character is drawn from that pack.

## Problem

1. A wrong sheet take is found only by the owner's eye, or not at all in an unattended run.
2. A wrong take is never drawn again on its own; the owner must ask for new takes and look again.
3. A take with three or five figures is cut into a wrong pack without a word.
4. A character that is hard to draw (attached animals, extra limbs) gets as few takes as anyone.

## Options

- **Check the cut instead** (count the figures the cutter finds): free and deterministic, but it cannot
  see a missing snake or a changed costume, and figures touching each other make it miscount. Kept as
  it is (the cut preview); not the check.
- **One judge call per take**: simpler replies, but N calls a round and no comparison between the takes
  of a character. Rejected: planner calls stay whole-batch calls (design §7).
- **One judge call per round over every new take, with retries as 0015 (chosen).**

## Decision

1. **The judge checks every sheet take** (design §9.1, D-120). Inside stage 6 (`sheets`), once the takes
   are drawn, `models.quality` (Claude Sonnet 5.5 for new projects) looks at every new take of the
   characters and props in **one** vision call: each take as one labelled JPEG 1536 px wide
   (`morvane #2`), with what it must show: a character's `id`, `name`, `kind`, `noun`, `cue` and
   `traits` (or a prop's `look`), the figures and views asked for (a character: four, `front`,
   `three-quarter`, `side`, `back`; a prop: two, `whole` and `detail`) and the prompt it was drawn from.
   The prompt is `data/prompts/sheets_check.md`. Per take the reply gives the figures counted, each
   figure's direction, each fixed trait with whether it is the same in every view, whether the backdrop
   is plain, a score (1 to 10, at most 5 with a major flag) and flags `figure-count`, `wrong-trait`,
   `inconsistent-views` or `extra`, `minor` or `major` (major: a pack cut from it would be wrong). It
   runs when `quality_check` is on, at most 60 takes a call.
2. **Automatic retries** (D-121). A take with a major flag is drawn again from the corrected sheet prompt
   the judge writes (the problem named and avoided, at most 2500 characters) with a seed of its own, and
   judged again in one call, up to `sheet_retries` rounds (a new setting, int 0 to 5, default 2, chosen
   when a project is made: CLI `new --sheet-retries`, the API's `settings`, the New video form). Every
   round is a kept version, recorded in `current/checks/sheet-retries.json` under the take's first file
   as soon as it is drawn and judged (a resume goes on without asking again). Events: `sheet_retry`
   (subject, take, round, flags), `sheet_retry_unfit` (a corrected prompt missing or too long; not
   drawn) and `sheets_checked` (takes, flagged, took_ms). The calls count in the `sheets` stage's cost
   (§13.5). The round with the highest score (the earliest on a tie) is the take offered.
3. **The owner still picks** (D-122, D-123). Each row of the `Sheets` record gains `checks`: the judge's
   rounds of each take, in the same order (`null` for a take it never saw). The Cast view shows each
   take's score, figures and flags, and its retries ("retry 1 of 2: 5 figures → redrawn"); a take still
   flagged after its retries is marked, never hidden. The take offered first (`picked`) is the
   best-scoring new take the judge did not miscount; so an unattended run goes on with it.
4. **Unusual characters get more takes** (D-125). The cast planner sets `unusual: true` on a character
   whose look is hard to draw (non-human anatomy, creatures, attached animals, extra limbs, masks); such
   a character gets at least four sheet takes, whatever `sheet_takes` says.
5. **A miscounted take is never cut** (D-124). A character's take whose offered round the judge counted
   with other than four figures cannot be picked (`pick` refuses it with the judge's evidence),
   approving `pick_sheets` with it is refused, and an unattended run stops at `pick_sheets` instead of
   cutting it (`auto_stopped`, with why). The owner picks another take or asks for new ones. The
   cutter is unchanged. A prop's two objects are not views: its count is flagged, never refused.

## Consequences

- Stage 6 makes hosted calls when `quality_check` is on: one, plus one per retry round with a major flag
  left; about 0.05 USD a call for two takes (D-127).
- Settings: `sheet_retries` (default 2). Cast: a character gains `unusual` (default false). `Sheets`
  rows gain `checks`. New record `current/checks/sheet-retries.json`, new events. No step version
  changes.
- Guarantee **21** (design §14): every sheet take is judged in one call per round; a take with a major
  flag is drawn again from the judge's corrected prompt, at most `sheet_retries` rounds, its best round
  offered; an unusual character gets at least four takes; a take the judge counted with other than
  four figures is never cut into a pack; unattended, the best take goes on; an older project redraws
  nothing.

## Tests

- `tests/e2e/test_ac21_sheet_judge.py`: an unusual character with `sheet_takes: 2` gets four takes; one
  call a round over the takes still flagged; a retry heals take 2 and is offered and cut; take 3 stays
  flagged after two retries, is marked and cannot be picked; unattended, the best take goes on and a
  run with only miscounted takes stops at `pick_sheets`; an older project redraws nothing.
- `tests/unit/test_sheets_check.py`: what the call carries, an unfit corrected prompt, a take the reply
  leaves out, the check off, new takes judged alone after a retake, a resume in the middle of a retry,
  the take offered first, the miscount refusal, unusual characters, the labelled picture.
- `tests/unit/test_prompt_rules.py`, `tests/unit/test_dashboard_page.py`, `tests/integration/test_costs.py`,
  `tests/e2e/test_ac18_project_options.py`, `tests/unit/test_settings.py`.

## Migration and compatibility

Settings stored without `sheet_retries` read 0: an older project's sheet takes (on a retake) are judged
when its `quality_check` is on, and never drawn again. A cast without `unusual` reads false. `Sheets`
records without `checks` read `[]` (no verdict: nothing refused). A run whose `sheets` stage is done is
not judged again.
