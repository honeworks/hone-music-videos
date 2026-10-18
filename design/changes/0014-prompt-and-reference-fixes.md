# 0014: Prompt and reference fixes from the first real run

## Status

`implemented in 0.1` (2026-10-11; unreleased). `accepted` 2026-10-11: owner delegated acceptance overnight; answers as recommended (the four open
questions below are answered as their recommendations: traits from a new cast-planner field, the anchor
written by the cast planner, no-face shots on Qwen with the full-body views and no portrait, the existing
Ember pack not re-cut). The owner locked the fixes on 2026-10-10, after diagnosing the bugs of the first
real run (*The Long Night*). Numbers 0009 to 0013 are reserved (options, run schedule, subtitles, the
YouTube version, social cuts). It builds on 0006 (portrait-first face references and the `check_stills`
vision check) and 0008 (batch redo and re-plan), both merged. Its smaller choices are D-077 to D-081 in
[decisions.md](../decisions.md).

## Context

The owner watched the first real run and listed 13 bugs. Their causes, diagnosed in the build log:

| Bug | Shots | What happened | Cause |
|---|---|---|---|
| 1 | S002 | a hand with a lighter enters near the lamp | Wan adds hands near flames; nothing says none enters |
| 2 | S003 S021 S027 S036 S051 S056 S058 | characters talk or sing | "her lips part" and the like; the non-goal "no lip sync" never reached the planner |
| 3 | S007 | the horse copied in side view from its reference, the wide composition ignored | references override composition (experiment D) |
| 4 | S030 | Darvin's and Loren's faces blend | two similar men (experiment C) |
| 5 | (pack) | `ember/side.png` holds a sliver of the neighbouring figure | the cutter's box reaches halfway to the next head, and the previous horse's rump lies there |
| 6 | S037 | an extra hand | two bodies in contact, a tangled pose |
| 7 | S030 S033 S035 S037 | Loren looks like a new person | the planner invents fixed traits (long hair), it never sees the sheet prompt; the second character of a two-person shot gets only a small-faced front view |
| 8 | S057 | an extra hand; a no-face wide shot drawn as a large posed figure facing the camera | the shot got her portrait as a reference |
| 9 | S042 | the still ignores "silhouette, wide"; in the clip the dead Loren sits up, bodies merge | portrait given; the motion prompt was written for the planned still, never says who lies still; bodies overlap |
| 10 | S045 | the dagger rises and turns | "push-in along the blade" (an oblique move), and nothing says the dagger lies still |
| 11 | S048 | modern shoes, a hurricane lantern, a labelled shirt | no period anchor; "laid out on a red carpet", "oil-lamp" read as modern |
| 12 | S011 | the helmet catches fire | "torchlight flickers over the helmet" |
| 13 | S014 | horses walk backward | a crowd of tiny horses, a pan, and no word on what they do |

The owner judged the polished stills good ("look amazing"); the look is not part of this change.

## Problem

1. The shot planner's limits (`data/prompts/limits.md`, design §8) say nothing about speech, about what
   must stay still, about hands or objects entering, about where fire is, about crowds, or about bodies
   in contact (bugs 1, 2, 6, 9, 10, 12, 13).
2. The shot planner gets each character's `cue` but not their fixed traits, and invents them (bug 7).
3. No still prompt says when and where the story happens (bug 11).
4. A shot without faces still gets the portrait, and the model then draws a face (bugs 3, 8, 9).
5. The motion prompt is written before the start frame exists, for the frame the planner imagined
   (bug 9).
6. Nothing checks a plan for speech, or a start frame for anachronisms (bugs 2, 11).
7. The cutter keeps parts of a neighbouring figure (bug 5).

## Options

- **Leave it as it is:** redo the bad shots by hand with edited prompts. Every new song repeats the
  bugs; rejected by the owner.
- **Fix each shot's prompts by hand in a redo** (0008's `--still-prompt`, `--motion-prompt`): fixes this
  video only. Rejected.
