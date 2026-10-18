# 0017: Prop sheets

## Status

`implemented in 0.1` (2026-10-11; unreleased). `accepted` 2026-10-11: asked for by the owner 2026-10-11,
needed before the next video. It builds on
0014 (references by kind of shot, the cast's `anchor`, the cutter) and 0009/0015 (the cast's `world`,
the start-frame check on its own model). Its smaller choices are D-100 to D-109 in
[decisions.md](../decisions.md).

## Context

Props exist only as text: `cast.json` lists them as `{id, name, carried_by, note}`, and the shot
planner paraphrases the note in every still prompt. The stills are drawn from those words alone, so the
prop changes from shot to shot. In *The Long Night v2* the `ruby-token`, "a gold armband set with one
large blood-red ruby, worn on Loren's left upper arm", is written six ways in S007, S008, S009, S022,
S023, S030, S036 and S040 ("the gold ruby armband", "a gold armband with a large red ruby", "a gold
armband whose single blood-red ruby peeks out"), and drawn small in one, large in another, with three
emeralds in one and one ruby in another. S007, an insert of the armband alone, has no cast, so it is
drawn by the text model with no reference at all.

Characters do not drift this way, because each has a sheet, a pack of views and `{id}` placeholders
that the library expands (§9, §10.1).

## Problem

1. A prop has no picture, so nothing holds its shape, size, count or colour between shots.
2. The shot planner rewrites the prop's description in its own words in every prompt.
3. The start-frame check does not know which props a shot shows, so it cannot flag a wrong one.

## Options

- **Better words only:** make the planner copy the note word for word. Fixes problem 2, not 1: the
  model still draws a different armband from the same words. Rejected.
- **Props on the character sheets:** draw the prop on its carrier's turnaround. A small object is tiny
  on a full-body sheet, a prop may change hands or lie alone (S007). Rejected.
- **A sheet and a pack per prop, as for characters (chosen):** drawn once from a fixed description,
  picked at the existing gate, cut into a main view and a detail view, given to the start frames that
  show it within the three reference slots, and checked by the vision check.

## Decision

1. **The prop's fixed look** (design §4.2, §7.2; D-100). A prop gains `look`: the object alone in one
   phrase (shape, material, colour, count, size against a hand or a body), never where it is or who has
   it ("a gold armband set with one large blood-red ruby, a finger wide"). `note` keeps the rest (who
   wears it, what happens to it). The cast planner writes both. A prop gains `source`, `"make"` (the
   default) or `"given:<sheet name>"`, as characters have.
2. **Prop sheets** (design §9; D-101, D-102). At the `sheets` stage, beside the characters' takes, each
   prop with a `look` and `source: "make"` gets `prop_sheet_takes` takes (a new setting, default 4, like
   `sheet_takes`), drawn by the `sheets` model (Z-Image) at 2048x1024 from a prompt the library builds:
   the look, the story's `anchor` (else `world`), the object twice on a plain light-grey studio backdrop
   (whole on the left, a close detail on the right), no people, no hands, no text. The takes are a new
   list `props` in the `Sheets` record (`SheetTakes`, its `character` field holding the prop id), each
   with its cut preview. The owner picks at the existing `pick_sheets` gate (`pick`, `retake` and the
   dashboard take prop ids as they take character ids; a retake's note goes to the props' prompts too);
   the gate passes on its own when no character and no prop needs a sheet, and in an unattended project
   the first take goes on, as for characters.
3. **Given prop sheets** (design §2.2; D-103). No new flag: a picture given with `--sheet name=file`
   reaches the cast planner as every given sheet does, and the planner sets a prop's `source` to
   `"given:<name>"` when the picture shows that object. A given prop sheet is never redrawn.
4. **The prop pack** (design §4, §9; D-104). The picked take (or the given picture) is cut by a simple
   object crop in the cutter (`split_objects`: the foreground's column runs over the whole height, each
   cropped to its box): the first object is `main.png`, a second `detail.png`; a picture with no
   separate object is `main.png` whole. Files go to `current/props/<prop-id>/` (`main.png`,
   `detail.png`, `sheet.png`, `takes/`). The `Packs` record gains `props: [{prop, main, detail, sheet}]`.
   No portrait, no model call.
5. **Shots name their props** (design §4.3, §7.3, §5.2; D-105). A shot gains `props: [ids]`, the props it
   shows. Still prompts write `{prop-id}` where the prop appears, as a noun phrase. `check_shots` errors
   with `unknown-prop` on a prop id not in the cast and with `placeholder` on a `{prop-id}` not in the
   shot's `props`. The shot planner's request carries each prop's `look`, and the prop's main view
   among the pictures.
6. **Prompt assembly** (design §10.1; D-105). `{prop-id}` becomes the prop's `look` word for word (its
   `note` when it has no look, an older cast); for the image model followed by the numbers of its
   pictures, "(image 2)" or "(images 2 and 3)", when it got any; for the polish pass the look alone.
   A shot with no cast but a prop with a pack is drawn by the start-frame model from the prop's
   pictures, then polished (S007); with no pictures at all it stays the text model's.
