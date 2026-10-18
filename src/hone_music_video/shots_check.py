"""`check_shots` (design §5.2): the shot plan checked against the timed lyrics, the cast and the settings.

Each finding names the shot (`where`), the rule and what is wrong, by how much in milliseconds where a
time is involved, so a repair call can act on it (§7.4). Errors go back to the planner and keep the shot
gate from being approved; warnings are shown."""

from __future__ import annotations

import itertools
import re

from hone_music_video.pace import pace_warnings
from hone_music_video.prompt_words import words_of_speech
from hone_music_video.records import Problem, Report, Shot, Shots, Timeline
from hone_music_video.records_timeline import clock
from hone_music_video.settings import Settings

FACES = ("medium", "close-up", "extreme-close-up")  # framings where a face can be recognised (§8.3)
NEAR_MS = 120  # a cut further than this from the song's edges (`_far_cuts`) is a warning
# What the text encoders read: about 512 tokens for Z-Image's Qwen3 and Wan's umT5, ~3 characters a token
# at worst, with room for the placeholders to grow ("the woman from images 1 and 2"; D-026).
STILL_PROMPT_CHARS = 1500
MOTION_PROMPT_CHARS = 1000
SHOT_ID = re.compile(r"^S\d{3,}$")
# Errors that do not break the video: the owner may approve the shot list with them (D-027). The others
# (tiling, cuts inside words, cast, placeholders, ids, empty prompts) block the gate.
ACCEPTABLE = frozenset(
    {
        "length",
        "prompt-length",
        "faces",
        "word-longer-than-max-shot",
        "unknown-line",
        "line-outside",
        "line-unlisted",
    }
)


def _p(rule: str, where: str, message: str) -> Problem:
    return Problem(rule=rule, where=where, message=message, acceptable=rule in ACCEPTABLE)


def _span(start: int, end: int) -> str:
    return f"{clock(start)}-{clock(end)}"


# ------------------------------------------------------------------------------ errors


def _tiling(shots: list[Shot], duration: int) -> list[Problem]:
    """The shots in order, from 0 to the song's end, each starting where the one before ends."""
    if not shots:
        return [_p("song-end", "plan", f"has no shots; the song is {clock(duration)} long")]
    found: list[Problem] = []
    first, last = shots[0], shots[-1]
    if first.start_ms != 0:
        late = f"starts at {clock(first.start_ms)}, not at {clock(0)} ({first.start_ms} ms late)"
        found.append(_p("song-start", first.id, late))
    for before, shot in itertools.pairwise(shots):
        off, ends = shot.start_ms - before.end_ms, f"{before.id} ends ({clock(before.end_ms)})"
        if off > 0:
            found.append(_p("gap", shot.id, f"starts {off} ms after {ends}: a gap"))
        elif off < 0:
            found.append(_p("overlap", shot.id, f"starts {-off} ms before {ends}: an overlap"))
    if last.end_ms != duration:
        side = "before" if last.end_ms < duration else "after"
        off = f"{abs(duration - last.end_ms)} ms {side} the song ends ({clock(duration)})"
        found.append(_p("song-end", last.id, f"ends at {clock(last.end_ms)}, {off}"))
    return found


def _length(shot: Shot, settings: Settings) -> list[Problem]:
    lasts, low, high = shot.end_ms - shot.start_ms, settings.min_shot_ms, settings.max_shot_ms
    if lasts < low:
        short = f"{low - lasts} ms shorter than the shortest shot ({low} ms)"
        return [_p("length", shot.id, f"lasts {lasts} ms, {short}")]
    if lasts > high:
        long = f"{lasts - high} ms longer than the longest shot ({high} ms)"
        return [_p("length", shot.id, f"lasts {lasts} ms, {long}")]
    return []


def _in_word(shot: Shot, timeline: Timeline) -> list[Problem]:
    """A cut (the shot's start) strictly inside a sung word."""
    cut = shot.start_ms
    for line in timeline.lines:
        for word in (w for w in line.words if w.start_ms < cut < w.end_ms):
            inside = (
                f"starts at {clock(cut)}, inside the sung word {word.text!r} of {line.id} "
                f"({_span(word.start_ms, word.end_ms)}), {cut - word.start_ms} ms after it starts and "
                f"{word.end_ms - cut} ms before it ends"
            )
            return [_p("cut-in-word", shot.id, inside)]
    return []


def _listed(shot: Shot, timeline: Timeline) -> list[Problem]:
    """Every line a shot lists exists and is sung during the shot."""
    lines = {ln.id: ln for ln in timeline.lines}
    found: list[Problem] = []
    for line_id in shot.lines:
        line = lines.get(line_id)
        if line is None:
            found.append(_p("unknown-line", shot.id, f"lists {line_id}, which is not a line of the timeline"))
            continue
        lists = f"lists {line.id} ({_span(line.start_ms, line.end_ms)})"
        if line.start_ms >= shot.end_ms:
            why = f"which is sung {line.start_ms - shot.end_ms} ms after the shot ends"
            found.append(_p("line-outside", shot.id, f"{lists}, {why}"))
        elif line.end_ms <= shot.start_ms:
            why = f"which ends {shot.start_ms - line.end_ms} ms before the shot starts"
            found.append(_p("line-outside", shot.id, f"{lists}, {why}"))
    return found


