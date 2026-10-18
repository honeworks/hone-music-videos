"""The owner's timing at the lyrics gate (change 0018, D-113 to D-116): a line's start and end set by hand.

Edits are kept by line id in `current/lyrics/owner-timing.json` while `review_lyrics` waits (after it,
as the decided gate's record, never applied again) and applied to whatever the lyrics stage made last: a
line's words move with it (scaled within it), a section holding an edited line spans its lines again,
an instrumental span next to one fills the new gap. A save checks every edit and refuses all of them on
any problem; after the lyrics run again, an edit whose line is gone or would now overlap a neighbour is
dropped and said so. Each saved timeline is a kept version (`timeline-<sha256[:12]>.json`, D-009);
approving decides the gate with it (`runs.approve`)."""

from __future__ import annotations

import hashlib
import itertools
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

import hone_flow as fk
from pydantic import BaseModel

from hone_music_video._files import now, read_json, write_bytes, write_json
from hone_music_video.errors import InvalidInput
from hone_music_video.lyrics_check import check_lyrics
from hone_music_video.project import Project
from hone_music_video.records import (
    STRICT,
    Instrumental,
    Line,
    Ms,
    Report,
    Section,
    Timeline,
    Version,
    Word,
    Words,
)
from hone_music_video.records_timeline import clock
from hone_music_video.workflow import ITEM

FOLDER = "lyrics"  # under current/
SPEC = re.compile(r"^(?P<line>[^=\s]+)=(?:(?P<start>\d+)-(?P<end>\d+)|(?P<off>-))$")


class LineTimes(BaseModel):
    """A line's start and end as the owner set them."""

    model_config = STRICT
    start_ms: Ms
    end_ms: Ms


class OwnerTiming(BaseModel):
    """`current/lyrics/owner-timing.json`: the owner's edits by line id, when they were saved, and the
    kept version of the timeline they made (project-relative)."""

    model_config = STRICT
    format_version: Version = "1"

    edits: dict[str, LineTimes]
    saved_at: str
    timeline: str
    decided: bool = False  # the gate was decided: kept as its record, never applied again


Edits = Mapping[str, LineTimes]
Changes = Mapping[str, LineTimes | None]  # None takes a line's edit back


@dataclass(frozen=True)
class Reviewed:
    """The timeline under review with the owner's edits applied, its check, and the edits kept and
    dropped (line id: why)."""

    timeline: Timeline
    report: Report
    kept: list[str] = field(default_factory=list[str])
    dropped: dict[str, str] = field(default_factory=dict[str, str])
    measured: dict[str, list[int]] = field(default_factory=dict[str, list[int]])  # kept lines, as made

    def summary(self) -> dict[str, Any]:
        """What the dashboard shows of it: the edits kept and dropped, their lines' measured times and
        the check's counts."""
        return {
            "kept": self.kept,
            "dropped": self.dropped,
            "measured": self.measured,
            "errors": len(self.report.errors),
            "warnings": len(self.report.warnings),
        }


# ------------------------------------------------------------------------------ applying edits


def _scaled(line: Line, times: LineTimes) -> Line:
    """The line at the owner's times, its words moved and scaled within it (`times` has length)."""
    old, new = line.end_ms - line.start_ms, times.end_ms - times.start_ms

    def at(ms: int) -> int:
        return times.start_ms + (round((ms - line.start_ms) * new / old) if old > 0 else 0)

    words: list[Word] = []
    for w in line.words:
        start = min(max(at(w.start_ms), times.start_ms), times.end_ms - 1)
        end = min(max(at(w.end_ms), start + 1), times.end_ms)
        words.append(Word(text=w.text, start_ms=start, end_ms=end))
    return line.model_copy(update={"start_ms": times.start_ms, "end_ms": times.end_ms, "words": words})


def _sections(base: Timeline, lines: list[Line], edits: Edits) -> list[Section]:
    """Each section holding an edited line spans its lines again; the others stay as made."""
    found: list[Section] = []
    for section in base.sections:
        own = [ln for ln in lines if ln.section == section.id]
        moved = any(ln.id in edits for ln in own)
        span = {"start_ms": own[0].start_ms, "end_ms": own[-1].end_ms} if moved else {}
        found.append(section.model_copy(update=span))
    return found


