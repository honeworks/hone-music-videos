"""`check_lyrics` (design §5.1): the timed lyrics checked against the song and the heard words.

Each finding names where it is (a line id, a section id, an instrumental span), the rule and by how much
in milliseconds. Errors keep the lyrics gate from being approved (D-015); warnings are shown."""

from __future__ import annotations

import itertools

from hone_music_video.aligned_lyrics import DISAGREE_MS, FAR_MS, UNSURE
from hone_music_video.lyrics_match import gaps, in_instrumental
from hone_music_video.records import Line, Moved, Problem, Report, Timeline, Word, Words
from hone_music_video.records_timeline import clock
from hone_music_video.timed_lyrics import plain, sung_lines

MOVED_MS = 150  # a line may sit at most this far from its heard words (D-003)


def _p(rule: str, where: str, message: str) -> Problem:
    return Problem(rule=rule, where=where, message=message)


def _span(where: str, start: int, end: int, duration: int) -> list[Problem]:
    if start >= end:
        return [_p("no-length", where, f"starts at {clock(start)}, not before its end {clock(end)}")]
    if end > duration:
        late = f"ends at {clock(end)}, {end - duration} ms after the song ends ({clock(duration)})"
        return [_p("outside-song", where, late)]
    return []


def _words(line: Line, duration: int) -> list[Problem]:
    found: list[Problem] = []
    previous: Word | None = None
    for n, word in enumerate(line.words, 1):
        where = f"{line.id} word {n} ({word.text})"
        found += _span(where, word.start_ms, word.end_ms, duration)
        if word.start_ms < line.start_ms or word.end_ms > line.end_ms:
            found.append(_p("word-outside-line", where, "lies outside its line's times"))
        if previous is not None and word.start_ms < previous.start_ms:
            early = previous.start_ms - word.start_ms
            found.append(_p("word-order", where, f"starts {early} ms before the word before it"))
        previous = word
    return found


def _heard(line: Line, heard: list[Word]) -> list[Problem]:
    """The line's start and end against its first and last heard word (D-003)."""
    first, last = line.heard_first, line.heard_last
    if first is None or last is None or not 0 <= first <= last < len(heard):
        why = f"is not timed from heard words (heard words {first}..{last} of {len(heard)})"
        return [_p("not-heard", line.id, why)]
    edges = (
        ("start", line.start_ms, first, heard[first].start_ms),
        ("end", line.end_ms, last, heard[last].end_ms),
    )
    found: list[Problem] = []
    for edge, ms, index, at in edges:
        if abs(ms - at) > MOVED_MS:
            moved = (
                f"its {edge} {clock(ms)} is {abs(ms - at)} ms from heard word {index} "
                f"({heard[index].text!r} at {clock(at)}); at most {MOVED_MS} ms"
            )
            found.append(_p("moved", line.id, moved))
    return found


def _lines(timeline: Timeline, heard: list[Word]) -> list[Problem]:
    found: list[Problem] = []
    previous: Line | None = None
    for line in timeline.lines:
        found += _span(line.id, line.start_ms, line.end_ms, timeline.duration_ms)
        if previous is not None and line.start_ms < previous.end_ms:
            early = previous.end_ms - line.start_ms
            found.append(_p("overlap", line.id, f"starts {early} ms before {previous.id} ends"))
        found += _words(line, timeline.duration_ms)
        if line.id not in timeline.owner_timed:  # the owner's times are not the words' (0018, D-115)
            found += _heard(line, heard)
        previous = line
    return found


def _sections(timeline: Timeline) -> list[Problem]:
    sections = {s.id: s for s in timeline.sections}
    found = [p for s in timeline.sections for p in _span(s.id, s.start_ms, s.end_ms, timeline.duration_ms)]
    for line in timeline.lines:
        section = sections.get(line.section)
        if section is None:
            found.append(_p("no-section", line.id, f"section {line.section!r} does not exist"))
        elif line.start_ms < section.start_ms or line.end_ms > section.end_ms:
            outside = (
                f"lies outside its section {section.id} ({clock(section.start_ms)}-{clock(section.end_ms)})"
            )
            found.append(_p("section-cover", line.id, outside))
    ordered = sorted(timeline.sections, key=lambda s: s.start_ms)
    for before, after in itertools.pairwise(ordered):
        if after.start_ms < before.end_ms:
            overlap = f"starts {before.end_ms - after.start_ms} ms before section {before.id} ends"
            found.append(_p("section-overlap", after.id, overlap))
    return found


def _instrumental(timeline: Timeline) -> list[Problem]:
    found: list[Problem] = []
    for n, span in enumerate(timeline.instrumental, 1):
        where = f"instrumental {n} ({span.kind})"
        found += _span(where, span.start_ms, span.end_ms, timeline.duration_ms)
        for line in timeline.lines:
            overlap = min(span.end_ms, line.end_ms) - max(span.start_ms, line.start_ms)
            if overlap > 0:
                found.append(
                    _p("instrumental-overlap", where, f"overlaps sung line {line.id} by {overlap} ms")
                )
    return found


