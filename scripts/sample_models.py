"""The sample model set of `sample-project.py`: `FakeModels` answering from real material.

- the transcriber "hears" every word of lyrics.txt, spread evenly over the measured song (invented
  times, a believable shape: an intro, sections, instrumental breaks, an outro; integer milliseconds),
  and the lyrics editor answers those lines, sections and breaks (the code times them, D-016);
- the cast planner: the trial's characters (character-packs/*/character.json) with sheet prompts;
- the shot planner: ~40 shots tiling the song, cut at line starts where it can, each borrowing a scene
  of the trial's inputs/video-stills.toml (prompt, cast) and its motion from inputs/video-clips.toml;
- every media call copies a trial file: sheet takes, portraits, start frames, raw (16 fps) and finished
  (32 fps, made 1280x720) clips; a scene the trial has no clip for gets a slow push-in made from its
  still with ffmpeg, once. The packs stage cuts the trial's sheet takes itself (M3)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sample_plans import cast_answer, shots_answer

from hone_music_video.errors import InvalidInput
from hone_music_video.ports import Generated
from hone_music_video.records import Shots, Word, Words
from hone_music_video.stages_plan import measure
from hone_music_video.testing import FakeModels

SECTION = re.compile(r"^\[(intro|verse \d+|pre-chorus|chorus|bridge|outro)\b", re.IGNORECASE)
BREAK = re.compile(r"^\[(musical drop|music stops|musical shift)", re.IGNORECASE)
X264 = ("-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p")  # every clip the sample cuts
CLIPS = {  # trial scene -> (raw 16 fps clip, finished 32 fps clip)
    "s01-balcony-dusk": (
        "balcony-review/4-before-smoothing-16fps.mp4",
        "balcony-review/3-length-8-seconds.mp4",
    ),
    "s09-loren-gallop": (
        "20261009T221841Z-5b874f/s09-loren-gallop/fast-8s-raw.mp4",
        "action-review/gallop-8s.mp4",
    ),
    "s15-loren-shield": (
        "20261009T221841Z-5b874f/s15-loren-shield/fast-8s-raw.mp4",
        "action-review/shield-8s.mp4",
    ),
}


def parse_lyrics(text: str) -> list[tuple[str, str]]:
    """("section", kind), ("break", kind) and ("line", text) in the order of lyrics.txt."""
    found: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip().strip("«»").strip()
        if (section := SECTION.match(line)) is not None:
            found.append(("section", section.group(1).lower().replace(" ", "-")))
        elif (pause := BREAK.match(line)) is not None:
            found.append(("break", pause.group(1).lower().replace(" ", "-")))
        elif line and not line.startswith("["):
            found.append(("line", line))
    return found


def timeline_answer(data: Mapping[str, Any]) -> dict[str, Any]:
    """The lyrics' lines spread over the song: 9 s intro, 10 s outro, a 7 s span per break."""
    duration, parts = int(data["duration_ms"]), parse_lyrics(data.get("lyrics") or "")
    if not any(kind == "line" for kind, _ in parts):
        raise InvalidInput("the sample needs lyrics.txt with sung lines (not only [bracketed] notes)")
    if duration <= 19_000:
        raise InvalidInput(f"the sample needs a song longer than 19 s (intro and outro); it is {duration} ms")
    weight = {
        "line": lambda t: 1800 + 420 * len(t.split()),
        "break": lambda _: 7000,
        "section": lambda _: 1500,
    }
    scale = (duration - 19_000) / sum(weight[kind](text) for kind, text in parts)
    t, lines, sections, instrumental = 9000.0, [], [], [{"start_ms": 0, "end_ms": 9000, "kind": "intro"}]
    for kind, text in parts:
        span = weight[kind](text) * scale
        if kind == "section":
            sections.append({"id": text, "kind": re.sub(r"-\d+$", "", text)})
        elif kind == "break":
            instrumental.append({"start_ms": round(t), "end_ms": round(t + span), "kind": text})
        else:
            lines.append(
                _line(len(lines) + 1, sections[-1]["id"] if sections else "intro", text, t, span * 0.86)
            )
        t += span
    instrumental.append({"start_ms": round(t), "end_ms": duration, "kind": "outro"})
    for section in sections:
        own = [ln for ln in lines if ln["section"] == section["id"]]
        section.update(start_ms=own[0]["start_ms"], end_ms=own[-1]["end_ms"])
    return {
        "duration_ms": duration,
        "language": "fa",
        "sections": [s for s in sections if "start_ms" in s],
        "lines": lines,
        "instrumental": instrumental,
    }


