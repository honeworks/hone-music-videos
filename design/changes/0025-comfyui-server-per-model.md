# 0025: Each model runs on the ComfyUI it needs, a blank picture is never kept, Wan runs on SageAttention 2.2, and the polish can be turned off

## Status

`implemented in 0.1` (accepted by the maintainer 2026-10-12, built 2026-10-12) for §1 to §6; Part
B is hone-models' own record, later. Its smaller choices are D-155 to D-160 in
[decisions.md](../decisions.md).

## Context

On *isolde-the-forgotten-wife* (2026-10-12) every scene redone with `qwen-image-edit-2511-4step` came out
black: eight drafts of about 5 KB each (S002 twice, S006, S008, S016, S020, S026, S043). The polish copied
the black, and the redo put it in use. The same model, with the same references and size, made good pictures
at 23:47 to 23:51 the evening before (S038, S043, S058).

What happened:

1. At 00:12 the dashboard's runner started the clips stage. Per D-033 the adapter adds
   `--use-sage-attention` to `HONE_COMFYUI_START` while a Wan session starts the server, so hone-models
   started ComfyUI with SageAttention for every model it runs.
2. Seconds later the dashboard was stopped with Ctrl-C. `Dashboard.close()` stops the HTTP server and puts
   `None` on the runner's queue, but it does not wait for the runner. That thread is a daemon thread, so it
   died with the process, and the session's `finally` block never ran. That block is the one that stops a
   server the session started. hone-models starts the server in its own process group, so Ctrl-C did not
   reach it either. Its parent is now `systemd --user`.
3. From then on every process found a server that answers. hone-models uses a server that already runs
   "as it is" (`_comfyui_server.running`), so the next dashboard's clips, and every picture redo after the
   run ended, ran on that SageAttention server.
4. Qwen-Image-Edit gives NaNs under SageAttention, which become an all-black picture. Wan is fine with it.
5. Nothing noticed: this project has `quality_check = false`, and no step looks for a blank picture.

D-033 assumed that a SageAttention server lives only as long as the Wan session that started it. One
interrupted dashboard broke that assumption, silently, for hours.

ComfyUI reports the flags it was started with (`GET /system_stats` gives `system.argv`, checked on ComfyUI
0.37.0), so a client can see which kind of server it is talking to.

The clips are also the slowest stage: about 4 to 6 minutes per shot on the reference machine (RTX 4060
Laptop 8 GB, 30 GB RAM), 67 shots in *isolde*. A trial the same day (2026-10-12, `experiments/video-speed`,
not committed) remade five of its shots (a close-up face, a run, two faces, arms in wind, a sword stroke)
with each clip's own start frame, prompt, seed, size and length:

| Setup | Five shots | Look |
|---|---|---|
| Wan 2.2 I2V 14B as built (fp8, lightx2v 4 steps, SageAttention 1.0.6) | 1427 s | the reference |
| the same on **SageAttention 2.2** (its fp8 kernels for RTX 40xx) | 1231 s | the same (same seeds) |
| the same plus ComfyUI's `--fast fp8_matrix_mult` | 1229 s | the same |
| Wan 2.2 TI2V-5B Turbo, 4 steps, at the pipeline's sizes | 529 s | worse: washed-out faces, light and colour drift from the start frame, stray objects |
| Wan 2.2 TI2V-5B Turbo at its native 1280×704 | 1858 s | better than above, still worse than 14B |

A back-to-back A/B with only the SageAttention version changed, both with the owner's `--reserve-vram 1.5`,
gave 256.7 → 225.0 s and 206.9 → 182.9 s: **12% faster**, from the version alone. The installed package was
1.0.6 because the docs say `pip install sageattention`, which installs the Triton-only 1.x; 2.2 has to be
built from source (no wheel for torch 2.14 and CUDA 13.0), and its `setup.py` asks for C++17 where torch
2.14 needs C++20. Also found: Wan 2.2 5B gives noise under SageAttention, so the "Wan wants SageAttention"
rule of D-033 holds for the 14B image-to-video model, not for every Wan.

## Problem

1. A ComfyUI started for one kind of model outlives its session when the dashboard is interrupted. Later,
   other models run on it with the wrong setup.
