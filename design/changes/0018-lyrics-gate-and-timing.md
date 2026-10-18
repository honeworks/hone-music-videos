# 0018: Gate controls that cannot be confused, and timing the owner can fix

## Status

`implemented in 0.1` (2026-10-11; unreleased). `accepted` 2026-10-11: asked for by the owner
2026-10-11. Its smaller choices are D-111 to D-119 in
[decisions.md](../decisions.md). It changes D-015's "no editing in 0.1" for the lyrics' times (not
their text).

## Context

In *isolde-the-forgotten-wife-2* the owner wrote "timing is not accurate" and meant to send the lyrics
back, but the run went on to the cast. The run's record shows `gate_approved review_lyrics` with an empty
note and no reject. On the Lyrics view the note box was inside a collapsed "Run the lyrics again with a
note" under a large Approve button: a note typed there and Approve pressed was silently lost. The
Overview's gate card offered Approve only. The dashboard's Approve never sent a note at all.

And a note could not have fixed the timing anyway: the lyrics editor never writes a time (D-016); every
time comes from the measured words, and when those are off (a line sung over a long held note, an
aligner that lands on a breath) the owner had no way to move a line.

## Problem

1. A decision at a gate can be made by mistake: what the owner wrote is lost when the wrong button is
   pressed, and the Overview cannot send a gate back at all.
2. A note typed at a gate is lost when the view redraws (every server-sent event redraws it).
3. The owner cannot correct a line's start or end, so a run with off timing must go on with it.

## Options

- **Keep the collapsed box, warn on Approve.** Fixes 1 half-way; 2 and 3 stay. Rejected.
- **One set of gate controls, used on every gate's page and on the Overview (chosen for 1, 2)**: an
  always-visible note box, Approve and "Reject with note" side by side, Approve with a typed note asks
  first, the note kept per project and gate across redraws.
- **Timing: a gate decision with an edited output (chosen for 3).** hone-flow's `edit` replaces a gate's
  output (as `pick_sheets` does with the picked takes); everything downstream reads the gate's output, so
  the owner's timeline is used as-is. Until the gate is decided, the owner's edits are kept beside the
  run (in `current/lyrics/`), applied by line id to whatever the lyrics stage made last. Rejected:
  *a new owner-edit step* in the workflow: a new step changes the workflow's shape, so every older run
  would need a fork to resume (0006), for nothing an edited gate output cannot do.
- **Timing: the lyrics editor told the new times in a note.** It never writes times (D-016). Rejected.

## Decision

1. **Gate controls** (design §13.2; D-111, D-112). Every gate the owner decides on a page shows the same
   controls (`dashboard_page/decide.js`): a note box always visible, then **Approve** and **Reject with
   note** side by side, with a line saying what rejecting does at this gate. "Reject with note" is
   disabled while the note is empty. Approve with text in the note box asks "You wrote a note. Reject
   with it instead?" with Reject, Approve anyway and Cancel. The note is kept per project and gate in
   memory and in `localStorage` (when it can be used) until the decision is sent, so a redraw keeps it,
   with the focus. The Overview's gate card has the same controls. What reject does per gate:
   `review_lyrics` runs the lyrics editor again with the note (text, lines and sections; to fix timing
   the owner edits the times); `review_cast` plans the cast again; `review_shots` plans every shot again
   in one call; `pick_sheets` draws new takes (`retake`; there the note may be empty) and Approve is
   "Use these takes" on the Cast view; `review_stills` has no reject (its frames are retried one by one
   on the Storyboard), so it shows Approve only, with that said.
2. **The owner's timing at `review_lyrics`** (design §6; D-113, D-114). In the Lyrics view each line shows
   its start and end. While the gate waits, a line's timing can be opened: play the line, set its start
   or end to the play position ("Set start here", "Set end here"), or nudge either by ±100 ms or
   ±500 ms. Changes are a draft (kept across redraws) until **Save timing**:
   `POST /api/projects/<id>/lyrics-timing` with `{line_id: {start_ms, end_ms}}` (`null` takes a line's
   edit back), `hmv.lyrics_timing(project, edits)`, CLI `hone-music-video lyrics-timing <project>
   L012=77300-81200 L013=-`. The server checks every edit: integer milliseconds, start before end,
   inside the song, a line that exists; then the lines stay in order without overlapping. A refused
   save changes nothing and names every problem. The words of an edited line move with it, scaled
   within it; a section that holds an edited line spans its lines again; an instrumental span next to
   an edited line fills the new gap (and is left out when no gap is left).
