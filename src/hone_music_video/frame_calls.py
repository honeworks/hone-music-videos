"""The frame planner's calls (0026): many small planner calls instead of one whole-video reply, each
kept as soon as it returns, checked by code and sent back once with what is wrong.

A call's reply is kept in `current/frame/calls/<label>-<key>.json` with what was sent (the data, the
images' names, the schema, the system prompt kept once as `system-<sha12>.md`) and the problems the code
found in the reply (0030 §2). The key is the sha256 of the model, the system prompt, the data and the
images: a plan made again after a failure (or with the same inputs) takes the replies it has and calls
only for the rest. The system prompts are the planner's own (`data/prompts/frame_*.md`) followed by the
parts of Hone Frame's prompt guide each call needs (`data/frame_guide/`)."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from hone_music_video._files import write_json
from hone_music_video._jobs import Job
from hone_music_video.records import Problem
from hone_music_video.stages_plan import system_prompt

T = TypeVar("T", bound=BaseModel)
Check = Callable[[Any], list[Problem]]

CALLS_AT_ONCE = 4  # the subjects' and the scene batches' calls run side by side
PROMPT_CHARS = 1500  # what the image model's text encoder reads, with room (design §5.2)
# Words of computer graphics and advertising: they pull a film still toward a render (Hone Frame's guide)
RENDER_WORDS = re.compile(
    r"\b(?:photo-?realistic|hyper-?realistic|hyper-?detailed|ultra-?detailed|razor-?sharp|[48]k"
    r"|ultra hd|octane|unreal engine|cgi|masterpiece|best quality|trending on artstation|3d render)\b",
    re.IGNORECASE,
)
# a number in the list, not a measure after it ("image 2, 24mm lens", "image 1, 3 metres away")
_NUMBER = r"\d+(?!\w)(?!\s*(?:%|°|(?:mm|cm|m|km|metres?|meters?|feet|foot|ft|inch(?:es)?|degrees?)\b))"
IMAGES = re.compile(rf"\bimages?\s+({_NUMBER}(?:\s*(?:,|and|&)\s*{_NUMBER})*)", re.IGNORECASE)


def guide(*names: str, until: str | None = None) -> str:
    """Parts of Hone Frame's prompt guide, in order; `until` cuts the first one at a heading."""
    folder = resources.files("hone_music_video") / "data" / "frame_guide"
    parts = [(folder / f"{name}.md").read_text(encoding="utf-8").strip() for name in names]
    if until and parts and until in parts[0]:
        parts[0] = parts[0].split(until, 1)[0].strip()
    return "\n\n".join(parts)


def images_named(prompt: str) -> set[int]:
    """The picture numbers a prompt names ("image 2", "images 1 and 3")."""
    return {int(n) for found in IMAGES.findall(prompt) for n in re.findall(r"\d+", found)}


def prompt_problems(where: str, prompt: str, pictures: int, *, starts: str = "") -> list[Problem]:
    """A prompt that is empty or too long, uses words of a render, names a picture it does not have or
    leaves one of its pictures unnamed, or does not begin with `starts` (the kind of picture)."""
    if not prompt.strip():
        return [Problem(rule="empty-prompt", where=where, message="the prompt is empty")]
    found: list[str] = []
    if len(prompt) > PROMPT_CHARS:
        found.append(f"has {len(prompt)} characters, over {PROMPT_CHARS}: write it shorter")
    words = sorted({w.lower() for w in RENDER_WORDS.findall(prompt)})
    if words:
        found.append(f"uses {', '.join(map(repr, words))}: words of a render; name the film's look instead")
    named, have = images_named(prompt), set(range(1, pictures + 1))
    if named - have:
        found.append(f"names image {', '.join(map(str, sorted(named - have)))}, but has {pictures} pictures")
    if have - named:
        found.append(f"never names image {', '.join(map(str, sorted(have - named)))}: say who or what it is")
    if starts and not _plain(prompt).startswith(_plain(starts)):
        found.append(f"does not begin with the kind of picture, word for word: {starts!r}")
    return [Problem(rule="frame-prompt", where=where, message=m) for m in found]


