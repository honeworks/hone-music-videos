# Prompt guide research, 2026-10-17/18: 100 hard cases on our still models

Branch `exp/frame-scene-generation`; harness in `research/prompt-guide/`, pictures in
`~/hone-research/prompt-guide-2026-10/` (live grid: `research/prompt-guide/gallery.py`, port 8795).

## Question

The scenes keep the look but lose the facts (counts, attachment, contact, gaze, sides, camera). Can the way
Opus writes subject and scene prompts, or a model setting we don't use, fix that, without judge calls after
generation?

## Setup

- **20 stories × 5 shots = 100 cases**, each a real project: a Bible and shot list in the planner's JSON,
  the real subject and scene calls, `frame_items.py`, `frame_toml.py`, the frame runner on
  `qwen-image-2.1-turbo`. Every case has a written checklist (415 checks) and tags: count, attach, contact,
  combat, gaze, mirror, scale, camera, sides, held, pose, dark, emotion, costume, literal.
- **Ideas.** I0 baseline · I1 facts first (Opus fills things+counts, links, visible, moment, avoid, then the
  prompt) · I2 I1 + an opening sentence written by code from the facts · I3 I1 + sides only as the
  picture's left/right and the key link inside the frame and lit · I4 I2 + the avoid list as a real negative
  (base Qwen, cfg 4, 30 steps) · I5 I2 at 16 steps · I6 an arrangement picture first, used as a reference ·
  I7 drawn from text, then `qwen-image-edit-2511` puts the identities in · I8 only the characters as
  references, the place in words · I9 I2 on `flux.2-klein-4b`.
- **Runs.** Pilot (4 stories, 20 cases): all ten ideas. Other 16 stories: I0, I2, I3, I8 (I1, I4–I7, I9
  dropped after the pilot for time or no gain). 840 pictures, none failed; ~7 h of GPU for the 16 stories.
- **Writers.** Pilot and part of the rest: Opus through the OpenAI-compatible gateway; 47 idea writes (balance ran out): clean
  Claude agents given only the same system prompt, data and schema.
- **Scoring.** Haiku 5.5 agents marked every check from contact sheets (research only, not a product
  judge). On the 15 cases I marked by hand it agreed on 83% of checks (it passes 59 checks I failed and
  fails 38 I passed), so differences under ~3 points are noise.

## Results

| Idea | Cases | Checks passed | Pictures fully right | Time a picture |
|---|---|---|---|---|
| I0 baseline | 100 | 75% | 32% | ~35–55 s |
| I2 facts + code opening | 100 | 77% | 32% | ~55 s |
| **I3 facts + frame sides + link lit** | 100 | **78%** | **37%** | ~55 s |
| **I8 characters only, place in words** | 100 | **78%** | 35% | ~50 s |
| Pilot only (20 cases; I0 there: 79%, 40%) | | | | |
| I4 negative, base model | 20 | 83% | 40% | ~240 s |
| I5 16 steps | 20 | 81% | 35% | ~90 s |
| I7 compose, then edit | 20 | 78% | 30% | ~275 s |
| I1 facts first | 20 | 77% | 25% | ~60 s |
| I6 arrangement picture | 13 | 78% | 23% | ~45 s |
| I9 klein | 20 | 73% | 15% | ~77 s |

Against the baseline, each prompt idea fixes 29–37 checks and breaks 22–25: a net gain of 2–3 points.
**No wording or setting is a breakthrough.**

By tag (I0 → I3 / I8): contact 69 → 77 / 77 · combat 69 → 74 / 81 · dark 83 → 92 / 75 · mirror 74 → 81 / 81 ·
pose 75 → 81 / 79 · sides 70 → 74 / 72 · count 76 → 80 / 78 · gaze 73 → 71 / **62** · emotion 70 → 68 / 70.

**51 checks (12%) fail under every idea.** They are of six kinds:
1. **A body's own side:** LEFT hand, RIGHT leg, eyepatch on the LEFT eye, sword in the LEFT hand only, ring
   on a LEFT hand (S014, S018, S023, S027, S033, S037, S041, S042, S051).
2. **Contact that needs a grip or a bite:** a horse biting a neck, a wolf's jaws on a leg, a thumb and finger
   holding a girl, a blade flat on a shoulder, a scalpel's handle into a palm, a rope ending at a saddle horn
   (S007, S029, S044, S046, S062, S088).
3. **Exact counts above three:** seven candles, twelve guests, five wolves, four hands, three fingers (S032,
   S050, S052, S086).
4. **Small marks on a face in a medium or wide shot:** a tear, a cut over an eyebrow, a swollen eye, a smile's
   reflection on a blade (S003, S014, S035, S078).
5. **Eyes meeting, or eyes on a small thing** (S001, S026).
6. **Movement states in a still:** a dive with wings folded, a sword passing through a wing, a girl sliding,
   strings hanging cut (S011, S015, S073, S085).

## Seen in the pictures (pilot, by hand)

- A creature's size comes from its reference; "several times larger" in the scene changes nothing.
- The place reference fixes the camera: straight-down shots keep the reference's angle unless the place is
  given in words (I7, I8, I9 look straight down; I0–I6 don't).
- Facts first makes attachment readable in close-ups (the snake grows out of the skin in I2/I3; the
  baseline drapes it).
- A loose extra copy appears when a part must be touched: a third snake in her hand instead of a hand on his.
- I4 made a knight bald; I6 put a horse on a sleeping man; I9 added a second horse and small figures.

## Conclusions

1. **Write the facts first, then the prompt (I3's form).** Small but steady gain, best on contact, darkness,
   mirrors and poses; no loss of look; no extra time.
2. **Give the place as a picture only when the camera is ordinary.** For an extreme camera (straight down,
   worm's-eye) and for two creatures fighting, the characters only, the place in words (I8: combat +12,
   camera fixed). Keep the place picture when eyelines matter (I8 gaze −11).
3. **Not worth it:** negatives (4–5× the time for a gain within noise), more steps, edit-after-compose,
   arrangement pictures, klein.
4. **The ceiling is the shot, not the prompt.** The six kinds above must be designed around in the shot list
   (and subject pictures), not written harder: a close-up of the one hand instead of "his LEFT hand"; the
   bite as the moment after (the dragon recoiling, a mark on its neck); counts of three or fewer, or a count
   that doesn't matter; a face mark only in a close-up; eyes meeting only in a two-shot at eye level;
   movement as its frozen position.
5. **Scale belongs in the creature's reference picture**, with a person or known object beside it.

## Limits of this research

One seed a case; one scorer (Haiku) for the totals; 80 of 100 cases on four ideas only; 47 of the idea
writes by agents, not the API. A confirmation run of the guideline through the real planner is still to do.
