"""`HoneModels`: the `Models` port on hone-models (decision D-001).

The registry is hone-models' catalog, then the library's own entries (`data/models.toml`: the planner
and the local workflows, D-008), then the user's `~/.config/hone/models.toml`, then `./hone-models.toml`
of the working folder; each later file wins, so the library's entries are defaults (D-022). A media
call inside `session(model)` goes through the session's client, so the model loads once for the stage
(D-005); a ComfyUI server started for a video model's session runs with SageAttention (D-033). Hosted
transcription goes to the in-library client of D-002 (`hosted_speech.py`), and vocal isolation to
Demucs (`vocals.py`, D-041) and forced alignment to the MMS aligner (`aligner.py`, 0005), until
hone-models has them. Each call passes hone-flow's trace context, so hone-models' records name the run
and the stage that made it (D-061)."""

from __future__ import annotations

import json
import os
from collections.abc import Generator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from functools import cached_property
from importlib import resources
from pathlib import Path
from typing import Any, TypeVar

import hone_flow as fk
import hone_models as mk
from hone_models.text import cost_usd as priced
from pydantic import BaseModel, ValidationError

from hone_music_video.adapters import aligner, comfyui_server, hosted_speech, vocals
from hone_music_video.adapters.comfyui_server import SAGE_SERVER, sage_version, server_argv
from hone_music_video.errors import ModelFailure, NotFound
from hone_music_video.ports import Generated, ImageInfo
from hone_music_video.records import AlignedWord, HostedCall, Word, Words
from hone_music_video.timed_lyrics import tidy

T = TypeVar("T", bound=BaseModel)
START = "HONE_COMFYUI_START"  # the command hone-models runs to start ComfyUI for a session
SAGE_ATTENTION = "--use-sage-attention"  # Wan 22% faster, no visible difference (history; D-033)
SAGE_FAILED = (
    "ComfyUI did not start with --use-sage-attention (added for video models, D-033): install "
    "sageattention in ComfyUI's Python, or start ComfyUI yourself ({error})"
)
DIFFUSION_LOADERS = ("UNETLoader", "UnetLoaderGGUF")  # a workflow that runs a diffusion model
WAN_14B = ("i2v", "14b")  # SageAttention only for the Wan 2.2 I2V 14B experts, as measured (0025 §1)
LIBRARY_REGISTRY = Path(str(resources.files("hone_music_video"))) / "data" / "models.toml"


def load_registry() -> Any:
    """hone-models' catalog, the library's entries, the user's file, the working folder's file.

    `mk.registry.load` always merges the user's and the working folder's files (its `default_paths`)
    before the paths it is given, and has no public way to skip them; so they are given again after the
    library's file, and win over it. Merging a file again changes nothing it already set."""
    own = [p for p in mk.registry.default_paths() if p.is_file()]
    return mk.registry.load(paths=[LIBRARY_REGISTRY, *own])


def _image_info(config: Any, registry: Any) -> ImageInfo:
    """An entry as the frame's checks read it (0027; Hone Frame's `models._info`)."""
    caps = config.capabilities
    try:
        installed = mk.catalog.installed(config)
    except mk.errors.HoneModelsError:
        installed = "unknown"
    try:
        inputs: tuple[str, ...] | None = tuple(mk.image(config.id, registry=registry).inputs)
    except mk.errors.HoneModelsError:
        inputs = None
    if inputs is not None and not inputs and installed != "yes":
        inputs = None
    return ImageInfo(
        id=config.id, kind=config.kind, local=bool(config.local), installed=installed,
        max_references=caps.max_references, sizes=tuple(caps.sizes or ()), inputs=inputs,
        license=caps.license, commercial_use=caps.commercial_use,
    )  # fmt: skip


def heard_words(transcript: mk.Transcript, call: HostedCall | None = None) -> Words:
    """hone-models' transcript as `Words` in integer milliseconds, tidied (`timed_lyrics.tidy`): Whisper's
    word times can overlap by a few ms or have no length, and lines timed from them must not (design §5.1,
    D-017). The service's own times stay in `call.reply`."""
    words = [
        Word(text=w.text, start_ms=round(w.start_s * 1000), end_ms=round(w.end_s * 1000))
        for w in transcript.words
    ]
    return Words(language=transcript.language, words=tidy(words), call=call)


