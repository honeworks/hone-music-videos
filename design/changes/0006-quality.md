# 0006: Start-frame quality: faces like the portrait, a check of every start frame, best of N takes

## Status

`accepted` 2026-10-10 by the owner (the three improvements below were approved on 2026-10-10). The
smaller choices are in [decisions.md](../decisions.md) D-065 to D-069, awaiting coordinator review.

## Context

The first real run (*The Long Night*) showed three things about the start frames:

- A close-up of Celina came out younger and softer than her portrait. Design §10.1 gave a person's
  references as front, portrait, side for every shot, so in a close-up the model leaned on the
  full-body front view, where the face is small.
- Nothing looks at the start frames before the clips are made. A start frame with melted hands, a
  missing character, an extra person, letters or a face where none was planned costs a clip (4 to 5
  minutes of GPU) and its finishing before the owner sees it.
- One take per shot is a lottery. The owner can already ask for `still_takes` takes, but then has to
  choose each one by hand.

## Decision

1. **Faces like the portrait** (design §10.1, guarantee 8, D-065). A shot with `faces: true` framed
   `medium`, `close-up` or `extreme-close-up` gives each person (and creature) the **portrait first**,
   then the front and side views; every other shot keeps the front view first. Animals are unchanged.
   Still at most three pictures. The start-frame prompt of such a shot ends with one identity sentence
   per character whose portrait it got: "The woman from images 1 and 2 keeps the face of image 1: same
   age, same features." A real-model test (skipped by default) draws the same close-up both ways for
   the owner to compare.
2. **A quality check of the start frames** (new stage `check_stills` after `stills`, design §10.3,
   D-066, D-067). One vision call per check to the planner model (`models.quality`, default
   `claude-opus-5-5` on the OpenAI-compatible gateway, through hone-models), never one per shot: contact sheets of every start
   frame made (4 x 3 tiles, each with its shot id and take burnt in), the characters' front views and
   portraits, and each still's shot, take, cast, framing, `faces` flag and still prompt. The reply gives
   every still a score from 1 to 10 and flags (`anatomy`, `wrong-character`, `missing-character`,
   `extra-people`, `text`, `unwanted-face`, `off-style`), each with a severity (`minor` or `major`)
   and a short reason. It is stored as the stage's record (`StillsCheck`) with the call's time; the
   cost is recorded by hone-models. The Storyboard shows the flags on each card. Setting
   `quality_check: true` (default); with `false` the stage makes no call.
3. **A gate only when asked** (D-067). Setting `quality_gate: "off" | "ask"` (default `"off"`). A new
   gate `review_stills` follows `check_stills`. It passes on its own (recorded as automated, like
   `pick_sheets` without sheets, D-024) unless `quality_gate` is `"ask"` and a start frame the video
   uses has a major flag (minor flags are shown, not blocking). Then the run waits: the owner redoes the flagged shots from the Storyboard (each
   redo checks again) or approves to go on to the clips. It is an ordinary gate (`GATES`), so anything
   that approves gates treats it like the others.
4. **Best of N takes, off by default** (D-068, D-069). Setting `pick_best_of: 1` (default; 2 or 3
   allowed) and `pick_shots: "faces" | "all"` (default `"faces"`: the shots with `faces: true`). When
   above 1, each chosen shot has that many planned takes (at least `still_takes`), each drawn and
   polished; the quality check's scores pick the take each such shot uses (the highest score, the
   earliest take on a tie), unless the owner chose one. Only the picked take gets a clip. It needs
   `quality_check: true`. Before starting, the New video form and the CLI (`new`, `run`) show a
   warning with an estimate, from the shot count when it is known, else from the song's length:
   "Best of 2 on shots with faces: about +54 min of GPU (≈ +2 min per shot × ~26 shots)" for a
   4-minute song. The numbers live in one module (`estimates.py`).

## Consequences

- The run has 14 stages and 5 gates: `check_stills` is stage 11 (a hosted call), `review_stills` its
  gate; `clips`, `finish` and `assemble` are stages 12 to 14. `clips` and `finish` read the check's
  picks (their step versions become 3).
- The settings gain `face_refs` (`"portrait-first"` or `"front-first"`), `quality_check`,
  `quality_gate`, `pick_best_of`, `pick_shots` and `models.quality`; none reach the planners.
- **Projects and runs made before keep their behaviour** (the coordinator's review): their stored
  settings have no `face_refs` and no `quality_check`, which then mean `"front-first"` and `false`.
  So their start frames keep their keys (D-009) and their runs make no check call. Resuming such a
  run (its stages differ, which hone-flow refuses) forks it instead: the fork reuses every finished
  stage and runs the rest with this version (event `run_forked_for_new_version`). A redo or a use on
  any run is refused, before anything runs, when its fork would make another shot's files again
  (other settings or code would give them new keys), naming those shots.
- A new project's face shots are drawn from the portrait first.
- One hosted vision call per check: about 0.2 USD for 60 shots (a few contact sheets and the pack
  pictures; about 0.4 USD with best of 3 on the shots with faces), and one more each time a redo or a
  use runs the check again. At most 144 start frames (12 sheets) per check.
- Best of 2 adds about 2 minutes of GPU per chosen shot; best of 3 about 4.
