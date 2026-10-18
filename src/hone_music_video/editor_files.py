"""The edit for editors (design §12.1, D-063): `edl.json` as Final Cut Pro 7 XML (`current/edit.xml`) and
a CMX3600 EDL (`current/edit.edl`), which DaVinci Resolve and Premiere Pro import.

Video track 1 has every finished clip at its frames of the edit list, named by its shot; audio track 1
has the song from frame 0. Frames are the video's (`Assembly.fps`); the files are linked by their
absolute paths on this machine. A clip shorter than its shot ends where the clip does: the frames the
video holds (`held_frames`) are a gap in the editor's timeline."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from hone_music_video._files import read_json, write_bytes
from hone_music_video._video import Clip, probe
from hone_music_video.errors import InvalidInput, RunStateError
from hone_music_video.project import Project
from hone_music_video.records import Assembly, Cut, Song
from hone_music_video.stages_plan import measure

XML, EDL = "edit.xml", "edit.edl"


@dataclass(frozen=True)
class Event:
    """One clip on a track: from `start` to `end` (excluded) in the timeline, its frames from the file's
    first; the file has `frames` frames."""

    name: str
    file: Path
    start: int
    end: int
    frames: int


@dataclass(frozen=True)
class Edit:
    """The video's edit: its name, frame rate and size, the shots, the song and what ffprobe found in it."""

    name: str
    fps: int
    size: tuple[int, int]
    shots: list[Event]
    song: Event
    audio: Song


def _sub(parent: ET.Element, tag: str, text: object = None, **attrs: str) -> ET.Element:
    element = ET.SubElement(parent, tag, attrs)
    if text is not None:
        element.text = str(text)
    return element


def _rate(parent: ET.Element, fps: int) -> None:
    rate = _sub(parent, "rate")
    _sub(rate, "timebase", fps)
    _sub(rate, "ntsc", "FALSE")


def file_url(path: Path) -> str:
    """`file://localhost/...`, the form Premiere and Resolve write in FCP7 XML, the path percent-encoded."""
    return "file://localhost" + quote(str(path.resolve()))


def _samples(parent: ET.Element, **values: object) -> ET.Element:
    found = _sub(parent, "samplecharacteristics")
    for tag, value in values.items():
        _sub(found, tag, value)
    return found


def _clipitem(track: ET.Element, event: Event, fps: int, media: ET.Element) -> ET.Element:
    item = _sub(track, "clipitem", id=f"clipitem-{event.name}")
    _sub(item, "name", event.name)
    _sub(item, "enabled", "TRUE")
    _sub(item, "duration", event.frames)
    _rate(item, fps)
    for tag, value in (
        ("start", event.start),
        ("end", event.end),
        ("in", 0),
        ("out", event.end - event.start),
    ):
        _sub(item, tag, value)
    file = _sub(item, "file", id=f"file-{event.name}")
    _sub(file, "name", event.file.name)
    _sub(file, "pathurl", file_url(event.file))
    _rate(file, fps)
    _sub(file, "duration", event.frames)
    file.append(media)
    return item


def _video(media: ET.Element, edit: Edit) -> None:
    video, (width, height) = _sub(media, "video"), edit.size
    _rate(_samples(_sub(video, "format"), width=width, height=height, pixelaspectratio="square"), edit.fps)
    track = _sub(video, "track")
    for event in edit.shots:
        clip_media = ET.Element("media")
        _samples(_sub(clip_media, "video"), width=width, height=height)
        _clipitem(track, event, edit.fps, clip_media)


def _audio(media: ET.Element, edit: Edit) -> None:
    song_media = ET.Element("media")
    song_audio = _sub(song_media, "audio")
    _samples(song_audio, depth=16, samplerate=edit.audio.sample_rate)
    _sub(song_audio, "channelcount", edit.audio.channels)
    audio = _sub(media, "audio")
    _samples(_sub(audio, "format"), depth=16, samplerate=edit.audio.sample_rate)
    source = _sub(_clipitem(_sub(audio, "track"), edit.song, edit.fps, song_media), "sourcetrack")
    _sub(source, "mediatype", "audio")
    _sub(source, "trackindex", 1)


