# 0024: Scenes and Clips as two views, a scene's history in the viewer, and a Preview

## Status

`implemented in 0.1` (accepted by the maintainer 2026-10-12, built 2026-10-12), asked for by the owner
while *isolde-the-forgotten-wife* was running; with the names Storyboard and Clips, and both compare
modes (the wipe first). Built with three refinements: a version names every take it belongs to
(`takes`, a list: a new seed keeps the still, so two takes share it), a finished clip's source is its
`inputs.video`, and the viewer's Redo follows the step shown (D-154); the take in use shows files its
stage has not listed yet (D-153). The drafts the check drew again are listed apart as "not used",
without their round number.

## Context

The Storyboard (§13.2) shows each shot's *newest* file on one card: the draft, then the polished start
frame, then the raw clip, then the finished clip, each replacing the one before. Its card also carries
the takes, the check's flags, the automatic retries, the motion prompt, the redo panel and the batch
pick. Every earlier file is still on disk as a kept version (D-009), and each version's record names the
file it was made from (`inputs.image`: a polished still names its draft, a clip names its still), but
the page shows none of that.

## Problem

1. One view mixes two jobs: judging pictures (stage 10, the `review_stills` gate) and judging motion
   (stages 12 and 13). On a 67-shot song the cards are long and the owner cannot tell which stage a card
   is showing.
2. The owner cannot see what a step changed: draft against polished, raw clip against finished clip.
3. A redo's earlier versions, and the drafts the check drew again (0015), are not shown at all.
4. Opening a picture shows it alone; to redo it the owner closes the viewer and finds the card.
5. Until the video is assembled (the last stage) there is no way to see the shots in order with the
   song, so pace, continuity and the story are judged only at the end, after hours of clips.

## Options

- **Leave it as it is.** Everything is on disk; the owner opens files by hand. Rejected: the problem
  is exactly that the page hides it.
- **More on the card** (tabs inside each card for draft, polished, raw, finished). Keeps one view but
  makes 67 cards heavier, and a comparison at thumbnail size shows nothing. Rejected.
- **Two views, the history in the viewer, a client-side Preview (chosen).** The cards get lighter; the
  detail is one click away at full size; the preview needs no new file and no model.
- *A preview rendered by ffmpeg* (a draft video assembled from whatever exists). Exact, but it is a
  CPU job that would compete with the running pipeline, it is stale the moment a new file arrives, and
  it needs a stage or a background task. Rejected for 0.1; the assembled video stays the exact cut.

## Decision

### 1. Storyboard becomes two views: Storyboard (pictures) and Clips

- **Storyboard**: the start frames only. Each card shows the polished frame of the take in use, or
  its draft while it is polished, with a tag "draft" or "polished"; the check's flags and score, the
  automatic retries, the takes, "Retry this frame", the scene redo (new start frame, edited still
  prompt, another model, upload), the queue notes and the `review_stills` gate. The tab's count is the
  polished frames.
- **Clips**: one card per shot showing its clip: the finished clip, or the raw clip while it is
  finished, tagged "raw" or "finished", hover to play, the motion prompt (planned and rewritten, D-080),
  the clip redo (new seed, edited motion prompt), the stage 12 and 13 progress. A shot with no clip yet
  shows its start frame dimmed with "waiting for its clip". The tab's count is the finished clips.
- Both views keep the song timeline, the batch pick (picks shared between them) and the batch bar,
  "Make these now" and the progress panel of their stages. Nothing is removed, only moved.

### 2. The scene viewer: before and after, every version, and Redo

A click on any shot's picture or clip, in either view, opens the **scene viewer** (the viewer of D-054,
for a shot):

- **The chain of the take in use** as steps: Draft → Polished → Raw clip → Finished clip, the steps
  not made yet greyed. A step opens at full size.
- **Compare**: draft against polished as a wipe (a slider over the two pictures at the same size) or
  side by side; raw against finished clip side by side, played together, with the song slice. The keys:
  `C` toggles compare, `←`/`→` the previous and next shot, `Esc` closes.
- **Versions**: every kept version of the shot, newest first, grouped by take: what the take came from
  (planned, a redo with its note, another model, an upload, a queued scene), its chain as thumbnails, the
  check's score and flags, and drafts the check drew again shown under their take as "redrawn by the
  check (round n)". The take in use is marked; another take has "Use this version" when the run has
  stopped (as today).
- **Redo** inside the viewer: the same controls as the card (§11.2, 0020): in the Storyboard's viewer
  the frame's redo (new start frame, edited still prompt, model menu with estimates, upload), in the
  Clips viewer the clip's (new seed, edited motion prompt). The same rules apply: queued while the run
  is busy (0020 §4), made at once on a paused run (0022), refused when empty (D-147). The viewer stays
  open and its versions refresh when the new files arrive.

The versions come from one new read-only request, made when the viewer opens and again on the
project's events while it is open:

```http
GET /api/projects/<id>/shots/<shot>/versions
```

```json
{
  "shot": "S067",
  "use": 0,
  "versions": [
    {"stage": "draw", "url": "/files/...", "made_at": "2026-10-11T20:44:01+00:00", "model": "qwen-image-2.1-turbo",
     "seed": 12, "from": null, "takes": [0], "in_use": true},
    {"stage": "stills", "url": "/files/...", "made_at": "...", "model": "z-image-turbo-polish",
     "seed": 472268875, "from": "/files/.../draw-3067d95f76c7.png", "takes": [0], "in_use": true}
  ]
}
```

