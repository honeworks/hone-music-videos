# 0028: Feeling-first planning, takes made overnight, and the overnight queue

## Status

`accepted (experimental)`: asked for by the owner on 2026-10-16 after the first real run of 0027
(*Isolde the forgotten wife (frame)*) and a review of the prompts sent for it. It is built on the branch
`exp/frame-scene-generation` only, like 0027. Its smaller choices are D-170 onwards.

## Context

The first 0027 run made a good-looking video that felt flat. A review of every planner call found that
the planner understood the events but weakened the song's feeling. Every finding was a gap in what the
pipeline carries between calls or checks, never something about that song:

1. **The song's directions were dropped.** The lyrics' notes (`[Chorus: HUGE GOTHIC DROP]`,
   `[Sound Effect: Sharp slithering sound]`, "fast whispers", "voice cracking") reached only the lyrics
   editor. A song given without notes, or without lyrics, had nothing at all about its music.
2. **Mood was only light.** `mood` was allowed to set "light, colour, stillness; never the story", so a
   terror beat came out as a calm, gentle face in dark light.
3. **Nothing carried what the viewer should feel**, from the whole song down to a shot, and nothing
   checked it. A character's hidden feeling (a smile over fear) was written as the surface only.
4. **A sung physical action was contradicted** ("pretend to sleep" was staged at a window).
5. **The still and its motion were mixed** in one beat ("sits up slowly, then …"): the image writer had to
   guess the instant, and the next shot did not know what the last one left.
6. **References did not match the shot**: a snake-head insert was made from a face close-up; a sleeping
   king's reference stood up; variants reached the prompt writers as "the look + Changed for asleep: …",
   a contradiction they resolved again in every prompt; the two people on a bed had no fixed layout.
7. **The checks were technical only**, and 65 of 73 shots were a static camera or a slow push-in.
8. **`takes` was never explained.** The shot list's instructions described a `hard` field that its
   schema no longer had; Opus guessed, and two clearly hard scenes got one picture.
9. **A hard scene's other takes were useless overnight**: the first was used, the others had no clip, so
   choosing another take in the morning cost a new clip.
10. **No overnight queue.** The owner wants to prepare four or five songs while online (the hosted calls),
    then run them all offline, one after another, and find every video finished.

## Decision

### 1. The song's shape, from three sources (A)

What the music does is taken from what is always there, and what the owner and the lyrics add:

- **Measured, always** (`music.py`, code, no model): for every section and every instrumental span, its
  loudness against the song's (dB), its change from the part before (dB), the loudness of the voice
  (the isolated vocals, when kept) and the words sung per second. A drop, a quiet break, a whispered or
  a rushed part show in these numbers with no lyrics at all.
- **The lyrics' notes, when there are any**: the lyrics editor keeps each section's bracketed notes word
  for word (`Section.notes`, `Instrumental.notes`); they are never sung, so no time changes.
- **The owner's feeling, when given**: a new optional field at creation, **Feeling** ("what should the
  viewer feel, and how should it change?"), next to the story. The story is what happens; the feeling is
  what it should do to the viewer. It is not required, and not per section: the planner maps it onto the
  song's parts.

The owner's feeling wins over the notes, the notes over the numbers. A song with none of them still has
its measured shape and its sung words.

Not chosen: a model that listens to the song. It would describe the music best, but hone-models has no
audio-understanding call yet; it can replace or join the measured shape later.

### 2. Feeling first (B, C)

- **The bible** gains `feeling` (what the whole video should make the viewer feel), `arc` (one entry per
  part of the song: `feel`, `intensity` 1–5, `turn` (what changed), `evidence` (what the viewer can see
  that makes them feel it)), and per character `presence` (what the viewer should feel about them, with
  the visible traits that make it so; the look carries those traits) and `inner` (what they feel, what
  they show, and how the feeling leaks).
