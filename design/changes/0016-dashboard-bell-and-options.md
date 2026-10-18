# 0016: The dashboard's bell, the look options and a retry at the start-frame review

## Status

`implemented in 0.1` (2026-10-11; unreleased). `accepted` 2026-10-11: asked for by the owner
2026-10-11. The page's half of the options; the settings themselves (`pace`, `mood`, `still_retries`,
the automatic retries and their `still_retry` events) are built beside it on the backend
(`feat/options-heal`). Its smaller choices are D-096 to D-099 in [decisions.md](../decisions.md).

## Context

A real run takes hours and stops at up to five gates. The owner leaves the dashboard open in a tab
and misses the moment a gate starts waiting: notifications (§13.4) go to a webhook, and the page itself
says nothing aloud. The New video form has no way to say how fast the video moves or how it should feel,
and its style is one bare text box. At the `review_stills` gate the flagged start frames were redone
with "Redo → New still", three clicks deep in a card, and the automatic retries the backend now makes
were invisible.

## Problem

1. The owner must notice, without watching the page, that a project waits for them.
2. The New video form must offer the pace, the mood and a style to start from, and the start-frame
   retries, and show what it sends.
3. At `review_stills` a flagged frame must say what is wrong and offer one obvious way to draw it again,
   and the frame's automatic retries must show.

## Decision

### The New video form (D-096)

- **Pace:** three choices (calm, balanced, energetic), each with one line on what it means. The choices
  come from `GET /api/settings`' `paces` (a list of names) when the server sends them, else these three.
- **Mood:** free text in any language (`dir="auto"`, so right-to-left scripts read right to left), and ten words to
  add or take out with a click: tragic, sad, tender, hopeful, triumphant, tense, dark, dreadful
  (دلهره‌آور), mysterious, epic. A chip shows whether the mood holds its word.
- **Style:** four presets (Historical epic film, Dark & moody cinema, Natural documentary realism,
  Modern cinematic) that fill the style text with a concrete look naming no era (the era comes from the
  story); the text stays editable.
- **Start-frame retries:** 0 to 5, default 2: "if the judge finds a major problem in a start frame, it
  is drawn again with a corrected prompt, up to this many times".
- "What will be sent" shows the settings as Start sends them, kept up to date.

### The bell (D-097)

- The page asks for the projects every 4 s. A project whose `waiting` is set (or whose status is
  `awaiting_review`) waits for the owner; once two polls in a row see the same wait, the page plays a
  chime for 15 s and shows "Waiting for you: <project> — <gate>" with **Stop**.
- Each wait rings once; a wait that ended is forgotten, so the next gate (or the same gate again) rings.
  The waits already rung are kept in `localStorage`, so reopening the page does not ring for them.
- The sound is made with the Web Audio API (a two-note bell, every 2.5 s), no audio file.
- Browsers keep audio locked until the owner clicks on the page: **Enable sound** (in the sidebar, and in
  the banner while locked) unlocks it and is remembered; on a later visit the first click or key unlocks
  it again. The banner says when the sound is locked. The header's bell button mutes it (remembered).

### A retry at `review_stills` (D-098)

- A flagged start frame in use is outlined on the Storyboard, lists its flags, and has **Retry this
  frame**: the redo with a new still of design §11.2 (the check runs again).
- Every card lists its frame's automatic retries from the progress log's
  `{"event": "still_retry", "shot", "take", "round", "flags"}` events of the take in use: "retry 1 of
  2: wrong character → redrawn" (the limit is the project's `still_retries`). Without such events
  nothing shows.

### Tests (D-099)

The page's own logic (when the bell rings, the mood words, the pace choices from a stubbed settings
reply, the settings the form sends, the retries' text) runs in Node in the default suite; skipped where
Node is not installed.

## Consequences

- The dashboard asks for the project list every 4 s while open (one small JSON reply).
- A wait can ring a few seconds late (two polls); the gates an unattended run passes on its own never
  ring.
- Several open tabs share the rung waits through `localStorage`, so usually only one rings.

## Docs to update

`design/current.md` §13.2 and §13.6, `docs/dashboard.md`, `CHANGELOG.md`.

## Migration and compatibility

None for stored data: page only. The form always sends `pace`, `mood` and `still_retries`, which a
server without the backend half (`feat/options-heal`) refuses as unknown settings, so this change is
merged after it. Without `paces` in the settings reply the form offers calm/balanced/energetic.