def _unlisted(shots: list[Shot], timeline: Timeline) -> list[Problem]:
    """Every line is listed by at least one shot; one that is not is reported at a shot it is sung in."""
    listed = {line_id for shot in shots for line_id in shot.lines}
    found: list[Problem] = []
    for line in (ln for ln in timeline.lines if ln.id not in listed):
        during = next((s.id for s in shots if s.start_ms < line.end_ms and s.end_ms > line.start_ms), None)
        sung = f"{line.id} ({_span(line.start_ms, line.end_ms)}) is sung"
        message = f"{sung} during {during} but no shot lists it" if during else f"{sung} but no shot lists it"
        found.append(_p("line-unlisted", during or line.id, message))
    return found


def _cast(shot: Shot, cast: list[str]) -> list[Problem]:
    """The shot's cast are characters of the plan."""
    who = ", ".join(cast) or "nobody"
    return [_p("unknown-cast", shot.id, f"names {c}, who is not a character ({who})")
            for c in shot.cast if c not in cast]  # fmt: skip


def _faces_and_prompts(shot: Shot) -> list[Problem]:
    found: list[Problem] = []
    if shot.faces and shot.framing not in FACES:
        why = (
            f"faces is true on a {shot.framing} shot; "
            "a recognisable face needs a medium shot, close-up or extreme close-up"
        )
        found.append(_p("faces", shot.id, why))
    for kind, text, limit in (
        ("still", shot.still_prompt, STILL_PROMPT_CHARS),
        ("motion", shot.motion_prompt, MOTION_PROMPT_CHARS),
    ):
        if not text.strip():
            found.append(_p("empty-prompt", shot.id, f"the {kind} prompt is empty"))
        elif len(text) > limit:
            over = f"{len(text)} characters, {len(text) - limit} over the limit of {limit}"
            found.append(_p("prompt-length", shot.id, f"the {kind} prompt has {over}"))
    return found


def _ids(shots: list[Shot]) -> list[Problem]:
    """Every shot id is `S` and three or more digits, and used once."""
    counts = {i: sum(s.id == i for s in shots) for i in dict.fromkeys(s.id for s in shots)}
    found = [_p("shot-id", i, f"the id {i} is used by {n} shots") for i, n in counts.items() if n > 1]
    return found + [
        _p("shot-id", i, f"the id {i} is not S followed by three or more digits (S001)")
        for i in counts
        if not SHOT_ID.match(i)
    ]


def _long_words(shots: list[Shot], timeline: Timeline, settings: Settings) -> list[Problem]:
    """A sung word longer than the longest shot: no plan can tile the song without breaking a rule."""
    found: list[Problem] = []
    high = settings.max_shot_ms
    for line in timeline.lines:
        for word in (w for w in line.words if w.end_ms - w.start_ms > high):
            where = next((s.id for s in shots if s.start_ms <= word.start_ms < s.end_ms), line.id)
            why = (
                f"the sung word {word.text!r} of {line.id} ({_span(word.start_ms, word.end_ms)}) lasts "
                f"{word.end_ms - word.start_ms} ms, longer than the longest shot ({high} ms): the shot "
                "around it must break the limit, because the song or the max_shot_ms setting makes it "
                "impossible to keep"
            )
            found.append(_p("word-longer-than-max-shot", where, why))
    return found


# ------------------------------------------------------------------------------ warnings


def _far_cuts(shots: list[Shot], timeline: Timeline) -> list[Problem]:
    anchors = [t for ln in timeline.lines for t in (ln.start_ms, ln.end_ms)]
    anchors += [s.start_ms for s in timeline.sections] + [0, timeline.duration_ms]
    anchors += [t for span in timeline.instrumental for t in (span.start_ms, span.end_ms)]
    found: list[Problem] = []
    for shot in shots[1:]:
        nearest = min(anchors, key=lambda t: abs(t - shot.start_ms), default=None)
        if nearest is not None and abs(nearest - shot.start_ms) > NEAR_MS:
            far = (
                f"the cut at {clock(shot.start_ms)} is {abs(nearest - shot.start_ms)} ms from the "
                "nearest line start or end, section start, instrumental edge or end of the song "
                f"({clock(nearest)}); "
                f"at most {NEAR_MS} ms is preferred"
            )
            found.append(_p("far-cut", shot.id, far))
    return found


def _faceless(shots: list[Shot]) -> list[Problem]:
    why = "faces is true but the shot has no cast: nobody's reference pictures keep that face the same"
    return [_p("faces-without-cast", s.id, why) for s in shots if s.faces and not s.cast]


