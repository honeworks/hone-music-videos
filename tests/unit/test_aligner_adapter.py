"""The MMS forced aligner adapter (D-055 to D-057): letters to align, the song read in pieces, a word
not sung across a pause of the vocals, and torchaudio's aligner run on a model that is not MMS."""

import math
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import hone_music_video as hmv
from hone_music_video.adapters import aligner
from hone_music_video.adapters.aligner import Span


def test_letters_are_the_aligners_alphabet_in_lower_case() -> None:
    alphabet = {c: n for n, c in enumerate("-abcdefghijklmnopqrstuvwxyz'*")}
    plain = str  # a romaniser that leaves the word as it is
    assert aligner.letters("Kaa-ra-van!", plain, alphabet) == "kaaravan"  # transliterations stay
    assert aligner.letters("«Darvin…»", plain, alphabet) == "darvin"
    assert aligner.letters("don't", plain, alphabet) == "don't"
    assert aligner.letters("—", plain, alphabet) == ""  # nothing to align
    assert aligner.letters("x*y", plain, alphabet) == "xy"  # the star is not a letter


def test_arabic_script_is_romanised_with_uroman() -> None:
    uroman = pytest.importorskip("uroman", reason="needs the align extra: uv sync --extra align")
    alphabet = {c: n for n, c in enumerate("-abcdefghijklmnopqrstuvwxyz'*")}
    romanise = uroman.Uroman().romanize_string
    assert aligner.letters("سَنگین،", romanise, alphabet) == "sangin"
    assert aligner.letters("Celina", romanise, alphabet) == "celina"


def test_the_song_is_read_in_pieces_with_context() -> None:
    rate = aligner.RATE
    pieces = aligner.pieces(65 * rate)
    assert pieces == [
        (0, 32 * rate, 0, 30 * rate),
        (28 * rate, 62 * rate, 30 * rate, 60 * rate),
        (58 * rate, 65 * rate, 60 * rate, 65 * rate),
    ]
    assert aligner.pieces(rate) == [(0, rate, 0, rate)]


def test_quiet_frames_are_far_below_the_loudest() -> None:
    loud, soft, silent = np.full(320, 0.5), np.full(320, 0.5 * 10 ** (-49 / 20)), np.zeros(320)
    samples = np.concatenate([loud, soft, silent]).astype(np.float32)
    assert aligner.quiet(samples, 3) == [False, False, True]
    assert aligner.quiet(np.zeros(640, dtype=np.float32), 2) == [True, True]


def test_a_word_is_not_sung_across_a_pause() -> None:
    quiet = [False] * 10 + [True] * aligner.PAUSE_FRAMES + [False] * 10
    m, a, n = Span(8, 9), Span(26, 27), Span(28, 30)
    assert aligner.sung_part([m, a, n], quiet) == [a, n]  # "m" was the line before's tail
    assert aligner.sung_part([a, n, Span(40, 41)], [False] * 50) == [a, n, Span(40, 41)]
    short = [False] * 10 + [True] * (aligner.PAUSE_FRAMES - 1) + [False] * 10
    assert aligner.sung_part([m, Span(25, 26)], short) == [m, Span(25, 26)]  # a breath, not a pause
    assert aligner.sung_part([m, Span(26, 27)], quiet) == [m]  # as many letters each side: the first


def test_without_the_extra_the_aligner_says_how_to_install_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(sys.modules, "torchaudio", None)  # import fails
    with pytest.raises(hmv.ToolMissing, match=r"install hone-music-video\[align\]"):
        hmv.HoneModels().align("MMS_FA", tmp_path / "a.wav", ["one"])


