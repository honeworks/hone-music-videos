"""`FrameModels`: the frame's `Models` port (`ports.py`) over this library's `Models` (design §7.2).

Hone Frame: its `models.py` calls hone-models directly (`mk.image(...).generate(..., cancel=...)`). Here
every call goes through this library's port (hone-models on its `main` branch, `adapters/hone_models.py`),
so a picture is recorded like every other model call of the video. What differs, and why:

- hone-models `main` has no `cancel` on a call. `generate` runs the call on a helper thread and waits;
  when `cancel` is set it asks ComfyUI to end the job (`pause.interrupt`, as Stop does, 0022) and raises
  `Cancelled` as soon as the call returns or after `CANCEL_WAIT_S`. Nothing of a cancelled picture is
  kept (Hone Frame's AC 4).
- A blank picture (one colour) is refused as a `ModelFailure`, as every model-made file of this library
  is (0025 §4); Hone Frame keeps it.
- `info` comes from the library port's `image_info` (the registry entry: local, max references, sizes,
  inputs, licence); `guide` from `image_guide` (hone-models' guide, without the per-situation notes its
  `main` branch does not have: the stage guides carry them, `data/frame_guide/`).

Hone Frame: ported from `src/hone_frame/models.py` (its 0008 branch, 2026-10-16) for
change 0027."""

from __future__ import annotations

import contextvars
import threading
import time
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hone_music_video import pause
from hone_music_video._blank import refuse_blank
from hone_music_video.errors import ModelFailure as LibraryFailure
from hone_music_video.errors import NotFound as LibraryNotFound
from hone_music_video.errors import Paused
from hone_music_video.frame.errors import NotFound
from hone_music_video.frame.ports import Cancelled, Generated, ModelFailure, ModelInfo
from hone_music_video.ports import ImageInfo, Models

CANCEL_WAIT_S = 30.0  # how long a cancelled call is waited for after ComfyUI is asked to end it
POLL_S = 0.1


def model_info(found: ImageInfo) -> ModelInfo:
    return ModelInfo(
        id=found.id, kind=found.kind, local=found.local, installed=found.installed,
        max_references=found.max_references, sizes=tuple(found.sizes), inputs=found.inputs,
        pose="reference" if found.max_references else "none", license=found.license,
        commercial_use=found.commercial_use,
    )  # fmt: skip


@dataclass(frozen=True)
class NoNotes:
    """hone-models' guide as Hone Frame's guide reads it (`ModelGuideLike`): its `main` branch has no
    notes per situation, so there are none (Hone Frame: hone-models 0020's `notes_about`)."""

    guide: Any
    pose: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict[str, Any])

    def __getattr__(self, name: str) -> Any:
        return getattr(self.guide, name)

    def notes_about(self, about: str) -> Sequence[Any]:
        return ()


class FrameModels:
    """The frame's port over the library's `Models` (`models`).

    Hone Frame: its `HoneModels` starts a local server on first use (`mk.session`) and keeps it for the
    life of the process. Here a model's session (`Models.session`, which starts ComfyUI and checks its
    flags, 0025) is opened on its first picture and kept while the run uses that model; another model
    closes it first, and `close` (the frame runner, when a run ends) ends it, so the clips stage gets
    its own server."""

    def __init__(self, models: Models) -> None:
        self.models = models
        self._session = ExitStack()
        self._open: str | None = None
        self._lock = threading.Lock()

    def _ensure_session(self, model_id: str) -> None:
        with self._lock:
            if self._open == model_id:
                return
            self._session.close()
            self._open = None
            self._session.enter_context(self.models.session(model_id))
            self._open = model_id

    def close(self) -> None:
        """End the open model session (its server stops when this library started it)."""
        with self._lock:
            self._session.close()
            self._open = None

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
        sent = {k: v for k, v in inputs.items() if v is not None}
        if references:
            sent["references"] = list(references)
        began = time.monotonic()
        try:
            self._ensure_session(model_id)
        except LibraryFailure as exc:
            raise ModelFailure(f"{model_id}: {exc}") from exc
        call = lambda: self.models.generate(model_id, prompt, out=out, seed=seed, inputs=sent)  # noqa: E731
        try:
            done = _cancellable(call, cancel)
        except Cancelled:
            out.unlink(missing_ok=True)
            raise
        except Paused as exc:  # the owner's Pause or Stop of the video's run (0022): a cancel here
            out.unlink(missing_ok=True)
            raise Cancelled(f"{model_id}: cancelled") from exc
        except LibraryFailure as exc:
            raise ModelFailure(f"{model_id}: {exc}") from exc
        try:  # Hone Frame keeps any picture; this library refuses a blank one (0025 §4, D-158)
            refuse_blank(model_id, done.path)
        except LibraryFailure as exc:
            raise ModelFailure(str(exc)) from exc
        return Generated(path=done.path, elapsed_s=round(time.monotonic() - began, 2))

    def info(self, model_id: str) -> ModelInfo:
        try:
            return model_info(self.models.image_info(model_id))
        except LibraryNotFound as exc:
            raise NotFound(f"no model {model_id!r} in the hone-models registry: {exc}") from exc

    def available(self, kind: str) -> list[ModelInfo]:
        return [model_info(i) for i in self.models.image_models() if i.kind == kind]

    def guide(self, model_id: str) -> Any:
        try:
            found = self.models.image_guide(model_id)
        except LibraryNotFound as exc:
            raise NotFound(f"no model {model_id!r} in the hone-models registry: {exc}") from exc
        info = self.info(model_id)
        return NoNotes(found, info.pose, dict(getattr(found, "inputs", {}) or {}))


def _cancellable(call: Any, cancel: threading.Event | None) -> Any:
    """`call()` on a helper thread (its context copied); `Cancelled` once `cancel` is set."""
    if cancel is None:
        return call()
    if cancel.is_set():
        raise Cancelled("cancelled before the call")
    context, box, done = contextvars.copy_context(), dict[str, Any](), threading.Event()

    def work() -> None:
        try:
            box["value"] = context.run(call)
        except BaseException as error:
            box["error"] = error
        finally:
            done.set()

    threading.Thread(target=work, name="hone-frame-call", daemon=True).start()
    while not done.wait(POLL_S):
        if cancel.is_set():
            pause.interrupt()  # Hone Frame: hone-models' cancel ends the job; here ComfyUI's interrupt
            done.wait(CANCEL_WAIT_S)
            raise Cancelled("cancelled")
    if cancel.is_set():
        raise Cancelled("cancelled")
    if "error" in box:
        raise box["error"]
    return box["value"]