def _runs(indices: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for i in indices:
        if runs and runs[-1][-1] == i - 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return runs


def _unused(timeline: Timeline, heard: list[Word]) -> list[Problem]:
    """Runs of heard words that no line is sung over."""
    used: set[int] = set()
    for line in timeline.lines:
        if line.heard_first is not None and line.heard_last is not None:
            used.update(range(line.heard_first, line.heard_last + 1))
    runs = _runs([i for i in range(len(heard)) if i not in used])
    found: list[Problem] = []
    for run in runs:
        text = " ".join(heard[i].text for i in run)
        where = f"heard words {run[0]}..{run[-1]}"
        found.append(_p("heard-unused", where, f"{text!r} at {clock(heard[run[0]].start_ms)} is in no line"))
    return found


def _not_found(timeline: Timeline, given: str | None) -> list[Problem]:
    """Given lines whose words appear in no line of the timeline (compared without marks and spaces)."""
    sung = plain(" ".join(line.text for line in timeline.lines))
    return [
        _p("lyrics-not-found", "given lyrics", f"{text!r} was not found in the audio")
        for text in sung_lines(given)
        if plain(text) and plain(text) not in sung
    ]


def _in_instrumental(timeline: Timeline, words: Words, given: str | None) -> list[Problem]:
    """Given lines still not heard whose gap is marked instrumental: they may be sung there (D-040)."""
    unheard = gaps(given, words.timing(), timeline.duration_ms)
    found: list[Problem] = []
    for gap, start, end in in_instrumental(timeline, unheard):
        lines = " / ".join(gap.lines)
        where = f"{clock(max(start, gap.start_ms))}-{clock(min(end, gap.end_ms))}"
        message = f"{lines!r} may be sung in {where}, which is marked instrumental; listen to it"
        found.append(_p("line-in-instrumental", f"instrumental {clock(start)}-{clock(end)}", message))
    return found


def _far(words: Words) -> list[Problem]:
    """The aligned lines recognition starts more than `FAR_MS` elsewhere: errors (0032)."""
    found: list[Problem] = []
    for line in words.aligned.disagree if words.aligned else []:
        apart = abs(line.aligned_ms - line.heard_ms)
        if apart > FAR_MS:
            message = (
                f"aligned at {clock(line.aligned_ms)}, heard at {clock(line.heard_ms)} ({apart} ms apart, "
                f"more than {FAR_MS} ms); set its times in the Lyrics view, or accept it"
            )
            found.append(_p("align-disagrees", line.line, message))
    return found


def _moved(moved: Moved) -> Problem:
    if moved.whole:
        message = (
            f"the aligner lost it at {clock(moved.from_ms)}: it is timed from the heard words, from "
            f"{clock(moved.to_ms)}; listen to it"
        )
        return _p("timed-from-heard", moved.line, message)
    message = (
        f"its first word started {moved.to_ms - moved.from_ms} ms before it was heard: it starts at "
        f"{clock(moved.to_ms)}, where it was heard; listen to it"
    )
    return _p("start-from-heard", moved.line, message)


def _alignment(words: Words) -> list[Problem]:
    """The given lyrics not aligned, the aligned lines recognition starts elsewhere (up to `FAR_MS`),
    those started or timed where they were heard (0030 §3, 0032) and those aligned with a low score
    (0005, D-058)."""
    found = [_p("not-aligned", "given lyrics", words.not_aligned)] if words.not_aligned else []
    for line in words.aligned.disagree if words.aligned else []:
        apart = abs(line.aligned_ms - line.heard_ms)
        message = (
            f"aligned at {clock(line.aligned_ms)}, heard at {clock(line.heard_ms)} ({apart} ms apart, "
            f"more than {DISAGREE_MS} ms); listen to it"
        )
        if apart <= FAR_MS:
            found.append(_p("align-disagrees", line.line, message))
    found += [_moved(moved) for moved in (words.aligned.moved if words.aligned else [])]
    for line in words.aligned.unsure if words.aligned else []:
        message = (
            f"aligned at {clock(line.start_ms)} with a low score ({line.score:.2f}, under {UNSURE}); "
            "listen to it"
        )
        found.append(_p("align-unsure", line.line, message))
    return found


def check_lyrics(timeline: Timeline, words: Words, given: str | None = None) -> Report:
    """The checks of design §5.1: errors for times outside the song, overlaps, lines moved from the
    words they are timed from (`Words.timing`) and sections or instrumental spans that do not fit;
    warnings for words no line uses and given lyrics lines not found in the audio, listens again that
    were not made, lines not heard where an instrumental span is marked (D-040, D-041), and given
    lyrics not aligned or aligned lines recognition starts elsewhere (0005); an error for a line more
    than `FAR_MS` from where it was heard (0032)."""
    timing = words.timing()
    errors = _lines(timeline, timing) + _sections(timeline) + _instrumental(timeline) + _far(words)
    warnings = _unused(timeline, timing) + _not_found(timeline, given)
    warnings += [_p("not-listened", "heard words", why) for why in words.not_listened]
    warnings += _in_instrumental(timeline, words, given) + _alignment(words)
    return Report(errors=errors, warnings=warnings)