def _line(n: int, section: str, text: str, start: float, span: float) -> dict[str, Any]:
    words = text.split()
    step = span / len(words)
    timed = [
        {"text": w, "start_ms": round(start + i * step), "end_ms": round(start + (i + 0.9) * step)}
        for i, w in enumerate(words)
    ]
    return {
        "id": f"L{n:03d}",
        "section": section,
        "text": text,
        "start_ms": timed[0]["start_ms"],
        "end_ms": timed[-1]["end_ms"],
        "words": timed,
    }


def lyrics_edit(timeline: Mapping[str, Any]) -> dict[str, Any]:
    """The lyrics editor's reply (`LyricsEdit`) for the sample timeline: each line over its own heard
    words, in order (the heard words are every line's words, see `SampleModels.transcribe`)."""
    lines, first = [], 0
    for line in timeline["lines"]:
        count = len(line["words"])
        heard = {"heard_first": first, "heard_last": first + count - 1}
        lines.append({"section": line["section"], "text": line["text"]} | heard)
        first += count
    ends = [ln["end_ms"] for ln in timeline["lines"]]
    breaks = [
        {"after_line": sum(end <= span["start_ms"] for end in ends), "kind": span["kind"]}
        for span in timeline["instrumental"]
    ]
    sections = [{"id": s["id"], "kind": s["kind"]} for s in timeline["sections"]]
    return {"language": timeline["language"], "sections": sections, "lines": lines, "instrumental": breaks}


class SampleModels(FakeModels):
    """`FakeModels` whose answers and files come from the trial (see the module docstring)."""

    def __init__(self, trial: Path, cache: Path, lyrics: str, **kwargs: Any) -> None:
        scenes = tomllib.loads((trial / "inputs" / "video-stills.toml").read_text())["items"]
        motions = {
            i["id"]: i["motion"]
            for i in tomllib.loads((trial / "inputs" / "video-clips.toml").read_text())["items"]
        }
        characters = {
            p.parent.name: json.loads(p.read_text())
            for p in sorted(trial.glob("character-packs/*/character.json"))
        }
        self.lyrics, self.timeline = lyrics, None
        answers = {
            "LyricsEdit": lambda _data: lyrics_edit(self.timeline or {}),
            "Cast": lambda data: cast_answer(data, characters),
            "Shots": lambda data: shots_answer(data, scenes, motions),
        }
        super().__init__(answers=answers, **kwargs)
        self.trial, self.cache, self.scenes = trial, cache, {s["prompt"]: s["id"] for s in scenes}

    def transcribe(self, model_id: str, audio: Path, *, language: str | None, prompt: str | None) -> Words:
        super().transcribe(model_id, audio, language=language, prompt=prompt)  # records the call
        duration = measure(audio).duration_ms
        self.timeline = timeline_answer({"duration_ms": duration, "lyrics": self.lyrics})
        heard = [Word.model_validate(w) for line in self.timeline["lines"] for w in line["words"]]
        return Words(language="fa", words=heard)

    def generate(
        self, model_id: str, prompt: str, *, out: Path, seed: int, inputs: Mapping[str, Any]
    ) -> Generated:
        super().generate(model_id, prompt, out=out, seed=seed, inputs=inputs)  # records the call
        if out.parent.name == "takes":
            source = self._take(out)
        elif out.parents[2].name == "packs":  # a portrait, raw or polished: the trial's
            source = self.trial / "character-packs" / out.parents[1].name / "portrait.png"
        else:
            stage, shot = out.name.split("-")[0], out.parents[1].name
            source = self._shot_file(stage, shot, out.parents[3])
        shutil.copyfile(source, out)
        return Generated(path=out, seed=seed)

    def _take(self, out: Path) -> Path:
        made = len([p for p in out.parent.glob("sheets-*.png") if p != out])
        return self.trial / "character-packs" / out.parents[1].name / "takes" / f"take-{made % 4 + 1}.png"

    def _shot_file(self, stage: str, shot_id: str, current: Path) -> Path:
        shots = Shots.model_validate_json((current / "shots.json").read_bytes()).shots
        index = next(n for n, s in enumerate(shots) if s.id == shot_id)
        shot = shots[index]
        scene = self.scenes.get(shot.still_prompt)
        still = still_for(self.trial, scene, shot.cast, index)
        if stage in ("draw", "stills"):  # a drawn still and its polish both copy the start frame
            return still
        clips = CLIPS.get(still.parent.name) if still.name.startswith("take-") else None
        if clips and stage == "clips":
            return self.trial / "video-clips" / clips[0]
        if clips:  # the trial's finished clips differ in size: all of the sample's are 1280x720
            return fitted(self.trial / "video-clips" / clips[1], self.cache)
        return push_in(still, self.cache, finished=stage == "finish")