3. **Kept, checked, used** (design §4, §5.1; D-113, D-115). A save writes the edited timeline as a kept
   version, `current/lyrics/timeline-<sha256[:12]>.json` (never overwritten, D-009), and
   `current/lyrics/owner-timing.json`: the edits, when they were saved and the version they made. The
   timeline marks the owner's lines (`owner_timed`, the line ids). `check_lyrics` runs again on the
   edited timeline and its report is what the view, the save's answer and `approve` go by. An owner-timed
   line is not checked against its words (`moved`, `not-heard`): its times are the owner's; every other
   rule applies. Approving with edits decides the gate with hone-flow's `edit` (the gate's output
   becomes the edited timeline, label `edited`): the cast planner, the shot planner, the shot check and
   the assembly use the owner's times as they are. Without edits, approve is as before.
4. **Running the lyrics again after edits** (D-116). A reject at `review_lyrics` with saved edits adds to
   the note that the owner timed those lines by hand and that the editor should change the text only,
   keeping every line and its words. After the rerun, the edits apply again by line id: an edit whose
   line no longer exists, or that would now overlap a neighbour, is dropped. The records the dashboard
   reads, the save's answer, `approve` and its `gate_approved` event say which edits were kept and which
   dropped (with why).
5. **Approve carries the note** (D-111). The dashboard's Approve no longer drops a note: with text in the
   box it asks first (above); "Approve anyway" sends no note and clears the box. An approval with the
   owner's timing keeps no note (hone-flow's `edit` takes none), so `approve --note` with saved edits is
   refused with what to do.

## Consequences

- Records: `Timeline` gains `owner_timed: list[str]` (default `[]`); `current/lyrics/` holds the owner's
  timing and its versions. Older timelines load unchanged; step versions stay (D-118).
- API: `POST /api/projects/<id>/lyrics-timing`; the `records` answer gains `lyrics_timing` (the edits
  kept and dropped); `approve` reads the note it is sent. CLI: `lyrics-timing`.
- An older run or a fork with no `owner-timing.json` behaves exactly as before.
- Guarantee (design §14): **22.** The owner's timing saved at the lyrics gate is checked (order,
  overlaps, inside the song), kept as a version, and is the timeline every later stage uses; a line's
  words move with it.

## Tests

All offline, in the default suite:

- `tests/e2e/test_ac22_owner_timing.py`: save timing through the public API; the fake shot planner and the
  cast planner see the edited times; the gate's output is the edited timeline; a rerun with a note keeps
  the matching edit and drops the other; the CLI `lyrics-timing`.
- `tests/unit/test_owner_timing.py`: validation (integers, order, overlap, inside the song, unknown
  lines, `null`), word scaling, sections and instrumental spans adjusted, check_lyrics on owner-timed
  lines.
- `tests/integration/test_dashboard.py`: `POST lyrics-timing` refusals and answers; reject with a note at
  `review_cast` as the Overview card sends it; approve with a note.
- `tests/unit/test_dashboard_page.py` (Node): a typed note survives a redraw; Approve with a typed note
  asks first and each answer does what it says; "Reject with note" disabled while empty; the timing
  draft's nudges and "set here".

## Docs to update

`design/current.md` §4, §5.1, §6, §13.2, §14; `docs/lyrics.md`, `docs/dashboard.md`, `docs/cli.md`;
`CHANGELOG.md`; `AGENTS.md`; `design/decisions.md` D-111 to D-119.

## Migration and compatibility

Nothing to migrate. A run waiting at `review_lyrics` when this lands can be timed and approved as
above. An approved lyrics gate is never edited again.
