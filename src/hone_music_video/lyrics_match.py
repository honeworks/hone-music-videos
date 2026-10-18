"""Given lyrics lines matched against heard words (D-040), despite Whisper's mishearings: which lines
were heard, and the gaps where the others belong. `second_listen.py` listens to those gaps again;
`check_lyrics` warns when a line still not heard belongs where an instrumental span is marked."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from hone_music_video.records import Timeline, Word
from hone_music_video.timed_lyrics import plain, sung_lines

# A line is found when a run of heard words scores at least this (`score`). Measured on the owner's
# song (43 sung lines, Whisper's mishearings such as Celina->صلینا, اسب->عصف, چاه->شاه):
# the 41 lines the first listen heard score 0.8 or more; the line it missed (the first line of Verse 1,
# under the drum drop) and the last ("آخ" not heard) score 0 (D-040).
FOUND = 0.6
STRETCH = 1.5  # a run of heard words is at most this many times the line's letters (plus one word)
WRITTEN = 2 / 3  # Darvin->دروین, Kaa-ra-van->کاروان, Celina->صلینا: Arabic script leaves short vowels out
LOOK = 3  # a found line's run may begin up to this many words after the first run that matches
# A line must begin within this many heard words after the line before it: on the owner's song a found
# line began at most 3 words after the previous one; a line missed there is not matched to a repeat
# (a chorus) further on, which would drag the alignment past the lines between (D-040).
SEARCH = 40
# A given line with more letters than this is a paragraph, not a sung line: it is not matched (the
# owner's longest line has 46; matching a 600-letter line took seconds, D-040).
LONGEST_LINE = 200
# A listen again whose reply has a longer word invented its times: the longest of the 305 words the
# owner's first listen heard was 3460 ms (a held "کاروان"); the echoed prompts of the real checks had a
# 10 440 ms "am…" and a 9660 ms "am" (D-040).
LONGEST_WORD_MS = 5000
ECHO_LETTERS = 3  # a transliteration this long found in a reply is the prompt echoed back


@dataclass(frozen=True)
class Gap:
    """Given lines not found in the heard words, the time between their found neighbours, and whether
    the song is written in Latin letters (else its Latin words are transliterations)."""

    lines: list[str]
    start_ms: int
    end_ms: int
    latin: bool


@dataclass(frozen=True)
class Key:
    """A line as compared with heard words: its letters and digits without marks, ZWNJ or punctuation,
    and how many letters are unknown."""

    letters: str
    unknown: int


def latin_song(lyrics: str | None) -> bool:
    """The song is written in Latin letters: no sung line has a letter of another script (decided once
    for the song, so an all-Latin line of a song in another script is still transliterations)."""
    return not any(not c.isascii() and c.isalpha() for c in "".join(sung_lines(lyrics)))


def _is_latin(word: str) -> bool:
    return all(c.isascii() for c in word if c.isalpha())


def line_key(text: str, latin: bool) -> Key:
    """In a song not written in Latin letters, the Latin words are transliterations (such as "Noh") that
    Whisper writes in the song's script, with fewer letters: unknown letters, matching any."""
    words = text.split()
    if latin:
        return Key(plain(" ".join(words)), 0)
    known = [w for w in words if not _is_latin(w)]
    unknown = len(plain("".join(w for w in words if _is_latin(w))))
    return Key(plain(" ".join(known)), round(unknown * WRITTEN))


def score(key: Key, run: str) -> float:
    """How well `run` (heard letters) matches the line: difflib's ratio, the unknown letters matching
    letters of the run left over (at most as many as the known letters matched); 0 when fewer than
    `FOUND` of the known letters are in the run."""
    blocks = SequenceMatcher(None, key.letters, run, autojunk=False).get_matching_blocks()
    matched = sum(b.size for b in blocks)
    if matched < FOUND * len(key.letters):
        return 0.0
    guessed = min(key.unknown, len(run) - matched, matched)
    return 2 * (matched + guessed) / (len(key.letters) + key.unknown + len(run))


def _best_run(key: Key, heard: list[str], start: int) -> tuple[float, int]:
    """The best-matching run of heard words beginning at `start`: its score and its last index. A run
    with fewer letters than `FOUND` of the line's known letters cannot reach `FOUND` and is not scored."""
    best, last, joined = 0.0, start, ""
    shortest, longest = FOUND * len(key.letters), (len(key.letters) + key.unknown) * STRETCH
    for end in range(start, len(heard)):
        joined += heard[end]
        if len(joined) > longest + len(heard[end]):
            break
        found = score(key, joined) if len(joined) >= shortest else 0.0
        if found > best:
            best, last = found, end
    return best, last


def find_line(key: Key, heard: list[str], start: int, limit: int | None = None) -> tuple[int, int] | None:
    """The heard words (first, last) a line is sung over: the first run beginning before `limit` (by
    default `SEARCH` words after `start`) that scores at least `FOUND`, or a better one beginning up to
    `LOOK` words later; `None` when no run does."""
    for first in range(start, min(start + SEARCH if limit is None else limit, len(heard))):
        found = _best_run(key, heard, first)
        if found[0] >= FOUND:
            later = range(first + 1, min(first + LOOK + 1, len(heard)))
            runs = [(*found, first)] + [(*_best_run(key, heard, s), s) for s in later]
            _, last, begin = max(runs, key=lambda r: (r[0], -r[2]))
            return begin, last
    return None