def test_without_ffmpeg_the_aligner_says_so(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(aligner.shutil, "which", lambda _name: None)
    with pytest.raises(hmv.ToolMissing, match="ffmpeg is not installed"):
        aligner.read_audio(tmp_path / "a.wav")


def test_audio_ffmpeg_cannot_read_fails_naming_it(tmp_path: Path) -> None:
    (tmp_path / "a.wav").write_bytes(b"not audio")
    with pytest.raises(hmv.ModelFailure, match=r"could not read a\.wav"):
        aligner.read_audio(tmp_path / "a.wav")


# ------------------------------------------------------------------------------ torchaudio's aligner

ALPHABET = ["-", "a", "m", "n", "o", "e", "*"]  # the blank first, the star last, as MMS_FA's


def song(path: Path, loud: list[tuple[float, float]], seconds: float) -> Path:
    """A 16 kHz WAV, a tone where `loud` says (in seconds), silence elsewhere."""
    t = np.arange(round(seconds * aligner.RATE)) / aligner.RATE
    on = np.zeros_like(t, dtype=bool)
    for a, b in loud:
        on |= (t >= a) & (t < b)
    samples = (np.sin(2 * math.pi * 220 * t) * 0.5 * on * 32767).astype("<i2")
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(aligner.RATE)
        out.writeframes(samples.tobytes())
    return path


class Bundle:
    """A stand-in for torchaudio's `MMS_FA` bundle: its "model" hears `letters` at the given times of a
    song of `seconds` (in ms; a blank everywhere else). It is called once per piece, in order
    (`aligner.pieces`), and gives a piece 320 samples a frame, or `per_piece` frames per 30 s (not a
    whole number of samples a frame, as the real model's 1499)."""

    def __init__(self, letters: dict[int, str], seconds: float, per_piece: int | None = None) -> None:
        self.letters, self.per_piece = letters, per_piece
        self.pieces = aligner.pieces(round(seconds * aligner.RATE))

    def get_dict(self, *, star: str | None) -> dict[str, int]:
        assert star == "*"
        return {c: n for n, c in enumerate(ALPHABET)}

    def get_model(self, *, with_star: bool, dl_kwargs: dict[str, str]) -> Any:
        assert with_star
        assert dl_kwargs == {"file_name": "fake_fa.pt"}  # its own name in torch's cache, not model.pt
        torch = pytest.importorskip("torch")

        def model(wave: Any) -> tuple[Any, None]:
            a, b, _, _ = self.pieces.pop(0)
            assert wave.shape[1] == b - a
            per = self.per_piece or aligner.PIECE_S * aligner.RATE // 320
            frames = (b - a) * per // (aligner.PIECE_S * aligner.RATE)
            emission = torch.full((1, frames, len(ALPHABET)), -10.0)
            emission[0, :, 0] = -0.01
            emission[0, :, -1] = -5.0  # the star: what is not the text, better than a letter not heard
            for ms, letter in self.letters.items():
                if a <= ms * 16 < b:
                    frame = (ms * 16 - a) * frames // (b - a)
                    emission[0, frame, :] = -10.0
                    emission[0, frame, ALPHABET.index(letter)] = -0.01
            return emission, None

        return model


def test_the_aligner_times_each_word_and_keeps_it_out_of_a_pause(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    torchaudio = pytest.importorskip("torchaudio", reason="needs the align extra: uv sync --extra align")
    pytest.importorskip("uroman", reason="needs the align extra: uv sync --extra align")
    # "mama" sung from 0.2 s to 0.5 s, a pause of a second, then "one no" from 1.5 s; the model hears an
    # "o" in the last frame before the pause (the tail of "mama"), which "one" must not take
    letters = {200: "m", 240: "a", 280: "m", 320: "a", 480: "o", 1520: "n", 1560: "e", 2000: "n", 2040: "o"}
    monkeypatch.setattr(torchaudio.pipelines, "FAKE_FA", Bundle(letters, 3.0), raising=False)
    audio = song(tmp_path / "vocals.wav", [(0.2, 0.5), (1.5, 2.2)], 3.0)
    timed = hmv.HoneModels().align("FAKE_FA", audio, ["Mama!", "one — no"])
    expected = [[("Mama!", 200, 340)], [("one", 1520, 1580), ("no", 2000, 2060)]]  # "—": no letter
    assert [[w.text for w in line] for line in timed] == [[t for t, _, _ in line] for line in expected]
    # in ms (20 ms frames); next to a star, torchaudio's path may move a letter's start by a frame
    for line, wanted in zip(timed, expected, strict=True):
        for word, (_, start, end) in zip(line, wanted, strict=True):
            assert abs(word.start_ms - start) <= 20 and word.end_ms == end, word


def test_a_text_too_long_for_the_song_fails_naming_the_song(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    torchaudio = pytest.importorskip("torchaudio", reason="needs the align extra: uv sync --extra align")
    pytest.importorskip("uroman", reason="needs the align extra: uv sync --extra align")
    monkeypatch.setattr(torchaudio.pipelines, "FAKE_FA", Bundle({}, 0.1), raising=False)
    audio = song(tmp_path / "short.wav", [(0.0, 0.1)], 0.1)
    with pytest.raises(hmv.ModelFailure, match=r"FAKE_FA could not align the lyrics to short\.wav"):
        hmv.HoneModels().align("FAKE_FA", audio, ["mama " * 20])


def test_a_words_score_is_its_letters_mean_probability_over_their_frames() -> None:
    word = aligner._word("ab", [Span(10, 11, 0.9), Span(12, 15, 0.1)], 20.0)
    assert (word.text, word.start_ms, word.end_ms, word.score) == ("ab", 200, 300, pytest.approx(0.3))


def test_a_long_song_is_heard_in_pieces_joined_within_a_frame() -> None:
    torch = pytest.importorskip("torch", reason="needs the align extra: uv sync --extra align")
    total = 65 * aligner.RATE
    samples = np.arange(total, dtype=np.float32)  # each sample holds its own position in the song

    def model(wave: Any) -> tuple[Any, None]:
        """1499 frames per 30 s, as MMS: each frame holds the position of its first sample."""
        size = wave.shape[1]
        frames = size * 1499 // (aligner.PIECE_S * aligner.RATE)
        return wave[0, torch.arange(frames) * size // frames].reshape(1, frames, 1), None

    emission = aligner._emission(torch, model, samples)
    frames = emission.shape[1]
    per_frame = total / frames
    expected = torch.arange(frames) * per_frame
    assert abs(frames - 65 * 1499 / 30) <= len(aligner.pieces(total))  # at most a frame lost per piece
    assert float((emission[0, :, 0] - expected).abs().max()) < per_frame  # rounding stays under a frame


def test_a_word_across_the_pieces_boundary_keeps_its_times(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    torchaudio = pytest.importorskip("torchaudio", reason="needs the align extra: uv sync --extra align")
    pytest.importorskip("uroman", reason="needs the align extra: uv sync --extra align")
    letters = {29_900: "m", 29_960: "a", 30_040: "m", 30_100: "a"}  # "mama" across 30 s
    monkeypatch.setattr(torchaudio.pipelines, "FAKE_FA", Bundle(letters, 65.0, per_piece=1499), raising=False)
    audio = song(tmp_path / "long.wav", [(29.5, 30.5)], 65.0)
    ((word,),) = hmv.HoneModels().align("FAKE_FA", audio, ["mama"])
    frame = 30_000 / 1499
    assert abs(word.start_ms - 29_900) <= 2 * frame and abs(word.end_ms - (30_100 + frame)) <= 2 * frame


def test_an_unknown_bundle_fails_and_a_bug_is_raised(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    torchaudio = pytest.importorskip("torchaudio", reason="needs the align extra: uv sync --extra align")
    pytest.importorskip("uroman", reason="needs the align extra: uv sync --extra align")
    audio = song(tmp_path / "a.wav", [(0.0, 0.5)], 1.0)
    with pytest.raises(hmv.ModelFailure, match="NO_SUCH_FA is not one of torchaudio's pipelines"):
        hmv.HoneModels().align("NO_SUCH_FA", audio, ["mama"])

    class Broken(Bundle):
        def get_dict(self, *, star: str | None) -> dict[str, int]:
            raise KeyError("a bug, not a model failure")

    monkeypatch.setattr(torchaudio.pipelines, "FAKE_FA", Broken({}, 1.0), raising=False)
    with pytest.raises(KeyError, match="a bug"):
        hmv.HoneModels().align("FAKE_FA", audio, ["mama"])