- **The locked fixes (chosen):** rules in the planner's limits, more data in the planner's request,
  a reference choice per kind of shot, the vision check also rewriting motion prompts and flagging
  anachronisms, one more `check_shots` warning, the cutter fix; then one batch redo of the affected
  shots.
- Writing every motion prompt after its start frame in a separate call per shot: breaks design §7.1
  (whole-song calls); the 0006 check is already one call that sees every start frame. Rejected.

## Decision

1. **(a) No words** (limits.md "Limits of the video", design §8.3; bug 2). New rule: "No one speaks,
   sings, whispers or mouths the lyrics: there is no lip sync. Faces stay alive: a smile, a laugh, a
   roar or battle cry as one held moment, a gasp, a clenched jaw, tears, lips slightly apart at rest,
   never forming words. Show what a character says or feels through the eyes, breath, tears, a turn of
   the head." Tied to a future `lip_sync` capability: the rule applies while there is none.
2. **(b) Motion rules** (limits.md, design §8.2 and §8.3; bugs 1, 6, 9, 10, 12, 13). New rules:
   - Name what moves, how and in which direction, **and who or what stays still** ("he lies completely
     still", "the dagger lies still on the grass"); the video model moves anything left unsaid.
   - Inserts use a simple camera move: a straight push-in, a pull-back or a pan; never a move "along" or
     "around" an object.
   - No hands, people or objects enter the frame unless the shot plans it.
   - Fire and smoke only at their sources ("the torch flames flicker"); light is described as light
     ("the warm glow of the torches shifts on the helmet"), never attached to a person or object.
   - Every moving crowd or animal group gets an explicit state and direction ("the horses stand
     still, grazing", "riders walk slowly to the right"); a crowd of small figures gets a static camera,
     never a pan across it.
   - Stills avoid overlapping bodies where motion happens and tangled two-body contact poses (cradling,
     embracing, grappling); show one body clearly, the other beside it.
3. **(c) Fixed traits** (design §7.2, §7.3; bug 7). The cast plan gains `traits` per character: the
   fixed look in one phrase (age, build, hair, beard; for an animal its colour and markings), copied
   from the sheet prompt it writes, or read from the image for a given sheet. The shot planner's
   request carries `traits` in `cast.characters`, and shots.md gets the rule: "Never alter a
   character's traits unless the story does (an injury, age passing); say the change in the still
   prompt." A cast without `traits` (made before) sends the sheet prompt's description instead
   (`sheet_prompt`, when the character has one). The sheet prompt itself still does not go to the
   planner otherwise (D-027 stands for the rest).
4. **The period and place anchor** (design §7.2, §7.3; bug 11). The cast plan gains `anchor`: one
   sentence naming the kind of film, the period and the place, from the story, for example "A still
   from a historical epic film, real set, a legendary ancient kingdom." The shot planner
   gets it as data, with the rules "Begin every still prompt with `anchor`; when it is empty, write the
   period and place from the story" and "Avoid phrases with a modern reading: say 'a woven rug laid on
   the floor', not 'a red carpet'; 'a clay oil lamp', not 'an oil-lamp'." `check_shots` warns
   `no-anchor` on a still prompt that lacks the cast's anchor.
5. **(d) References by kind of shot** (design §10.1, guarantee 8; bugs 3, 7, 8, 9). A new value of
   0006's setting: `face_refs: "by-shot"`, the new default.
   - A face shot (`faces: true`, medium or closer) gives each person and creature in its cast the
     portrait first, in turn (Loren's portrait comes before Darvin's front view), as 0006 does.
   - A shot without faces (`faces: false`: wide, silhouette, turned away, inserts with a cast) gets no
     portrait: a person's front and side views, an animal's side and front views.
   - Whether such shots are instead drawn by Z-Image from text alone (no references) is left to
     experiment D (S007, S057, S042); until then the default is Qwen with the full-body views and no
     portrait (open question 3).
6. **(e) The vision check rewrites motion prompts and flags anachronisms** (design §10.3, §11.1;
   bugs 9, 11). In the same single `check_stills` call, each start frame also comes with its beat,
   camera and planned motion prompt, the cast's `anchor`, and the limits of the video (§8.3). The reply
   gives each start frame a `motion_prompt` rewritten to the frame as drawn: the planned motion kept,
   the figures named where they are, who stays still said, the §8.3 rules followed. A new flag kind
   `anachronism` (minor or major, like the others) names what does not belong to the period. The
   clip uses the rewrite, unless the take's motion prompt was written by the owner (a redo with
   `--motion-prompt`). A start frame keeps the rewrite first written for it: a later check (after a
   redo) asks only for start frames without one. The Storyboard shows the planned and the rewritten
   prompt. A new setting `rewrite_motion` (default `true`; it needs `quality_check`).
7. **(f) Speech warning** (design §5.2; bug 2). `check_shots` warns `speech` on a still or motion prompt
   with a word of speech: speak, say, sing, whisper, talk, call out, recite, chant, mouth the words,
   lips move or form words (whole words, any case). Expressions (smile, laugh, shout, roar, gasp, cry)
   are never warned. It is a warning, not an error: it does not go to the repair call.
8. **(g) The cutter crop** (design §9 step 2; bug 5). After a figure's box is found, only the
   foreground connected to that figure's own head run (in the top third) is kept; foreground of a
   neighbour that reaches into the box is painted with the backdrop colour, and the box is narrowed to
   what is left. NumPy only, no new dependency.

### The batch redo

After the fixes are built, the owner's project is redone with 0008, in one fork and one assembly:
S002 S003 S007 S011 S014 S021 S027 S030 S033 S035 S036 S037 S042 S045 S048 S051 S056 S057 S058
(19 shots; the queue file's older list has 15, without S011, S014, S045 and S048 from bugs 10 to 13).

1. `hone-music-video replan projects/the-long-night <the 19 shots> --note "..."`: one whole-song call
   with the new shots.md and limits.md, the traits (from the sheet prompts, the cast being older) and
   the period from the story, which may change only these shots.
2. Applying it writes the changed shots' own `refs` by the "by-shot" rule when the project's
   `face_refs` is older, so only these shots get the new references (a shot's `refs` already override
   the setting, §10.1), and no other shot's key changes (0008's guard).
3. `--dry-run` first, for what it makes and how long (about 19 × 7 to 9 min of GPU).

The speech warning will also name S053 (a speech-like verb in the log's count); the owner decides whether
to add it.

## Consequences

- `cast.json` gains `traits` per character and `anchor`; `shots.json` is unchanged.
- The check record (`StillsCheck`) gains `motion_prompt` per start frame and the flag kind
  `anachronism`; the check call grows by the motion prompts (a few cents for 60 shots).
- Settings: `face_refs` gains `"by-shot"` (the new default); `rewrite_motion` is new; neither reaches the
  planners.
- `check_shots` gains the warnings `speech` and `no-anchor`.
- The planners' prompts grow by about 25 lines; no extra call anywhere. Step versions: `plan_cast` and
  `plan_shots` keep theirs (their records only gain optional fields), so 0008's guard does not refuse a
  redo of an older run; `check_stills` and `clips` go up one, and a clip's key changes only where its
  motion prompt changed. (As built, D-080: the step versions stay, since an older project rewrites
  nothing and a version change would make "assemble again" refuse every older run.)
- Guarantees (design §14), numbered after the last case when built (14 to 17 on today's list):
  - **8 (changed):** every shot with a cast gets at most three reference pictures chosen by §10.1; in a
    face shot each person's portrait comes first; a shot without faces gets no portrait.
  - **14:** the shot planner's request carries each character's fixed traits and the story's anchor.
  - **15:** `check_shots` warns on speech words in a prompt and on a still prompt without the anchor,
    never on expressions.
  - **16:** a clip is made from the vision check's rewritten motion prompt, unless the owner wrote the
    take's motion prompt; an older project's clips keep their prompts.
  - **17:** a cut figure holds no part of its neighbour.

## Tests

All offline with fakes, in the default suite:

- `tests/e2e/test_ac14_planner_traits_anchor.py`: the fake planner records the shot planner's request:
  `traits` and `anchor` in it; an older cast (no `traits`) sends the sheet prompt's description.
- `tests/e2e/test_ac8_reference_picking.py` (extended): per kind of shot: a two-person face shot gives
  both portraits first; a `faces: false` wide shot with a person and an animal gets no portrait;
  `"portrait-first"` and `"front-first"` keep 0006's choices.
- `tests/e2e/test_ac15_speech_warning.py` and `tests/unit/test_shots_check.py`: "she whispers the line",
  "he sings" and "mouths the words" warn `speech`; "she smiles", "he laughs", "a roar" do not; a still
  prompt without the anchor warns `no-anchor`; warnings never reach a repair call.
- `tests/e2e/test_ac16_motion_rewrite.py`: the fake vision reply rewrites S002's motion prompt; the
  clip job carries the rewrite; an owner-edited take keeps its own; an `anachronism` flag is stored; a
  redo's check asks only for the redone start frame; with `rewrite_motion` absent (an older project)
  nothing changes.
- `tests/e2e/test_ac17_cutter_crop.py` and `tests/unit/test_cutter.py`: a synthetic sheet of four
  figures where one's rump reaches under its neighbour's head (like the ember sheet): no pixel of the
  neighbour in the cut figure.
- `tests/unit/test_records.py`: an older `cast.json` and an older check record load.
- `tests/integration/test_old_runs.py` (extended): applying a re-plan on a project with an older
  `face_refs` writes `refs` only on the changed shots, and the guard lets the redo run.

The prompts' new rules are checked by eye on the redo (not by a test).

## Docs to update

`design/current.md` §5.2, §7.2, §7.3, §8.2, §8.3, §9, §10.1, §10.3, §11.1, §14; `docs/cast.md` (traits,
anchor), `docs/shots.md` (the new rules and warnings), `docs/render.md` (references by shot, the
rewritten motion prompt, anachronisms), `docs/settings.md` (`face_refs`, `rewrite_motion`),
`docs/dashboard.md` (the two motion prompts on a card); `CHANGELOG.md`; `design/decisions.md` D-077 to
D-084 when built.

## Migration and compatibility

New data is optional: `traits` and `anchor` default to empty, `motion_prompt` in the check record to
none, so older files load. Projects and runs made before keep their behaviour: their stored settings
have no `"by-shot"` and no `rewrite_motion`, which then keep their stored `face_refs` (or 0006's
`"front-first"`) and mean `false`; their start frames and clips keep their keys. The cutter fix applies
when packs are cut again (new projects, new sheet takes); existing packs are not re-cut. The batch redo
above is how an older project gets the fixes, shot by shot.

## Open questions for the owner (answered 2026-10-11: as recommended)

1. **Where the fixed traits come from.** Recommended: the new `traits` field written by the cast
   planner (copied from its sheet prompt, read from the image for a given sheet), not the whole sheet
   prompt sent to the shot planner.
2. **Who writes the anchor sentence.** Recommended: the cast planner, from the story ("A still from a
   historical epic film, real set, <period and place>"); 0009's style list may later set the kind of
   film.
3. **Experiment D: no-face shots drawn from text?** Recommended default: Qwen with the full-body views
   and no portrait; switch those shots to Z-Image from text only if experiment D shows it better (a
   later decision in D-077..D-084).
4. **The ember pack in the owner's project.** Re-cutting it would remake every shot that uses Ember.
   Recommended: keep the old pack (the sliver is at the edge of the side view); S007's real problem is
   its composition, which (d) and experiment D address.
