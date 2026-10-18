# The dashboard

> **Since [0027](../design/changes/0027-hone-frame-is-the-scene-pipeline.md)**:
> the cast, packs, start-frame check, polish, picture menu and their gates described here are gone. The
> plan is written as a Hone Frame project file and the scenes are made in the dashboard's **Scenes** view
> (or `hone-music-video frame ...`, [cli.md](cli.md)); the gates are `review_lyrics`, `review_plan` and
> `review_scenes`. [design/current.md](../design/current.md) §7, §9 to §11 and §13.2 describe it.
> A scene with several prompts is made from its first; **Run prompt N** in its panel makes another
> beside the picture in use without marking what is made from it, and **Use this version** picks it
> ([0033](../design/changes/0033-one-prompt-at-a-time.md)).


```text
hone-music-video dashboard                       # http://127.0.0.1:8794/ , projects in ./projects
hone-music-video dashboard --projects ~/videos --port 8800
hone-music-video dashboard --fake-models         # every stage on fake models, to try it
```

A small web server on `localhost` only (design §13). It runs one project at a time (one GPU): a project
waiting its turn shows `queued`. Every view updates live as the run makes things, and every picture
the run makes is shown as it lands: drafts, start frames, raw clips, finished clips, sheet takes and
portrait drafts ([0003](../design/changes/0003-live-progress.md)). Long stages show real progress,
never an invented percentage: the files done of all (a shot with a cast is a draft and a polish), the
one being made ("drafting S007 · 3 of 110"), the time elapsed, the time per picture measured in this run,
the model load, and the time left from those measured times ("estimating…" until two are done). An
overall bar covers the start frames, clips, finishing and assembly with the clock time they should end;
times this run has not measured yet are the reference machine's (design §15), marked "estimate".
Whatever is being made right now has a light motion (off when your system asks for reduced motion).
Every picture and clip opens in a viewer over the page: arrow keys for the previous and next, Esc to
close, and a link to the file itself. It serves only a project's `current/`
folder, its song and its given sheets.

