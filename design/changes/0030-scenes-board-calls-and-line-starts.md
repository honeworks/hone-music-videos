# 0030: The Scenes view as a board, the planner's calls on the Plan view, and line starts fixed by code

## Status

`accepted (experimental)`, 2026-10-18, by the owner (all three parts), for the branch
`exp/frame-scene-generation` only. Asked for by the owner with the acceptance of 0029. Built; its smaller
choices are D-178 (among them: no price per planner call).

## Context

1. The Scenes view is Hone Frame's workspace: a list of items and one open item. The Clips view is a board
   of cards with a viewer over the page. The owner wants the scenes to look like the clips, and the
   information and actions to be there when a picture is opened.
2. The owner wants to see the API calls clearly. Today the planner's replies are kept in
   `frame/calls/<label>-<key>.json` (label, model, time, reply), but nothing shows them, and the request
   (system prompt and data) is not kept. The costs are in `current/costs.json`.
3. The Lyrics page "always gets messy" around later sung parts. Across the projects with the forced
   aligner (0005), the times agree with the heard words to about 100 ms, except at **the first word of a
   line that comes after a pause**: the aligner stretches that word back into the silence, so the line
   starts 0.9 to 2.1 s early. *This too shall pass*: L013 (913 ms), L015 (1844 ms), L016 (2079 ms).
   Each shows as an `align-disagrees` warning, and in each the line's first word is the same word the
   transcription heard later, and its second word agrees with the heard words within 150 ms. The other
   kind of warning is the opposite: in *Isolde (feeling)* L014 and L031 the transcription left out the
   sung "لالا لالا" (it wrote "[هولا هولا]"), so it "heard" the line start at its third word, and the
   aligner is right. The rule below must move the first kind and leave the second.   The owner then moves these lines by hand.

## Decision

### 1. The Scenes view as a board (dashboard)

- The Scenes view opens on a **board**, one card per shot in time order, like the Clips view: the scene's
  picture in use (or its takes as a small strip, a dimmed placeholder while it is made), the shot id, its
  state (waiting, running, made, picked, failed), the beat, the time and length, the cast, the framing and
  the number of versions. The song's timeline sits above it, as on Clips. Characters, objects and places
  get a second board under it, grouped by subject.
- A click opens a **viewer over the page** (the Clips viewer's frame and keys: ←/→ the shot before and
  after, Esc closes):
  - the picture large, every version and take below it, newest first;
  - its **information**: the prompt (or prompts), the references in order as thumbnails ("image 1: …"),
    the seed, the model, the size, when it was made and how long it took, the shot's beat, feel and
    evidence, and its motion prompt;
  - its **actions**, the ones Hone Frame's item panel has: use this version, accept, pick among takes,
    run again with a new seed, edit the prompt and run, mark or unmark, and open it in the workspace.
    An action that changes the scene asks about its dependants as the workspace does (Hone Frame's
    dependants dialog), and a scene changed after the clips remakes only its clip, as today.
- The workspace (items, sheets, project file, guide) stays, as a tab of the Scenes view; nothing of
  Hone Frame's behaviour changes, the board and viewer call the same frame API.

### 2. The planner's calls on the Plan view

- Each kept call also keeps its **request**: the system prompt's name and hash, the data sent, the
  images' names, the schema, and for a repair round the problems sent back; and its cost and tokens
  from the hosted reply. The key and the file name stay as they are, so a plan made again reuses the
  replies already kept (an old file without a request still reads).
- The Plan view gets a **Calls** panel: one row per call in the order made (the story, the shot list,
  the review, the shot list's repair, each subject, each scene batch and its repair), with its model,
  time, cost, and how many problems it was sent back with. A row opens the call: what was sent (the
  data, readable, the system prompt one click away) and the reply, with the problems the code found in
  it. The lyrics' calls (the transcription, the second listens, the lyrics editor) are listed the same
  way on the Lyrics view.
- A total at the top: calls, time and cost of the plan.

### 3. A line's start taken from the heard words (lyrics, no extra call)

- When a line's first aligned word is the heard word it was found at, or the heard word just before it
  (a line can be found from its second word; the same word, compared as the matching of lines to heard
  words compares them, 0005), and starts more than 750 ms earlier than it, and its second word agrees with the next heard word within 300 ms, the line and its first word
  start at the heard word's start. Its end and the other words stay the aligner's.
- The line then no longer warns; a `start-from-heard` note in the lyrics check says which lines were
  moved and by how much, so the owner can check them on the Lyrics view.
- A line where the first words are not the same, or the second word disagrees too, stays as it is, with
  its warning (the transcription missed words, or the two disagree about more than the pause).

## Consequences

- The Scenes view looks and works like the Clips view; Hone Frame's own screens are one tab away.
- The kept call files grow by the data they were sent (tens of kilobytes per call).
- The lines that start after a pause start on the voice; the owner moves fewer lines by hand.

## Verification

- Default suite: the board's and viewer's data from the frame API (the page itself checked by hand in a
  browser); a call file with its request read back, an old one without it still read; the Calls panel's
  rows from a planned fake project; the line start moved when only the first word disagrees, not moved
  when the second disagrees too or the first words differ (from the two projects' recorded words above).
- By hand: *This too shall pass* and *Isolde (feeling)* re-checked from their kept words: the three
  lines of the first start on the voice, and no other line of either moves.
