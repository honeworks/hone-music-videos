"""The `Models` port's contract: the fake passes it, a broken implementation does not."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video._video import Clip, probe
from hone_music_video.testing import FakeModels, check_models


def test_the_fake_keeps_the_contract(tmp_path: Path) -> None:
    models = FakeModels()
    check_models(models, tmp_path)
    kinds = ["transcribe", "plan", "session", "generate", "separate", "align", "align"]
    assert [c.kind for c in models.calls] == kinds


def test_the_fake_is_deterministic(tmp_path: Path) -> None:
    one, two = FakeModels(), FakeModels()
    check_models(one, tmp_path / "a")
    check_models(two, tmp_path / "b")
    assert (tmp_path / "a" / "contract-image.png").read_bytes() == (
        tmp_path / "b" / "contract-image.png"
    ).read_bytes()


class WrongSeed(FakeModels):
    def generate(
        self, model_id: str, prompt: str, *, out: Path, seed: int, inputs: Mapping[str, Any]
    ) -> hmv.Generated:
        made = super().generate(model_id, prompt, out=out, seed=seed, inputs=inputs)
        return hmv.Generated(path=made.path, seed=seed + 1)


def test_a_broken_implementation_fails_the_contract(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="seed it used"):
        check_models(WrongSeed(), tmp_path)


class Backwards(FakeModels):
    def align(self, model_id: str, audio: Path, lines: Sequence[str]) -> list[list[hmv.AlignedWord]]:
        return [list(reversed(line)) for line in super().align(model_id, audio, lines)]


def test_an_aligner_out_of_order_fails_the_contract(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="aligned words are in order"):
        check_models(Backwards(), tmp_path)


def test_scripted_answers_and_call_hooks(tmp_path: Path) -> None:
    seen: list[str] = []
    answer = {"duration_ms": 1, "sections": [], "lines": []}
    models = FakeModels(
        answers={"Timeline": lambda _data: answer}, on_call=lambda call: seen.append(call.kind)
    )
    plan = models.plan("m", system="s", data={}, images=[tmp_path], schema=hmv.Timeline)
    assert plan.duration_ms == 1 and seen == ["plan"] and models.calls[0].images == [tmp_path]


def test_the_fakes_clips_are_real_videos_of_the_frames_asked(tmp_path: Path) -> None:
    """A clip: `duration_s` at 16 fps and one frame more (Wan's entry, D-033); its finish: twice its
    frames at 32 fps (RIFE x2, D-032); one small size, so the real assembly joins them."""
    models = FakeModels()
    clip, finished = tmp_path / "clip.mp4", tmp_path / "finished.mp4"
    models.generate("clips", "a push-in", out=clip, seed=1, inputs={"duration_s": 2.0, "size": "832x480"})
    models.generate("finish", "", out=finished, seed=1, inputs={"video": clip, "size": "1920x1080"})
    assert probe(clip) == Clip(size="64x36", rate="16/1", frames=33)
    assert probe(finished) == Clip(size="64x36", rate="32/1", frames=66)
