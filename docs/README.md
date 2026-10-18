# hone-music-video guides

A guide per part of the flow. The design behind them is [design/current.md](../design/current.md); the
section numbers there (design §5.3) are the ones the code and these guides refer to.

| Guide | What it covers |
|---|---|
| [lyrics.md](lyrics.md) | stages 1 to 4: the song measured, the words heard, the timed lyrics and their checks; the lyrics gate |
| [cast.md](cast.md) | stages 5 to 7: the cast plan, the turnaround sheets, picking a take, the character packs |
| [shots.md](shots.md) | stages 8 and 9: the shot plan, its checks and repairs; the shot gate |
| [render.md](render.md) | stages 10 to 13: start frames and their check, clips, finishing; redoing a shot |
| [assembly.md](assembly.md) | stage 14: the video cut to the millisecond, the edit list, assembling again |
| [operations.md](operations.md) | notifications (Slack, Telegram, ...), what a video cost, the edit for DaVinci Resolve and Premiere |
| [dashboard.md](dashboard.md) | the web dashboard: every view and what it does |
| [cli.md](cli.md) | every `hone-music-video` command |
| [settings.md](settings.md) | every setting and model role, with its default |
| [troubleshooting.md](troubleshooting.md) | what to do when a stage stops |

A project is a folder (design §4): `project.json` (the name, settings and inputs), `input/` (the song,
lyrics and given sheets), `events.jsonl` (the progress log), `runs/` (the resumable run) and `current/`
(the accepted plans, every picture and clip made, kept as versions, and the video). Times in every
record are integer milliseconds.
