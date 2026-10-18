"""The one port: how hone-music-video calls models. `HoneModels` (hone-models) is the real one,
`hone_music_video.testing.FakeModels` the fake.

Its calls have the shape of hone-models' clients: a structured completion with images (the planners,
design §7.1), a transcription with word times (design §6, D-002), a media job (images, clips and the
finishing job, design §9 to §11), a session that keeps one model loaded for a stage (D-005), the
song's vocals isolated for the first listen (D-041, D-045), and given lyrics aligned to them (0005).
Failures raise `ModelFailure`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from hone_music_video.records import AlignedWord, HostedCall, Words

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class Generated:
    """One media job: the file written and the seed used. `call` is the hosted call an in-library client
    made, with its price (the Gemini image client, 0020, D-130); None when hone-models made the call and
    recorded it."""

    path: Path
    seed: int
    call: HostedCall | None = None
    recorded: Mapping[str, Any] | None = None  # inputs the job worked out itself: an upload's crop (D-131)


@dataclass(frozen=True)
class ImageInfo:
    """An image model as its registry entry declares it, for the frame's checks (change 0027, Hone
    Frame's `ModelInfo`): where it runs, how many references it takes, its sizes, the named inputs it
    takes (None: not known, the model is not installed), its licence."""

    id: str
    kind: str = "image"
    local: bool = True
    installed: str = "unknown"  # yes | no | unknown
    max_references: int | None = None
    sizes: tuple[str, ...] = ()
    inputs: tuple[str, ...] | None = ()
    license: str | None = None
    commercial_use: bool | None = None


class Models(Protocol):
    """How every stage calls a model: planner, transcription, media job, session (design §3.2)."""

    def plan(
        self,
        model_id: str,
        *,
        system: str,
        data: Mapping[str, Any],
        images: Sequence[Path],
        schema: type[T],
    ) -> T:
        """One whole-plan call: the system prompt, the plan's inputs as JSON data (settings included),
        the images in order; the reply validated against `schema`."""
        ...

    def transcribe(self, model_id: str, audio: Path, *, language: str | None, prompt: str | None) -> Words:
        """Every heard word with its start and end in milliseconds; `prompt` biases the words."""
        ...

    def separate_vocals(self, model_id: str, audio: Path, *, out: Path) -> Path:
        """The vocals of `audio` (the whole song, once per song and model) as a WAV written to `out`, on
        the CPU; `ToolMissing` when the separation extra is not installed (D-041, D-045)."""
        ...

    def align(self, model_id: str, audio: Path, lines: Sequence[str]) -> list[list[AlignedWord]]:
        """Each given line's words with their start and end in milliseconds and their score, aligned to
        `audio` (the song's vocals) on the CPU, in order; a word without a letter to align is left out.
        `ToolMissing` when the alignment extra is not installed (0005, D-055, D-058)."""
        ...

    def generate(
        self, model_id: str, prompt: str, *, out: Path, seed: int, inputs: Mapping[str, Any]
    ) -> Generated:
        """One image, clip or finishing job written to `out` (hone-models' named inputs: `size`,
        `references`, `image`, `source`, ...)."""
        ...

    def image_info(self, model_id: str) -> ImageInfo:
        """What an image model is and takes (0027); `NotFound` for an id the registry does not know."""
        ...

    def image_models(self) -> list[ImageInfo]:
        """Every image model of the registry that is not disabled (0027)."""
        ...

    def image_guide(self, model_id: str) -> Any:
        """hone-models' guide of a model (its `ModelGuide`); `NotFound` for an unknown id (0027)."""
        ...

    def session(self, model_id: str) -> AbstractContextManager[None]:
        """Keep `model_id` loaded for the calls inside the block (one load per stage, D-005)."""
        ...
