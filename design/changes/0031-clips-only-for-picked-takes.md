# 0031: Clips only for the picked takes

## Status

`accepted (experimental)`, 2026-10-18, by the owner (asked for in the session that found it), for the
branch `exp/frame-scene-generation` only. Changes 0028 §5. Built.

## Context

0028 §5 makes a clip and a finished clip for every take of a scene with several, after the takes in use,
so that picking another take later only cuts the video again. On *Midnight Mambo Shoes* the planner gave
65 of 69 scenes takes (36 scenes three draws of one prompt, 29 two or three prompts): 107 more clips
than the 69 in use, about five hours of GPU time before the finishing stage, which finishes them too.
The owner stopped the run.

## Decision

- **A new setting `take_clips`**: `"picked"` (the default) makes a clip, and a finished clip, only for
  the take in use of each scene; `"all"` keeps 0028 §5 (every take overnight). A project stored without
  it reads `"picked"`, so a run resumed after this change makes no more clips of other takes. It does
  not reach the planner.
- **Picking another take makes its clip when it has none**: as before, the pick is followed by Remake
  (the Scenes or Clips view, or `hone-music-video remake`): the shot's start frame changed, so its clip
  and finished clip are made; a take whose clip was made already (a clip of the same picture, motion
  prompt and seed is kept, D-009) is reused and only the cut is made again.

## Consequences

- An unattended night makes the video from the takes in use; choosing another take in the morning costs
  its clip (about 2 to 4 minutes) unless it was made before.
- Guarantee 68 changes: a scene's takes never wait for a pick; with `take_clips: "all"` each take gets its
  clip and finished clip.
