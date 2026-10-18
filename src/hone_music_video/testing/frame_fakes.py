"""The frame's fakes (change 0027): `FakeFrameModels`, the frame's `Models` port without models (images are
small coloured PNGs), and `SAMPLE`, a small project file. Hone Frame: ported from
`src/hone_frame/testing/fake_models.py` and `sample.py`, so its acceptance tests run here as they are."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from PIL import Image

from hone_music_video.frame.errors import NotFound
from hone_music_video.frame.ports import Cancelled, Generated, ModelFailure, ModelInfo

SIZES = (
    "256x256", "512x512", "768x768", "1024x1024", "1024x576", "576x1024", "704x880", "832x1248", "2048x1024",
)  # fmt: skip
EDIT_INPUTS = ("camera_angle", "cfg", "lightning", "lora_strength", "negative", "references", "size", "steps")
CATALOGUE = {
    info.id: info
    for info in (
        ModelInfo(
            "z-image-turbo", "image", True, installed="yes", max_references=0, pose="none",
            sizes=SIZES, inputs=("size", "steps"), license="Apache-2.0", commercial_use=True,
        ),
        ModelInfo(
            "flux.2-klein-4b", "image", True, installed="yes", max_references=2, pose="reference",
            sizes=SIZES, inputs=("references", "size", "steps"), license="Apache-2.0", commercial_use=True,
        ),
        ModelInfo(
            "qwen-image-edit-2511", "image", True, installed="yes", max_references=3, pose="reference",
            sizes=SIZES, inputs=EDIT_INPUTS, license="Apache-2.0", commercial_use=True,
            prompt_inputs=("camera_angle",),
        ),
        ModelInfo(
            "qwen-image-2.1-turbo", "image", True, installed="yes", max_references=10, pose="reference",
            sizes=SIZES, inputs=("cfg", "ref_resolution", "references", "size", "steps"),
            license="Qwen research licence", commercial_use=False,
        ),
        ModelInfo("hosted-image", "image", False, installed="yes", max_references=4, inputs=("size",)),
        ModelInfo("gemma4-12b", "chat", True, installed="yes"),
    )
}  # fmt: skip


@dataclass(frozen=True)
class FakeNote:
    """A guide note, as hone-models' `GuideNote`."""

    about: str
    says: str
    source: str | None = None
    checked: date | None = None


@dataclass(frozen=True)
class FakeInput:
    """One input of a model's guide, as hone-models' `GuideInput`."""

    origin: str = "own"
    note: str | None = None


@dataclass(frozen=True)
class FakeGuide:
    """A model's guide (as hone-models' `ModelGuide`), built from its `ModelInfo` and the given notes."""

    id: str
    license: str | None
    commercial_use: bool | None
    sizes: tuple[str, ...]
    max_references: int | None
    pose: str | None
    notes: tuple[FakeNote, ...] = ()
    prompt: str | None = "Plain sentences."
    inputs: dict[str, FakeInput] = field(default_factory=dict[str, FakeInput])
    summary: str | None = None

    def notes_about(self, about: str) -> list[FakeNote]:
        return [n for n in self.notes if n.about == about]


@dataclass
class Call:
    model: str
    prompt: str
    seed: int
    references: list[Path] = field(default_factory=list[Path])
    inputs: dict[str, Any] = field(default_factory=dict[str, Any])
    cancelled: bool = False


