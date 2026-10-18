# 0023: Shots planned within the limits, and a polish that fixes

## Status

`proposed` (2026-10-12), **experiments first**: nothing here is built until the experiments of §Experiments
have run and the owner has chosen from their results. The Decision below is the shape the owner asked for;
its open choices (marked **to measure**) are filled in from the results, then the record goes back to the
owner for acceptance. Builds on 0020 to 0022.

## Context

On *isolde-the-forgotten-wife* (67 shots, Qwen-Image-2.1 Turbo, 0021) the owner found two kinds of fault.

**Shots the models cannot make well.** S008 (Theron on his throne at the end of a hall, `wide`) and
S026 (Morvane riding at the head of his army, `extreme-wide`) put a named character far away: about 150 and
20 pixels tall in a 1024x576 frame. The planner followed the limits as written (§8.3, "Faces must be
large": both are `faces: false`, the character "a small figure, far away"); what the limits do not say is
that a small character also loses what makes them themselves: the face, and with it the costume and the
signature props (Morvane's snakes read as horns, Theron's crown changes shape). 16 of the 67 shots are
`wide` or `extreme-wide` with a cast. `limits.md` is also out of date for 0021 (six references, "three on
some image models"; Qwen-Image-2.1 Turbo takes six, up to ten).

The shot plan is one whole-song call (§7.1, rule 4): on this song 573 s and 0.95 USD for 67 shots, one
reply of every still and motion prompt. Its 24 warnings and the faults above did not trigger a repair
(no errors).

**A polish that harms.** The polish (§10.2) is Z-Image Turbo image-to-image at denoise 0.3 with no
reference pictures and the still prompt with each character's cue. It was chosen to give Qwen-Image-Edit
2511's renders a photographic finish. On Qwen-Image-2.1 Turbo's drafts, which are already photographic, it
mostly redraws what is small: S008's Theron gets another face and another crown; in S026 two soldiers get
Morvane's snakes (the prompt says "two snakes rising from his shoulders" and the polish cannot tell who).

What the owner wants of each:

- **The planner** knows the limits and plans within them, in its first call where it can; a cheaper model
  checking batches of about 10 shots is acceptable if the first call cannot. Planning in two steps (one
  call for the list of shots, then about 10 shots a call for their prompts) may follow the rules better
  than one reply of 67.
- **The polish** fixes what the draw gets wrong (a hand's shape, a wrong prop, an extra person) and brings
  the frame to the project's style and mood (realistic and dark, say), **with the shot's reference
  pictures**, so it changes no face and no asset.

## Problem

1. The limits do not tell the planner that a named character must be large enough to be recognised, and no
   check catches a shot that makes one small.
2. One reply of every shot is long and slow (9.5 minutes); whether its later shots follow the rules as well
   as its first is not known.
3. The polish has no references: it changes faces and props, and puts one character's traits on others.
4. Nothing fixes a draft's faults in place: §10.4 draws the frame again from a corrected prompt (another
   ~50 s and another composition), and only when `quality_check` and `still_retries` are on.

## Options

**For the planner**

- **Leave it as it is.** Faults like S008 and S026 stay; the owner redoes them by hand. Rejected by the
  owner.
- **A. The limits and free checks (smallest).** One new limit (a cast member's size), `limits.md` brought
  up to date, and `check_shots` rules for what code can see; a broken rule goes back through the existing
  repair (§7.4), so a plan that follows the rules costs no extra call.
- **B. A plus planning in two steps.** One whole-song call returns the outline (every shot's times, lines,
  beat, framing, cast, props, location, camera); then calls of about 10 shots each write their still and
  motion prompts, each seeing the whole outline, the cast and the end of the batch before it. Changes rule
  4 and §7.1.
- **C. A plus a cheap checker.** Claude Haiku 5.5 reads about 10 finished shots a call against the limits
  and flags what code cannot see; flagged shots go to the repair. Not pursued: an extra call on every
  plan for what the code rules of A already see.

**For the polish**

- **Leave it as it is** (Z-Image, no references). Rejected: it harms the frames it should improve.
- **No polish** for Qwen-Image-2.1 Turbo drafts. Smallest; keeps the faults the draw makes.
- **D. An edit model with the references (chosen shape).** The draft is image 1, the shot's references
  follow; a short prompt keeps the picture, sets the style and mood, and names the fixes the start-frame
  check found for that frame.
- *Image-to-image at twice the size, faces pasted back* (discussed 2026-10-11): keeps faces but cannot
  fix a prop or a hand, and knows no reference. Not pursued.

## Decision (the shape; the open choices are measured first)

### 1. The planner plans within the limits

- `limits.md` (§8) gets a rule with its reason, its wording **to measure** (P1). A cast member may be
  small only when their face is not visible (the owner, 2026-10-12):
  > A character in `cast` whose face can be seen fills at least about a third of the frame's height, even
  > in a wide shot: put them in the foreground with the place and the crowd behind. A cast member who is
  > small in the frame is seen from behind, in silhouette or turned away: at that size the image model
  > cannot draw their face.
- `limits.md` states the reference budget of the project's scene model (from its entry, not a fixed
  number), and the video model's size.
- `check_shots` gets rules for what code can see, each an error (so the repair runs) or a warning, **to
  measure** (P1): a cast member in a `wide` or `extreme-wide` shot whose still prompt does not say they
  are seen from behind, in silhouette or turned away; a placeholder next to "far away", "in the
  distance", "small figure", "tiny" without those words; more than two cast members in contact poses
  (the words of §8.2).
- Two-step planning (B) is adopted **only if** P2 shows it follows the rules clearly better than A alone
  (at least half the violations A leaves) at an acceptable cost; then rule 4 and §7.1 change, with the
  batches run in parallel. The cheap checker (C) is not measured: the code rules cover what it would.

### 2. The polish fixes, with the references

- `models.polish` becomes an edit entry that takes references, **to measure** (F1):
  `qwen-image-edit-2511-4step` (an edit model; three slots, so the draft and two references) or
  `qwen-image-2.1-turbo` (six slots; draws a new picture from its references, may recompose).
- Its inputs: the draft as image 1, then the references the draft was drawn from, within the model's
  budget (§10.1's order).
- Its prompt is short, **length and wording to measure** (F2, F3):
  1. the keep line: "The same picture as image 1: the same composition, the same people, each with the face
     and costume of their reference";
  2. the style line, from `settings.style` and `settings.mood`;
  3. the fixes: one to three concrete edits for this frame, phrased positively ("Redraw the king's right
     hand with five fingers on the armrest", "Only the rider has snakes on his shoulders").
- The fixes come from the start-frame check (§10.3), which already looks at every draft in one call and
  flags `anatomy`, `wrong-prop`, `extra-people` with their evidence: its reply gains an `edit` per flagged
  frame. A frame without flags, or a project with `quality_check` off, is polished with lines 1 and 2 only.
- Every frame is polished (left to the agent by the owner, 2026-10-12): the keep and style lines give the
  whole video one look; only flagged frames get fixes. If F1 shows the style pass alone changes nothing
  worth its time, only flagged frames are polished.
- A frame from text with no cast (no references) is polished with lines 1 and 2.
- Whether §10.4 (drawing again) stays for what an edit cannot fix (a wrong composition, a missing
  character), or the edit replaces it: **to measure** (F2).

### What stays

The draw, the clips, the finishing, the gates. Projects stored before keep their polish model and their
plan's form (their stored settings); a new limit text changes only new plans.

## Experiments

All in `experiments/0023-*` (ignored, never committed), on *isolde-the-forgotten-wife*: its cast, packs,
timeline and 67 drafts. GPU work only under `scripts/gpu-lock.sh`, models unloaded after. Hosted calls are
recorded by hone-models as in a run.

**Budget: at most 3 USD of hosted calls** (the owner, 2026-10-12): P1 one Opus re-plan (about 0.95 USD,
this song's measured cost); the polish two Sonnet calls (about 0.35 USD); P2 about 1 to 1.5 USD, run only
if P1 leaves faults and the owner agrees. Everything else runs on the GPU.

### Planner

**P1. The limits and free checks (A).** Plan the song again once, with the new limit and up-to-date
`limits.md`; today's plan (`current/shots.json`, made with today's prompt) is the baseline, at no cost.
- Measure per plan: shots with a cast member that is small (by the candidate code rules, and by the owner's
  reading of the prompts); `check_shots` errors and warnings; time and cost.
- Each candidate code rule: how many shots it flags, how many of those the owner agrees with (a rule with
  many false alarms becomes a warning or is dropped).

**P2. Two steps (B) against one (A).** Only if P1 leaves faults, and after asking the owner. The same
inputs: one outline call, then batches of 10, in parallel.
- Measure: the violations of P1 in each plan, **by position** (first, middle, last third of the song: does
  one reply get worse towards its end?); continuity across batch borders (costume, time of day, a prop
  carried over; the owner reads the shots at each border); the wall time (one 9.5-minute call against an
  outline and parallel batches) and the cost.

### Polish

Frames: S008, S026, and about eight more chosen from a contact sheet of the 67 drafts: medium and close
shots with faces, two with more than one character, and frames with visible faults (a hand, a prop, an
extra person). One Claude Sonnet 5.5 check of those ten drafts (§10.3, about 0.10 USD) gives the flags,
the evidence and the edit instructions of F2.

**F0. Baselines:** the draft (no polish) and today's Z-Image polish, for every frame.

**F1. The model.** `qwen-image-edit-2511-4step` (draft + two references) and `qwen-image-2.1-turbo`
(draft + up to five references, read at 768), each with the keep and style lines only.

**F2. The fixes.** For each model of F1: keep and style lines plus the check's fixes (at most three edits
a frame, from the drafts' check above).

**F3. The prompt's length.** On three frames with known fixes: the same fixes inside prompts of about
60, 120 and 250 words, and as a long rule list ("fix any bad hands, remove extra people, correct the
props, …"). Where does the model stop following?

Measured for every frame and case:

| What | How |
|---|---|
| The composition kept | the draft and the polish compared at low resolution (structural similarity), and by eye |
| The faces kept | face similarity (ArcFace, InsightFace on the CPU, experiment only) of each cast face to the character's portrait, draft against polish |
| The fixes made | one start-frame check over every polished frame of every case together (about 0.25 USD): the flags resolved, the flags new |
| The style | the owner's verdict on one contact sheet per frame (draft, Z-Image, each case side by side) |
| The cost | seconds per frame, GPU peak memory |

**F4. Does it carry into the clip?** For the best case only, one clip each of S008 and one medium shot
from the draft and from the polish (about 5 minutes of GPU each): does Wan keep what the polish gained?

### What decides

- Planner: A alone if it removes most small-cast shots with a visible face and P2 does not halve what
  remains; B if it does, and its border continuity holds.
- Polish: the case that keeps the composition, keeps or raises face similarity against the draft, resolves
  most major flags and adds none, and costs at most about 60 s a frame. If neither model keeps the
  composition, the polish is turned off for Qwen-Image-2.1 Turbo drafts instead.

The results go into this record (a table per experiment), then the Decision is completed and the
acceptance cases fixed.

## Acceptance cases (§14; draft, fixed after the experiments)

41. The shot planner's prompt has the cast-size limit and the scene model's reference budget from its
    registry entry.
42. `check_shots` reports the chosen small-cast rules, each with shot, rule and words; a plan that breaks
    one as an error goes through the repair (§7.4).
43. The polish of a frame with a cast sends the draft as image 1 and the shot's references after it,
    within the polish model's budget; its prompt has the keep line, the style line and at most three fixes.
44. The start-frame check's reply carries an `edit` for each flagged frame; the polish of that frame uses it;
    a frame without flags, or a project with `quality_check` off, is polished without fixes.
45. A project stored before 0023 keeps its polish model and its plan's form; its keys do not change.
46. (If B) the outline is one call for the whole song; each batch call sees the whole outline; a batch's
    invalid reply is retried alone; the joined plan tiles the song as one call's would.

Tests: unit tests of the prompt text, the code rules and the polish's inputs; e2e with `FakeModels` for
42 to 46 (`test_ac42_small_cast.py`, `test_ac43_polish_refs.py`); one real-model test of the polish
(`tests/gpu`, marker `gpu`) on two committed small frames, if their size allows.

## Consequences

- Wide shots with a named character become fewer, or bring the character to the foreground: a change of
  look the owner accepts for recognisable characters.
- The polish costs about as much as a draw (about 50 s against 17 to 26 s), roughly 30 to 40 more minutes
  of GPU for a 67-shot video; the drafts' check (one hosted call, about 0.25 USD) becomes useful even
  without retries.
- (If B) the shot plan becomes several calls; its wall time should drop (parallel batches), its cost may
  rise.

## Migration and compatibility

- Stored formats: the check's `edit` is new optional data; `format_version` stays `"1"`. Old projects
  read their stored `models.polish` and plan as before.
- No new dependency in the library. InsightFace is used by the experiments only.
- Crash halfway: the polish is a kept version as today (D-009); a batch of B is kept as a version when it
  returns, so a resume asks only for the batches missing.
- Two processes: nothing new is written outside a run's stages.
- Smaller option: P1's limit and checks alone, and no polish, are measured as the baseline every larger
  option must beat.

## Answered

1. A cast member may be small only when their face is not visible: from behind, in silhouette or turned
   away (the owner, 2026-10-12).
2. Every frame is polished; only flagged frames get fixes (left to the agent, 2026-10-12; §2).
3. The experiments' hosted calls stay under 3 USD; P2 only with the owner's agreement (the owner,
   2026-10-12).