def _spans(base: Timeline, lines: list[Line], edits: Edits) -> list[Instrumental]:
    """Each instrumental span next to an edited line fills the new gap; one left with none is left out."""
    found: list[Instrumental] = []
    for span in base.instrumental:
        after = sum(ln.end_ms <= span.start_ms for ln in base.lines)  # the lines before it, as made
        before = lines[after - 1] if after else None
        later = lines[after] if after < len(lines) else None
        start = before.end_ms if before and before.id in edits else span.start_ms
        end = later.start_ms if later and later.id in edits else span.end_ms
        if start < end:
            found.append(span.model_copy(update={"start_ms": start, "end_ms": end}))
    return found


def _timed(base: Timeline, edits: Edits) -> Timeline:
    """`base` with the edits applied (each to an existing line, with length), its sections and
    instrumental spans adjusted, the edited lines marked as the owner's."""
    lines = [_scaled(ln, edits[ln.id]) if ln.id in edits else ln for ln in base.lines]
    update = {
        "lines": lines,
        "sections": _sections(base, lines, edits),
        "instrumental": _spans(base, lines, edits),
        "owner_timed": sorted({*base.owner_timed, *edits}),
    }
    return base.model_copy(update=update)


def _own_problems(base: Timeline, edits: Edits) -> dict[str, str]:
    """Each edit that cannot apply on its own: an unknown line, no length, outside the song."""
    ids = {ln.id for ln in base.lines}
    found: dict[str, str] = {}
    for line, t in edits.items():
        if line not in ids:
            found[line] = f"{line}: there is no line {line} now"
        elif t.start_ms >= t.end_ms:
            found[line] = f"{line}: starts at {clock(t.start_ms)}, not before its end {clock(t.end_ms)}"
        elif t.end_ms > base.duration_ms:
            found[line] = (
                f"{line}: ends at {clock(t.end_ms)}, after the song ends ({clock(base.duration_ms)})"
            )
    return found


def _order_problems(timeline: Timeline, edited: set[str]) -> list[tuple[set[str], str]]:
    """Neighbours that overlap where one of them was edited: the edited ids and what is wrong."""
    return [
        ({a.id, b.id} & edited, f"{b.id} starts {a.end_ms - b.start_ms} ms before {a.id} ends")
        for a, b in itertools.pairwise(timeline.lines)
        if b.start_ms < a.end_ms and {a.id, b.id} & edited
    ]


def _attempt(base: Timeline, edits: Edits) -> tuple[Timeline, dict[str, str]]:
    """`base` with the edits that apply on their own, and every problem by line id: an edit that cannot
    apply on its own, or an overlap with a neighbour (the one rule set of saving and dropping)."""
    problems = _own_problems(base, edits)
    timeline = _timed(base, {line: t for line, t in edits.items() if line not in problems})
    for ids, why in _order_problems(timeline, set(edits) - set(problems)):
        problems |= dict.fromkeys(ids, why)
    return timeline, problems


def apply_timing(base: Timeline, edits: Edits) -> tuple[Timeline, list[str], dict[str, str]]:
    """`base` with every edit that still fits: the timeline, the edits kept and those dropped with why
    (a line gone, no length, outside the song, an overlap with a neighbour)."""
    kept, dropped = dict(edits), dict[str, str]()
    while True:
        timeline, problems = _attempt(base, kept)
        if not problems:
            return timeline, sorted(kept), dropped
        dropped |= problems  # each names an edited line, so this ends
        kept = {line: t for line, t in kept.items() if line not in problems}


# ------------------------------------------------------------------------------ the project's edits


def read_timing(project: Project) -> OwnerTiming | None:
    """The owner's saved edits while the lyrics gate waits; None once it was decided (D-118)."""
    path = project.current / FOLDER / "owner-timing.json"
    found = read_json(path, OwnerTiming) if path.is_file() else None
    return found if found and not found.decided else None


def decided(project: Project) -> None:
    """Mark the saved edits as the record of the decided gate, so they are never applied again."""
    found = read_timing(project)
    if found is not None:
        write_json(project.current / FOLDER / "owner-timing.json", found.model_copy(update={"decided": True}))


def _reviewed(project: Project, run: fk.Run, base: Timeline, edits: Edits) -> Reviewed:
    timeline, kept, dropped = apply_timing(base, edits)
    measured = {ln.id: [ln.start_ms, ln.end_ms] for ln in base.lines if ln.id in kept}
    return Reviewed(timeline, checked(project, run, timeline), kept, dropped, measured)


