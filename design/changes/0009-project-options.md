# 0009: Project options (pace, mood, style) and the story's world

## Status

`implemented in 0.1` (2026-10-11; unreleased). `accepted` 2026-10-11: asked for by the owner
2026-10-11. Its smaller choices are D-084 and D-085 in [decisions.md](../decisions.md). It was reserved
as "options" when 0014 was written; the story's world (part B) joined it the same day.

## Context

Before starting a new song the owner wants to say, once, how the video should feel: how fast it is cut
and what mood it has. Today the only such setting is `style`, and the planners' prompts hard-code
historical examples ("a historical epic film … an ancient kingdom"): a modern story risks coming out
ancient. The first real run also showed that the period anchor alone (0014) does not keep objects out of
the story's world: the check flagged hurricane lanterns and steel chains after the fact.

## Problem

1. No way to ask for a calm or an energetic cut, or for a mood, other than writing it into the story
   notes (guarantee 13: settings are data, never words the owner must write into a prompt).
2. The prompts' examples are historical; nothing says the anchor comes from the story.
3. Nothing tells the shot planner and the check what belongs in the story's world and what must not
   appear.

## Options

- **Story notes only:** the owner writes "calm, dark" into the story. Breaks guarantee 13; rejected.
- **A list of moods:** fixed words (tragic, tender, …). The owner writes in more than one language and
  wants free words; rejected for a free text.
- **Pace, mood and world as data (chosen):** two settings and one cast field, given to the planners as
  data, with rules in their prompts and one `check_shots` warning.

## Decision

1. **`pace`**: `"calm"` | `"balanced"` | `"energetic"`, default `"balanced"`. The shot planner gets it in
   `settings` and, as `pace_shot_ms`, the shot length it prefers inside the shot limits: calm 6.5 to 8 s
   (few cuts inside a verse, cuts on line or section starts, one shot may carry two short lines),
   energetic 2 to 4.5 s, balanced none. `check_shots` warns `pace` on a shot outside that length (never
   the last, which ends with the song); a warning, not an error (D-084).
2. **`mood`**: free text in any language, default `""`. The cast and shot planners get it in `settings`;
   it sets the light and colour of the still prompts, the camera's speed, how still the motion is and
   how open the faces are; it never changes the story, the cast or the world. The start-frame check
   gets it and may flag `off-mood` (0015).
3. **`style`** stays a free string with its era-neutral default. The prompts' examples are marked as
   examples (`<the anchor>` in the shot planner's JSON example, an ancient and a modern anchor in the
   cast planner's), and both say the anchor and the world come from the story.
4. **`world`** (D-085): the cast planner (one whole-song call) writes it beside `anchor`: the period
   and place, what belongs in it (materials, clothing, light sources, technology) and what must not
   appear, from the story: a modern story allows phones and cars, an ancient one forbids them. The shot
   planner gets it as data ("everything a still prompt names belongs to `world`") and so does the
   start-frame check. The check's flag keeps its name, `anachronism`, and now means "out of the story's
   world" (its stored records stay readable). A cast without `world` (made before) reads it as `""`:
   the planners and the check fall back to the anchor and the story.
5. CLI `new --pace --mood` (beside `--settings`; a flag wins over the file). `POST /api/projects` takes
   them in `settings`, validated like every setting; `GET /api/settings` returns the defaults and the
   allowed `paces` (and `still_retries`' range, 0015).

## Consequences

- `cast.json` gains `world`; the settings gain `pace` and `mood`, both given to the planners (not the
  check's settings).
- The shot planner's data gains `world` and `pace_shot_ms`; the check's data gains `mood` and `world`.
- `check_shots` gains the warning `pace`.
- The New video form's fields for the options are built on the dashboard's own branch, from
  `GET /api/settings`; until they land, a project made from the dashboard gets the defaults and the
  options are set with the CLI or the API.
- Guarantee **18** (design §14): the project's options and the story's world reach the planners and the
  start-frame check as data, never as words in a prompt; a project or cast made before keeps its plans.

## Tests

- `tests/e2e/test_ac18_project_options.py`: the CLI flags (winning over the settings file) reach the
  cast and shot planners and both checks as data; `world` reaches the shot planner and the checks; an
  older project and cast send `world: ""`, `pace_shot_ms: null`, `pace: "balanced"`; the dashboard API
  lists the paces and refuses a wrong one.
- `tests/unit/test_shots_check.py`: the `pace` warning for calm and energetic, none for balanced, the
  range inside the shot limits.
- `tests/unit/test_settings.py`: defaults, validation, older settings.
- `tests/unit/test_prompt_rules.py`: the prompts' world, pace and mood rules; no hard-coded period.

## Migration and compatibility

Settings stored without `pace` and `mood` read `"balanced"` and `""`: the plans are as before (the
planner sees a balanced pace and no mood). A cast without `world` reads `""`. Nothing already made
changes: no file key depends on these.
