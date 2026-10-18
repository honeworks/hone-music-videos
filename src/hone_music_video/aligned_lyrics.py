"""Given lyrics aligned to the song's vocals (change 0005, design §6 step 1c): the lines are timed from
the aligned words, and recognition is the cross-check.

Forced alignment places the given words on the audio: it does not have to recognise them, so no given
line is missed. The heard words stay in `words.json`; a given line whose aligned start is more than
`DISAGREE_MS` from the start of the heard words it was found in is named (D-058), and so is a line
the aligner placed with a score under `UNSURE` (D-058). Aligned on the mix (the vocals could not be
isolated), the lyrics report says so. When the aligner is off, not installed or fails, the lines are
timed from the heard words as before, and the lyrics report says why (`not_aligned`)."""

from __future__ import annotations

import time
from pathlib import Path

from hone_music_video._jobs import Job
from hone_music_video.errors import ModelFailure, ToolMissing
from hone_music_video.lyrics_match import found_spans
from hone_music_video.records import AlignedWord, Alignment, Disagreement, Moved, Song, Unsure, Word, Words
from hone_music_video.timed_lyrics import plain, sung_lines, tidy

# On the owner's song, 39 of the 42 lines recognition found start within 467 ms of their aligned start
# (median 25 ms); the other three are 982 to 2595 ms apart, and in each one of the two is off the
# singing by 450 ms or more (D-058).
DISAGREE_MS = 750
# A line's score is its words' scores weighted by their length. On the owner's song 41 of 43 lines score
# 0.49 or more; the two under 0.3 are the whispered outro line (0.17) and the last line, whose held
# "Lo-ren-am…" (0.05) is placed seconds late (0.12) (D-058).
UNSURE = 0.3
# Midnight Mambo Shoes: the outro's lines the aligner lost are 5.9 to 32.9 s from where they were heard;
# a confident line further than this from it is an error, never auto-approved (0032)
FAR_MS = 3000
# This too shall pass: the three lines the aligner starts 0.9 to 2.1 s early have their second word
# within 150 ms of recognition's (0030 §3)
SECOND_WORD_MS = 300
NOT_ALIGNED = "the given lyrics were not aligned, so the lines are timed from the heard words: {why}"
ON_MIX = "the given lyrics were aligned on the mix (no isolated vocals); their timing may be less exact"


def findings(
    lines: list[str], timed: list[list[AlignedWord]], heard: list[int | None]
) -> tuple[list[Disagreement], list[Unsure]]:
    """The aligned lines whose start is more than `DISAGREE_MS` from where they were heard (`heard`:
    each line's heard start, `None` when not found), and those whose score, their words' scores
    weighted by their length, is under `UNSURE` (D-058). A line without words or length is neither."""
    disagree: list[Disagreement] = []
    unsure: list[Unsure] = []
    for text, own, at in zip(lines, timed, heard, strict=True):
        score = _score(own)
        if score is None:
            continue
        start = own[0].start_ms
        if at is not None and abs(start - at) > DISAGREE_MS:
            disagree.append(Disagreement(line=text, aligned_ms=start, heard_ms=at))
        if score < UNSURE:
            unsure.append(Unsure(line=text, start_ms=start, score=round(score, 3)))
    return disagree, unsure


def _score(own: list[AlignedWord]) -> float | None:
    """A line's score: its words' scores weighted by their length; `None` without words or length."""
    lengths = [w.end_ms - w.start_ms for w in own]
    if not own or sum(lengths) == 0:
        return None
    return sum(w.score * n for w, n in zip(own, lengths, strict=True)) / sum(lengths)


def _from_heard(own: list[AlignedWord], heard: list[Word], n: int | None) -> AlignedWord | None:
    """A line's first aligned word where recognition heard it, when the aligner stretched it back into
    the pause (0030 §3): the same word is the heard word the line was found at, or the one before it
    (a line can be found from its second word), the aligner starts it over `DISAGREE_MS` earlier, and
    its second word is within `SECOND_WORD_MS` of the next heard word; else `None`."""
    if n is None or len(own) < 2:  # a first and a second word
        return None
    k = next(
        (k for k in (n, n - 1) if 0 <= k < len(heard) - 1 and plain(heard[k].text) == plain(own[0].text)),
        None,
    )
    if k is None:
        return None
    first, second = heard[k], heard[k + 1]
    early = first.start_ms - own[0].start_ms > DISAGREE_MS
    if not early or abs(own[1].start_ms - second.start_ms) > SECOND_WORD_MS:
        return None
    end = own[0].end_ms if own[0].end_ms > first.start_ms else min(first.end_ms, own[1].start_ms)
    return own[0].model_copy(update={"start_ms": first.start_ms, "end_ms": end})