def fcp7_xml(edit: Edit) -> bytes:
    """The edit as `xmeml` version 4: one sequence, video track 1 the shots, audio track 1 the song."""
    root = ET.Element("xmeml", version="4")
    sequence = _sub(root, "sequence", id="sequence-1")
    _sub(sequence, "name", edit.name)
    _sub(sequence, "duration", max(e.end for e in [*edit.shots, edit.song]))
    _rate(sequence, edit.fps)
    timecode = _sub(sequence, "timecode")
    _rate(timecode, edit.fps)
    for tag, value in (("string", "00:00:00:00"), ("frame", 0), ("displayformat", "NDF")):
        _sub(timecode, tag, value)
    media = _sub(sequence, "media")
    _video(media, edit)
    _audio(media, edit)
    ET.indent(root)
    return b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n' + ET.tostring(root, encoding="utf-8")


def timecode(frame: int, fps: int) -> str:
    """`hh:mm:ss:ff` at `fps` frames a second (non-drop)."""
    seconds, frames = divmod(frame, fps)
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}:{frames:02d}"


def cmx3600(edit: Edit) -> bytes:
    """The edit as a CMX3600 EDL: one cut per shot (its reel the shot id), then the song."""
    fps, stereo = edit.fps, edit.audio.channels > 1
    lines = [f"TITLE: {edit.name}", "FCM: NON-DROP FRAME", ""]
    rows = [(e, e.name[:8], "V") for e in edit.shots] + [(edit.song, "SONG", "AA" if stereo else "A")]
    for number, (event, reel, track) in enumerate(rows, 1):
        source = f"{timecode(0, fps)} {timecode(event.end - event.start, fps)}"
        record = f"{timecode(event.start, fps)} {timecode(event.end, fps)}"
        lines += [f"{number:03d}  {reel:<8} {track:<5} C        {source} {record}"]
        lines += [f"* FROM CLIP NAME: {event.file.name}", f"* SOURCE FILE: {event.file.resolve()}", ""]
    return "\n".join(lines).encode()


def edit_of(project: Project, assembly: Assembly, clips: Mapping[str, Clip], audio: Song) -> Edit:
    """The edit list's cuts as events (a shot under half a frame has none), with each shot's clip as
    measured (`clips`, by shot) and the song as long as it is."""
    if not assembly.edl:
        raise RunStateError(f"{project.id}'s edit list has no shots: there is nothing to export")
    fps = assembly.fps
    shots = [
        Event(c.shot, project.path(c.clip), c.first_frame, c.first_frame + used, clips[c.shot].frames)
        for c in assembly.edl
        if (used := min(c.last_frame - c.first_frame + 1, clips[c.shot].frames)) > 0
    ]
    frames = (audio.duration_ms * fps + 500) // 1000
    song = Event("song", project.path(project.record().inputs.song), 0, frames, frames)
    width, height = (int(n) for n in clips[assembly.edl[0].shot].size.split("x"))
    return Edit(project.record().name, fps, (width, height), shots, song, audio)


def write(project: Project, assembly: Assembly, clips: Mapping[str, Clip], audio: Song) -> list[Path]:
    """`current/edit.xml` and `current/edit.edl` from the edit list; returns their paths."""
    edit = edit_of(project, assembly, clips, audio)
    xml, edl = project.current / XML, project.current / EDL
    write_bytes(xml, fcp7_xml(edit))
    write_bytes(edl, cmx3600(edit))
    return [xml, edl]


def _measured(project: Project, cut: Cut) -> Clip:
    path = project.path(cut.clip)
    if not path.is_file():
        raise InvalidInput(f"{cut.shot}'s finished clip {cut.clip} is missing; assemble the video again")
    return probe(path)


def export(project: Project) -> list[Path]:
    """The editor files of the video assembled last (`current/edl.json`), written again: for a video
    assembled before they existed (D-064). Measures the clips and the song; no model call, no run."""
    edl = project.current / "edl.json"
    if not edl.is_file():
        raise RunStateError(f"{project.id} has no assembled video yet; its edit list comes with the video")
    assembly = read_json(edl, Assembly)
    clips = {c.shot: _measured(project, c) for c in assembly.edl}
    return write(project, assembly, clips, measure(project.path(project.record().inputs.song)))
