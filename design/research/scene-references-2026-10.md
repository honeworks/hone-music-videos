# Scene references for an edit model, 2026-10-31: 0034 measured

Change [0034](../changes/0034-scene-references-for-an-edit-model.md) on the harness of 0029
([prompt-guide-2026-10.md](prompt-guide-2026-10.md)): the same 20 stories, 100 hard cases, 415 checks,
one seed a case. The study, its harness, the replies and every score are in the private research
repository (`hone-research/studies/0015-scene-references-edit-model/`); the pictures are in
`~/hone-research/prompt-guide-2026-10/`.

## Question

Qwen-Image 2.1 edits its first reference picture and takes the others as content. Before 0034 every
scene's image 1 was a character on a grey studio backdrop. Does giving the model the place first, and
fewer or different character pictures, make scenes that keep the facts and look less posed?

## Setup

- **Arms**, each a scene item with the shot's seed, all on `qwen-image-2.1-turbo`:
  - `c`: the control, the product before 0034 (`main`): the characters, then the place, then the
    objects; `main`'s scene instructions.
  - `j`: 0034 as built: J1 (the place first), J2 (a wide shot without faces has its people in words,
    no character picture) and J5 (the rule "say what changes from the pictures").
  - `j5x`: `j` without the J5 paragraph (the pilot's 20 cases).
  - `j4`: `j`'s prompts with the encoder's tags, `<image1>` for "image 1" (the pilot).
  - `j3`: `j` with J3's expression close-ups on the 17 face shots whose checks hold a feeling.
  - `k`: J1 without J2: the place first and the character pictures kept, on J2's 22 wide cases.
- **Writers.** The scene calls were the product's own (system prompt, data, schema), answered by clean
  Claude agents, one request each (the gateway's credit was spent); the control was written by the same
  writers, so the writer is not a difference between the arms.
- **Scoring.** Haiku 5.5 agents scored every check from contact sheets with the arms **shuffled under
  letters** (blind), plus a `posed` mark: a figure that looks pasted in from a studio reference (stiff,
  square to the camera, wrong size for the place, lit apart from it, or on a grey backdrop). On 0029's
  hand check Haiku agreed on 83% of checks, so differences under about 3 points are noise.
- **Runs.** About 400 pictures, ~55 s each, none failed.

## Results

| Arm | Cases | Checks passed | Pictures fully right | Posed |
|---|---|---|---|---|
| `c` control | 100 | 76% | 32% | 22% |
| `j` 0034 as built | 100 | 75% | 34% | 20% |

The total hides two parts that pull apart:

| Where | Arm | Cases | Checks passed | Fully right | Posed |
|---|---|---|---|---|---|
| Every case but J2's (J1 + J5) | `c` | 78 | 75% | 27% | 23% |
| | `j` | 78 | 77% | **38%** | 23% |
| J2's wide shots without faces | `c` | 22 | 82% | 50% | 27% |
| | `j` | 22 | **68%** | **23%** | 5% |

The same 22 cases scored again in a round of their own, blind, `c`, `j` and `k` on one sheet each:

| J2's 22 cases, second round | Checks passed | Fully right | Posed |
|---|---|---|---|
| `c` control | 74% | 4 | 7 |
| `j` people in words | 66% | 3 | 1 |
| `k` the place first, the characters kept | 74% | **7** | 5 |

The control scored 82% in the first round and 74% in the second on the same pictures: on 22 cases one
scorer's rounds differ by up to eight points, so only differences inside one round are compared.

On the 78 cases J1 changes, the tags gain: pose +5, scale +6, gaze +14, costume +6; camera −1.

| Pilot (20 cases) | Checks passed | Fully right | Posed |
|---|---|---|---|
| `j` | 78% | 30% | 15% |
| `j5x` (no J5 paragraph) | 78% | 20% | 40% |
| `j4` (`<image1>` tags) | 78% | 30% | 20% |

| J3's 17 face cases | Checks passed | Fully right | Checks on the cases tagged `emotion` |
|---|---|---|---|
| `c` | 65% | 3 | 70% |
| `j` | 73% | 4 | 72% |
| `j3` (expression close-up) | 66% | 2 | 70% |

J3's close-up reference broke the scale and the camera (attach 38%, camera 25%, scale 47% on its cases)
and the feeling did not gain.

## Conclusions

1. **J1 ships: the place is image 1.** About four pictures in ten fully right instead of one in four on
   the cases it changes, the facts no worse, scale and pose better.
2. **J5 ships: "say what changes from the pictures".** Without it the facts are the same and posed
   figures nearly triple.
3. **J2 is dropped.** A wide shot without faces keeps its characters' pictures, behind the place: in words
   the people lose the facts (82% to 68% of checks, half the pictures fully right to a quarter), although
   they look less posed. With the place first and the characters kept (`k`) the facts
   are the control's and more pictures are fully right, so the place leads every scene.
4. **J3 is dropped.** An expression close-up as a face shot's reference loses the facts and does not
   carry the feeling better; the face is written in the prompt as before.
5. **J4 is not taken.** The encoder's tags are no better than "image 1".
6. **The ceiling is still the shot.** Checks passed stay between 75% and 78% under every arm, as in 0029:
   a body's own side, a grip, counts above three. What a shot plans decides more than what a scene
   writes; that is the next change.

## §4, the setups, on the batch's shot lists

The ten batch projects' shot lists made again with 0034's instructions (their kept bibles, the same
timelines; the shot list, the review and its repair answered by agents, the review on Haiku):

| | Before 0034 | After |
|---|---|---|
| Setups opening on a wide or medium master | 23 of 26 | 24 of 24 |
| Later shots of a setup made `from_scene` | 4 (3%) | 17 (15%) |
| Wide shots without faces whose `cast` is empty | 61 of 159 (38%) | 111 of 145 (77%) |

The last row is a fault of 0034's wording: "gets no picture of its people" was read as "lists no
people", and the review (which could not see `from_scene` either) asked for the people back with poses.
Both are fixed (D-182).

## Limits

One seed a case; one scorer kind; J3, J4, J5 and `k` on 17 to 22 cases each; agents, not the API, wrote
every call (the same for every arm).
