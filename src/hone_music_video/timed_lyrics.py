"""Timed lyrics (design §6): what the lyrics editor answers, and the timeline the code builds from it.

The editor never writes a time (D-003, D-016). It answers `LyricsEdit`: each line's corrected text and
the range of heard words it is sung over (indices into `words.json`), the sections, and after which line
each instrumental span falls. The code then takes every time from the heard words: a line starts at its
first heard word and ends at its last, each written word gets the times of the heard words it lines up
with, a section spans its lines, an instrumental span fills the gap between two lines."""

from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher

from pydantic import BaseModel

from hone_music_video.records import STRICT, Instrumental, Line, Section, Timeline, Word, Words

PROMPT_CHARS = 400  # Whisper keeps only the last ~224 tokens of its prompt; other scripts tokenise densely


class EditedSection(BaseModel):
    """A section of the song: `kind` is intro, verse, pre-chorus, chorus, bridge or outro."""

    model_config = STRICT
    id: str
    kind: str
    notes: str = ""  # the lyrics' bracketed notes for this section, word for word (0028)


class EditedLine(BaseModel):
    """A sung line: its corrected text, its section, and the heard words it is sung over (inclusive)."""

    model_config = STRICT
    section: str
    text: str
    heard_first: int
    heard_last: int


class EditedBreak(BaseModel):
    """An instrumental span: after line `after_line` (1-based; 0 = before the first line)."""

    model_config = STRICT
    after_line: int
    kind: str
    notes: str = ""  # as a section's (0028)


class LyricsEdit(BaseModel):
    """The lyrics editor's reply (the JSON Schema of its one call, design §6 step 2)."""

    model_config = STRICT
    language: str | None = None
    sections: list[EditedSection]
    lines: list[EditedLine]
    instrumental: list[EditedBreak] = []


# ------------------------------------------------------------------------------ the given lyrics


def sung_lines(lyrics: str | None) -> list[str]:
    """The given lyrics' sung lines: blank lines and [bracketed notes] (sections, directions) left out."""
    found = [line.strip() for line in (lyrics or "").splitlines()]
    return [line for line in found if line and not line.startswith("[")]


def transcription_prompt(lyrics: str | None) -> str | None:
    """The sung lines from the start of the lyrics, whole lines up to `PROMPT_CHARS` characters (a first
    line longer than that is cut at a word), so the opening of the song is what biases the transcriber
    (design §6, D-017)."""
    prompt = ""
    for line in sung_lines(lyrics):
        joined = f"{prompt} {line}".strip()
        if len(joined) > PROMPT_CHARS:
            if not prompt:
                prompt = joined[:PROMPT_CHARS].rsplit(" ", 1)[0]
            break
        prompt = joined
    return prompt or None


def tidy(words: list[Word], duration_ms: int | None = None) -> list[Word]:
    """Heard words as lines can be timed from (D-017): each ends where the next one starts at the latest
    and lasts at least 1 ms; with the song's length, a word starting at or after the end is left out and a
    word running past it ends there."""
    found: list[Word] = []
    for n, word in enumerate(words):
        start, end = word.start_ms, word.end_ms
        later = words[n + 1].start_ms if n + 1 < len(words) else end
        if later > start:
            end = min(end, later)  # cut an overlap at the next word's start
        if found:
            start = max(start, found[-1].end_ms)
        end = max(end, start + 1)
        if duration_ms is not None:
            if start >= duration_ms:
                break
            end = min(end, duration_ms)
        found.append(Word(text=word.text, start_ms=start, end_ms=end))
    return found


def plain(text: str) -> str:
    """Text for comparing words: letters and digits only, lower case, without marks (Arabic-script
    vowel signs, accents), joined without spaces."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed.lower() if unicodedata.category(c)[0] in "LN")


# ------------------------------------------------------------------------------ checking the reply


def _section_problems(edit: LyricsEdit) -> list[str]:
    """Section ids are unique, and each section's lines are one run, in the order of `sections`."""
    ids = [s.id for s in edit.sections]
    problems = ["section ids repeat; give every section its own id"] if len(set(ids)) != len(ids) else []
    named = [line.section for line in edit.lines if line.section in ids]
    runs = [section for n, section in enumerate(named) if n == 0 or section != named[n - 1]]
    split = sorted({section for section in runs if runs.count(section) > 1})
    problems += [f"section {section!r}: its lines are not one run; keep them together" for section in split]
    if not split and runs != sorted(runs, key=ids.index):
        problems.append(f"the lines' sections come in the order {runs}, not the order of sections")
    return problems