class FakeFrameModels:
    """Scriptable stand-in for hone-models (design §7.2).

    - `generate` writes a small PNG (1/16 of the requested size, its colour from the seed) and records
      every call in `calls`, the prompt exactly as received.
    - `fail_generate(times)` makes the next calls raise `ModelFailure`.
    - `block = True` makes `generate` wait until its `cancel` event is set, then raise `Cancelled`
      (`started` is set when the blocking call begins), so pausing can be tested without timing;
      `block_after = n` lets the first `n` calls through and blocks the next one.
    - `guide` builds a model's guide from its info and the `notes` given per model id.
    - `info` / `available` answer from a small catalogue (`CATALOGUE`, plus `infos`); an unknown id is
      `NotFound`, as with hone-models.
    """

    def __init__(
        self,
        *,
        infos: dict[str, ModelInfo] | None = None,
        elapsed_s: float = 2.0,
        block: bool = False,
        block_after: int = 0,
        notes: dict[str, list[FakeNote]] | None = None,
    ) -> None:
        self.infos = CATALOGUE | dict(infos or {})
        self.notes = dict(notes or {})
        self.elapsed_s = elapsed_s
        self.block = block
        self.block_after = block_after
        self.started = threading.Event()
        self.calls: list[Call] = []
        self._fail = 0
        self._lock = threading.Lock()

    def fail_generate(self, times: int = 1) -> None:
        self._fail += times

    def generate(
        self,
        model_id: str,
        prompt: str,
        *,
        out: Path,
        seed: int,
        references: list[Path],
        inputs: dict[str, Any],
        cancel: threading.Event | None = None,
    ) -> Generated:
        call = Call(model_id, prompt, seed, list(references), dict(inputs))
        with self._lock:
            self.calls.append(call)
            failing, self._fail = self._fail > 0, max(self._fail - 1, 0)
            blocking = self.block and len(self.calls) > self.block_after
        if blocking or not self.block:
            self.started.set()
        if blocking and cancel is not None:
            cancel.wait(timeout=30)
        if cancel is not None and cancel.is_set():
            call.cancelled = True
            raise Cancelled(f"{model_id}: cancelled")
        if failing:
            raise ModelFailure(f"{model_id}: scripted failure")
        width, height = (int(v) for v in str(inputs.get("size") or "1024x1024").split("x"))
        colour = (seed % 256, (seed // 256) % 256, (seed // 65536) % 256)
        Image.new("RGB", (max(width // 16, 8), max(height // 16, 8)), colour).save(out, format="PNG")
        return Generated(path=out, elapsed_s=self.elapsed_s)

    def info(self, model_id: str) -> ModelInfo:
        if model_id not in self.infos:
            raise NotFound(f"no model {model_id!r} in the fake catalogue")
        return self.infos[model_id]

    def available(self, kind: str) -> list[ModelInfo]:
        return [i for i in self.infos.values() if i.kind == kind]

    def guide(self, model_id: str) -> FakeGuide:
        i = self.info(model_id)
        notes = tuple(self.notes.get(model_id, ()))
        inputs = {name: FakeInput() for name in i.inputs or ()}
        return FakeGuide(
            i.id, i.license, i.commercial_use, i.sizes, i.max_references, i.pose, notes, inputs=inputs
        )

    @property
    def prompts(self) -> list[str]:
        return [c.prompt for c in self.calls]


# Hone Frame: `testing/sample.py`
SAMPLE = """\
# Morning at home: every prompt below is sent exactly as written.
[project]
name = "Morning at home"
style = "soft natural light, lived-in"   # reference only: never sent to a model

[defaults]
model = "z-image-turbo"
size = "1024x1024"

[characters.woman.hero]
size = "832x1248"
prompt = "A woman in her late twenties, black hair in a loose bun, cream knit sweater, full figure"

[characters.woman.side]
model = "qwen-image-edit-2511"
refs = ["woman.hero"]
prompt = "The woman in image 1, seen from her left side, full figure, same clothes"

[places.kitchen.wide]
size = "1024x576"
prompt = "A small bright kitchen, white subway tiles, wooden shelves, a window over the sink"

[scenes.coffee]
model = "qwen-image-edit-2511"
refs = ["woman.hero", "kitchen.wide"]
prompt = "The woman in image 1 pours coffee in the kitchen of image 2, seen from the doorway"

[sheets.woman-views]
layout = "before-after"
images = ["woman.hero", "woman.side"]
labels = ["Front", "Side"]
"""