- **The shot list** gains, per shot, `feel` and `evidence`; its rules say: the mood and the arc shape
  staging, performance, the actions chosen, the camera and the pacing, keeping the story's events; a
  hidden feeling shows both the surface and the leak; the danger or tension grows with the arc's
  intensity; a sung physical action of someone on screen is shown (C); the camera is chosen for the
  feeling (distance, height, obstruction, eyeline) and varied.
- **The scene writer** gets each shot's `feel`, `evidence`, its part of the arc and its characters'
  `presence` and `inner`, and writes the evidence as what bodies and faces do.
- **A review call** (F) reads the arc and the shot list and answers, per shot: is the feeling visible,
  does the shot contradict its lyric, does tension grow where the arc rises, are compositions and camera
  moves repeated. Its findings go back to the shot list as repairs, like the technical checks. It runs
  on `models.review` (Claude Haiku 5.5 by default: a check, not a planner). Code adds a camera check: no
  single move on more than 40% of the shots, never four in a row.

### 3. Opening, motion, ends (D)

A shot's `beat` is its **opening frame only**; `motion` is the one change during the clip; `ends` is what
the next shot inherits (where people are, what they hold, what changed). The scene prompt is written
from the beat, the motion prompt from `motion` and `camera`, and each shot's scene writer sees the
shot before's `ends`. `ends` is for continuity in planning only; no end frame is given to the video model.

### 4. References that match the shot (E)

- **Variants and states are complete descriptions**: a variant's `look` is the whole look in that state;
  a place state's `look` the whole place in that light. The prompt writers get it alone.
- **Poses**: a cast entry may give `pose` (`sitting`, `lying`, `kneeling`); the look's picture in that
  pose is made in words from the hero or variant (Hone Frame's guide, Poses) and the scene uses it.
- **Details**: a cast entry with `view: "detail"` and a `part` ("the snake on his left shoulder") gets a
  close detail picture made from the look, for inserts of that part.
- **Setups**: the shot list may declare `setups` (`id`, `layout`: who is where, by their own left and
  right, and against what); shots in a setup name it, the scene writer gets its layout, and a later shot
  in the same setup may be made from the first (`from_scene`).

### 5. Takes (the `takes` fix, and hard scenes overnight)

- The shot list's instructions explain `takes`: `one`; `count` (three draws of one prompt: the moment is
  clear, only the drawing may fail); `prompts` (two or three different shots of a hard moment: bodies in
  contact, a creature with a person, hands, an unusual angle, many people). `hard` is gone.
- **A take never waits for approval.** The first picture of a scene with takes is used at once, in an
  attended run too; the others are kept. Holds (the demo, the heroes) still wait in an attended run.
- **Every take gets its clip and its finish overnight** (since 0031 only with `take_clips: "all"`), after the takes in use. Choosing another take in
  the morning (the Scenes view) and pressing Remake reuses its clip: only the cut is made again.

### 6. The overnight queue

- **Prepare**: a project made with "Prepare only" (or asked to while it runs) stops before the first
  local stage (the scenes), with every hosted call done (lyrics, plan). Its status is `paused` and it
  shows as *prepared*.
- **Run all prepared**: one button runs every prepared project, oldest first, one after another,
  unattended from there (`approve: auto`). Nothing after the plan needs the internet.
- **The queue survives** a restart of the dashboard: it is kept in `<projects>/.queue.json`, and the
  project that was running when the dashboard stopped is resumed first.
- **A failed run is tried again**: the runner resumes a run that failed (not paused) at the end of the
  queue, at most twice, so one bad clip (ComfyUI interrupted, a crash) does not cost the night.

## Consequences

- Plans cost a little more (the arc and the review call, about two more calls) and are longer.
- New projects only: the records gain fields with defaults, so earlier projects read as before; their
  runs are not planned again.
- More GPU time for hard scenes overnight (about 3–4 minutes per extra take); in exchange a morning pick
  costs a cut, not a clip.
- The checks of a feeling are a model's judgement (the review call); its findings are repairs, never
  refusals, like the planner's other problems.
