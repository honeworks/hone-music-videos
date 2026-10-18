"""Forced alignment of given lyrics (change 0005, D-055 to D-057): Meta's MMS aligner, torchaudio's
`MMS_FA` bundle, on the CPU, in this library until hone-models has an alignment client (a temporary
exception like D-002 and D-041, behind the `Models` port).

It needs the `align` extra (torch, torchaudio, uroman), imported only here and only when called. The
weights (1.2 GB) download on first use to torch's cache (`~/.cache/torch/hub`, or `$TORCH_HOME`), never
into a project or the repository. The aligner knows Latin letters only, so every word goes through
`uroman` first (D-056). It runs on the CPU whatever GPU there is (D-005): the song is heard in pieces of
30 s, about 50 s for a five-minute song (D-055)."""

from __future__ import annotations

import itertools
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError

import numpy as np
import numpy.typing as npt

from hone_music_video.errors import ModelFailure, ToolMissing
from hone_music_video.records import AlignedWord

INSTALL = (
    "install hone-music-video[align] to time given lyrics by forced alignment (not available on Intel macOS)"
)
RATE = 16_000  # what the MMS models hear
PIECE_S, CONTEXT_S = 30, 2  # the song heard in pieces of 30 s, each with 2 s more on each side (D-055)
QUIET_DB = -50  # a 20 ms frame this far below the loudest frame of the vocals is quiet (D-057)
PAUSE_FRAMES = 15  # quiet frames in a row (300 ms) that no word is sung across (D-057)
BLANK, STAR = "-", "*"  # MMS_FA's blank, and the token that takes what is not the text

Samples = npt.NDArray[np.float32]


@dataclass(frozen=True)
class Span:
    """A letter's frames of the emission, `start` included, `end` not, and its mean probability there."""

    start: int
    end: int
    score: float = 1.0


def read_audio(audio: Path) -> Samples:
    """`audio` as 16 kHz mono samples, decoded by ffmpeg (torchaudio no longer reads files itself)."""
    if shutil.which("ffmpeg") is None:
        raise ToolMissing("ffmpeg is not installed; install it to time given lyrics by forced alignment")
    command = ["ffmpeg", "-v", "error", "-i", str(audio), "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"]
    done = subprocess.run(command, capture_output=True, check=False)  # noqa: S603
    if done.returncode != 0 or not done.stdout:
        why = done.stderr.decode(errors="replace").strip() or "no audio"
        raise ModelFailure(f"could not read {audio.name} to align the lyrics: {why}")
    raw: bytes = done.stdout
    return np.frombuffer(raw, dtype=np.float32)  # pyright: ignore[reportUnknownMemberType] - numpy's stub


def letters(word: str, romanise: Callable[[str], str], alphabet: Mapping[str, int]) -> str:
    """The word's letters as the aligner knows them: romanised, lower case, only the alphabet's letters
    (hyphens, marks, punctuation and digits left out, D-056)."""
    return "".join(c for c in romanise(word).lower() if c in alphabet and c not in (BLANK, STAR))


def pieces(total: int) -> list[tuple[int, int, int, int]]:
    """The pieces the song is heard in: (heard from, heard to, kept from, kept to) in samples; each
    keeps `PIECE_S` and hears `CONTEXT_S` more on each side, inside the song."""
    step, context = PIECE_S * RATE, CONTEXT_S * RATE
    return [
        (max(0, s - context), min(total, s + step + context), s, min(total, s + step))
        for s in range(0, total, step)
    ]


def quiet(samples: Samples, frames: int) -> list[bool]:
    """For each of `frames` equal frames of `samples`: is it `QUIET_DB` or more below the loudest?"""
    edges = np.arange(frames + 1) * len(samples) // frames
    rms = np.array([np.sqrt(np.mean(np.square(samples[a:b]))) for a, b in itertools.pairwise(edges)])
    return [bool(r <= rms.max() * 10 ** (QUIET_DB / 20)) for r in rms]


def sung_part(spans: list[Span], is_quiet: Sequence[bool]) -> list[Span]:
    """A word's letters, without those across a pause of the vocals (`PAUSE_FRAMES` quiet frames in a
    row between two letters): the side with the most letters, the first on a tie (D-057)."""
    groups = [[spans[0]]]
    for span in spans[1:]:
        run = longest = 0
        for frame in range(groups[-1][-1].end, span.start):
            run = run + 1 if is_quiet[frame] else 0
            longest = max(longest, run)
        if longest >= PAUSE_FRAMES:
            groups.append([span])
        else:
            groups[-1].append(span)
    return max(groups, key=len)


