"""`HoneModels` keeps the `Models` contract, with hone-models' clients stood in for (no model runs)."""

import json
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.adapters import hone_models as adapter
from hone_music_video.testing import check_generate, check_plan, check_separate, check_transcribe
from hone_music_video.testing.answers import lyrics_answer
from tests.speech_server import SpeechServer, serving


class Text:
    """A text client that answers the lyrics plan from the data it is sent."""

    def complete(self, messages: Any, *, schema: Any, trace: Any) -> Any:
        data = json.loads(messages[1]["content"][0]["text"])
        return SimpleNamespace(parsed=lyrics_answer(data), error=None)


class Media:
    """A media client that writes its file and keeps what it was asked."""

    def __init__(self) -> None:
        self.asked: list[dict[str, Any]] = []
        self.sessions = 0

    def generate(self, prompt: str, *, out: Path, seed: int, trace: Any, **inputs: Any) -> Any:
        self.asked.append({"prompt": prompt, "seed": seed, **inputs})
        out.write_bytes(b"made")
        return SimpleNamespace(path=out, seed=seed, error=None, error_kind=None)

    @contextmanager
    def session(self) -> Generator[None]:
        self.sessions += 1
        yield


@pytest.fixture
def media(monkeypatch: pytest.MonkeyPatch) -> Media:
    stub = Media()
    monkeypatch.setattr(adapter.mk, "text", lambda _model, registry: Text())
    monkeypatch.setattr(adapter.mk, "image", lambda _model, registry: stub)
    return stub


def test_plan_keeps_the_contract(media: Media, tmp_path: Path) -> None:
    check_plan(hmv.HoneModels(), tmp_path)


def test_generate_keeps_the_contract_and_passes_the_inputs_on(media: Media, tmp_path: Path) -> None:
    check_generate(hmv.HoneModels(), tmp_path, model_id="z-image-turbo")
    assert media.asked == [{"prompt": "a lighthouse", "seed": 7, "size": "64x64"}]
    assert media.sessions == 1


def test_transcribe_keeps_the_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    heard = SpeechServer(words=[("one", 0.5, 1.1), ("two", 1.3, 1.3), ("three", 2.0, 2.6)])
    with serving(monkeypatch, heard):
        check_transcribe(hmv.HoneModels(), tmp_path, model_id="whisper-1")


class Separator:
    """Demucs' `Separator` without a model: the "vocals" are the slice's name."""

    samplerate = 44100

    def __init__(self, **_options: Any) -> None:
        pass

    def separate_audio_file(self, audio: Path) -> tuple[None, dict[str, str]]:
        return None, {"vocals": audio.name}


def save_audio(vocals: str, out: Path, *, samplerate: int) -> None:
    out.write_text(f"{vocals} at {samplerate}")


def test_separate_vocals_keeps_the_contract(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "demucs.audio", SimpleNamespace(save_audio=save_audio))
    monkeypatch.setitem(sys.modules, "demucs.api", SimpleNamespace(Separator=Separator))
    check_separate(hmv.HoneModels(), tmp_path, model_id="htdemucs")