def edit_problems(edit: LyricsEdit, heard: int) -> list[str]:
    """What makes the reply unusable (sent back once, design §7.1); empty when it can be timed."""
    ids = [s.id for s in edit.sections]
    problems = _section_problems(edit)
    last = -1
    for n, line in enumerate(edit.lines, 1):
        if line.section not in ids:
            problems.append(f"line {n}: section {line.section!r} is not in sections")
        if not 0 <= line.heard_first <= line.heard_last < heard:
            first, last_word = line.heard_first, line.heard_last
            problems.append(f"line {n}: heard words {first}..{last_word} are not a range of 0..{heard - 1}")
        elif line.heard_first <= last:
            problems.append(f"line {n}: starts at heard word {line.heard_first}, inside the line before it")
        last = max(last, line.heard_last)
    problems += [
        f"instrumental span {n}: after_line {b.after_line} is not 0..{len(edit.lines)}"
        for n, b in enumerate(edit.instrumental, 1)
        if not 0 <= b.after_line <= len(edit.lines)
    ]
    return problems


# ------------------------------------------------------------------------------ building the timeline


def _spread(tokens: list[str], heard: list[Word]) -> list[Word]:
    """Each token gets the times of its share of `heard`, in order (several tokens may share one word)."""
    n, m = len(tokens), len(heard)
    shares = [(k * m // n, max(k * m // n, (k + 1) * m // n - 1)) for k in range(n)]
    return [
        Word(text=t, start_ms=heard[a].start_ms, end_ms=heard[b].end_ms)
        for t, (a, b) in zip(tokens, shares, strict=True)
    ]


def line_words(text: str, heard: list[Word]) -> list[Word]:
    """The line's written words, each timed from the heard words it lines up with: matching words take
    their heard word's times, the others share the heard words between their neighbours."""
    tokens = text.split()
    if not tokens or not heard:
        return []
    matcher = SequenceMatcher(
        None, [plain(t) for t in tokens], [plain(w.text) for w in heard], autojunk=False
    )
    timed: list[Word] = []
    for _tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if i1 == i2:
            continue  # heard words no written word lines up with
        if j1 < j2:  # written words over heard words (matching or not)
            a, b = j1, j2
        elif j1 > 0:  # written words no heard word lines up with: the heard word before them
            a, b = j1 - 1, j1
        else:  # ... or, at the start of the line, the first heard word
            a, b = 0, 1
        timed += _spread(tokens[i1:i2], heard[a:b])
    return timed


def _line(n: int, edited: EditedLine, heard: list[Word]) -> Line:
    own = heard[edited.heard_first : edited.heard_last + 1]
    return Line(
        id=f"L{n:03d}",
        section=edited.section,
        text=edited.text.strip(),
        start_ms=own[0].start_ms,
        end_ms=own[-1].end_ms,
        words=line_words(edited.text, own),
        heard_first=edited.heard_first,
        heard_last=edited.heard_last,
    )


def _sections(edit: LyricsEdit, lines: list[Line]) -> list[Section]:
    found: list[Section] = []
    for section in edit.sections:
        own = [line for line in lines if line.section == section.id]
        if own:
            start, end = own[0].start_ms, own[-1].end_ms
            notes = section.notes.strip()
            found.append(Section(id=section.id, kind=section.kind, start_ms=start, end_ms=end, notes=notes))
    return found


def _breaks(edit: LyricsEdit, lines: list[Line], duration_ms: int) -> list[Instrumental]:
    found: list[Instrumental] = []
    for b in edit.instrumental:
        start = lines[b.after_line - 1].end_ms if b.after_line > 0 else 0
        end = lines[b.after_line].start_ms if b.after_line < len(lines) else duration_ms
        if start < end:
            found.append(Instrumental(start_ms=start, end_ms=end, kind=b.kind, notes=b.notes.strip()))
    return found


def build_timeline(edit: LyricsEdit, words: Words, duration_ms: int, language: str | None) -> Timeline:
    """The timeline of design §4.1, every time taken from the words (`Words.timing`: the aligned words,
    else the heard words) or the song's ends. `edit` must have no `edit_problems`."""
    lines = [_line(n, line, words.timing()) for n, line in enumerate(edit.lines, 1)]
    return Timeline(
        duration_ms=duration_ms,
        language=language or edit.language,
        sections=_sections(edit, lines),
        lines=lines,
        instrumental=_breaks(edit, lines, duration_ms),
    )
