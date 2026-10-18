"""`FakeModels`: the `Models` port without models. Deterministic, offline, and every call is recorded."""

from __future__ import annotations

import hashlib
import threading
import wave
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, TypeVar

from pydantic import BaseModel

from hone_music_video.errors import NotFound
from hone_music_video.ports import Generated, ImageInfo
from hone_music_video.project import IMAGE_TYPES
from hone_music_video.records import AlignedWord, Word, Words
from hone_music_video.testing.answers import DEFAULT_ANSWERS
from hone_music_video.testing.frame_answers import FRAME_ANSWERS
from hone_music_video.testing.media import gradient_png_bytes, make_clip, make_interpolated

T = TypeVar("T", bound=BaseModel)
Answer = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass
class Call:
    """One recorded call. `kind` is `plan`, `transcribe`, `separate`, `align`, `generate` or
    `session`."""

    kind: str
    model: str
    prompt: str = ""
    data: dict[str, Any] = field(default_factory=dict[str, Any])
    images: list[Path] = field(default_factory=list[Path])
    schema: str = ""
    out: Path | None = None
    seed: int | None = None
    inputs: dict[str, Any] = field(default_factory=dict[str, Any])


ANSWERS = {**DEFAULT_ANSWERS, **FRAME_ANSWERS}  # the frame planner's calls too (0026)

QWEN_SIZES = (
    "256x256",
    "512x512",
    "768x768",
    "1024x1024",
    "1328x1328",
    "1024x576",
    "576x1024",
    "1280x720",
    "720x1280",
    "1344x768",
    "768x1344",
    "1664x928",
    "928x1664",
    "1024x768",
    "768x1024",
    "1152x864",
    "864x1152",
    "1216x832",
    "832x1216",
    "1536x1024",
    "1024x1536",
    "1152x896",
    "896x1152",
    "704x880",
    "832x1248",
    "1536x640",
    "640x1536",
    "2048x1024",
)
IMAGE_INFOS = {  # the frame's model checks on the fake (0027): the registry's entries as they are declared
    i.id: i
    for i in (
        ImageInfo("qwen-image-2.1-turbo", installed="yes", max_references=6, sizes=QWEN_SIZES,
                  inputs=("cfg", "ref_resolution", "references", "size", "steps"),
                  license="Qwen research license", commercial_use=False),
        ImageInfo("z-image-turbo", installed="yes", max_references=0, sizes=QWEN_SIZES,
                  inputs=("size", "steps"), license="Apache-2.0", commercial_use=True),
        ImageInfo("fake-hosted-edit", local=False, installed="yes", max_references=4, inputs=("size",)),
    )
}  # fmt: skip


def _seconds(audio: Path) -> float:
    try:
        with wave.open(str(audio), "rb") as song:
            return song.getnframes() / song.getframerate()
    except (wave.Error, EOFError):
        return 30.0


def _video(out: Path, inputs: Mapping[str, Any], rgb: tuple[int, int, int]) -> None:
    """A clip of `duration_s` at 16 fps (16 frames a second and one more, as Wan's entry asks, D-033),
    64x36; or a finished clip: its `video` at 32 fps, twice its frames (RIFE x2, D-032)."""
    if "video" in inputs:
        make_interpolated(out, Path(inputs["video"]), 32, rgb, box=True)
    else:
        make_clip(out, round(float(inputs.get("duration_s", 1)) * 16) + 1, 16, rgb, box=True)