2. Nothing checks that the running server suits the model about to use it.
3. A blank picture or clip is kept as a version, polished, and put in use.
4. The clips run on SageAttention 1.x, 12% slower than they could on this GPU, because the documented
   install gives that version.
5. Every start frame is polished, and there is no way to make a video without the polish short of editing
   the code, though 0023 found that it can change faces and props.

## Options

- **Leave it as it is**, and document "after a Ctrl-C, stop ComfyUI yourself". This depends on the owner
  remembering, and the failure is silent. Rejected.
- **Two servers**, a plain one on 8188 and a SageAttention one on another port, each model sent to its own.
  Simple routing, but every ComfyUI holds its models in RAM: the one running now holds 16 GB, half the
  machine. Two would swap. Rejected.
- **SageAttention per workflow:** drop the server flag and patch only the Wan model inside its workflow,
  with ComfyUI-KJNodes' SageAttention node. One plain server would then suit every model, and a leftover
  server would be harmless. But it needs a custom node installed in ComfyUI, which D-033 avoided on
  purpose, and Wan's speed would have to be measured again. This is the alternative if the owner prefers
  one server setup over the check below.
- **Chosen: the library owns the server's lifetime and checks the server before each model, and a blank
  output is refused.** This is §1 to §4 below.

For the clips' speed (§5):

- **A smaller clip model** (Wan 2.2 TI2V-5B Turbo): 2.7× faster, but it drifts from the start frame and
  breaks faces, which the cast-driven shots cannot afford. Its 24 fps would also change the finish's
  16 → 32 fps (D-004). Rejected for now.
- **Wan 14B as GGUF** (Q4/Q5): with 4 steps the time is compute, not weights moving from RAM, and GGUF
  does not lower compute. Not tried.
- **LTX-2.5 distilled** (int8): gated on Hugging Face, about 40 GB, and its transformer plus text encoder
  (37 GB) do not fit the machine's 30 GB of RAM. Not tried; the next candidate on a bigger machine.
- **ComfyUI `--fast`**: no gain measured. Rejected.
- **Chosen: SageAttention 2.2 in ComfyUI's Python**, the same flag and the same look, 12% faster.

For the polish (§6):

- **Wait for 0023's polish with references.** It is experiments first and may still harm some frames;
  the owner wants to make videos without the polish now. Rejected as the only answer.
- **Chosen: a project setting**, off for new projects, with room for the owner's later polish modes.

## Decision

### 1. Each ComfyUI model says what server it needs (A)

The rule of D-033 becomes the model's need, narrowed to what was measured: a ComfyUI model whose workflow
runs the Wan 2.2 **I2V 14B** experts wants SageAttention. Every other ComfyUI model (Qwen-Image,
Qwen-Image-Edit, Z-Image, the polish, the finish, and any other video model, the Wan 2.2 5B among them,
until it is measured) wants a server without it. The rule stays in the adapter, read from the workflow's
diffusion loaders as today. The registry gets no new field.

### 2. The adapter checks the running server before using it (A)

Before a ComfyUI session or plain call, the adapter reads `system.argv` from `/system_stats` once and
compares it with the model's need.

| Server | Model wants SageAttention | Model wants a plain server |
|---|---|---|
| none running | started with the flag (D-033, as today) | started without it (as today) |
| plain | used (slower; a warning, as today) | used |
| SageAttention, a leftover hone-models started (Part B), idle | replaced: stopped, started with the flag | replaced: stopped, started without it |
| SageAttention, busy, or started by the owner | used | refused: `ModelFailure("ComfyUI at <url> runs with --use-sage-attention, which makes <model>'s pictures black: let its job end, or restart it without the flag")` |

"Busy" means `/queue` has a running or pending job, or a hone-models GPU lease is held for that server.
A server another process is using is never stopped. The refusal is shown on the shot or picture like any
other model failure, and nothing is kept.

### 3. The dashboard stops its runner before it exits (A)