def held(project: Project) -> list[str]:
    """The lines the owner has timed, for the note of a rerun at the waiting gate."""
    found = read_timing(project)
    return sorted(found.edits) if found else []


def checked(project: Project, run: fk.Run, timeline: Timeline) -> Report:
    """`check_lyrics` on a timeline of this run (the edited one), with the run's words and the lyrics."""
    words: Words = run.output("transcribe", ITEM)
    return check_lyrics(timeline, words, project.record().inputs.lyrics)


def under_review(project: Project, run: fk.Run) -> Reviewed | None:
    """The lyrics stage's last timeline with the owner's saved edits applied and checked again; None
    when the owner has saved none."""
    found = read_timing(project)
    if found is None:
        return None
    return _reviewed(project, run, run.output("lyrics", ITEM), found.edits)


def save(project: Project, run: fk.Run, changes: Changes) -> Reviewed:
    """Save the owner's changes on top of the edits that still fit; refused whole (`InvalidInput`, every
    problem named) when one does not. The timeline is kept as a version and checked again."""
    base: Timeline = run.output("lyrics", ITEM)
    stored = read_timing(project)
    _, still, dropped = apply_timing(base, stored.edits if stored else {})
    edits = {line: stored.edits[line] for line in still} if stored else {}
    for line, times in changes.items():
        if times is None:
            edits.pop(line, None)
        else:
            edits[line] = times
    timeline, problems = _attempt(base, edits)
    messages = list(dict.fromkeys(problems.values()))  # an overlap names two lines, said once
    if messages:
        raise InvalidInput("the timing cannot be saved: " + "; ".join(messages), messages)
    _keep(project, timeline, edits)
    saved = _reviewed(project, run, base, edits)
    return replace(saved, dropped={k: v for k, v in dropped.items() if k not in edits})


def _keep(project: Project, timeline: Timeline, edits: dict[str, LineTimes]) -> None:
    """The timeline as a version, never overwritten (D-009), and the edits that made it."""
    folder = project.current / FOLDER
    data = timeline.model_dump_json(indent=2).encode()
    version = folder / f"timeline-{hashlib.sha256(data).hexdigest()[:12]}.json"
    if not version.is_file():
        write_bytes(version, data)
    record = OwnerTiming(edits=edits, saved_at=now(), timeline=project.relative(version))
    write_json(folder / "owner-timing.json", record)


def rerun_note(project: Project, note: str) -> str:
    """The owner's note for the lyrics editor, told which lines the owner timed by hand (D-116)."""
    lines = held(project)
    if not lines:
        return note
    return (
        f"{note}\n\n(The owner set the times of {', '.join(lines)} by hand; they are kept where these "
        "line ids remain. Change the text only: keep every line, its order and its heard words.)"
    )


def parse_changes(data: Any) -> Changes:
    """`{line_id: {start_ms, end_ms} | null}` as the dashboard sends it; `InvalidInput` names each bad one."""
    if not isinstance(data, dict) or not data:
        raise InvalidInput("send the timing as {line id: {start_ms, end_ms}}", ["timing: an object"])
    found: dict[str, LineTimes | None] = {}
    problems: list[str] = []
    for line, value in data.items():  # pyright: ignore[reportUnknownVariableType]
        try:
            found[str(line)] = None if value is None else LineTimes.model_validate(value)  # pyright: ignore[reportUnknownArgumentType]
        except ValueError:
            problems.append(f"{line}: give start_ms and end_ms as whole milliseconds from 0")
    if problems:
        raise InvalidInput("the timing cannot be saved: " + "; ".join(problems), problems)
    return found


def parse_spec(texts: list[str]) -> dict[str, dict[str, int] | None]:
    """`L012=77300-81200` (start and end in ms) or `L012=-` (take the edit back), as the CLI takes them,
    in the shape the API and `hmv.lyrics_timing` take (`parse_changes` checks them there)."""
    found: dict[str, dict[str, int] | None] = {}
    for text in texts:
        match = SPEC.match(text)
        if match is None:
            raise InvalidInput(
                f"{text!r}: write LINE=START-END in milliseconds (L012=77300-81200), or LINE=-"
            )
        start, end = match["start"], match["end"]
        found[match["line"]] = None if match["off"] else {"start_ms": int(start), "end_ms": int(end)}
    return found