7. **The reference budget** (design §10.1; D-106). Still at most three pictures a still.
   - A **prop shot** (framing `insert`, or `close-up` or `extreme-close-up` without faces, showing a prop
     with a pack): each prop's main view first, then the characters' views as before (§10.1), then the
     props' detail views.
   - **Any other shot**: each character's first view (the portrait in a face shot), then each prop's main
     view, then the characters' other views as before, then the props' detail views. So in a face shot
     the portraits keep priority and the prop gets a slot only when one is free after them.
   - A shot's own `refs` may name a prop's view (`ruby-token/main`); they still override the rule.
   - A shot without props, or whose props have no pack, gets exactly the pictures it got before.
8. **The check** (design §10.3; D-107). The vision call also gets each prop's main view, the cast's props
   with their `look`, and per start frame its shot's `props`. A new flag kind `wrong-prop`: a prop that
   does not match its look and picture, `major` when its shape, count or colour differs, `minor` for
   size or detail. It counts like every major flag (the gate, `still_retries`).
9. **Older projects** (D-108). A cast written before has props without `look`: they get no sheet, no
   pack and no picture; a `{prop-id}` placeholder (which older plans do not have) is still expanded, to
   the note. A shot without `props` reads `[]`. Every older start frame keeps its key. Step versions
   stay, as in 0014: the records only gain optional fields.
10. **The dashboard** (design §13.2; D-109). The Cast view shows the props after the characters: each
    prop's look, its takes with their cut previews and the pick at `pick_sheets`, then its main and
    detail views once cut.

## Consequences

- `cast.json`: props gain `look` and `source`. `shots.json`: shots gain `props`. `Sheets` gains `props`;
  `Packs` gains `props`. The check record's flag kinds gain `wrong-prop`.
- Settings: `prop_sheet_takes` (default 4). Stored settings without it read 4; an older cast has no prop
  to draw, so nothing changes for it.
- GPU time: a Z-Image take is about 25 s, so 5 props x 4 takes add about 8 minutes at the sheets stage.
  No new model call kind; no change to the planner calls' count.
- Prompts: cast.md (look, source), shots.md (`props`, `{prop-id}`), quality.md (`wrong-prop`).
- Guarantee (design §14): **20.** A prop with a sheet is drawn from it: a still that shows it gets its
  pictures by the budget of §10.1 (at most three; first in a prop shot; after the portraits in a face
  shot), and its placeholder becomes its look word for word; a cast without prop sheets draws as before.

## Tests

All offline with fakes, in the default suite:

- `tests/e2e/test_ac20_prop_sheets.py`: a run whose cast has three props: one to make (its
  `prop_sheet_takes` takes drawn from a prompt holding its look and the anchor, one picked by `pick`
  and cut), one from a given picture of two objects (main and detail views), one with only a note (no
  sheet). The start-frame calls get the pictures of the budget rule (an insert with a cast, an insert
  without one drawn by the start-frame model, a one-person close-up, a two-person face shot, a wide
  shot, a shot whose prop has no sheet) and prompts with the look word for word; the planner and the
  check see the looks and the prop pictures; a `wrong-prop` flag is stored and flags the shot; the
  dashboard's records hold the prop takes and packs. A second case: a cast without looks draws no prop
  sheet, and a shot without a cast keeps the text model with the note expanded.
- `tests/unit/test_prompt_assembly.py`: the budget rule case by case (detail views, no free slot, a
  prop without a pack); shots without props get exactly the pictures of before; the look word for word
  for both models; a shot's own `refs` with a prop view; an unknown placeholder refused.
- `tests/unit/test_cutter.py`: `split_objects` on a sheet of a flat dagger and its pommel, and on a
  plain picture.
- `tests/unit/test_shots_check.py`: `unknown-prop`; a `{prop-id}` the shot does not list.
- `tests/unit/test_stages_cast.py`: the props' problems (an id used twice, a bad id, a missing given
  sheet).
- `tests/unit/test_records.py`: older casts, shots, sheets and packs load.

## Docs to update

`design/current.md` §2.3, §4, §4.2, §4.3, §5.2, §7.2, §7.3, §9, §10.1, §10.3, §13.2, §14; `docs/cast.md`,
`docs/shots.md`, `docs/render.md`, `docs/settings.md`, `docs/dashboard.md`; `CHANGELOG.md`; `AGENTS.md`;
`design/decisions.md` D-100 to D-109.

## Migration and compatibility

All new fields are optional (`look` `""`, `source` `"make"`, shot `props` `[]`, `Sheets.props` and
`Packs.props` `[]`). Older casts have no look, so no prop sheet is drawn and every start frame keeps
its key. An older project gets prop sheets only from a new run (a new cast plan); a re-plan of a few
shots keeps the cast as it is.
