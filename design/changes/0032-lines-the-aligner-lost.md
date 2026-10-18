# 0032: Lines the aligner lost are timed from the heard words

## Status

`accepted (experimental)`, 2026-10-18, by the owner ("fix the lyrics timing issue with best options you
pick"), for the branch `exp/frame-scene-generation` only. Changes 0005 (the aligned words win) and 0030 §3.
Built.

## Context

On *Midnight Mambo Shoes* the forced aligner put the outro's first lines inside the 60 s guitar and violin
solo: "I can't fight it." 31.8 s and "No, I can't lose." 32.9 s before they are sung, "In these midnight
mambo shoes." 5.9 s, with scores of 0.11, 0.14 and 0.22. Recognition heard all three where they are sung.
The code named the three lines (`align-disagrees`, `align-unsure`) but kept the aligned times, and an
unattended project passes warnings: the lyrics editor ended the solo 31 s early, one line spanned 30 s,
and the planner timed eleven scenes against lines that are not sung there.

0030 §3 moves only a line whose first word was stretched into the pause; a whole line in the wrong place
stays. Lines 1 to 29 of the song agree with recognition within 100 ms (one within 1.1 s), so the aligner
is right almost everywhere and the heard words are right where it is lost.

## Decision

1. **A line the aligner lost is timed from its heard words.** When an aligned line's start is more than
   `DISAGREE_MS` (750 ms) from where recognition heard it **and** its score is under `UNSURE` (0.3), its
   aligned words are placed over the heard words it was found in: the same words, their lengths in the
   same proportions, from the first heard word's start to the last one's end. A line placed with a good
   score keeps its aligned times (recognition can be the wrong one: *Isolde (feeling)*, L014). A move
   that would put the line over a neighbouring line is not made. The move is kept in `aligned.moved`
   (`whole: true`) and the check warns `timed-from-heard`.
2. **A disagreement over `FAR_MS` (3 s) that is left is an error.** `align-disagrees` stays a warning up
   to 3 s apart; beyond it the lyrics check reports an error, so an unattended project stops at the
   lyrics gate instead of planning on wrong times (an error is never auto-approved, D-076). The owner
   sets the line's times in the Lyrics view (0018) or approves accepting the error.

The windowed alignment (aligning each section only around where it was heard) would be more exact, but
needs the aligner to run per slice; it is not done here.

## Consequences

- *Midnight Mambo Shoes*' outro is timed where it is sung; the solo ends at 3:36.
- A run whose lyrics are already approved keeps its timeline: the change applies to a new transcribe.
- `Moved` gains `whole` (default `false`, so stored records read as before).