def _spread(texts: Sequence[str], audio: Path) -> list[Word]:
    """The words evenly over the middle eight tenths of the audio, each three quarters of its share."""
    duration_ms = round(_seconds(audio) * 1000)
    start, span = duration_ms // 10, duration_ms * 8 // 10
    step = span // max(len(texts), 1)
    return [
        Word(text=t, start_ms=start + i * step, end_ms=start + i * step + step * 3 // 4)
        for i, t in enumerate(texts)
    ]


class FakeModels:
    """A stand-in for hone-models (the `Models` port).

    - `plan` answers with `answers[<schema name>](data)` when given, else a plausible answer built from
      the data (`hone_music_video.testing.answers`), validated against the schema.
    - `transcribe` hears the prompt's words (or "la"), spread evenly over the middle of the song.
    - `generate` writes a small PNG for an image, a small real video for an `.mp4` (needs ffmpeg), a few
      bytes for anything else.
    - `separate_vocals` writes the audio to `out` with a few bytes after it (the "vocals" are the song).
    - `align` places the given words evenly over the middle of the song, as `transcribe` hears them,
      each with a score of 1.
    - `plan_cost_usd` is the cost each `plan` call reports in `last_plan_cost_usd` (None: unknown).
    - `on_call(call)` runs before every call returns (tests use it to slow a run down, or to crash it
      at a chosen call).
    - `image_info`, `image_models`, `image_guide` answer from `IMAGE_INFOS` (0027).
    - `calls` lists every call in order (a `session` block is a call of kind `session`).
    """

    def __init__(
        self,
        *,
        answers: Mapping[str, Answer] | None = None,
        on_call: Callable[[Call], object] | None = None,
        plan_cost_usd: float | None = None,
    ) -> None:
        self.answers = dict(answers or {})
        self.plan_cost_usd = plan_cost_usd
        self.last_plan_cost_usd: float | None = None  # as `HoneModels` records it (0008)
        self.on_call = on_call
        self.calls: list[Call] = []
        self._lock = threading.Lock()

    def _record(self, call: Call) -> None:
        with self._lock:
            self.calls.append(call)
        if self.on_call is not None:
            self.on_call(call)

    def calls_of(self, kind: str) -> list[Call]:
        """The recorded calls of one kind, in order."""
        return [c for c in self.calls if c.kind == kind]

    def plan(
        self,
        model_id: str,
        *,
        system: str,
        data: Mapping[str, Any],
        images: Sequence[Path],
        schema: type[T],
    ) -> T:
        call = Call("plan", model_id, system, dict(data), list(images), schema.__name__)
        self._record(call)
        answer = self.answers.get(schema.__name__) or ANSWERS[schema.__name__]
        self.last_plan_cost_usd = self.plan_cost_usd
        return schema.model_validate(dict(answer(data)))

    def transcribe(self, model_id: str, audio: Path, *, language: str | None, prompt: str | None) -> Words:
        self._record(Call("transcribe", model_id, prompt or "", {"language": language}, [audio]))
        return Words(language=language or "en", words=_spread((prompt or "la " * 24).split(), audio))

    def align(self, model_id: str, audio: Path, lines: Sequence[str]) -> list[list[AlignedWord]]:
        self._record(Call("align", model_id, data={"lines": list(lines)}, images=[audio]))
        placed = iter(_spread([w for line in lines for w in line.split()], audio))
        return [[AlignedWord(**next(placed).model_dump(), score=1.0) for _ in line.split()] for line in lines]

    def separate_vocals(self, model_id: str, audio: Path, *, out: Path) -> Path:
        self._record(Call("separate", model_id, images=[audio], out=out))
        out.write_bytes(audio.read_bytes() + b"vocals")  # still a WAV: its reader stops at the data
        return out

    def generate(
        self, model_id: str, prompt: str, *, out: Path, seed: int, inputs: Mapping[str, Any]
    ) -> Generated:
        self._record(Call("generate", model_id, prompt, out=out, seed=seed, inputs=dict(inputs)))
        digest = hashlib.sha256(f"{model_id}|{prompt}|{seed}".encode()).digest()
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix.lower() in IMAGE_TYPES:
            out.write_bytes(gradient_png_bytes(32, 18, (digest[0], digest[1], digest[2])))
        elif out.suffix.lower() == ".mp4":
            _video(out, inputs, (digest[0], digest[1], digest[2]))
        else:
            out.write_bytes(b"fake " + model_id.encode() + b" " + digest.hex().encode())
        return Generated(path=out, seed=seed)

    def image_info(self, model_id: str) -> ImageInfo:
        if model_id not in IMAGE_INFOS:
            raise NotFound(f"no model {model_id!r} in the fake registry")
        return IMAGE_INFOS[model_id]

    def image_models(self) -> list[ImageInfo]:
        return list(IMAGE_INFOS.values())

    def image_guide(self, model_id: str) -> Any:
        found = self.image_info(model_id)
        return SimpleNamespace(
            id=found.id, summary=None, prompt="Plain sentences.", license=found.license,
            commercial_use=found.commercial_use, sizes=found.sizes, max_references=found.max_references,
            inputs={},
        )  # fmt: skip

    @contextmanager
    def session(self, model_id: str) -> Generator[None]:
        self._record(Call("session", model_id))
        yield