def still_for(trial: Path, scene: str | None, cast: list[str], index: int) -> Path:
    """The trial's start frame of the scene, else a picture of the shot's first cast member."""
    takes = sorted(trial.glob(f"video-stills/*/{scene}/take-[0-9].png")) if scene else []
    if takes:
        return takes[index % len(takes)]
    pools = {
        "celina": ["s01-balcony-dusk", "s02-cradle-infant"],
        "loren": ["s08-loren-heroic-portrait", "s09-loren-gallop", "s15-loren-shield"],
        "war-stallion": ["s09-loren-gallop"],
        "": ["s03-armband-velvet", "s09-loren-gallop", "s01-balcony-dusk"],
    }
    who = cast[0] if cast else ""
    pool = [
        p for name in pools.get(who, []) for p in sorted(trial.glob(f"video-stills/*/{name}/take-[0-9].png"))
    ]
    pool += (
        [trial / "character-packs" / who / "portrait.png"]
        if who and (trial / "character-packs" / who / "portrait.png").is_file()
        else []
    )
    if not pool:
        raise InvalidInput(f"the trial has no start frame or portrait for {who or 'a shot without cast'}")
    return pool[index % len(pool)]


def push_in(still: Path, cache: Path, *, finished: bool) -> Path:
    """A slow push-in on a still: 16 fps 832x468 (raw) or 32 fps 1280x720 (finished), 8.1 s, made once."""
    fps, size = (32, "1280x720") if finished else (16, "832x468")
    key = hashlib.sha256(f"{still}|{fps}".encode()).hexdigest()[:12]
    out = cache / f"push-in-{key}.mp4"
    if out.is_file():
        return out
    cache.mkdir(parents=True, exist_ok=True)
    frames = round(8.1 * fps)
    look = (
        f"scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440:(iw-2560)/2:(ih-1440)/3,"
        f"zoompan=z='min(zoom+0.0009,1.15)':x='iw/2-(iw/zoom/2)':y='ih/3-(ih/zoom/3)':d={frames}:s={size}:fps={fps}"
    )
    tmp = out.with_suffix(".tmp.mp4")
    ffmpeg("-i", still, "-vf", look, "-frames:v", frames, *X264, "-crf", "21", tmp)
    tmp.replace(out)
    return out


def fitted(clip: Path, cache: Path) -> Path:
    """A trial clip at the sample's finished size and rate, 1280x720 at 32 fps (the library's assembly
    joins clips of one size and the video's rate, D-035), made once."""
    out = cache / f"fitted-{hashlib.sha256(str(clip).encode()).hexdigest()[:12]}.mp4"
    if not out.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".tmp.mp4")
        look = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=32"
        ffmpeg("-i", clip, "-vf", look, "-an", *X264, "-crf", "20", tmp)
        tmp.replace(out)
    return out


def ffmpeg(*args: object) -> None:
    """Run ffmpeg quietly, overwriting its output; fail on any error."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)
