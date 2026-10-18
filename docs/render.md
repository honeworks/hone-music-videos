# Start frames, their check, clips and finishing (stages 10 to 13)

> **Since [0027](../design/changes/0027-hone-frame-is-the-scene-pipeline.md)**:
> the cast, packs, start-frame check, polish, picture menu and their gates described here are gone. The
> plan is written as a Hone Frame project file and the scenes are made in the dashboard's **Scenes** view
> (or `hone-music-video frame ...`, [cli.md](cli.md)); the gates are `review_lyrics`, `review_plan` and
> `review_scenes`. [design/current.md](../design/current.md) §7, §9 to §11 and §13.2 describe it.


After the shot gate the long local stages run with no one watching: about 7 minutes per 5-second shot
with a cast on an 8 GB GPU, about 9 with faces (design §15). Each stage loads its model once and makes
every shot in turn, so the dashboard shows each frame and clip as it arrives, and a run stopped halfway
resumes without remaking the shots it finished.

**`stills`** draws each shot's first frame (design §10). A shot with a cast: Qwen-Image-Edit 2511 4-step
from up to three pack pictures chosen by kind of shot (or the shot's own `refs`), the `{id}`
placeholders named by their pictures, then the Z-Image polish. In a shot whose faces must be
recognisable (`faces`, medium or closer) each person's portrait comes first, one character after
another, and the prompt says each face is its portrait's, so a close-up keeps the face's age and
features. Any other shot (wide, silhouette, turned away) gets no portrait: a person's front and side
views, an animal's side and front views, so the model does not draw a large posed face.
Projects made before keep their own choice (`face_refs`). A shot without
a cast: Z-Image Turbo from text. `still_takes` draws more than one; the first goes on.

**A scene with another model, or your own picture** (0020). A scene's redo can name a model from the menu
(`redo --still --model qwen-image-3.0`, or the Redo panel on the Storyboard) or an upload (`redo --upload
frame.png`). The scene's references go to that model, as many as it takes, the named details first. Every
scene, from any model and an upload too, is polished by the local polish model, then animated as before; a
picture a model drew is checked and drawn again as above, an uploaded one is not checked and not drawn
again. The take records the model and whether it was uploaded. A hosted picture is counted in `costs`
([operations.md](operations.md)).

**Stop after the scenes** (0020). With `quality_gate: "always"` (the New video form's "Stop after the
scenes are drawn", `new --stop-after-scenes`) a run that asks for your approval waits at `review_stills`
once every scene is drawn and checked, so you can change any before the clips are made; a run without
stopping for approval does not stop there. Off by default.

**Changing a scene while the run is busy** (0020). A redo or an upload sent while the run is going is
queued (`current/scene-queue.json`), not refused. While the start frames are being drawn, each queued
scene gets its new picture in the same stage, between two scenes ("will be drawn next"), and its clip is
made from it, with no fork. Sent later (the clips are being made, or the video is finished), it waits;
when the run stops, everything queued is made as **one** fork (like a batch redo): only those scenes'
start frame, clip and finished clip, then the video is assembled once. It is refused, naming the scenes,
when any other scene would be made again. `hone-music-video apply-queue PROJECT` makes the queue at once
on a stopped run (`--dry-run` says what, how long and what it costs); the Storyboard's **Make these now**
does the same.

**Props** (0017). A shot lists the props it shows; each `{prop-id}` in its still prompt becomes the
prop's look word for word, with the numbers of its pictures, and the prop's main and detail views share
the three slots: in an insert, or a close-up without faces, the prop's main view comes first, then the
characters' views, then its detail view; in any other shot each character's first view comes first (the
portrait in a face shot), then the prop's main view, then the rest. So a face keeps its portrait and a
prop gets a slot only when one is free. A shot without a cast that shows a prop with a sheet (an insert
of the armband alone) is drawn by Qwen from the prop's pictures, then polished.

**Start frames that heal themselves** (`still_retries`, 2 by default). Before the polish, the drafts
(and the stills of shots without a cast) are checked in one call. A frame with a major flag gets a
corrected still prompt from the check (its characters' fixed traits stated, the problem avoided) and is
drawn again with a new seed; the frames drawn again are checked again in one call, up to
`still_retries` rounds, and the best-scoring round is polished. Every round is kept, in
`current/checks/still-retries.json` and as a version; the progress log has a `still_retry` event (shot,
take, round, the flags) for each. A redo with a new still goes through the same loop, for that shot
alone. This is not `pick_best_of`: only frames with a major flag are drawn again. Projects made before
draw nothing again.

**`check_stills`** looks at every start frame before any clip is made: one call to the judge
(`models.quality`, Claude Sonnet 5.5 by default: about 110 s and 0.23 USD for 60 shots; Haiku 5.5
costs about 0.01 USD but misses wrong characters and objects out of the story's world; projects made
before keep their judge, D-110) with
contact sheets of the start frames, labelled by shot, and the characters' pictures and fixed traits,
the props' looks and main views,
the story's world and the mood. It goes through each frame in a fixed order: the characters' fixed
traits, the number of people, faces where none were planned, hands and limbs, things out of the story's
world, the mood, the composition asked for, text and style. Each start frame gets a score and flags
(`anatomy`, `wrong-character`, `missing-character`, `extra-people`, `text`, `unwanted-face`,
`off-style`, `anachronism`: out of the story's world, `off-mood`, `composition`, `wrong-prop`: a prop
unlike its look and picture, major for another shape, count or colour), each with its
evidence, major when the frame would mislead the viewer or contradict the cast or the story; the
Storyboard shows them on its card. The same call rewrites each motion prompt to its start frame as
drawn (`rewrite_motion`, on by default): the planned motion kept, the figures named where they are, who
stays still said, never the mouth or speech (a rewrite that names them is dropped). The clip is made
from the rewrite, unless you wrote the motion prompt yourself in a
redo; a start frame keeps the first rewrite written for it, and the Clips view shows the planned and the
rewritten prompt. It does not stop the run unless you ask
(`"quality_gate": "ask"`): then the run waits at **Review the start frames** while a start frame the
video uses has a major flag (minor ones are only shown), so you can redo it before its clip is made,
or approve to go on. `"quality_check": false` skips the call; projects made before this check have it
off.

**Best of 2 or 3** (off by default): with `"pick_best_of": 2` each shot with faces (`"pick_shots":
"all"` for every shot) gets two start frames, and the check picks the better one; only that one is
animated. It costs about 2 minutes of GPU per shot and take; the New video form and the CLI show the
estimate before the run starts, e.g. "Best of 2 on shots with faces: about +54 min of GPU (≈ +2 min per
shot × ~26 shots)" for a 4-minute song.

**`clips`** animates each still with Wan 2.2 I2V 14B (4-step LoRA) from the motion prompt (the check's
rewrite when there is one), at 832x480
(16:9), or 960x544 when the shot has `faces` and the clip is at most 110 frames (longer ones do not fit 8 GB
at that size, D-082), 16 frames a second and one frame longer than the shot
(design §11.1).

**`finish`** makes each clip 1920x1080 at 32 fps in one ComfyUI job: Real-ESRGAN x2, a Lanczos resize to
the output size, RIFE x2 (design §11.3).

Every file is kept as a version named after what made it (`current/shots/<id>/versions/`), with a JSON
record of the model, prompt, seed and inputs beside it; `still.png`, `clip-raw.mp4` and `clip.mp4` in
the shot's folder are the versions the video uses.

## Redo a shot

Any shot can be made again once the shot list is approved and the run has stopped: a new seed (a new
clip from the same still), a new still, or edited prompts. Each redo is a new **take** of the shot; the
old ones stay and you can put any back ("use this version"). A redo runs only that shot, then assembles
the video again (the start frames are checked again first; takes the check picked stay picked). A redo
that would make other shots again too (a project made by an earlier version, say) is refused and names
them. A run made by an earlier version resumes as a fork that keeps everything it finished.

```text
hone-music-video redo projects/my-song S004 --seed
hone-music-video redo projects/my-song S004 --motion-prompt "Static camera. She turns her head."
hone-music-video use projects/my-song S004 1        # back to its first take
```

From Python: `hmv.redo(project, models, "S004", hmv.Redo(seed=True))`, `hmv.use(project, models, "S004", 0)`;
from the dashboard: the Storyboard. See [examples/redo_a_shot.py](../examples/redo_a_shot.py).

## Setting up the local models

They run on [ComfyUI](https://github.com/comfyanonymous/ComfyUI) through hone-models.

- Set `HONE_COMFYUI_START` to the command that starts ComfyUI (for example `~/ComfyUI/start.sh --port
  8188`); each stage starts it, uses it and stops it. `HONE_COMFYUI_URL` is its address (default
  `http://127.0.0.1:8188`). A ComfyUI you started yourself is used as it is.
- The models (in ComfyUI's model folders): Z-Image Turbo (sheets, start frames from text, the polish),
  Qwen-Image-Edit 2511 Q4_K_M GGUF with the lightx2v 4-step Lightning LoRA (portraits, start frames),
  Wan 2.2 I2V 14B fp8 high and low noise with the lightx2v 4-step LoRA (clips), Real-ESRGAN x2plus and
  RIFE 4.9 (finishing), with the custom nodes their workflows use (`src/hone_music_video/data/workflows/`).
  hone-models' `hone-models models install <id>` prints the download commands of an entry that lists its
  files.
- For the clips the library adds `--use-sage-attention` to `HONE_COMFYUI_START` (only the Wan 2.2 I2V
  14B workflow). ComfyUI's Python needs SageAttention 2.2. A prebuilt wheel matching ComfyUI's torch and
  CUDA works too; the rollback is
  `uv pip install --python ~/ComfyUI/.venv/bin/python --no-deps sageattention==1.0.6`. Set
  `HONE_COMFYUI_PYTHON=~/ComfyUI/.venv/bin/python` so each clip's record shows the version.

  ```bash
  git clone https://github.com/thu-ml/SageAttention ~/build/SageAttention && cd ~/build/SageAttention
  sed -i 's/-std=c++17/-std=c++20/g' setup.py          # torch 2.9 and later need C++20
  export TORCH_CUDA_ARCH_LIST="8.9"                     # your GPU's architecture (8.9: RTX 40xx)
  uv build --wheel --no-build-isolation --python ~/ComfyUI/.venv/bin/python
  uv pip install --python ~/ComfyUI/.venv/bin/python --no-deps dist/sageattention-2.2.0-*.whl
  ```
