# Assembly (stage 14)

The last stage cuts every finished clip to its shot's exact frames and lays them under the song
(design §5.3, §12). It runs `ffmpeg` on the CPU; no model is called.

**Frames from absolute times.** Shot `i` gets the output frames `round(start_ms * fps / 1000)` to
`round(end_ms * fps / 1000) - 1`. Positions come from the absolute times, never from adding durations,
so rounding never accumulates: at 32 fps every cut is within 16 ms of its planned time, and the video
lasts `duration_ms` to within one frame. Each shot takes its clip's frames from the clip's first; a clip
is made a little longer than its shot, and the rest is cut away.

**One encoding.** Each shot's frames are encoded once (H.264, `yuv420p`, CRF 17, x264's `medium`
preset), every cut with the same settings, and the cuts are joined without being encoded again. The song
is carried into the MP4 as it is when it is AAC or MP3, else encoded to AAC at 320 kb/s. The result is
`current/video.mp4`.

**The edit list.** `current/edl.json` says, for every shot, the clip file it uses (the finished clip of
the take in use, under `current/shots/<id>/versions/`) and its first and last frame in the video (both
included), so any editor can rebuild the cut:

```json
{"format_version": "1", "fps": 32, "video": "current/video.mp4",
 "edl": [{"shot": "S001", "clip": "current/shots/S001/versions/finish-3fa2c81d90be.mp4",
          "first_frame": 0, "last_frame": 198, "held_frames": 0}]}
```

**A clip shorter than its shot** (it should not happen: clips are made a frame longer, but a shot longer
than the clip model's 8 s, approved with its error, is one) has its last frame held for the missing
frames: every cut is exactly its shot's frames. The edit list records how many were held
(`held_frames`, estimated from the clip's packets), the progress log has a `clip_short` event, and the
Video view marks the shot. **Clips of different sizes or another frame rate** are refused, naming each
clip (they would not join): redo those shots (`hone-music-video redo PROJECT SHOT --seed`) or put
their files back, then `resume`.

**Time.** About 77 s for a five-minute video of 60 shots at 1920x1080 and 32 fps, measured on an
i9-14900HX (32 threads); fewer cores take longer. Most of it is the encoding.

## Assemble again

`hmv.assemble(project, models)`, `hone-music-video assemble <project>` or **Assemble again** in the Video
view cuts the video again from the finished clips the run has, with this version's assembly. Use it for
a run assembled by an older version of hone-music-video (0.1 before M6 wrote only the edit list), or
after changing the assembly. It is a fork of the run where only `assemble` runs: every other stage is
reused as it is, and no model is called. It needs the finished clips (the `finish` stage done) and a
stopped run, and it refuses, saying which, when another stage of the run would have to run again (made
by a version whose stage has changed since) (D-036).

```text
hone-music-video assemble projects/my-song
```

A redo or "use this version" assembles the video again by itself.

## The edit for editors

Each assembly also writes `current/edit.xml` (Final Cut Pro 7 XML) and `current/edit.edl` (CMX3600):
the same cuts for DaVinci Resolve and Premiere Pro. How to open them, and `hone-music-video export` for
a video assembled before they existed, are in [operations.md](operations.md#the-edit-for-editors).