def _modules() -> tuple[Any, Any, Any]:
    try:
        import torch  # noqa: PLC0415 - the optional extra
        import torchaudio  # noqa: PLC0415  # pyright: ignore[reportMissingTypeStubs]
        import uroman  # noqa: PLC0415  # pyright: ignore[reportMissingTypeStubs]
    except ImportError:
        raise ToolMissing(f"torchaudio or uroman is not installed: {INSTALL}") from None
    return torch, torchaudio, uroman


def _emission(torch: Any, model: Any, samples: Samples) -> Any:
    """The model's log-probabilities for the whole song, heard piece by piece (`pieces`)."""
    kept: list[Any] = []
    with torch.inference_mode():
        for a, b, s, e in pieces(len(samples)):
            heard, _ = model(torch.from_numpy(samples[a:b].copy()).unsqueeze(0))
            per = heard.shape[1] / (b - a)  # frames per sample
            first = round((s - a) * per)
            kept.append(heard[0, first : first + round((e - s) * per)])
    return torch.cat(kept).unsqueeze(0)


def _spans(torch: Any, torchaudio: Any, emission: Any, tokens: list[int]) -> list[Span]:
    """Each token's frames on the best path through the emission (torchaudio's forced aligner)."""
    path, scores = torchaudio.functional.forced_align(emission, torch.tensor([tokens], dtype=torch.int32))
    merged = torchaudio.functional.merge_tokens(path[0], scores[0].exp())
    return [Span(m.start, m.end, float(m.score)) for m in merged]


def _word(text: str, own: list[Span], ms: float) -> AlignedWord:
    """A word from its letters: from the first's start to the last's end, its score their mean
    probability over their frames (D-058)."""
    frames = sum(s.end - s.start for s in own)
    score = sum(s.score * (s.end - s.start) for s in own) / frames
    start, end = round(own[0].start * ms), round(own[-1].end * ms)
    return AlignedWord(text=text, start_ms=start, end_ms=end, score=min(1.0, max(0.0, score)))


def _align(
    modules: tuple[Any, Any, Any], model_id: str, samples: Samples, lines: Sequence[str]
) -> list[list[AlignedWord]]:
    torch, torchaudio, uroman = modules
    bundle = getattr(torchaudio.pipelines, model_id, None)
    if bundle is None:
        raise ModelFailure(f"{model_id} is not one of torchaudio's pipelines (models.align: try MMS_FA)")
    alphabet: dict[str, int] = bundle.get_dict(star=STAR)
    romanise = uroman.Uroman().romanize_string
    words = [(n, w, letters(w, romanise, alphabet)) for n, line in enumerate(lines) for w in line.split()]
    words = [(n, w, t) for n, w, t in words if t]
    tokens = [alphabet[STAR]]
    for _, _, text in words:
        tokens += [alphabet[c] for c in text] + [alphabet[STAR]]
    # its own file name in torch's cache: torchaudio's default for MMS_FA is a bare `model.pt` (D-055)
    model = bundle.get_model(with_star=True, dl_kwargs={"file_name": f"{model_id.lower()}.pt"})
    emission = _emission(torch, model, samples)
    spans, frames = _spans(torch, torchaudio, emission, tokens), emission.shape[1]
    is_quiet, ms = quiet(samples, frames), len(samples) * 1000 / (frames * RATE)
    timed: list[list[AlignedWord]] = [[] for _ in lines]
    at = 1  # the first word's letters follow the first star
    for n, word, text in words:
        timed[n].append(_word(word, sung_part(spans[at : at + len(text)], is_quiet), ms))
        at += len(text) + 1
    return timed


def align(model_id: str, audio: Path, lines: Sequence[str]) -> list[list[AlignedWord]]:
    """Each line's words with their start and end in ms and their score, aligned to `audio`; a word
    without a letter the aligner knows is left out."""
    modules = _modules()  # ToolMissing before the audio is read
    samples = read_audio(audio)
    try:
        return _align(modules, model_id, samples, lines)
    except (RuntimeError, OSError, URLError) as error:  # torch's own errors, the download; not our bugs
        raise ModelFailure(
            f"{model_id} could not align the lyrics to {audio.name}: {error} (the first run downloads its "
            "weights, about 1.2 GB, to torch's cache: ~/.cache/torch/hub or $TORCH_HOME)"
        ) from error