def _speech(shot: Shot) -> list[Problem]:
    """A still prompt with a word of speech, a motion prompt with one or a word of the mouth: no one
    speaks or sings on screen, and naming the mouth makes the video model move it (§8.3, D-078, D-088)."""
    found: list[Problem] = []
    for kind, text in (("still", shot.still_prompt), ("motion", shot.motion_prompt)):
        words = words_of_speech(text, motion=kind == "motion")
        if words:
            said = ", ".join(repr(w) for w in words)
            why = f"the {kind} prompt has {said}: no one speaks or sings (no lip sync); show it in the face"
            if kind == "motion":
                why += " through what moves (eyes, tears, a turn of the head) and say the face stays still"
            found.append(_p("speech", shot.id, why))
    return found


BODY_SIDE = re.compile(
    r"\b(?:left|right)\s+(?:hand|arm|leg|foot|eye|ear|shoulder|knee|wrist|cheek|hip|wing|paw|hoof|fist|palm"
    r"|finger|thumb|elbow|brow|eyebrow)s?\b",
    re.IGNORECASE,
)
MANY = re.compile(
    r"\b(?:four|five|six|seven|eight|nine|ten|eleven|twelve|dozen|[4-9]|[1-9]\d+)\s+[a-z]+", re.IGNORECASE
)
CLOSE = ("close-up", "extreme-close-up", "insert")


def model_limits(where: str, beat: str, framing: str) -> list[Problem]:
    """`model-limit`: what a beat asks that no prompt makes the still models draw (0029 §2): a body's own
    side outside a close shot, more than three of a kind to be counted."""
    found: list[Problem] = []
    side = BODY_SIDE.search(beat)
    if side and framing not in CLOSE:
        why = (f"the beat names {side.group()!r} in a {framing} shot: the models can't draw a body's own "
               "side; make it a close-up of that one part, or leave the side out")  # fmt: skip
        found.append(_p("model-limit", where, why))
    many = MANY.search(beat)
    if many:
        why = (f"the beat counts {many.group()!r}: more than three of a kind are seldom drawn exactly; "
               "show three or fewer, or a number that doesn't matter")  # fmt: skip
        found.append(_p("model-limit", where, why))
    return found


def _same_framing(shots: list[Shot]) -> list[Problem]:
    found: list[Problem] = []
    for framing, run in itertools.groupby(shots, key=lambda s: s.framing):
        row = list(run)
        if len(row) >= 3:
            same = f"{row[0].id} to {row[-1].id} are all {framing} shots ({len(row)} in a row)"
            found.append(_p("same-framing", row[0].id, same))
    return found


def _missing(shots: list[Shot], character: str, duration: int) -> list[Problem]:
    """The longest stretch after a character's first shot without them, when over a third of the song."""
    seen = [s for s in shots if character in s.cast]
    if not seen:
        return []
    gaps = [(a.end_ms, b.start_ms) for a, b in itertools.pairwise(seen)] + [(seen[-1].end_ms, duration)]
    start, end = max(gaps, key=lambda gap: gap[1] - gap[0])
    if (end - start) * 3 <= duration:
        return []
    where = next((s.id for s in shots if s.start_ms >= start), seen[-1].id)
    gone = (
        f"{character} is not seen from {clock(start)} to {clock(end)} "
        f"({end - start} ms, more than a third of the song)"
    )
    return [_p("character-missing", where, gone)]


def check_shots(shots: Shots, timeline: Timeline, cast: list[str], settings: Settings) -> Report:
    """The checks of design §5.2. Errors: the shots tile the song exactly, each within the shot limits, no
    cut inside a sung word, ids `S001`.. used once, lines and shots overlap both ways, the cast exists
    (`cast`: the characters' ids), faces only from a medium shot or closer, prompts written and within
    their model's length, no sung word longer than the longest shot; the `acceptable` ones may be
    approved (D-027). Warnings: cuts far from the song's edges, the same framing three times in a row, a
    character missing for a third of the song, a recognisable face without a cast, a word of speech in a
    prompt, a word of the mouth in a motion prompt (D-088), a shot outside the pace's length (D-084), a
    beat that asks what the still models can't draw (0029)."""
    plan, duration = shots.shots, timeline.duration_ms
    errors = _tiling(plan, duration) + _ids(plan)
    for shot in plan:
        errors += _length(shot, settings) + _listed(shot, timeline)
        errors += _cast(shot, cast) + _faces_and_prompts(shot)
        errors += _in_word(shot, timeline) if 0 < shot.start_ms < duration else []
    errors += _unlisted(plan, timeline) + _long_words(plan, timeline, settings)
    warnings = _far_cuts(plan, timeline) + _same_framing(plan) + _faceless(plan)
    warnings += [p for shot in plan for p in _speech(shot)]
    warnings += [p for shot in plan for p in model_limits(shot.id, shot.beat, shot.framing)]
    warnings += pace_warnings(plan, settings)
    for character in cast:
        warnings += _missing(plan, character, duration)
    return Report(errors=errors, warnings=warnings)
