# The shot plan (stages 8 and 9)

> **Since [0027](../design/changes/0027-hone-frame-is-the-scene-pipeline.md)**:
> the cast, packs, start-frame check, polish, picture menu and their gates described here are gone. The
> plan is written as a Hone Frame project file and the scenes are made in the dashboard's **Scenes** view
> (or `hone-music-video frame ...`, [cli.md](cli.md)); the gates are `review_lyrics`, `review_plan` and
> `review_scenes`. [design/current.md](../design/current.md) §7, §9 to §11 and §13.2 describe it.


Every shot of the video is planned in **one** call, never one call per shot (design §7.3, §8).

**`plan_shots`** sends the shot planner the timed lyrics with every word's times, the story, the anchor,
the story's world (what belongs in it and what must not appear), the pace's preferred shot length, the
cast with each character's fixed `traits` and front view and portrait as images, the settings as
data and the written limits of the local models (design §8: one action and one camera move per shot,
faces large enough to recognise, at most 8 s, no text in the picture, no one speaks or sings, a motion
prompt never names the mouth, lips, jaw, breath, speech or words, not even negated (the clip model does
not follow negations), say who and what stays still, nothing enters the frame unplanned, fire only at its source, crowds with an explicit
state and a static camera, no tangled contact poses...). Every still prompt begins with the anchor, and
a character's traits never change unless the story changes them; nothing the world forbids is named.
The pace sets the shot lengths and where to cut, the mood the light, colour, camera speed, stillness and
how open the faces are. It returns every shot: start and end in
milliseconds, the lines sung over it, the story beat, framing, `faces`, cast, the props it shows
(`props`, each written as `{prop-id}` in the still prompt, never in the planner's own words), location,
camera, the
**still prompt** (the first frame) and the **motion prompt** (only motion and camera).

**`check_shots`** checks the plan against the timed lyrics (design §5.2). Errors: the shots must tile the
song exactly (the first starts at 0, each where the previous ends, the last at `duration_ms`), no cut
inside a sung word, shot lengths within `min_shot_ms` and `max_shot_ms`, every line listed by a shot
it overlaps, known cast, props (`unknown-prop`) and placeholders (a `{prop-id}` only in a shot that lists
the prop), `faces` only on medium or closer framing, prompts within their
length. Warnings: cuts far from a line, section or instrumental edge; three equal framings in a row; a
character missing for a long stretch; `speech`: a prompt with a word of speech (speak, say, sing,
whisper, talk, call out, recite, chant, mouth the words, lips move; never smile, laugh, shout, roar, gasp
or cry), since the video has no lip sync, and in a motion prompt also a word of the mouth (mouth, lips,
jaw, teeth, breath, voice, words), negated or not; `no-anchor`: a still prompt without the anchor;
`pace`: a shot outside the length its pace prefers (not the last). Warnings never
go back to the planner. Each finding names the shot, the rule and the amount in ms.

**Repairs.** Errors go back to the planner with the whole plan, at most twice. What remains is shown at
**the shot gate (`review_shots`)**: errors that would break the video (tiling, cuts in words, cast,
placeholders, ids, empty prompts) block it; the others you may approve with an explicit
acknowledgement. You can always plan the shots again with a note.

```text
hone-music-video check-shots projects/my-song               # every error and warning
hone-music-video approve projects/my-song --accept-errors   # keep errors that do not break the video
hone-music-video reject projects/my-song --note "more close-ups in the chorus"
```

The approved plan is `current/shots.json` (design §4.3). **Cost:** about $0.6 for a five-minute song.

## Re-plan a few shots

Once the video is made, a few shots can be planned again with a note, without touching the others
([0008](../design/changes/0008-batch-redo.md)):

```text
hone-music-video replan projects/my-song S012-S015 --note "show the duel from a distance"
hone-music-video replan projects/my-song --apply      # or --discard
```

It is one call to the shot planner over the whole song (never one per shot), with the whole current
plan, the shots to change and your note, and the rule "change only these shots; keep every other shot
exactly; keep their times unless the note asks". The reply is checked: the same shots in the same
order, every other shot unchanged, no new check error (the song stays tiled). A reply that fails goes
back once with the problems; if it fails again nothing changes and the error shows how the reply
differed. The proposal shows each changed shot as it is and as proposed, the calls' cost as recorded
(else about $0.6 a call, marked as an estimate) and how long making them should take. Applying it
makes only the changed shots (their takes start again from the new prompts) and assembles the video
once; the Shots view and `check-shots` then show the applied plan's findings. A project in auto mode
applies it at once. While a proposal waits, redos wait too: apply or discard it first. From Python:
`hmv.replan`, `hmv.apply_replan`, `hmv.discard_replan`; on the Storyboard: **Re-plan these shots**.