| View | What it shows and does |
|---|---|
| Projects | every project with its stage, thumbnail and length; **New video** |
| New video | drop the song, paste the lyrics, story notes, given sheets with names, the settings (below; with the GPU time extra start-frame takes would add, and what will be sent), **Stop after the scenes are drawn** (it does not stop an automatic run), the three default models (first pictures, views, scenes: a list each, with its estimate per picture, and the estimate for the whole video when one is hosted), **Run without stopping for my approval**; **Start** |
| Project | the 14 stages as a timeline with each stage's bar, the overall estimate and the gate waiting for you; the activity |
| Lyrics | every line with its start and end and its words, play a line, the findings under their lines; at the gate, a line's timing (the clock beside it): set its start or end to the play position or nudge it by ±100/±500 ms, then **Save timing** (checked again); **Approve** or **Reject with note** |
| Cast | the characters and props, which given sheet covers whom, the sheet takes as they are drawn with their cut previews and the judge's score, flags and retries under each (a take still flagged is outlined), the portrait draft while it is polished; a card per prop with its look, its takes and its main and detail views; pick a take (a character's or a prop's) or ask for new ones. In a project of separate pictures (0020): each character's first picture, then (after `pick_sheets`) its side, back, portrait and details, and each prop's picture, each with who made it (a model or your own file), the judge's flags and its other takes; **Redo** (a note and a model from the menu, with estimates) and **Upload** on each; **Approve** accepts what is shown, at `pick_sheets` and then `review_packs` |
| Shots | the shot list on the song's timeline, framing, cast, prompts, findings under each shot; **Approve** (with acceptable errors after a confirmation) or plan again with a note |
| Storyboard | the start frames' bar; every shot's start frame as it lands, its draft while it is polished, tagged **draft** or **polished**, with its state (waiting, drafting, draft ready, polishing, polished, failed); a click opens the shot in the scene viewer (below); what the start-frame check flagged on each card, and each take's score; the frame's automatic retries ("retry 1 of 2: wrong character → redrawn"); each shot's takes with **Use this version**; **Redo this start frame**: a new start frame, an edited still prompt, a new still from a model of the menu (with estimates) or your own picture (**Upload**); a redo sent while the run is busy shows "will be drawn next" (during the start frames) or "queued", and **Make these now** makes everything queued as one fork once the run has stopped, after showing its time and hosted cost; several shots picked together and redone or re-planned (below); at Review the start frames, each flagged frame outlined with **Retry this frame**, and **Approve** |
| Clips | the clips' and finishing's bars; every shot's clip as it lands, raw while it is finished, tagged **raw** or **finished**, hover to play; a shot without a clip shows its start frame dimmed; the motion prompt as planned and as the check rewrote it for the clip; **Redo this clip**: a new seed or an edited motion prompt (same start frame); a click opens the scene viewer; picking several shots and the queue as on the Storyboard |
| Preview | the video as it would look with what is made so far: the song plays and each shot shows its best file (the finished clip, else the raw clip, else the polished frame, else the draft, else a dark card with the shot's beat), the current lyric line over it; under it the shots coloured by what each has, a click jumps there; space plays, ←/→ the previous and next shot; a click on the picture opens the shot. New files show up at the shot's next turn without stopping the song. The Video view has the exact cut once the video is assembled |
| Video | the video with the song; downloads (the video, every finished clip, the edit list, the edit for DaVinci Resolve and Premiere: `edit.xml`, `edit.edl`); what the video cost (hosted calls and GPU time, by stage: [operations.md](operations.md)); the edit list as a table (each shot's frames, start, length, clip, held frames); **Assemble again** |

**The scene viewer** ([0024](../design/changes/0024-scenes-clips-and-preview.md)): a click on a shot's
picture or clip opens it over the page. At the top, its steps for the take shown: **Draft**,
**Polished** (or **Start frame** when it was drawn from text), **Raw clip**, **Finished clip**. **Wipe**
puts the draft over the polished frame with a slider to move between them; **Side by side** shows them
next to each other; on a clip, **Compare** plays the raw and the finished clip together with the song. On
the right, the redo of what is shown (the frame's on a picture, the clip's on a clip, as on the cards)
and every version of the shot by take, with what made it (the model, the seed, the prompt and when);
versions no take uses (an earlier draft, or one the check drew again) are listed apart. ←/→ go to the
previous and next shot, C compares, Esc closes. It follows the run: a redo's new files appear in it
while it is open.

**Deciding a review** ([0018](../design/changes/0018-lyrics-gate-and-timing.md)): every review has the
same controls on its view and on the Overview's card: a note box, then **Approve** and **Reject with
note** side by side, with a line saying what rejecting does there (the lyrics editor runs again; the
cast or the shots are planned again; at Pick the sheets, **New takes with note**, the note optional;
Review the start frames takes no note: retry a frame on its card). **Reject with note** waits until the
note has text. Pressing **Approve** with a note written asks "You wrote a note. Reject with it
instead?" (**Reject**, **Approve anyway**, **Cancel**). A note you are typing stays when the page
updates live, until you decide.

**The look** ([0016](../design/changes/0016-dashboard-bell-and-options.md)): on the New video form,
**Pace** is calm (longer shots, slow moves), balanced or energetic (shorter shots, more cuts); **Mood**
is free text in any language (right-to-left scripts read right to left), with words to add or take out by a click;
**Style** is free text, or one of four presets to start from (Historical epic film, Dark & moody cinema,
Natural documentary realism, Modern cinematic) that describe a look without naming an era: the era
comes from your story. **Start-frame retries** (0 to 5, default 2): if the judge finds a major problem
in a start frame, it is drawn again with a corrected prompt, up to this many times. **Sheet retries** (0 to
5, default 2): the same for a character's or prop's sheet take.

**The bell** (0016): when any project starts waiting for you at a review, the page rings for 15 seconds
and shows "Waiting for you: *project* — *review*" with **Stop**. It rings once per wait (a few seconds
after the run stops), and again at the next review; a run without stopping for approval rings only
where it stops for you. Browsers play no sound until you click on the page: click **Enable sound** once
(in the sidebar, or in the banner); the page remembers it and unlocks the sound again with your first
click on a later visit. The bell button at the top of the sidebar mutes it. The page must be open in a
tab for the bell to ring; notifications ([operations.md](operations.md)) reach you elsewhere.

**Unattended runs** ([0004](../design/changes/0004-unattended-runs.md)): with "Run without stopping for
my approval" (on the New video form, or the switch at the top of a project) every review is approved as
soon as the run reaches it (except those two), and the sheet takes on offer (the first of each character) are used. It
never approves over errors, and in a project of separate pictures (0020) it always stops at `pick_sheets` and
`review_packs` for you: when the lyrics check or the shot check finds any (even acceptable ones),
the run stops at that review and waits for you ("Stopped: needs you"). Switching a waiting project on
continues its run. The project shows "auto", and each review passed so says "auto-approved".

**Pictures and hosted models** ([0020](../design/changes/0020-owner-sheets-and-frames.md)): every
picture you can redo offers the same menu: the local models, the hosted ones (each with "about $…"),
and **Upload my own picture**. Both gates of the pictures, `pick_sheets` and `review_packs`, always wait
in a new project, also with "Run without stopping for my approval" (the run stops with "needs you");
`review_stills` waits too when you asked to stop after the scenes, unless the project runs without
stopping. The menu is `GET /api/projects/<id>/image-models?for=…`.

**Several shots at once** ([0008](../design/changes/0008-batch-redo.md)): once the run has stopped, tick
shots on their cards (shift-click picks the range from the last one), or drag over the shots on the
song's timeline. The bar over the board then offers **New seed for all**, **New start frame for all**,
their prompts to edit in a list (**Redo the edited shots**), and **Re-plan these shots** with a note.
Each asks first, with what it would take: "7 shots ≈ 55 min of GPU, then the video is assembled
once" (this project's measured time per picture or clip; "an estimate" where §15's times stand in).
Only those shots are made, in one go, and the video is assembled once; earlier versions are kept.
A redo that would remake a file of any other shot (made with other settings or by an older version, or
removed) is refused with the shots and why. A re-plan is one call to the shot planner over the whole song (about $0.6) that may
change only the shots you picked; its proposal shows each changed shot's fields and prompts, now and
proposed, with **Apply** and **Discard** (a project in auto mode applies it at once).

The progress log `events.jsonl` has a `units` event when a stage starts making (what it will make, by
kind) and a `version_started` and a `version_made` event around every picture or clip (its stage, kind,
shot or character, file and time in ms). A run made before them is counted from its folders. A start
frame drawn again (design §10.4) adds a `still_retry` event (`shot`, `take`, `round`, `flags`) and a
new `units` event with the extra draft; `still_retry_unfit` names a frame whose corrected prompt could
not be drawn. `GET /api/settings` gives the defaults, the `paces` and the ranges of `still_retries` and `sheet_retries`.

The JSON API the page uses is in design §13 and decisions D-013, D-031, D-036, D-050 to D-054, D-069, D-070 to D-074 and D-096 to D-099; for scripts, prefer the
Python API (`import hone_music_video as hmv`) or the command line.
