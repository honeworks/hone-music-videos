# Settings

Settings are given with the song (the New video form, `new --settings settings.json`, or
`hmv.create_project(..., settings={...})`) and validated: an unknown key is refused, and so is a value
that does not fit (design §2.3). They reach the planners as data; you never write them into a prompt.
On the command line `new --pace calm --mood "tragic" --still-retries 3 --sheet-retries 2` sets the project options
(a flag wins over the same key in `--settings`); the API takes them in `settings`. Projects made before an option read it as its old
behaviour: `pace` balanced, no mood, no start frame or sheet take drawn again.

| Setting | Default | Meaning |
|---|---|---|
| `style` | `"photoreal live-action film, 35mm film look, natural film grain"` | the look, a phrase the planners weave into every prompt |
| `aspect_ratio` | `"16:9"` | also `"9:16"`, `"1:1"`, `"4:5"` |
| `resolution` | `1080` | the short side of the finished video, in pixels |
| `fps` | `32` | the video's frame rate; only 32 (Wan's 16 fps doubled by RIFE) |
| `min_shot_ms` / `max_shot_ms` | `2000` / `8000` | shot length limits (8 s is the clip model's tested maximum) |
| `still_takes` | `1` | start frames drawn per shot; the first goes on to its clip |
| `quality_check` | `true` | one hosted vision call checks every start frame before the clips ([render.md](render.md)) |
| `quality_gate` | `"off"` | `"ask"`: wait before the clips when a start frame the video uses has a major flag; `"always"`: wait after every scene is drawn and checked, to change any before the clips (`new --stop-after-scenes`; an unattended project does not wait there, 0020) |
| `rewrite_motion` | `true` | the check also rewrites each motion prompt to its start frame as drawn, and the clip uses it (only with `quality_check`; a motion prompt you write in a redo is used as it is) |
| `face_refs` | `"by-shot"` | the references by kind of shot: in a close-up or medium shot with faces each person's portrait first, in any other shot no portrait; `"portrait-first"` (0006: the portrait first in face shots only) and `"front-first"` (before 0006) are what older projects keep |
| `pick_best_of` | `1` | `2` or `3`: that many start frames for the chosen shots, the check picks the best; about +2 min of GPU per shot and extra take (needs `quality_check`) |
| `pick_shots` | `"faces"` | the shots `pick_best_of` chooses: those with faces, or `"all"` |
| `packs` | `"views"` | `"views"`: a character's pictures are separate (front, side, back, portrait and details), one picture per prop; `"sheet"`: the four-figure turnaround sheet and the cutter. Projects made before 0020 read `"sheet"` ([cast.md](cast.md)) |
| `sheet_takes` | `4` | turnaround takes per character, to pick from (only with `packs: "sheet"`) |
| `prop_sheet_takes` | `4` | sheet takes per prop with a look, to pick from (0017; only with `packs: "sheet"`) |
| `language` | `null` | the sung language, when known (passed to the transcriber) |
| `pace` | `"balanced"` | `"calm"`: long shots (about 6.5 to 8 s), few cuts inside a verse, cuts on line or section starts; `"energetic"`: short shots (2 to 4.5 s); `check-shots` warns `pace` on a shot outside that length |
| `mood` | `""` | the mood in free words, any language ("tragic", "tender, hopeful", "dark, دلهره‌آور"): it sets the light, colour, camera speed, how still the motion is and how open the faces are |
| `take_clips` | `"picked"` | which takes of a scene get clips: `"picked"`, only the one in use (another take gets its clip when you pick it and remake); `"all"`, every take overnight, so a later pick only cuts the video again (0031) |
| `still_retries` | `2` | `0` to `5`: a start frame whose draft has a major flag is drawn again from the check's corrected prompt, at most this many rounds, before its polish and clip ([render.md](render.md)); needs `quality_check` |
| `sheet_retries` | `2` | `0` to `5`: a sheet take the judge gives a major flag (the wrong number of figures, a trait missing or changing between views) is drawn again from its corrected prompt, at most this many rounds ([cast.md](cast.md)); needs `quality_check` |
| `models` | below | the hone-models registry id per role |

| Role (`models.<role>`) | Default | Used for |
|---|---|---|
| `speech` | `scribe_v2` | word times (OpenAI-compatible gateway; `whisper-1`, `scribe_v1`, `groq.whisper-large-v3` and `groq.whisper-large-v3-turbo` work too) |
| `lyrics`, `cast`, `shots` | `claude-opus-5-5` | the three planners (an OpenAI-compatible gateway) |
| `quality` | `claude-sonnet-5-5` | the check of the start frames (an OpenAI-compatible gateway); about 0.23 USD a check of 59 frames, retries a few cents more; `claude-haiku-5-5` costs about 0.01 USD but misses wrong characters and objects out of the story's world (D-110) |
| `sheets` | `z-image-turbo` | a character's first picture and a prop's picture (turnaround sheets with `packs: "sheet"`), start frames without a cast |
| `views` | `qwen-image-edit-2511-4step` | a character's side, back, portrait and details, drawn from its first picture (a model that takes reference pictures); a project stored without it reads `models.stills` (0020) |
| `stills` | `qwen-image-edit-2511-4step` | portraits and start frames with a cast |
| `polish` | `z-image-turbo-polish` | the polish pass |
| `clips` | `wan2.2-i2v-14b` | clips |
| `finish` | `esrgan-rife-x2` | upscaling, resize and frame interpolation, one job per clip |
| `vocals` | `htdemucs` | the song's vocals for the first listen (Demucs on the CPU, the `separate` extra; not a registry id) |
| `align` | `MMS_FA` | given lyrics aligned to the vocals (torchaudio's MMS forced aligner on the CPU, the `align` extra; not a registry id); `null` turns it off, and projects made before it read as `null` |

`models.sheets`, `models.views` and `models.stills` may name a hosted model (`image-models` lists them
with their estimates; on the command line `new --sheets-model`, `--views-model`, `--stills-model`, on the
New video form a list for each). A hosted default is paid for on every picture of its kind; the cost is
printed or shown before the run starts. `views` and `stills` are refused if the model takes no
reference pictures (when the plan has a cast). The polish (`models.polish`) is always local.

Sizes per aspect ratio (start frame, clip, clip with faces): 16:9 1024x576, 832x480, 960x544; 9:16
576x1024, 480x832, 544x960; 1:1 768x768, 624x624, 720x720; 4:5 704x880, 576x720, 640x800 (D-030). A face clip longer than 110 frames (6.8 s) uses the clip size
(D-082).

```json
{"aspect_ratio": "9:16", "style": "hand-painted animation, warm light", "max_shot_ms": 6000}
```

**Environment.** `OPENAI_COMPATIBLE_API_KEY` (the hosted models; or a `.env` file in the working folder, never
committed), `OPENAI_COMPATIBLE_BASE_URL` (another gateway address), `HONE_COMFYUI_START` and `HONE_COMFYUI_URL` (the
local models, [render.md](render.md)). The library's registry entries can be overridden in
`~/.config/hone/models.toml` or a `hone-models.toml` in the working folder.
