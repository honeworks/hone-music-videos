# Troubleshooting

`hone-music-video status <project>` shows every stage with its error; the dashboard's Project view shows
the same, and the progress log is `<project>/events.jsonl`. After fixing the cause, `resume` continues
where the run stopped: finished stages and finished shots are kept.

| What you see | What to do |
|---|---|
| `ffprobe is not installed`, `ffmpeg is not installed` or `ffmpeg and ffprobe are not installed` | install ffmpeg (it brings ffprobe), then `resume` |
| `song.xyz is not a song ffprobe can read` | give a WAV, FLAC, MP3, M4A or OGG |
| an error naming `OPENAI_COMPATIBLE_API_KEY` | put the key in the environment or a `.env` file in the folder you run from |
| `ComfyUI did not start with --use-sage-attention` | the clips stage adds that flag for Wan 2.2 I2V 14B; build SageAttention 2.2 into ComfyUI's Python (below), or start ComfyUI yourself |
| Start frames or pictures are black | ComfyUI is running with `--use-sage-attention`, which makes the picture models' output black. The run stops with `ComfyUI at <url> runs with --use-sage-attention...`. Restart ComfyUI without the flag, or close the dashboard (it stops the ComfyUI it started) |
| the stills or clips stage cannot reach ComfyUI | set `HONE_COMFYUI_START` to the command that starts it, or start it yourself at `HONE_COMFYUI_URL` (default `http://127.0.0.1:8188`) |
| out of GPU memory | close other GPU programs; the models are sized for an 8 GB card one stage at a time |
| `the timed lyrics have N errors` at approve | run the lyrics again with a note (`reject --note`) |
| `the shot list has N errors` at approve | plan the shots again with a note, or `approve --accept-errors` when none would break the video |
| `... is running in another process` | another command or the dashboard holds the run; wait for it or stop it |
| `the finished clips must share one size and be 32/1 fps` | a finished clip was replaced by hand; redo the odd shots (`hone-music-video redo PROJECT SHOT --seed`) or put their files back, then `resume` |
| a shot marked `held` in the Video view | its clip was shorter than the shot (a shot over 8 s); its last frame is held. There is no shot editor in 0.1: accept it, or plan the shots again with a note asking for shorter shots |
| `assembling again would also run ...` | the run was made by a version whose other stages have changed; a fork would remake them. Use the version that made the run, or start a new run |
| a project listed as `unreadable` | it was made by a newer version of hone-music-video; the reason is shown |

SageAttention 2.2, in ComfyUI's own Python (a prebuilt wheel matching its torch and CUDA works too; the
rollback is `uv pip install --python ~/ComfyUI/.venv/bin/python --no-deps sageattention==1.0.6`). Set
`HONE_COMFYUI_PYTHON=~/ComfyUI/.venv/bin/python` so each clip's record shows the version.

```bash
git clone https://github.com/thu-ml/SageAttention ~/build/SageAttention && cd ~/build/SageAttention
sed -i 's/-std=c++17/-std=c++20/g' setup.py          # torch 2.9 and later need C++20
export TORCH_CUDA_ARCH_LIST="8.9"                     # your GPU's architecture (8.9: RTX 40xx)
uv build --wheel --no-build-isolation --python ~/ComfyUI/.venv/bin/python
uv pip install --python ~/ComfyUI/.venv/bin/python --no-deps dist/sageattention-2.2.0-*.whl
```

Faces in wide shots stay weak on an 8 GB GPU (design §15): the shot planner is told to avoid them;
redo such a shot or plan the shots again with a note asking for a closer framing.
