# Examples

Each example runs offline on fake models (no network, no GPU; it needs `ffmpeg`), in a temporary folder,
and the tests run every one of them. Read them in this order:

| Example | What it shows |
|---|---|
| [quickstart.py](quickstart.py) | a song in, a music video out: every stage, the owner's gates, the edit list and `video.mp4` |
| [redo_a_shot.py](redo_a_shot.py) | redo one shot with a new seed, put an earlier take back, assemble the video again without a model |

```text
uv run examples/quickstart.py
```
