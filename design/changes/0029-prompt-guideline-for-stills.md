# 0029: A prompt guideline for the still models, from 100 hard cases

## Status

`accepted (experimental)`, 2026-10-18, by the owner, for the branch `exp/frame-scene-generation` only.
Evidence: [design/research/prompt-guide-2026-10.md](../research/prompt-guide-2026-10.md) (100 cases, 840
pictures). Built: §1 to §4 (`frame_prompts`, `frame_items`, `shots_check.model_limits`, `frame_review`,
the prompts); the hosted confirmation run of the Verification is still to do. Smaller choices: D-177.

## Context

The scenes keep the look but lose the facts. The owner asked what the planner should write so the still
models get hard scenes right, without judge calls after generation, and with simpler shots only where
nothing else works. The research found that prompt wording gains a little (75% → 78% of checks), that the
place picture decides the camera, and that six kinds of fact fail under every idea and every model. Those
must be avoided when the shot is planned.

## Decision

### 1. Scene prompts: facts first (`frame_scenes.md`, the scene reply)

Each scene in the reply gets a `facts` object before its prompt. It is not sent to the image model:
- `things`: everyone and every countable thing, each with its count and the image that shows it;
- `links`: each relationship the beat depends on, in one sentence, naming both ends the same way every time;
- `visible`: what the camera must show for the links to read;
- `moment`: the one frozen instant.

The prompt is written from the facts, in this order: the kind; the things with their counts and the links;
framing and camera; faces and bodies; light; the finish last and short. Sides are named only as the
picture's left or right; a body's own side only together with the picture's side. Every link is inside
the frame and lit. A movement is written as its frozen position. A feeling is never a size word.

`check_scenes` gains: a `things` count above three warns; a link's two ends are named in the prompt.

### 2. Shot list: design around what the models can't draw (`frame_shots.md`, `limits.md`)

The shot-list call gets the six limits as rules, each with what to plan instead:
1. A body's own side (LEFT hand, RIGHT leg) → a close-up of that one hand or leg, or no side at all.
2. A grip or a bite between two bodies → the moment just before or after (the recoil, the mark), or a
   close-up of only the touching parts.
3. More than three of a kind that must be counted → three or fewer, or a number that doesn't matter.
4. A tear, a cut or a swollen eye → only in a close-up of the face.
5. Eyes meeting → a two-shot at eye level; eyes on a small thing → the thing large in the frame.
6. A movement state (diving, sliding, passing through) → its frozen position.

The review call (0028 §2) checks the shot list against these rules too. The shot-list check (§5.2) warns on
the words it can find (LEFT/RIGHT with a body part; a count word above three in a beat).

### 3. References: the place picture only for an ordinary camera (`frame_items.scene_refs`)

A shot whose camera is overhead, straight down or worm's-eye, or whose beat sets two creatures against each
other, gets only its characters as references. The scene call then gets the place's words
(`place_in_words`) to write into the prompt. Every other shot keeps today's references.

### 4. Subject pictures: a creature's size is in its reference (`frame_assets.md`)

A creature or giant much larger or smaller than a person is drawn with a person or a known object beside it
for scale. A scene can't change the size its reference shows.

### 5. Kept as it is

The Turbo model at 8 steps and cfg 1, with no negative prompt and no edit step after composing. Klein is not
used for scenes. The research found no gain worth their time.

## Consequences

- One more field per scene in the planner's reply: longer replies, same number of calls.
- Fewer impossible shots reach the GPU; some beats are planned as two shots or as a close-up.
- Already fixed during the research (commit df29d3c): "image 2, 24mm lens" was read as image 24.

## Verification

- Default suite: the new reply field, the checks of §1 and §2, the reference choice of §3.
- One real run through the planner on the OpenAI-compatible gateway: the 20 pilot cases with the new prompts, scored with the same
  checklists. The rules are kept if facts pass at least as often as I3 did (78%). The shots the new rules
  re-plan are scored as new shots.
