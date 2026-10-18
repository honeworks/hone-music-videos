# 0033: An item with several prompts makes one prompt at a time

## Status

`accepted (experimental)`, 2026-10-18, by the owner ("When we have multiple prompts for one image, dont
start running all of them. Just the first one. Unless I click on run this prompt … Running a prompt should
not trigger regenerating dependant"), for the branch `exp/frame-scene-generation` only. Changes D-076 (one
image per prompt) and 0028 §5 for items with `prompts`. Built.

## Context

An item with `prompts = [...]` makes one image per prompt each time it is made (D-076): a scene the planner
gave three prompts costs three pictures before anyone has seen one, and 0031 already makes a clip only for
the take in use. The owner wants to see the first prompt's picture and decide whether another prompt is
worth its time.

## Decision

1. **A make of an item with several prompts makes one image.** It uses the prompt of the picture in use
   (so a remake after a reference changed keeps the take the owner chose), or the first prompt when there
   is none. Its seed is still `seed + k` for prompt `k`. One image never waits for a pick; `hold` still
   waits. `count` without `prompts` is unchanged.
2. **Run this prompt.** The item panel shows **Run prompt N** for each prompt (`POST
   …/items/<id>/run-prompt` `{"prompt": k}`, from 0): the item is marked with that prompt and the frame
   run started when it is not going. `hone-music-video frame run-prompt PROJECT ITEM N` (from 1) marks it;
   `frame run` makes it. Nothing made from the item is marked, and the owner is not asked about them.
3. **The new picture is a candidate, not the choice.** When the item already has a picture in use, the
   prompt's picture is kept as a version beside it and the picture in use stays; the owner uses it with
   "Use this version", which asks about the dependants as before. When the item has no picture yet, it
   becomes the picture in use.
4. The prompt asked for is kept in `state.json` (`run_prompt`, from 0, `null` otherwise) until it is
   made; Unmark and a plain mark clear it.

## Consequences

- A planned scene with three prompts costs one picture overnight instead of three.
- `effective.per_run` gives the images one make makes; estimates use it.
- Hone Frame's guide (`data/frame_guide/project-file.md`, its `prompts` row) says so.
- Guarantee 73 is added; a stored `state.json` reads as before (`run_prompt` defaults to `null`).
