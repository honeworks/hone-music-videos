# Notifications, what a video cost, and the edit for editors

> **Since [0027](../design/changes/0027-hone-frame-is-the-scene-pipeline.md)**:
> the cast, packs, start-frame check, polish, picture menu and their gates described here are gone. The
> plan is written as a Hone Frame project file and the scenes are made in the dashboard's **Scenes** view
> (or `hone-music-video frame ...`, [cli.md](cli.md)); the gates are `review_lyrics`, `review_plan` and
> `review_scenes`. [design/current.md](../design/current.md) §7, §9 to §11 and §13.2 describe it.


Three things for a video that runs overnight (design §12.1, §13.4, §13.5; change
[0007](../design/changes/0007-operations.md)).

## Notifications

The run sends one message when it **stops at a gate** for you (the gate is named: `review_lyrics`,
`review_cast`, `pick_sheets`, `review_packs`, `review_shots`), when **a stage fails** (the stage and its first error
line) and when **the video is done**. Each message names the project and links to its page on the
dashboard:

```text
video · run 20261010T100654Z-bfcb16 awaiting_review
The Long Night
1 item awaiting review at review_shots
/home/me/videos/projects/the-long-night/runs/video/runs/20261010T100654Z-bfcb16/
http://localhost:8794/#/p/the-long-night
event 20261010T100654Z-bfcb16/run.awaiting_review/4
```

Set it up in the environment, or in the `.env` file of the folder you run `hone-music-video` from (the
same file as `OPENAI_COMPATIBLE_API_KEY`; never commit it):

| Variable | Meaning |
|---|---|
| `HONE_MV_NOTIFY_URL` | the webhook URL; without it nothing is sent |
| `HONE_MV_NOTIFY_KIND` | `slack` (the default), `mattermost`, `discord`, `telegram` or `http` |
| `HONE_MV_DASHBOARD_URL` | the dashboard's address in the link (default `http://localhost:8794`) |

```text
# Slack, Mattermost or Discord: the channel's incoming webhook
HONE_MV_NOTIFY_URL=https://hooks.slack.com/services/T000/B000/XXXX

# Telegram: your bot's token (from @BotFather) and your chat's id in the sendMessage URL
HONE_MV_NOTIFY_URL=https://api.telegram.org/bot123456:ABC-your-token/sendMessage?chat_id=987654321
HONE_MV_NOTIFY_KIND=telegram

# any HTTP endpoint: a JSON POST (event, project label, summary, link) with an Idempotency-Key header
HONE_MV_NOTIFY_URL=https://example.org/hooks/hone
HONE_MV_NOTIFY_KIND=http
```

To find your Telegram chat id, send your bot a message, then open
`https://api.telegram.org/bot<token>/getUpdates` and read `message.chat.id`.

The URL is a secret: it is read when a message is sent and written nowhere (not in the run, the
project's files or any log). Each delivery's result is kept in the run's `manifest.json`
(`notifications`, with the variable's name only); a message that cannot be sent never stops the run
and is not sent again by itself. A process that dies (a crash, a reboot) sends nothing: check the
dashboard when no message comes.

## What a video cost

```text
hone-music-video costs projects/my-song
my-song: $1.42 of hosted calls, 7.9 h of GPU
  reruns and redos added $0.63 and 0.4 h
  measure       cpu         0.0 min  $0.0000
  transcribe    hosted      1.0 min  $0.0310
  ...
```

The same is in the Video view ("This video cost $1.42 of hosted calls and 7.9 h of GPU", then each stage) and
in `current/costs.json`. Everything comes from what was recorded: each stage's time from the run's
records (every attempt, in every run of the project), the planners' prices from hone-models' record of
each call (the start-frame check's too), the transcriptions' from `words.json`. Each stage is split into the first pass, reruns (a
stage run again after you rejected its gate, or after it failed) and redos (redone shots, assembling
again). Hosted pictures (a model of the menu, [cast.md](cast.md)) are counted in the stage that drew them (sheets, packs, stills): hone-models records a hosted picture's price, and a Gemini picture's price is kept in its version record (D-134). The menu shows an estimate before each choice, marked "about", and the New video form and `new` show the estimate of the whole video when a default model is hosted; what `costs` reports is the recorded price. A hosted call without a recorded price, a transcription that failed, and a planner stage
whose call hone-models has no record of are counted as unknown ("+ ?"), never guessed. GPU time is
the time of the GPU stages (sheets, packs, start frames, clips, finishing), model loads included.

Run `costs` from the folder the runs ran in: hone-models keeps its record of the calls in
`.hone/models/spans.db` there (or under `$HONE_HOME`); without it, `costs` says "no hone-models records
found at ..." and the planners' calls are unknown. `current/costs.json` is written after every run,
resume, redo and assembly.

## The edit for editors

Beside `edl.json`, the assembly writes the same edit as `current/edit.xml` (Final Cut Pro 7 XML) and
`current/edit.edl` (CMX3600). Both are in the Video view's downloads.

- **DaVinci Resolve:** File > Import > Timeline, choose `edit.xml`.
- **Premiere Pro:** File > Import, choose `edit.xml`.

Video track 1 has every finished clip at its frames (named by its shot: `S001`, `S002`, ...), audio track
1 the song from the start, at the video's frame rate (32 fps by default). The clips are linked by their
paths on this machine; after moving the project, relink the media. A clip shorter than its shot (rare,
see [assembly.md](assembly.md)) ends at its own last frame, leaving a gap the video fills by holding the
frame.

For a video assembled before these files existed:

```text
hone-music-video export projects/my-song
```
