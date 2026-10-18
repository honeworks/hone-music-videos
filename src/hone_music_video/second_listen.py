"""Listening again (design §6 step 1b, D-040, D-046): a given lyrics line the first listen did not hear
is listened for in the slice of the song where it belongs.

Each gap of `lyrics_match.gaps` is cut into windows of at most 30 s, each with the missing lines
expected in it (the gap's lines spread over its windows in order). A window is cut from the song with a
margin and sent to the same transcriber with those lines as the prompt: first the slice of the mix (the
second listen), then, when that does not find every line, the same slice of the song's isolated vocals
(the third; D-046 has the measurement). Without the vocals (D-045) the mix is the one listen. The words
the last listen heard inside the window, shifted by the slice's start, take the place of the first
listen's words there; every time is still a heard word's (D-003)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from hone_music_video._jobs import Job
from hone_music_video.errors import ModelFailure, ToolMissing
from hone_music_video.lyrics_match import Gap, all_heard, gaps, suspect
from hone_music_video.records import ListenAgain, Separation, Song, Word, Words
from hone_music_video.records_timeline import clock
from hone_music_video.timed_lyrics import tidy, transcription_prompt

MARGIN_MS = 500  # the slice reaches this far past the window on each side, inside the song
WINDOW_MS = 30_000  # a gap is listened to in windows at most this long (D-040, D-046)
MAX_LISTENS = 16  # listens again per song, second and third counted, in song order (D-046)


def cut(song: Path, start_ms: int, end_ms: int, out: Path) -> Path:
    """The song (or its vocals) from `start_ms` to `end_ms` as a mono 16 kHz WAV, what Whisper hears
    (PCM, so the slice starts exactly at `start_ms`)."""
    if shutil.which("ffmpeg") is None:
        raise ToolMissing("ffmpeg is not installed; install it to listen again for lyrics lines not heard")
    command = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start_ms / 1000:.3f}", "-i", str(song)]
    command += ["-t", f"{(end_ms - start_ms) / 1000:.3f}", "-vn", "-ac", "1", "-ar", "16000"]
    done = subprocess.run([*command, str(out)], capture_output=True, text=True, check=False)  # noqa: S603
    if done.returncode != 0:
        raise ModelFailure(f"could not cut {song.name} at {start_ms}-{end_ms} ms: {done.stderr.strip()}")
    return out


def windows(gap: Gap) -> list[Gap]:
    """The gap cut into the fewest equal windows of at most `WINDOW_MS`, in order, each with the lines
    expected in it: the gap's lines spread evenly over the windows in order, a line that falls on a
    boundary in both windows (D-046). A gap of up to `WINDOW_MS` is one window with all its lines."""
    length, count = gap.end_ms - gap.start_ms, -(-(gap.end_ms - gap.start_ms) // WINDOW_MS)
    found, lines = list[Gap](), len(gap.lines)
    for n in range(count):
        start, end = gap.start_ms + length * n // count, gap.start_ms + length * (n + 1) // count
        expected = gap.lines[lines * n // count : -(-lines * (n + 1) // count)]
        found.append(Gap(expected, start, end, gap.latin))
    return found


Source = tuple[Path, Separation | None]  # the mix, or the song's vocals with their separation


def _hear(
    job: Job, source: Source, window: Gap, start: int, end: int, *, folder: Path
) -> tuple[list[Word], ListenAgain]:
    """One listen to a window's slice: the words heard in the whole slice (margins included), in song
    time (none when its reply is not taken as heard), and its record."""
    audio, vocals = source
    piece = cut(audio, start, end, folder / f"{'vocals' if vocals else 'slice'}-{start}-{end}.wav")
    prompt = transcription_prompt("\n".join(window.lines))
    heard = job.models.transcribe(
        job.settings.models.speech, piece, language=job.settings.language, prompt=prompt
    )
    rejected = suspect(heard.words, window, prompt or "")
    shifted = (
        []
        if rejected
        else [Word(text=w.text, start_ms=w.start_ms + start, end_ms=w.end_ms + start) for w in heard.words]
    )
    kept = [w for w in shifted if window.start_ms <= w.start_ms < window.end_ms]
    record = ListenAgain(
        lines=window.lines,
        start_ms=start,
        end_ms=end,
        gap_start_ms=window.start_ms,
        gap_end_ms=window.end_ms,
        heard=len(kept),
        call=heard.call,
        vocals=vocals,
        rejected=rejected,
    )
    job.events.write(
        "listened_again",
        listen="third" if vocals else "second",
        start_ms=start,
        end_ms=end,
        heard=len(kept),
        rejected=rejected,
    )
    return shifted, record


def _listen(
    job: Job, sources: list[Source], window: Gap, duration_ms: int, *, folder: Path, left: int
) -> tuple[list[Word], list[ListenAgain], bool]:
    """The listens of a window, one per source in order until every expected line is heard in the
    slice (its margins included: a line on a window's edge is heard whole there), at most `left`: the
    words of the last listen that heard any in the window, the listens' records, and whether a listen
    still needed was not made because of the cap."""
    start, end = max(0, window.start_ms - MARGIN_MS), min(duration_ms, window.end_ms + MARGIN_MS)
    words: list[Word] = []
    records: list[ListenAgain] = []
    for source in sources:
        if len(records) == left:
            return words, records, True
        heard, record = _hear(job, source, window, start, end, folder=folder)
        records.append(record)
        words = [w for w in heard if window.start_ms <= w.start_ms < window.end_ms] or words
        if all_heard(window, heard):
            break
    return words, records, False


def _span(gap: Gap) -> str:
    return f"{clock(gap.start_ms)}-{clock(gap.end_ms)}"


def listen_again(
    job: Job, song: Path, measured: Song, lyrics: str | None, words: Words, *, vocals: Path | None
) -> Words:
    """The heard words with each gap listened to again in windows (at most `MAX_LISTENS` listens): the
    words the last listen heard inside a window replace the first listen's words there; a listen that
    hears nothing there changes nothing. Each listen is kept in `Words.listened_again`, each window not
    listened to named in `Words.not_listened`."""
    found = [w for gap in gaps(lyrics, words.words, measured.duration_ms) for w in windows(gap)]
    sources: list[Source] = [(song, None)] + ([(vocals, words.vocals)] if vocals else [])
    merged, records, skipped, dropped = list(words.words), list[ListenAgain](), list[Gap](), list[Gap]()
    with tempfile.TemporaryDirectory(dir=song.parent, prefix=".listen-again-") as tmp:
        for window in found:
            left = MAX_LISTENS - len(records)
            if left <= 0:
                skipped.append(window)
                continue
            heard, listens, cut_short = _listen(
                job, sources, window, measured.duration_ms, folder=Path(tmp), left=left
            )
            records += listens
            dropped += [window] if cut_short else []
            if heard:
                outside = [w for w in merged if not window.start_ms <= w.start_ms < window.end_ms]
                merged = sorted(outside + heard, key=lambda w: w.start_ms)
    capped = f"(at most {MAX_LISTENS} listens per song)"
    not_listened = list(words.not_listened)
    not_listened += [f"the vocals listen of window {_span(w)} not made {capped}" for w in dropped]
    if skipped:
        not_listened.append(f"windows {', '.join(_span(w) for w in skipped)} not listened to again {capped}")
    update = {
        "words": tidy(merged, measured.duration_ms),
        "listened_again": records,
        "not_listened": not_listened,
    }
    return words.model_copy(update=update)