class HoneModels:
    """Every call through hone-models, which records the prompt, the images, the cost and the time."""

    def __init__(self) -> None:
        self._open: dict[str, mk.MediaClient] = {}  # the clients of the open sessions, by model id
        self._sage: dict[str, str] = {}  # the SageAttention version of an open Wan session (0025 §5)
        self.last_plan_cost_usd: float | None = None  # the last `plan` call's cost, when priced (0008)

    @cached_property
    def registry(self) -> Any:
        return load_registry()

    def _media(self, model_id: str) -> mk.MediaClient:
        if model_id in self._open:
            return self._open[model_id]
        kind = self.registry.get(model_id).kind
        maker = mk.video if kind == "video" else mk.image
        return maker(model_id, registry=self.registry)

    def plan(
        self,
        model_id: str,
        *,
        system: str,
        data: Mapping[str, Any],
        images: Sequence[Path],
        schema: type[T],
    ) -> T:
        content: list[dict[str, Any]] = [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]
        content += [{"type": "image", "path": str(p)} for p in images]
        messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]
        client = mk.text(model_id, registry=self.registry)
        result = client.complete(messages, schema=schema, trace=fk.current_trace() or None)
        usage = getattr(result, "usage", None)
        self.last_plan_cost_usd = priced(self.registry.get(model_id), usage) if usage else None
        if result.error or result.parsed is None:
            raise ModelFailure(
                f"{model_id} gave no usable {schema.__name__}: {result.error or 'empty reply'}"
            )
        try:
            return schema.model_validate(result.parsed, from_attributes=True)
        except ValidationError as error:
            raise ModelFailure(f"{model_id} replied with an invalid {schema.__name__}: {error}") from None

    def transcribe(self, model_id: str, audio: Path, *, language: str | None, prompt: str | None) -> Words:
        # D-002: the one place that changes to `mk.transcriber(model_id, registry=self.registry)` once
        # hone-models has hosted transcription (its change 0019); hone-models then records the call.
        config = self.registry.get(model_id)
        heard, call = hosted_speech.transcribe(config, audio, language=language, prompt=prompt)
        return heard_words(heard, call)

    def separate_vocals(self, model_id: str, audio: Path, *, out: Path) -> Path:
        # D-041: in this library until hone-models has a separation client, like D-002
        return vocals.separate(model_id, audio, out)

    def align(self, model_id: str, audio: Path, lines: Sequence[str]) -> list[list[AlignedWord]]:
        # 0005: in this library until hone-models has an alignment client, like D-002 and D-041
        return aligner.align(model_id, audio, lines)

    def generate(
        self, model_id: str, prompt: str, *, out: Path, seed: int, inputs: Mapping[str, Any]
    ) -> Generated:
        if model_id not in self._open:
            self._check_server(model_id)
        client = self._media(model_id)
        result = client.generate(prompt, out=out, seed=seed, trace=fk.current_trace() or None, **inputs)
        if result.error or result.path is None:
            raise ModelFailure(
                f"{model_id} made no file ({result.error_kind}): {result.error or 'no output'}"
            )
        recorded = {"sage_attention": self._sage[model_id]} if model_id in self._sage else None
        return Generated(path=result.path, seed=result.seed, recorded=recorded)

    def image_info(self, model_id: str) -> ImageInfo:
        config = self.registry.models.get(model_id)
        if config is None:
            raise NotFound(f"no model {model_id!r} in the registry")
        return _image_info(config, self.registry)

    def image_models(self) -> list[ImageInfo]:
        found = [c for c in self.registry.models.values() if c.kind == "image" and not c.disabled]
        return [_image_info(c, self.registry) for c in sorted(found, key=lambda c: c.id)]

    def image_guide(self, model_id: str) -> Any:
        if model_id not in self.registry.models:
            raise NotFound(f"no model {model_id!r} in the registry")
        return mk.guide(model_id, registry=self.registry)

    def _sage_attention(self, model_id: str) -> bool:
        """The Wan 2.2 I2V 14B experts (0025 §1); every other ComfyUI model, the Wan 5B among them,
        wants a plain server."""
        config = self.registry.get(model_id)
        if config.provider != "comfyui" or not config.workflow:
            return False
        nodes: dict[str, dict[str, Any]] = json.loads(Path(config.workflow).read_text(encoding="utf-8"))
        return any(
            node.get("class_type") in DIFFUSION_LOADERS
            and all(part in str(node.get("inputs", {}).get("unet_name", "")).lower() for part in WAN_14B)
            for node in nodes.values()
        )

    def _check_server(self, model_id: str) -> None:
        """A ComfyUI model that wants a plain server is refused on one started with SageAttention
        (0025 §2, D-156); no server answering is hone-models' to start."""
        config = self.registry.get(model_id)
        if config.provider != "comfyui" or self._sage_attention(model_id):
            return
        url = comfyui_server.comfy_url()
        argv = server_argv(url)
        if argv is not None and SAGE_ATTENTION in argv:
            raise ModelFailure(SAGE_SERVER.format(url=url, model=model_id))

    @contextmanager
    def _comfyui_flags(self, model_id: str) -> Generator[bool]:
        """`HONE_COMFYUI_START` gets SageAttention while a Wan session starts the server: the flag is
        ComfyUI's own (no change to its Python environment); a server already running is used as it is
        (D-033). Yields whether the flag was added."""
        start = os.environ.get(START, "")
        if not start or SAGE_ATTENTION in start or not self._sage_attention(model_id):
            yield False
            return
        os.environ[START] = f"{start} {SAGE_ATTENTION}"
        try:
            yield True
        finally:
            os.environ[START] = start

    @contextmanager
    def session(self, model_id: str) -> Generator[None]:
        self._check_server(model_id)
        client = self._media(model_id)
        with ExitStack() as stack:
            flagged = stack.enter_context(self._comfyui_flags(model_id))
            try:
                stack.enter_context(client.session())
            except mk.errors.ProviderError as error:
                if flagged:
                    raise ModelFailure(SAGE_FAILED.format(error=error)) from error
                raise
            self._open[model_id] = client
            if self._sage_attention(model_id):
                self._sage[model_id] = sage_version(os.environ.get(START, ""))
            try:
                yield
            finally:
                self._sage.pop(model_id, None)
                del self._open[model_id]