def started_where_heard(
    lines: list[str], timed: list[list[AlignedWord]], heard: list[Word], found: list[int | None]
) -> list[Moved]:
    """Each line whose first word was stretched into the pause starts where it was heard (changed in
    `timed`); the lines moved."""
    moved: list[Moved] = []
    for text, own, n in zip(lines, timed, found, strict=True):
        word = _from_heard(own, heard, n)
        if word is not None:
            moved.append(Moved(line=text, from_ms=own[0].start_ms, to_ms=word.start_ms))
            own[0] = word
    return moved


def _over(own: list[AlignedWord], start: int, end: int) -> list[AlignedWord]:
    """The line's words placed from `start` to `end`, their lengths in the same proportions."""
    first, length = own[0].start_ms, max(1, own[-1].end_ms - own[0].start_ms)

    def at(ms: int) -> int:
        return start + round((ms - first) * (end - start) / length)

    return [w.model_copy(update={"start_ms": at(w.start_ms), "end_ms": at(w.end_ms)}) for w in own]


def _lost(
    own: list[AlignedWord], heard: list[Word], span: tuple[int, int] | None
) -> list[AlignedWord] | None:
    """The line's words over its heard words when the aligner lost it: more than `DISAGREE_MS` from where
    it was heard and a score under `UNSURE` (0032); else `None`."""
    score = _score(own)
    if span is None or score is None or score >= UNSURE:
        return None
    first, last = heard[span[0]], heard[span[1]]
    if abs(own[0].start_ms - first.start_ms) <= DISAGREE_MS:
        return None
    return _over(own, first.start_ms, last.end_ms)


def timed_where_heard(
    lines: list[str], timed: list[list[AlignedWord]], heard: list[Word], spans: list[tuple[int, int] | None]
) -> list[Moved]:
    """Each line the aligner lost timed from its heard words (changed in `timed`), unless that would put
    it over a neighbouring line; the lines moved (0032)."""
    placed = [_lost(own, heard, span) for own, span in zip(timed, spans, strict=True)]
    while True:  # a move over a neighbour is dropped; the neighbours are then checked again
        final = [p if p is not None else own for p, own in zip(placed, timed, strict=True)]
        clash = next((n for n, p in enumerate(placed) if p is not None and _overlaps(final, n)), None)
        if clash is None:
            break
        placed[clash] = None
    moved: list[Moved] = []
    for n, (text, words) in enumerate(zip(lines, placed, strict=True)):
        if words is not None:
            moved.append(Moved(line=text, from_ms=timed[n][0].start_ms, to_ms=words[0].start_ms, whole=True))
            timed[n] = words
    return moved


def _overlaps(final: list[list[AlignedWord]], n: int) -> bool:
    """Line `n` starts before the line before it ends, or ends after the line after it starts."""
    before = next((own[-1].end_ms for own in reversed(final[:n]) if own), None)
    after = next((own[0].start_ms for own in final[n + 1 :] if own), None)
    own = final[n]
    return (before is not None and own[0].start_ms < before) or (after is not None and own[-1].end_ms > after)


def align_lyrics(job: Job, audio: Path, measured: Song, lyrics: str | None, heard: Words) -> Words:
    """`heard` with the given sung lines aligned to `audio` (the vocals, or the mix when they could not
    be isolated): the aligned words tidied inside the song (D-017) and the lines recognition starts
    elsewhere. Unchanged without sung lines or with `models.align` off."""
    model, lines = job.settings.models.align, sung_lines(lyrics)
    if model is None or not lines:
        return heard
    began = time.monotonic()
    try:
        timed = job.models.align(model, audio, lines)
    except (ToolMissing, ModelFailure) as error:
        return heard.model_copy(update={"not_aligned": NOT_ALIGNED.format(why=error)})
    took_ms = round((time.monotonic() - began) * 1000)
    spans = found_spans(lyrics, heard.words)
    found = [None if span is None else span[0] for span in spans]
    moved = started_where_heard(lines, timed, heard.words, found)
    moved += timed_where_heard(lines, timed, heard.words, spans)
    words = tidy([w for line in timed for w in line], measured.duration_ms)
    if not words:
        why = "no given word has a letter the aligner knows"
        return heard.model_copy(update={"not_aligned": NOT_ALIGNED.format(why=why)})
    starts = [None if n is None else heard.words[n].start_ms for n in found]
    disagree, unsure = findings(lines, timed, starts)
    job.events.write(
        "lyrics_aligned",
        model=model,
        took_ms=took_ms,
        words=len(words),
        disagree=len(disagree),
        unsure=len(unsure),
        moved=len(moved),
    )
    aligned = Alignment(
        model=model, took_ms=took_ms, words=words, disagree=disagree, unsure=unsure, moved=moved
    )
    on_mix = [ON_MIX] if heard.vocals is None else []  # the first listen could not isolate them (D-045)
    return heard.model_copy(update={"aligned": aligned, "not_listened": heard.not_listened + on_mix})
