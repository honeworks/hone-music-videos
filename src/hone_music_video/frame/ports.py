"""The one port: how hone-frame calls models (design §7.2). The default is `HoneModels` (hone-models).

Hone Frame: ported from `src/hone_frame/ports.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from hone_music_video.frame.errors import HoneFrameError
from hone_music_video.frame.guide import ModelGuideLike


class ModelFailure(HoneFrameError):  # noqa: N818 - Hone Frame's name
    """A model call that did not give an image. The item becomes `failed` and the run stops (§8)."""


class Cancelled(HoneFrameError):  # noqa: N818 - Hone Frame's name
    """The call was cancelled through its `cancel` event (pause or stop); nothing was made."""


@dataclass(frozen=True)
class ModelInfo:
    """What a model is and takes, as hone-models declares it (unknown is `None`)."""

    id: str
    kind: str  # image | chat | ...
    local: bool
    installed: str = "unknown"  # yes | no | unknown
    max_references: int | None = None
    sizes: tuple[str, ...] = ()
    inputs: tuple[str, ...] | None = ()  # the named inputs it takes; None: not known (not installed)
    prompt_inputs: tuple[str, ...] = ()  # inputs hone-models writes INTO the prompt: never sent (D-073)
    pose: str | None = None  # none | reference | control (hone-models 0020)
    license: str | None = None
    commercial_use: bool | None = None


@dataclass(frozen=True)
class Generated:
    """One image job: the file it wrote, or `error` (the item fails with it)."""

    path: Path | None
    elapsed_s: float | None = None
    error: str | None = None


class Models(Protocol):
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
        """Make one image at `out`. `prompt` is sent exactly as given; setting `cancel` stops the call
        and raises `Cancelled`; a failure raises `ModelFailure` or returns `Generated(error=...)`. An input
        the model does not take raises `ModelFailure`: nothing is dropped silently."""
        ...

    def info(self, model_id: str) -> ModelInfo:
        """What the model is and takes; `NotFound` for an unknown id."""
        ...

    def available(self, kind: str) -> list[ModelInfo]:
        """Every model of this kind that the registry lists."""
        ...

    def guide(self, model_id: str) -> ModelGuideLike:
        """What the model's writers should know (hone-models' guide); `NotFound` for an unknown id."""
        ...


def license_warning(info: ModelInfo) -> str | None:
    """The warning shown next to a model whose licence does not allow commercial use (design §7.3)."""
    if info.commercial_use is not False:
        return None
    return f"{info.id}: {info.license or 'research licence'}, not for commercial use"