Built from the shot's `versions/*.json` (D-009) and `takes.json` (D-031): `from` is the version's
`inputs.image` as a URL (a polished still's draft, a raw clip's still, a finished clip's raw clip); `takes` are the takes whose files lead back to it
through `from`, else empty (an orphan, such as a draft the check drew again); `in_use` marks the take
in use's chain. A version record that cannot be read is left out, never an error. It reads files only:
no record, folder or lock is written. It lives in a new module `_dashboard_versions.py` (the records
module is near its size limit). The main `records` answer does not change.

### 3. A Preview view

A new tab **Preview**, after Clips, shown once the shot plan is approved. It plays the song and, at each
moment, the shot that covers it, from the best file the shot's take in use has:

| The shot has | The preview shows |
|---|---|
| a finished clip | the finished clip |
| a raw clip | the raw clip |
| a polished start frame | the picture |
| a draft | the draft |
| nothing yet | a dark card with the shot id and its beat |

- A clip plays from its start at the shot's start (as the assembly cuts it, §12) and holds its last
  frame when shorter than the shot; it is muted, the song plays.
- Under the picture, the song's timeline with each shot coloured by what it has (draft, polished, raw,
  finished, nothing), the play position, and the current lyric line; a click seeks. Keys: space plays,
  `←`/`→` the previous and next shot.
- Each shot's file is chosen afresh when the records change, so a frame or clip that arrives during
  playback appears at its next turn without stopping the song. The next shot's clip is preloaded.
- A note above it: "A preview from what is made so far. The Video view has the exact cut once the
  video is assembled." A click on the picture opens that shot's scene viewer (§2).

It is page logic only (`views/preview.js`) over what the records already give (`shots`, `shot_files`,
the timeline, the song); no request, file or model call is added. Choosing the file per shot is one pure
function, tested in Node.

### Not in this change

The owner asked what else the dashboard should have; those ideas are in §Answered, each its own
change.

## Acceptance cases (§14)

(0023 reserves 41 to 46.)

47. A shot's versions request lists every kept version of the shot with its stage, URL, model, seed,
    `from` and take; a polished still names its draft, a clip its still; the take in use's chain is
    marked; a draft not leading to any take is listed with no take; an unreadable version record
    is left out; an unknown project or shot is 404. The request writes nothing in the project.
48. The Preview's choice per shot is the furthest file of the take in use (finished clip, raw clip,
    polished frame, draft, nothing), and a file that arrives changes that shot's choice.
49. The Storyboard shows only pictures and the Clips view only clips: a shot with a finished clip shows
    its frame on the Storyboard and its clip on Clips; every control of today's Storyboard is on one of
    the two.
50. A redo sent from the scene viewer sends the same request as the card's, and is queued, made at
    once or refused under the same rules.

Tests: `tests/integration/test_dashboard_versions.py` for 47 (a project made by `FakeModels`, a redone
shot and a corrupt version record); `tests/unit/test_dashboard_preview_page.py` for 48, and
`tests/unit/test_dashboard_scene_page.py` for 49 and 50, in Node with the fake DOM as the queue's tests.

## Consequences

- Two new tabs (Clips, Preview), one new read-only API request, one new Python module and three page
  modules (`views/clips.js`, `views/preview.js`, `views/scene.js` for the viewer, and `views/board.js`
  and `views/scene-parts.js` for what the views share), one stylesheet (`scenes.css`); `storyboard.js` gets
  smaller. No record, stored format, setting, CLI command or model call changes.
- The Preview is approximate where the assembly is exact (frame rounding, D-035); the note says so.
- The versions request reads a few JSON files per version; it is made for one shot at a time, only
  while its viewer is open.

## Migration and compatibility

Nothing stored changes. The old `#/p/<id>/storyboard` link still opens the Storyboard. Projects made
before 0015 have no redrawn drafts; before 0020 no `model` per take; both show what they have. Crash
halfway and two processes: nothing is written. A running pipeline is not touched by the page: the new
request only reads finished version files (a version is recorded only once its file is complete, D-009).

## Answered

1. The names: Storyboard and Clips (the maintainer, 2026-10-12).
2. Compare draft against polished: both, the wipe first.
3. Ideas for later changes, none in 0024; the maintainer chose all but the last for their own records:
   - a **Shot inspector** in the viewer: the exact prompts sent (still, polish, motion), the reference
     pictures each prompt got (§10.1), the seed, the model, the time it took and its cost;
   - a **Problems** list: every flagged frame, failed shot, `clip_short` and planner warning across the
     run in one place, each a link to its scene;
   - **Continuity strip**: one character's frames across the song side by side, to spot a drifting face
     or costume;
   - **Compare two takes** of a shot side by side (not only before and after);
   - a **GPU and queue panel**: what is running now, what is queued, the GPU lease waits (as in the
     terminal's "GPU lease … has waited 30 s"), and the time left per stage;
   - a **comment per shot** kept for the next redo or re-plan (a note without making anything yet);
   - *(not chosen)* **Export the preview** as a quick low-resolution draft video.