def _plain(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(".")


@dataclass(frozen=True)
class Planner:
    """The planner model, the stage's job, and where the replies are kept."""

    job: Job
    model: str
    folder: Path  # `current/frame/calls/`
    fresh: bool = False  # call again even when a reply is kept

    def call(
        self,
        label: str,
        system: str,
        data: Mapping[str, Any],
        schema: type[T],
        *,
        images: Sequence[Path] = (),
        check: Check | None = None,
        repairs: int = 1,
    ) -> tuple[T, list[Problem]]:
        """One call, checked; a reply with problems is sent back with them up to `repairs` times. The
        reply and what is still wrong with it (the owner sees it; nothing is refused)."""
        reply, path = self._kept(label, system, data, images, schema)
        problems = self._checked(path, reply, check)
        for n in range(1, repairs + 1):
            if not problems:
                break
            again = {**data, "previous_reply": reply.model_dump(mode="json")}
            again["problems"] = [p.model_dump(include={"where", "message"}) for p in problems]
            reply, path = self._kept(f"{label}-repair{n}", system, again, images, schema)
            problems = self._checked(path, reply, check)
        return reply, problems

    @staticmethod
    def _checked(path: Path, reply: BaseModel, check: Check | None) -> list[Problem]:
        """The reply's problems, also kept in its call's file for the Plan view's Calls (0030 §2)."""
        problems = check(reply) if check else []
        kept = json.loads(path.read_text(encoding="utf-8"))
        found = [p.model_dump(include={"where", "message"}) for p in problems]
        if kept.get("problems") != found:
            write_json(path, kept | {"problems": found})
        return problems

    def _kept(
        self, label: str, system: str, data: Mapping[str, Any], images: Sequence[Path], schema: type[T]
    ) -> tuple[T, Path]:
        pictures = [hashlib.sha256(p.read_bytes()).hexdigest() for p in images]
        made = {"model": self.model, "system": system, "data": data, "images": pictures}
        key = hashlib.sha256(json.dumps(made, sort_keys=True, default=str).encode()).hexdigest()
        path = self.folder / f"{label}-{key[:12]}.json"
        if path.is_file() and not self.fresh:
            kept = json.loads(path.read_text(encoding="utf-8"))
            return schema.model_validate(kept["reply"]), path
        at = datetime.now(UTC).isoformat(timespec="microseconds")  # orders the calls made side by side
        began = time.monotonic()
        reply = self.job.models.plan(self.model, system=system, data=data, images=images, schema=schema)
        took = round((time.monotonic() - began) * 1000)
        write_json(path, {
            "label": label, "model": self.model, "took_ms": took, "at": at,
            "request": {"system": self._system_file(system), "data": data, "images": [p.name for p in images],
                        "schema": schema.__name__},
            "reply": reply.model_dump(mode="json"),
        })  # fmt: skip
        self.job.events.write("frame_call", label=label, model=self.model, took_ms=took)
        return reply, path

    def _system_file(self, system: str) -> str:
        """The system prompt kept once beside the calls (`system-<sha12>.md`); its name."""
        name = f"system-{hashlib.sha256(system.encode()).hexdigest()[:12]}.md"
        path = self.folder / name
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(system, encoding="utf-8")
        return name


# of `limits.md`, what the frame planner follows: the six facts no prompt fixes (0029) and the video's
# limits; its other still image rules are Hone Frame's guide here
MODEL_LIMITS = "## What no prompt makes the still models draw"


def system(*prompts: str, guides: Sequence[str] = (), until: str | None = None, limits: bool = False) -> str:
    """A call's system prompt: the planner's prompts, the models' limits when asked (`MODEL_LIMITS` to the
    end of `limits.md`), then the guide's parts under a heading."""
    text = system_prompt(*prompts)
    if limits:
        text += (
            "\n\n# The limits of the models\n\n"
            + MODEL_LIMITS
            + system_prompt("limits").split(MODEL_LIMITS, 1)[1]
        )
    if guides:
        text += "\n\n# The guide (Hone Frame's prompt guide)\n\n" + guide(*guides, until=until)
    return text
