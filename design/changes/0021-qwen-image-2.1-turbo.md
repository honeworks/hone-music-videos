# 0021: Qwen-Image-2.1 Turbo draws every picture

## Status

`implemented in 0.1` (accepted by the maintainer 2026-10-11). It builds on 0020 (the menu, picture packs, each project's default models) and
changes none of its records or gates. Its smaller choices will be D-139 onward in
[decisions.md](../decisions.md).

## Context

The owner compared the local text-to-image models on five hard epic characters (Morvane, Darvin, the
White Giant, the Firebird, Liora), two seeds each, as a four-view sheet (2048x1024) and as one full-body
picture (832x1248), with the cast planner's own prompt templates (`experiments/sheet-baseline`,
2026-10-11, git-ignored):

| Model | Sheet | Full body | What it drew |
|---|---|---|---|
| Z-Image Turbo (today's `models.sheets`) | ~50 s | ~23 s | views repeated or missing; Darvin's mace an axe; the Firebird not in profile |
| FLUX.2 klein 4B | ~20 s | ~10 s | the weakest pictures |
| Qwen-Image-2.1 Turbo (8 steps) | ~40 s | ~18 s | all ten sheets right: four views in order, Morvane's snakes in every view, the ox-headed mace, the Firebird in profile |
| Qwen-Image-2.1 (25 steps) | ~100 s | | a little sharper than Turbo, 2.5x slower |
| HiDream-O1-Image | | | stopped; the owner rejected its pictures |

Then one two-character scene (Darvin confronts Morvane, 1024x576, seed 7) on Qwen-Image-2.1 Turbo with
references cut from its own sheets (`experiments/scene-refs`):

| References | Read at | Time | Result |
|---|---|---|---|
| none | | 21 s | no likeness |
| 3 full-body views | 1024 | 63 s | right |
| 6 / 10 full-body views | 1024 | 215 / 436 s | right, slow |
| 6 / 10 full-body views | 512 | 34 / 51 s | **each character drawn twice** |
| each character's whole sheet | 768 / 1024 | 29 / 48 s | **the sheet's row of four copied into the scene** |
| one full body and one face per character | 512 / 768 / 1024 | 28 / 50 / 81 s | right, no duplicates |

Peak GPU memory was 7.0 to 7.5 GB in every case: on the 8 GB card the limit is time, not memory. Today's
scene model, Qwen-Image-Edit 2511 at Q4, takes about 141 s a scene (design §15) and at most three
references.

Qwen-Image-2.1 is under the Qwen research licence: research and evaluation only, no commercial use. The
owner accepts it as the default and asked for a warning when a video is created.

## Problem

1. The local first pictures (Z-Image) miss what the cast asks for.
2. A scene gets at most three references, so it cannot carry each character's view, face and details.
3. More references can make a scene worse: two full-body pictures of one character become two people.
4. Nothing tells the owner that a model in use forbids commercial use.

## Options

1. **Leave it as it is.** Z-Image first pictures, Qwen-Image-Edit views and scenes, three references.
   Rejected: the baseline above.
2. **Qwen-Image-2.1 for the first pictures only**, Qwen-Image-Edit for views and scenes: one role
   changes, but scenes keep three slots and their 141 s.
3. **Hosted models for everything** (0020's menu): about $4 to $5 a video at the menu's prices, every
   picture leaves the machine. Stays a choice in the menu, not the default.
4. **Qwen-Image-2.1 Turbo for every picture, with a reference rule that keeps one body per character
   (chosen).**

## Decision

### 1. One model for every picture

- A new library entry `qwen-image-2.1-turbo` in `data/models.toml` and its workflow
  `data/workflows/qwen-image-2.1-turbo.json` (the graph proved in `experiments/scene-refs`): the int8
  Qwen-Image-2.1 model, the int8 Qwen3-VL 8B text encoder and its VAE (Comfy-Org's files), the Turbo
  LoRA at strength 1, 8 steps, cfg 1, euler/simple, and ten reference slots, `TextEncodeQwenImage21`'s
  `images.image_1` to `images.image_10`, each a `LoadImage` (the node also VAE-encodes them). hone-models
  drops an empty slot with its links, so the same entry draws from text alone (a first picture) and from
  references (views, scenes).
- `max_references = 6` (§3). A workflow input `ref_resolution` (`TextEncodeQwenImage21.resolution`,
  default 768): each reference is read at about 768x768. `vram_gb = 7.6`, `license = "Qwen research
  license"`, `commercial_use = false`, and its four install files (about 21 GB).
- The defaults of 0020 §7: `models.sheets`, `models.views` and `models.stills` are
  `qwen-image-2.1-turbo`. `models.polish` stays Z-Image, `models.clips` Wan 2.2, `models.finish` ESRGAN
  and RIFE.
- **Projects already created keep their models**: `project.json` stores every setting, so only a new
  project gets the new defaults. Nothing is migrated.
- Qwen-Image-Edit 2511 and Z-Image Turbo stay in the menu (0020 §1) as the local models allowed for
  commercial use.

### 2. Packs: 0020's separate pictures, given more references

The pack stays as 0020 §2 has it (a first picture, then side, back, portrait and details from it, the
gates `pick_sheets` and `review_packs`), on the new model. What changes is what each picture is given,
always within the model's `max_references`:

- **Props first.** Stage 6 draws the props' pictures in one batch, then the characters'. A character's
  first picture gets as references the owner's given sheets (as 0020 already does) and the picture of
  every prop whose `carried_by` names it (Darvin's mace), each named in the prompt by its image number
  ("the mace in image 2 is the one he carries"). A carrier's take is keyed by its references (D-009),
  so when the owner redoes a prop at `pick_sheets`, its carriers are drawn again in the same stage with
  the new prop; nothing else is.
- **Details before views.** In stage 7 each detail is drawn first, from the first picture. Then the side
  gets the first picture and the character's details, the back the first picture only (amended by the
  maintainer 2026-10-11, D-146: a chest pendant given to the back was painted on it); the portrait, as today, the front and
  side, then the details.

### 3. Scenes: one picture of each character

A new value of the setting `face_refs`, `"one-body"`, the default for new projects (stored settings keep
`"by-shot"`, `"portrait-first"` or `"front-first"`, so older projects' references and keys do not
change). In a `"one-body"` project, `prompt_assembly.references` gives a shot:

1. each character in it **one** picture: a full-body view (`front`, `side` or `back`), `"by-shot"`'s
   first choice (D-079); in a face shot its portrait instead;
2. then the details the shot names (0020 §4), then each prop's main picture, then the props' detail
   pictures;
3. never a second full-body view of one character, nor its portrait beside its body, never a sheet
   (amended by the maintainer 2026-10-11, D-145: case 35's portraits beside the bodies drew Morvane twice);
4. at most the model's `max_references` (six).

A shot's own `refs` naming two of one character's full-body views and portrait is an error of `check_shots` (§5.2) in
a `"one-body"` project (rule `one-body`, naming the shot and the views), so the planner's repair (§7.4)
fixes it; other projects accept it as today.

### 4. The warning when a video is created

- The New video form shows, above Start, each model the video would use (its `models` roles) whose
  registry entry has `commercial_use = false`, with its licence and roles:

  ```text
  Not for commercial use:
    Qwen-Image-2.1 Turbo (Qwen research license): first pictures, views, scenes
  ```

  A role whose entry records no `commercial_use` is listed as "licence not recorded". Start still works.
- `hone-music-video new` prints the same lines before it creates the project.
- The list comes from the registry (a function in `image_menu.py`, used by both), never typed by hand.
  The library's own entries record their licences where they do not yet: `wan2.2-i2v-14b` (Apache-2.0,
  commercial use allowed), the planners' hosted entries.

```text
$ hone-music-video new "Isolde 4" --song song.mp3 --lyrics lyrics.txt
Not for commercial use:
  Qwen-Image-2.1 Turbo (Qwen research license): first pictures, views, scenes
created projects/isolde-4
```

## Acceptance cases

Numbered after design §14's last (29):

30. A new project's settings name `qwen-image-2.1-turbo` for `sheets`, `views` and `stills` and
    `face_refs: "one-body"`; a project stored before keeps its models and `face_refs`.
31. A character with a carried prop gets the prop's picture as a reference in its first picture, named
    in the prompt; a redone prop redraws its carriers and no other first picture.
32. In a `"one-body"` project, every shot's references hold at most one full-body view or portrait per
    character and at most `max_references` pictures; a `"by-shot"` project's references are unchanged.
33. `check_shots` reports `one-body` for a shot whose `refs` name two full-body views or portrait of one
    character,
    in a `"one-body"` project only.
34. The New video form and `new` list every role whose model forbids commercial use, with its licence.
35. Real model (`tests/gpu`, through the GPU lock): one first picture and one two-character scene from
    its `"one-body"` references on `qwen-image-2.1-turbo`, each under 90 s.

## Tests

- Unit: the settings defaults and a stored project's settings (30); `stages_firsts` with a fake model,
  the props drawn before their carriers and the carrier's references and prompt (31); `references` and
  `budget` over one-, two- and three-character shots, face shots and named details, and an unchanged
  `"by-shot"` case (32); `check_shots`' new rule (33); the non-commercial list from a registry with one
  such entry and one without a licence (34).
- Integration: the dashboard's New video API returns the list; `new` prints it (34).
- GPU: case 35, through `scripts/gpu-lock.sh`, model unloaded after.

## Milestones

One milestone, to be built quickly: the entry and its workflow; the defaults; `"one-body"` and its
`check_shots` rule; props first and details before views; the warning; docs; then case 35 and one real
video.

## Consequences

- Every new video uses a model that forbids commercial use, unless the owner picks another in the menu;
  the warning says so each time.
- Scenes take about 50 s against 141 s: stage 10 of a 60-shot video about an hour instead of two and a
  half, before retries.
- A character carrying props and the views with details take a few more references, a few seconds each.

## Migration and compatibility

- Stored settings keep their models and `face_refs`; no step version changes for a stored project, and
  no stored format changes (`"one-body"` is a new value of an existing field).
- `qwen-image-edit-2511-4step` and its three slots stay.

## Risks

- **Licence:** the default is non-commercial; the warning is the guard, never a block.
- **One scene measured:** the `"one-body"` rule rests on one scene, three seeds with and without
  portraits (D-145); the first real video checks it.
- **Views from references on Qwen-Image-2.1 are not measured** (only first pictures and scenes are). If
  they drift, `models.views` goes back to Qwen-Image-Edit 2511 by one setting, per project.
- **Crash halfway, two processes:** nothing new is written; stages 6, 7 and 10 write as they do today.
- **Dependencies:** none new; ComfyUI needs `TextEncodeQwenImage21` (in ComfyUI since September 2026) and
  about 21 GB of model files.
- **The smaller option** (2) leaves scenes on three slots and 141 s, which is what the owner asked to
  change.

## The owner's answers (2026-10-11)

All three picture roles on Qwen-Image-2.1 Turbo; it is the library's default, with a warning shown, not
blocking; props, given pictures and details as references, chosen so that scenes do not drift;
references read at 768, at most six; props reviewed at the same gate; no previous scene as a reference
for its location; Qwen-Image-Edit and Z-Image stay in the menu; projects already made unchanged; packs
stay 0020's separate pictures (left to the agent); 0021 starts from `main` after 0020.

## Open questions

None left. Acceptance of the record is the maintainer's.
