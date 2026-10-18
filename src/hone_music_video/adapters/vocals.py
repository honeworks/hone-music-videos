"""Vocal isolation for the first listen (D-041, D-045): Demucs `htdemucs` (MIT) on the CPU, in this
library until hone-models has a separation client (a temporary exception like D-002, behind the `Models`
port).

It needs the `separate` extra (torch and demucs), imported only here and only when called. The weights
(about 80 MB) download on first use to the Hugging Face cache (`~/.cache/huggingface/hub`, or
`$HF_HOME`), never into a project or the repository. It runs on the CPU whatever GPU there is: the GPU
belongs to the image and video models (D-005); a five-minute song takes a minute or two, once."""

from __future__ import annotations

from pathlib import Path

from hone_music_video.errors import ModelFailure, ToolMissing

INSTALL = "install hone-music-video[separate] to listen to the isolated vocals"


def separate(model_id: str, audio: Path, out: Path) -> Path:
    """The vocals of `audio` written to `out` as a WAV at the model's rate (44.1 kHz stereo)."""
    try:
        from demucs.api import Separator  # noqa: PLC0415 - the optional extra
        from demucs.audio import save_audio  # noqa: PLC0415
    except ImportError:
        raise ToolMissing(f"demucs is not installed: {INSTALL}") from None
    try:
        separator = Separator(model=model_id, device="cpu", progress=False)
        _, sources = separator.separate_audio_file(audio)
        save_audio(sources["vocals"], out, samplerate=separator.samplerate)
    except Exception as error:  # demucs and torch raise many kinds (download, decoding, memory)
        raise ModelFailure(
            f"{model_id} could not isolate the vocals of {audio.name}: {error} (the first run downloads "
            "its weights, about 80 MB, to the Hugging Face cache: ~/.cache/huggingface/hub or $HF_HOME)"
        ) from error
    return out