def _matched(lines: list[str], words: list[Word], latin: bool) -> list[tuple[str, tuple[int, int] | None]]:
    """Each line that can be matched, in order, with the heard words it is sung over (`None`: missing).
    A line without known letters (all transliterations) or longer than `LONGEST_LINE` letters is left
    out: it cannot be matched, so it is never missing. After `missed` lines in a row not found, the next
    is looked for within `SEARCH * (1 + missed)` words: a long run of words that are no line (Whisper's
    "موسیقی موسیقی…" over two minutes) does not hide every line after it (D-040)."""
    heard, cursor, missed = [plain(w.text) for w in words], 0, 0
    found: list[tuple[str, tuple[int, int] | None]] = []
    for text in lines:
        key = line_key(text, latin)
        if not 0 < len(key.letters) <= LONGEST_LINE:
            continue
        at = find_line(key, heard, cursor, cursor + SEARCH * (1 + missed))
        found.append((text, at))
        cursor, missed = (at[1] + 1, 0) if at else (cursor, missed + 1)
    return found


def gaps(lyrics: str | None, words: list[Word], duration_ms: int) -> list[Gap]:
    """The runs of given sung lines not found in the heard words (in order), each with its gap: from the
    end of the found line before it (or 0) to the start of the found line after it (or the song's end);
    a gap without room (its neighbours touch) is left out."""
    latin = latin_song(lyrics)
    found: list[Gap] = []
    missing: list[str] = []
    gap_start = 0
    for text, at in _matched(sung_lines(lyrics), words, latin):
        if at is None:
            missing.append(text)
            continue
        if missing:
            found.append(Gap(missing, gap_start, words[at[0]].start_ms, latin))
            missing = []
        gap_start = words[at[1]].end_ms
    if missing:
        found.append(Gap(missing, gap_start, duration_ms, latin))
    return [g for g in found if g.start_ms < g.end_ms]


def lines_found(lyrics: str | None, words: list[Word]) -> tuple[int, int]:
    """How many of the given sung lines that can be matched are found in `words`, and how many there
    are (D-047)."""
    matched = _matched(sung_lines(lyrics), words, latin_song(lyrics))
    return sum(at is not None for _, at in matched), len(matched)


def found_spans(lyrics: str | None, words: list[Word]) -> list[tuple[int, int] | None]:
    """For each given sung line, the indexes of the first and last heard words it was found in (`None`:
    not found, or a line that cannot be matched)."""
    matched = iter(_matched(sung_lines(lyrics), words, latin_song(lyrics)))
    found = next(matched, None)
    spans: list[tuple[int, int] | None] = []
    for text in sung_lines(lyrics):
        if found is None or found[0] != text:
            spans.append(None)  # left out by `_matched`: it cannot be matched
            continue
        spans.append(found[1])
        found = next(matched, None)
    return spans


def found_words(lyrics: str | None, words: list[Word]) -> list[int | None]:
    """For each given sung line, the index of the first heard word it was found in (`None`: not found,
    or a line that cannot be matched)."""
    return [None if span is None else span[0] for span in found_spans(lyrics, words)]


def found_starts(lyrics: str | None, words: list[Word]) -> list[int | None]:
    """For each given sung line, the start of the first heard word it was found in (`None`: not found,
    or a line that cannot be matched); the cross-check of aligned lines (D-058)."""
    return [None if n is None else words[n].start_ms for n in found_words(lyrics, words)]


def all_heard(gap: Gap, words: list[Word]) -> bool:
    """Every one of the gap's lines is found in `words`, in order."""
    return all(at is not None for _, at in _matched(gap.lines, words, gap.latin))


def suspect(words: list[Word], gap: Gap, prompt: str) -> str | None:
    """Why a listen again's reply is not taken as heard (D-040), or `None`: a word longer than
    `LONGEST_WORD_MS` (an invented time), or the prompt echoed back: in a song not written in Latin
    letters, the reply has the given lines' own transliterations letter for letter, which Whisper writes
    in the song's script when it hears them (Darvin->دروین), never as given."""
    long = [w for w in words if w.end_ms - w.start_ms > LONGEST_WORD_MS]
    if long:
        word = long[0]
        return f"{word.text!r} lasts {word.end_ms - word.start_ms} ms (at most {LONGEST_WORD_MS} ms)"
    text = " ".join(w.text for w in words)
    given = [] if gap.latin else [plain(w) for w in prompt.split() if _is_latin(w)]
    copied = [t for t in given if len(t) >= ECHO_LETTERS and t in plain(text)]
    if copied:
        return f"the prompt echoed back (its transliteration {copied[0]!r}): {text!r}"
    return None


def in_instrumental(timeline: Timeline, unheard: list[Gap]) -> list[tuple[Gap, int, int]]:
    """Each gap of lines still not heard that overlaps an instrumental span, with that span's start and
    end: the line may be sung there, so the owner checks it by ear (D-040)."""
    return [
        (gap, span.start_ms, span.end_ms)
        for gap in unheard
        for span in timeline.instrumental
        if min(span.end_ms, gap.end_ms) > max(span.start_ms, gap.start_ms)
    ]
