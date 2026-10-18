# The command line

Every command takes the project's folder (`projects/my-song`) except `new` and `dashboard`. Exit codes:
0 success (also a run that stops at a gate), 1 failure (`error: ...` is printed), 2 a usage error.
`--fake-models` runs the stages on fake models; `--json` prints the run's state as JSON.

Since change [0027](../design/changes/0027-hone-frame-is-the-scene-pipeline.md)
the scenes are made the Hone Frame way: the plan is written as a Hone Frame project file, `frame ...`
does Hone Frame's actions on it, and `remake` makes again only the clips of the scenes that changed.

| Command | What it does |
|---|---|
| `new NAME --song FILE [--lyrics FILE] [--story TEXT] [--feeling TEXT] [--prepare] [--sheet NAME=FILE[:NOTE]] [--pose NAME=FILE[:NOTE]] [--settings FILE] [--pace calm\|balanced\|energetic] [--mood TEXT] [--projects DIR] [--auto-approve]` | make a project; the settings are a JSON file (unknown keys refused; `models.frame` lists the scenes' image models, the first the default), `--pace` and `--mood` win over the file; `--pose` gives a pose picture a character's variant takes; `--auto-approve` runs it without stopping for approval (each hold accepted, each pick its first picture), except at a review whose check finds errors (0004); `--feeling` says what the viewer should feel and how it changes (0028); `--prepare` stops the run before the scenes with every hosted call made, and `resume` makes the rest offline (0028); the models whose licence forbids commercial use are printed |
| `run PROJECT` | start the run; it goes to the first gate |
| `resume PROJECT` | continue the run (after a gate decision, a crash or a stop) |
| `status PROJECT` | the run and every stage |
| `approve PROJECT [--gate G] [--note T]` | approve the gate waiting; at `review_scenes` the scenes as they are (refused while a scene has no picture in use) |
| `reject PROJECT --note T [--gate G]` | run the gate's stage again with a note (the lyrics, or the plan); after timing edits the lyrics editor is asked to change the text only (0018) |
| `lyrics-timing PROJECT LINE=START-END ... [LINE=-]` | at `review_lyrics`: set lines' start and end in ms by hand (`L012=77300-81200`; `L012=-` takes the edit back); checked, kept in `current/lyrics/`, used by `approve`; prints the check and exits 1 on errors (0018) |
| `check-shots PROJECT` | every error and warning of the planned shot list; exit 1 with errors |
| `frame status PROJECT` | every item of the frame project: status, picture in use, versions, flags, mark; the run |
| `frame run PROJECT` | make the marked items, top to bottom (the demo first) |
| `frame accept PROJECT ITEM [VERSION]` | accept a held item, or pick one of its pictures (a scene's takes never wait: its first picture is used; `frame use` swaps in another, then `remake`) |
| `frame use PROJECT ITEM VERSION [--dependants]` | make an older version the one in use |
| `frame redo PROJECT ITEM [--dependants]` | mark an item to make again (`--dependants`: the items made from it too) |
| `frame unmark PROJECT ITEM` | clear an item's mark |
| `frame run-prompt PROJECT ITEM N` | an item with several prompts: mark it to make prompt N (from 1) beside its picture in use, nothing made from it; `frame run` makes it (0033) |
| `frame replace PROJECT ITEM FILE [--dependants]` | your own picture as a new version of the item |
| `frame edit PROJECT ITEM FIELD=VALUE ...` | change an item's fields (`prompt="..."`, `seed=7`, `hold=true`, `count=null`); checked like an import, written back keeping the file's comments |
| `frame guide PROJECT` | the prompt guide for the project's models |
| `redo PROJECT SHOT... [--later]` | new clip seeds for these shots (ids or ranges like `S012-S015`), then `remake`; `--later` only saves them |
| `motion PROJECT SHOT TEXT` | set a shot's motion prompt; `remake` makes its clip again |
| `remake PROJECT` | make the clips of the shots whose scene picture, motion prompt or seed changed, and cut the video again; every other clip is kept |
| `pause PROJECT [--now]` | pause the running video after the file being made, or stop it at once (0022) |
| `assemble PROJECT` | cut the video again from the finished clips (no model is called) |
| `export PROJECT` | write the edit for DaVinci Resolve and Premiere again (`edit.xml`, `edit.edl`; [operations.md](operations.md)) |
| `costs PROJECT [--json]` | what the video cost: hosted calls and GPU time by stage; writes `current/costs.json` |
| `dashboard [--projects DIR] [--port N]` | serve the dashboard on localhost |

```text
hone-music-video new "My song" --song song.mp3 --lyrics lyrics.txt --sheet "Darvin=darvin.png:the hero"
hone-music-video run projects/my-song                       # to review_lyrics
hone-music-video approve projects/my-song && hone-music-video resume projects/my-song   # the plan
hone-music-video approve projects/my-song && hone-music-video resume projects/my-song   # the scenes
hone-music-video frame status projects/my-song              # demo.3 waits: the demo is held
hone-music-video frame accept projects/my-song demo.3
hone-music-video frame run projects/my-song                 # the rest, top to bottom
hone-music-video frame accept projects/my-song S012 2       # the second picture of a scene with several
hone-music-video frame edit projects/my-song oasis.wide prompt="Dawn over a desert oasis, ..."
hone-music-video frame redo projects/my-song oasis.wide --dependants   # and the scenes made from it
hone-music-video frame run projects/my-song
hone-music-video approve projects/my-song && hone-music-video resume projects/my-song   # clips, video
hone-music-video motion projects/my-song S004 "Slow push in; her scarf moves in the wind."
hone-music-video redo projects/my-song S007 --later
hone-music-video remake projects/my-song                    # only S004's and S007's clips, then the cut
```