On Ctrl-C or SIGTERM, `Dashboard.close()` asks the busy project to Stop (0022: the request file and
ComfyUI's `/interrupt`), then waits for the runner thread for up to `CLOSE_WAIT_S = 60` seconds. That lets
every open session's `finally` block run, which stops the server the session started. A second Ctrl-C
exits at once and logs "a ComfyUI started by this dashboard may still be running". The run is resumable
as after any Stop (D-009).

### 4. A blank picture or clip is refused (A)

When a generated file is made (`_jobs`), a picture whose pixels all lie within 2 levels of one colour on
every channel (read at 64×36) is refused. So is a clip whose first, middle and last frames all are. The
refusal raises `ModelFailure("<model> returned a blank picture")`, and the file is not kept as a version
or put in use. A stage with retries draws again in its next round. Otherwise the stage, redo or picture
fails with that message. Uploaded pictures are not checked: the owner chose them.

### 5. Wan's clips run on SageAttention 2.2 (A)

The flag, its rule (§1) and the workflow stay as they are; the documented setup changes, so a new machine
gets the faster kernels:

- `README.md`, `docs/render.md` and `docs/troubleshooting.md` give the 2.2 build instead of
  `pip install sageattention`: clone `thu-ml/SageAttention`, build a wheel against ComfyUI's Python with
  `TORCH_CUDA_ARCH_LIST` set to the GPU's architecture and `-std=c++20` in its `setup.py` for torch 2.9
  and later (`uv build --wheel --no-build-isolation --python <ComfyUI python>`), install it with
  `--no-deps`. A prebuilt wheel that matches ComfyUI's torch and CUDA is fine too. The rollback is
  `sageattention==1.0.6`.
- §15's per-unit times (`progress.DEFAULT_MS`, the estimate before a run) are measured again on 2.2.
- The adapter reports the SageAttention version it ran with once per clips session, in the session's
  span (`hone.music_video.sage_attention`, read with ComfyUI's own Python from the start command's
  interpreter when the command is a Python one, else `unknown`), so a slow machine on 1.x shows in the
  run's records instead of only in its times. It is never a refusal: 1.x still works.

### 6. The polish can be turned off for a video (A)

Today every start frame is drawn and then polished (§10.2: Z-Image Turbo image-to-image at 0.3). 0023
found that the polish can harm (it changes faces and props, with no references), and the owner tested a
video without it by editing the code (`TEMP_NO_POLISH`, discarded). That becomes a setting:

- `Settings.polish: Literal["on", "off"] = "off"` for a new project (the owner, 2026-10-12). A choice
  rather than a flag, so the owner's later polish modes add values to the same setting.
- It covers the start frames only. A character's first picture (stage 6) and portrait (stage 7) keep
  their polish.
- `off`: a start frame is its draft. Stage 10 makes no polish job, loads no polish model, and its chosen
  file (`still.png`) is the draft. The drafts' keys do not change, so a shot left as it is keeps its draft.
  Polishing drafts already made, without drawing them again, is left for a later polish mode (D-155).
  Retries (0015), the start-frame check (§10.3) and the clips are
  unchanged: they read the start frame, whichever it is.
- It is set when the video is made: `hone-music-video new --polish on|off` and a switch in the New video
  form beside the pace and the mood (`views/options.js`). The project's settings keep it, and a switch in
  the project's header changes it later.
- Each take remembers whether its start frame is polished (`Take.polish`, `None` for the run's setting).
  A redo that draws a new start frame records the project's setting at that moment in the new take, so
  changing the setting affects the shots redone afterwards, while every other shot keeps
  its start frame and its clip (the owner, 2026-10-12, D-155). A fork keeps the run's settings, as before.
- It reaches no planner: like the check settings, `for_planner` leaves it out.
- Stored settings without it read `on` (`BEFORE_0025`), so their keys and pictures stay as they are.
- The progress units and the estimate before a run (0003) count no polish unit when it is off.
- When 0023's polish with references is built, it applies only while `polish` is `on`.

### Part B: hone-models knows the servers it started (hone-models' own record)

When `_comfyui_server.running()` starts a server, it records the URL, process group, start command and
time in a machine-wide file under hone-models' state folder, and removes the entry when it stops the
server. A later session, in any process, that finds a healthy server at a recorded URL, whose process is
still alive and whose recorded command differs from the current `HONE_COMFYUI_START`, replaces it when
idle: it stops the process group and starts the server again. It does not replace the server while it is
busy. A server it has no record of is never stopped. This is what makes §2's "leftover" automatic even
after the dashboard was killed outright (`SIGKILL`, a crash, a power loss), where §3 cannot help.

Until Part B is in hone-models, §2's leftover row falls back to the refusal. §3 prevents the common case
(Ctrl-C), and §4 makes sure no black picture is ever kept.

## Acceptance cases (§14)

51. A ComfyUI image model on a server started with `--use-sage-attention` that is busy, or that
    hone-models has no record of, is refused with the message of §2. Nothing is drawn or kept. A Wan
    model on the same server runs (`test_ac51_server_check.py`, a fake `/system_stats`).
52. With Part B: an idle leftover server with the wrong flags is replaced before the model runs, and a
    busy one is never stopped (`test_ac51_server_check.py`).
53. Ctrl-C on the dashboard during a session stops the runner, and the ComfyUI it started is stopped
    within `CLOSE_WAIT_S` (`test_ac53_dashboard_close.py`, a fake server process).
54. A blank picture from any stage (draft, polish, pack, prop, upload excepted) is refused, not kept and
    not put in use (retries: D-158). A redo that gets one fails with the message
    (`test_ac54_blank_output.py`).
55. A blank clip is refused the same way. A dark but not blank picture (a night scene) is kept
    (`test_ac54_blank_output.py`, a real dark still from the fixtures).
56. Only the Wan 2.2 I2V 14B workflow gets `--use-sage-attention`; another ComfyUI video model and every
    image model get a plain server (`test_ac51_server_check.py`).
57. A clips session records the SageAttention version (`2.2.0`, `1.0.6` or `unknown`) in its span, and a
    1.x version runs as before (`test_ac51_server_check.py`, a fake interpreter).
58. With polish = "off" no polish call is made, each start frame in use is its draft, and the clips are
    made from it. After the polish is switched on, a redo that draws a new start frame polishes only that
    shot; every other shot keeps its start frame and clip (D-155; `test_ac58_polish_off.py`).
59. Settings stored without `polish` read `on`: their start frames' keys do not change, and nothing is made
    again (`test_ac58_polish_off.py`).

## Consequences

- D-033 changes from "a server already running is used as it is" to "a server already running is checked
  first". The SageAttention speed-up for Wan stays.
- Each ComfyUI session costs one more `GET /system_stats`, and each generated file a 64×36 read. Clips
  read three frames through ffmpeg (`_video.py`).
- An owner who starts ComfyUI with `--use-sage-attention` by hand gets a clear refusal for the image
  models, instead of black pictures.
- Closing the dashboard can take up to a minute while a clip is interrupted and its session closes.
- With SageAttention 2.2 a 67-shot video's clips take about 30 minutes less on the reference machine
  (12% of the clips stage). Setting up a machine takes one source build of about 10 minutes.
- Whether Qwen-Image-Edit is still black under SageAttention 2.2 was not tested; §2 keeps image models
  off a SageAttention server either way.
- New videos have no polish by default, which reverses 0023's "every frame polished" for new projects;
  0023's polish, once built, is what `polish = "on"` runs.
- D-033 gets a successor decision in `design/decisions.md` (the server check, the narrowed rule, 2.2).

## Migration and compatibility

One new setting, `polish`; settings stored without it read `on`, so no stored project changes. No other
stored format changes. The black takes already made stay as versions; once this is built, the black start
frames of *isolde* (S002, S006, S008, S016, S020, S026, S043) are redone. The leftover server started at
00:12 was stopped by hand on 2026-10-12. The reference machine already runs SageAttention 2.2 (installed
2026-10-12 for the trial); other machines keep 1.x until they rebuild, and their clips are only slower.

## Open questions

1. ~~§2 and Part B, or SageAttention per workflow (KJNodes)?~~ §2 and Part B (owner, 2026-10-12).
2. ~~Is 60 s the right wait for §3?~~ 60 s; a Wan clip interrupted by Stop ends within seconds, and the
   wait ends as soon as the runner does.
3. ~~Log near-blank pictures before refusing them?~~ No: refuse from the first build (owner, 2026-10-12).
4. ~~§5's version in the span?~~ Yes (owner, 2026-10-12).
