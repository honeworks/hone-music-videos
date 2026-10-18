"""The first listen (design §6 step 1): the song's vocals, isolated once on the CPU, go to the transcriber
with the opening of the given lyrics as the prompt (D-045); a first listen that finds too few of the
given lines is made once more and the better kept (D-047).

Without the `separate` extra, or when the separation fails, the first listen hears the mix and says why
in `Words.not_listened`, so the lyrics report warns. The vocals are kept in the project's `vocals/`,
named after the model and the song's sha256 with their `Separation` record beside them (written last),
so a run made again does not separate the song again."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from hone_music_video._files import read_json, write_json
from hone_music_video._jobs import Job
from hone_music_video.errors import ModelFailure, ToolMissing
from hone_music_video.lyrics_match import Gap, latin_song, lines_found, suspect
from hone_music_video.records import Retry, Separation, Song, Words
from hone_music_video.timed_lyrics import tidy, transcription_prompt


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def song_vocals(job: Job, song: Path) -> tuple[Path, Separation]:
    """The song's vocals and their record: made once per song (by sha256) and model, then kept in the
    project; `ToolMissing` without the extra, `ModelFailure` when the separation fails."""
    model, digest = job.settings.models.vocals, _sha256(song)
    key = hashlib.sha256(f"{model}|{digest}".encode()).hexdigest()[:12]
    out = job.project.vocals_dir / f"{model}-{key}.wav"
    if out.is_file() and out.with_suffix(".json").is_file():
        return out, read_json(out.with_suffix(".json"), Separation)
    out.parent.mkdir(parents=True, exist_ok=True)
    partial = out.with_name(f".{out.stem}.partial.wav")  # a crash leaves no file that looks finished
    began = time.monotonic()
    try:
        job.models.separate_vocals(model, song, out=partial)
    except (ToolMissing, ModelFailure):
        partial.unlink(missing_ok=True)
        raise
    took_ms = round((time.monotonic() - began) * 1000)
    partial.replace(out)
    made = Separation(model=model, took_ms=took_ms, input_sha256=digest, output_sha256=_sha256(out))
    write_json(out.with_suffix(".json"), made)
    job.events.write("vocals_isolated", model=model, took_ms=took_ms)
    return out, made


def _hear(job: Job, audio: Path, measured: Song, lyrics: str | None) -> Words:
    """One first listen of `audio`: the heard words, tidied inside the song (D-017)."""
    heard = job.models.transcribe(
        job.settings.models.speech, audio, language=job.settings.language, prompt=transcription_prompt(lyrics)
    )
    return heard.model_copy(update={"words": tidy(heard.words, measured.duration_ms)})


def _rejected(heard: Words, lyrics: str | None) -> str | None:
    """Why a first listen is not to be trusted (D-040's guard on the whole song): a word longer than
    `LONGEST_WORD_MS`, or, in a song not written in Latin letters, the prompt's transliterations copied."""
    song = Gap([], 0, 0, latin_song(lyrics))
    return suspect(heard.words, song, transcription_prompt(lyrics) or "")


def _hear_twice_if_poor(job: Job, audio: Path, measured: Song, lyrics: str | None) -> Words:
    """The first listen, made again once when more than a third of the given sung lines are not found
    in it (D-047): a listen that passes the guard (`_rejected`) is preferred, then the one that found
    more lines, the first on a tie."""
    heard = _hear(job, audio, measured, lyrics)
    found, lines = lines_found(lyrics, heard.words)
    job.events.write("first_listen", found=found, lines=lines)
    if 3 * (lines - found) <= lines:
        return heard
    again = _hear(job, audio, measured, lyrics)
    found_again = lines_found(lyrics, again.words)[0]
    job.events.write("first_listen", found=found_again, lines=lines, again=True)
    first_rejected, again_rejected = _rejected(heard, lyrics), _rejected(again, lyrics)
    kept_again = (again_rejected is None, found_again) > (first_rejected is None, found)
    retry = Retry(
        lines=lines,
        first_found=found,
        again_found=found_again,
        kept_again=kept_again,
        other=(heard if kept_again else again).call,
        first_rejected=first_rejected,
        again_rejected=again_rejected,
    )
    return (again if kept_again else heard).model_copy(update={"retried": retry})


def first_listen(job: Job, song: Path, measured: Song, lyrics: str | None) -> tuple[Words, Path | None]:
    """The heard words of the song's vocals (or of the mix, with why, when they cannot be isolated),
    and the vocals file (`None`: the mix was heard)."""
    try:
        vocals, made = song_vocals(job, song)
    except (ToolMissing, ModelFailure) as error:
        heard = _hear_twice_if_poor(job, song, measured, lyrics)
        why = f"first listen on the mix, not the isolated vocals: {error}"
        return heard.model_copy(update={"not_listened": [why]}), None
    heard = _hear_twice_if_poor(job, vocals, measured, lyrics)
    return heard.model_copy(update={"vocals": made}), vocals
