# 0034: Scene references designed for an edit model

## Status

`proposed`, 2026-10-19, after the overnight batch of 2026-10-19 (twelve projects, about 900 scene
pictures) and a reading of how ComfyUI's Qwen-Image 2.1 encoder uses reference pictures. Its smaller
choices will be D-180 onwards. Every part is measured on the harness of 0029
(`research/prompt-guide/`, 100 cases, the same seeds) before it ships; a part that gains nothing is
dropped from this record and the reason kept.

## Context

0027 made Hone Frame the only scene pipeline: every scene is drawn by `qwen-image-2.1-turbo` from
reference pictures (the characters' views, the place's view, the objects' heroes) and a prompt that names
each picture by its number. 0029 asked what the planner should *write* so the still model keeps the
facts, and measured the answer: the best wording moved the facts kept from 75% to 78% of the checks, and
six kinds of fact failed under every wording. Its conclusion was "the ceiling is the shot, not the
prompt". It did not say why the ceiling is where it is.

**How the model reads a scene.** ComfyUI's `TextEncodeQwenImage21` node (upstream, commit 6bfaacc6)
wraps the prompt as `<image1>[picture] <image2>[picture] … <prompt>` under the system line "Comprehend
and analyze the provided prompt", drops the vision tokens and splices each reference's VAE latent into
the DiT's sequence. ComfyUI's tutorial for the model says it plainly: *image_1 is the image being
edited, the rest supply content*, and the canvas should stay close to image_1's size. Qwen's own README
composes several subjects without numbering them at all ("These three characters are sitting around a
campfire").

**What we give it.** Every scene's image 1 is a character's hero or view: a full figure in a neutral
pose on a mid-grey backdrop (Hone Frame's guide, Hero), 832x1248, read at about 624x928 on a 1664x928
canvas. The model edits a studio portrait into a landscape. What the batch's pictures show follows from
that:

- *Rostam's Death (Sol)*, S002: the prompt asked for "both complete figures small beneath weathered
  blue-grey mountains"; the picture has two large figures filling the frame, in the heroes' stance.
- *Dancing with a Ghost*, the storyboard of 63 scenes: calm, posed, centred figures, the same medium
  two-shot in the same ballroom, shot after shot. The prompts were right; the pictures are the references
  with a room behind them.
- The frames made **without** references (the inserts, *Toos View* S002, the demo) are the most filmic of
  the batch: the text-to-image path is not fighting a picture.
- Faces are calm because every close reference is calm. The scene prompts describe what the face does, as
  0028 asked, but a picture outweighs the words (Hone Frame's guide, "A picture outweighs the words"; D-146).

The planner's writers never see the pictures, so the scene prompt says what to *keep* from image 1 and
never what must change (the backdrop, the stance). `setups` and `from_scene` (0027, 0028) exist but are
seldom used, so coverage of one arrangement is re-drawn from the studio references each time instead of
from one master scene.

Two things about the batch's prompts themselves, found on the way: six of the twelve plans
(kalat-mountain-story, my-bloody-story, stay-on-the-gate, zahaak; toos-view from the shot list;
make-me-a-small-cup's subjects and scenes) were written by Claude Code subagents through the batch's
`bridge.py`, not by the API, and their call files say `claude-opus-5-5`; and four hero prompts stayed over
1500 characters after the one repair and were installed as they were. Neither changes the picture, both
matter when prompts are compared.

## Problem

1. A scene inherits the stance, scale, framing and calm of its image 1, which is a studio figure; the
   words cannot move it (0029's ceiling).
2. A wide shot whose faces cannot be recognised still carries two or three studio references it cannot
   use, and pays for them in time and in pasted figures.
3. A face shot gets a neutral close-up, so the feeling 0028 plans for the face is written but not drawn.
4. Shots that share an arrangement are drawn from scratch each time: no continuity, no variety of
   coverage, three references every time.
5. Small gaps in the rules: the guide's examples open with "Photorealistic", which the code then bans;
   the demo prompts may carry an aspect ratio ("In a 16:9 full-length costume study"), which no check
   catches; a subject prompt over the limit is installed after one failed repair.

## Options

1. **Leave it as it is, and keep tuning the words.** 0029 measured this: two to three points per idea,
   each idea fixing about thirty checks and breaking about twenty-five. Rejected: the ceiling is not the
   words.
2. **Change the model or its settings**: the base model with a negative and cfg 4, more steps, an edit
   step after composing, Flux Klein. All measured in 0029 at four to five times the time for a gain within
   noise. Rejected.
3. **A judge call per picture, with retries.** Ruled out by the owner in 0029 ("without judge calls after
   generation"); 0027 removed the judges and retries for a reason. Rejected.
4. **Design the references and the coverage for an edit model, and measure each part.** The place as
   image 1; no character pictures where no face is recognised; expression close-ups for face shots; one
   master scene per arrangement; the rule gaps closed. Chosen.

## Decision

### 1. The place is image 1

A scene's references are, in order: **the place's view, then the characters, then the objects**
(`frame_items.scene_refs`). The place view is already made at the scene's size, so the canvas matches the
picture being edited. The scene prompt names them in that order: "In the ballroom from image 1, the woman
from image 2 stands at the table …". The scene call's instructions (`frame_scenes.md`) say so, and add
one rule the writers lacked: **say what changes from the pictures**, since an edit model keeps everything
left unsaid: the backdrop is gone, the figure's stance is the beat's, the figure's size in the frame.

Unchanged: a `place_in_words` scene (0029 §3) still has only its characters; a `from_scene` scene still
has that scene alone; the objects past the limit are still words. The limit of four pictures stays. The
facts' `image` numbers follow the new order.

### 2. A wide shot without faces takes no character picture

When a shot's `faces` is false and its framing is `wide` or `extreme-wide`, its scene takes **the place
picture only** (and its objects, within the limit). Its people reach the scene call in `in_words`, each
with its noun and look, and the writer names the one or two large things that keep them recognisable at
that distance (0028: "a rich costume with one or two things of its own keeps a character recognisable in
a wide shot"), as the Scenes guide already asks for a figure in the background. A shot that needs the
exact look at that distance is a shot the list plans closer.

The shot list's instructions say it, so the planner knows a wide shot costs no character pictures; the
sidecar's `cast` still names who is in the frame.

### 3. Expression close-ups

The bible gives every character up to **three `expressions`** (`id`, `face`: what the face does, as the
Faces guide writes it: eyes, brows, mouth held, jaw), chosen from the character's `inner` and the arc;
none for a character the story never sees close. Code makes an item `<character>.close-<id>` (and
`<character>.<variant>-close-<id>`) for each expression a shot uses, from the look's **neutral close-up**
(refs `[<look>.close]`, square, as the Faces guide asks: "make the expression from the neutral close-up,
not from the full figure"). The subject call writes its prompt like any close-up.

A shot's `cast` entry gains `expression` (one of the character's expressions, only with `view: "close"`;
`""` for the neutral face). A face shot with an expression takes that picture as its reference; its
facts and prompt still describe the face, so the words and the picture agree. An expression the bible does
not have is a shot problem sent back; an expression no shot uses makes no item.

### 4. One master per setup

Every `setup` the shot list declares has a **master**: its first shot shows the whole arrangement in a
`wide` or `medium` framing (code checks it; a setup whose first shot is closer is a shot problem). The
shot-list instructions ask that a later shot of the setup whose camera stays on the master's side be made
`from_scene` the master, and the review call reads the setups for it (one more thing in its list, 0028
§2). A `from_scene` scene is drawn from one picture that already has the room, the people and the light,
so coverage of an arrangement keeps its continuity and costs one reference.

### 5. The rule gaps

- The scene and subject calls are told that the guide's examples predate the rule on words of a render:
  the guide stays word for word (0026), the instruction says "where an example writes
  'Photorealistic', write the project's `kind`".
- `bible_problems` refuses a `kind`, `finish` or demo prompt that names a size or an aspect ratio
  (`16:9`, `9:16`, `1:1`, `4:5`, `1664x928`, "aspect ratio"); `prompt_problems` does the same for every
  prompt.
- A subject prompt is repaired twice, like the shot list (`SHOT_REPAIRS`), before what is left is kept.

### 6. What is not changed

The model and its settings (8 steps, cfg 1, no negative, `ref_resolution` 768); the four-picture limit;
the facts-first form of 0029; the neutral heroes on the grey backdrop, which the guide wants neutral so
that nothing of them is copied into every scene. The naming of pictures ("image 1" against the encoder's
`<image1>` tag) is measured in the Verification and changed only in the prompt text if it gains.

## Verification

On the harness of 0029 (`research/prompt-guide/`: 20 stories, 100 cases, 415 checks, one seed a case,
Haiku scoring, noise about three points), each part as an idea against I3 (78% of checks, 37% of pictures
fully right):

| Idea | What changes | Ships when |
|---|---|---|
| J1 place first (§1) | the reference order and the prompt's order; no new pictures | facts ≥ I3 and the `camera`, `scale` and `pose` tags gain, or the pictures are plainly less posed by hand |
| J2 wide without faces (§2) | the wide, faceless cases lose their character pictures | those cases gain, and no face is wrong where none was wanted |
| J3 expressions (§3) | the face-shot cases take an expression close-up | the `emotion` tag gains (70% under I3; the one tag every idea of 0029 left flat) |
| J4 `<image1>` tags | the pilot's 20 cases, wording only | gains outside noise; else "image 1" stays |
| J5 what changes from image 1 | the pilot's 20 cases, wording only | gains outside noise; else the rule is kept as advice only |

§4 is not a picture experiment: it is checked on the shot lists of the twelve batch projects (how many
setups get a master and a `from_scene` child after the instruction) and by eye on one re-planned project.
§5 is unit tests.

Then one real project re-planned and run end to end (*Dancing with a Ghost*, whose storyboard shows the
problem), its storyboard beside the old one.

### Guarantees (new acceptance cases, after 73 in `design/current.md` §14)

74. A scene's references are its place's view first, then its characters, then its objects, and its
    prompt names each by its number in that order; a `place_in_words` scene has only its characters, a
    `from_scene` scene only that scene.
75. A `wide` or `extreme-wide` shot with `faces: false` takes no character picture: its people reach the
    scene call as words, and its prompt names no picture it does not have.
76. A character's expressions in the bible become close-ups made from its neutral close-up, one item per
    expression a shot uses; a face shot with an `expression` takes that picture; an expression the bible
    lacks is a shot problem sent back.
77. The first shot of every setup shows the whole arrangement in a `wide` or `medium` framing, or the
    shot list is sent back.
78. A `kind`, `finish`, demo prompt or any prompt that names a size or an aspect ratio is sent back; a
    subject prompt is repaired twice before what is left is kept.

### Tests

- `tests/test_frame_items.py`: the reference order (74), the wide rule with and without objects and with
  `place_in_words` (75), the expression items and their refs (76).
- `tests/test_frame_prompts.py`: `_shot_data` puts the wide shot's people in `in_words` (75); the facts'
  image numbers follow the order (74); the fallback scene names the place as image 1.
- `tests/test_frame_plan.py`: `shot_problems` on a setup without a master (77) and on an expression the
  bible lacks (76); `bible_problems` and `prompt_problems` on size words (78); two subject repairs (78).
- `tests/frame/`: nothing; the project file stays a Hone Frame file (an expression close-up is an item
  with one ref).
- The harness results go to `design/research/scene-references-2026-10.md` with the pictures' folder.

## Consequences

- **Fewer references per scene** (a wide shot: one; a setup's coverage: one), so scenes are faster.
- **A few more assets**: up to three close-ups per character seen close, about thirty seconds each; a
  five-character story adds at most fifteen pictures.
- **A re-plan calls everything again**: the system prompts change, so the kept replies' keys change. A
  project planned before 0034 keeps its plan until the owner re-plans.
- The Scenes view, the sidecar, the clips and the dashboard do not change: an expression close-up is an
  item like any other, and `shots.json` keeps naming the cast by id.
- The guide copy of 0026 stays word for word; only the planner's own instructions change.
- For comparisons of prompt quality, the batch's tooling should pass a distinct model id when a
  subagent answers a call, so the Calls panel tells the writers apart; that is session tooling, not this
  library.

## Migration and compatibility

- **Stored formats:** `FrameCharacter.expressions` and `CastUse.expression` are optional with empty
  defaults, so every kept reply (`frame/calls/*.json`) and every `plan.json` written before 0034 still
  validates; `shots.json` does not change. No deprecation.
- **Project files:** a file written before 0034 opens and runs as it is; the new order and items appear
  only when the plan is made again.
- **Dependencies, extras, secrets:** none.
- **A crash halfway, two processes:** the planner writes only its kept replies and the plan, as in 0027;
  nothing new is written during a run.
- **The smaller option:** §1 and §2 alone change two functions and one instruction file and need no new
  pictures; they go first, and §3 and §4 follow only if the harness shows §1 and §2 were not enough on
  the `emotion` tag and on coverage.

## Open questions for the owner

1. Three expressions per character, or more for the lead? Each is a picture before the scenes and an
   item in the Scenes view.
2. Should a wide shot that needs the exact costume (a recognisable silhouette, a creature) be able to
   keep one character picture (`refs_in_wide: true` on the shot), or is "plan it closer" enough?
3. May the harness run on the GPU between the batch's videos, under `scripts/gpu-lock.sh`? About seven
   hours for the 100 cases on J1 and J2 together.
