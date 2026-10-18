"""Which project files the dashboard serves, with which content type, and HTTP byte ranges for seeking.

It serves a project's `current/` folder (pictures, clips, the video, the records beside them), the song,
the given pictures in `input/` (D-013), and the frame workspace's pictures: every version, its thumbnail
(made once, on first use, as Hone Frame's server makes it) and the given files (0027); never
`project.json`, the run folder or anything outside the projects folder."""

from __future__ import annotations

import re
from http import HTTPStatus
from io import BufferedIOBase
from pathlib import Path

from hone_music_video.frame._http import thumbnail
from hone_music_video.project import SONG_TYPES

THUMB_PX = 384  # Hone Frame: `dashboard.THUMB_PX`

PICTURES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
# the edit for editors too (design §12.1): FCP7 XML and a CMX3600 EDL
EDITS = {".xml": "application/xml", ".edl": "text/plain; charset=utf-8"}
CURRENT = PICTURES | EDITS | {".mp4": "video/mp4", ".json": "application/json"}
RANGE = re.compile(r"bytes=(\d*)-(\d*)")
CHUNK = 1 << 20  # a video is sent a megabyte at a time, never read into memory at once
FILE_HEADERS = {
    "Accept-Ranges": "bytes",
    "Content-Security-Policy": "default-src 'none'; sandbox",
    "Cache-Control": "no-cache",
    "X-Content-Type-Options": "nosniff",
}


def servable(projects: Path, relative: str) -> tuple[Path, str] | None:
    """The file at `<projects>/<relative>` and its content type, if the dashboard may serve it."""
    root = projects.resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return None
    where, suffix = target.relative_to(root).parts[1:], target.suffix.lower()
    match where:
        case ["current", _, *_] if suffix in CURRENT:
            return target, CURRENT[suffix]
        case ["input", name] if name.startswith("song.") and suffix in SONG_TYPES:
            return target, SONG_TYPES[suffix]
        case ["input", "sheets" | "poses", _] | [
            "frame",
            "projects",
            _,
            "items" | "assets" | "thumbs",
            *_,
        ] if suffix in PICTURES:
            return target, PICTURES[suffix]
        case _:
            return None


def frame_thumbnail(projects: Path, relative: str) -> None:
    """Make a frame version's thumbnail when it is asked for and missing (Hone Frame's `_http.thumbnail`,
    384 px WebP, made once): `<project>/frame/projects/<id>/thumbs/<item>/vNNN.webp`."""
    root = projects.resolve()
    target = (root / relative).resolve()
    parts = target.relative_to(root).parts if target.is_relative_to(root) else ()
    if (
        len(parts) != 7
        or parts[1:3] != ("frame", "projects")
        or parts[4] != "thumbs"
        or target.suffix != ".webp"
    ):
        return
    source = target.parents[2] / "items" / parts[5] / target.with_suffix(".png").name
    if source.is_file() and not target.is_file():
        thumbnail(source, target, THUMB_PX)


def byte_range(header: str | None, size: int) -> tuple[int, int] | None:
    """The first and last byte one well-formed `Range: bytes=a-b` header asks for (`-n`: the last n).

    None (send the whole file) when there is no header or it is not one well-formed bytes range: another
    unit, several ranges, whitespace, last before first (RFC 9110 §14.2). `ValueError` (answer 416) for a
    well-formed range the file cannot satisfy."""
    found = RANGE.fullmatch(header or "")
    if found is None or found.groups() == ("", ""):
        return None
    first, last = found.groups()
    if first == "":  # the last n bytes
        start, end = size - int(last), size - 1
        if int(last) == 0 or size == 0:
            raise ValueError(f"range {header!r} asks for no bytes of a {size}-byte file")
        return max(start, 0), end
    if last and int(last) < int(first):
        return None
    if int(first) >= size:
        raise ValueError(f"range {header!r} starts after the end of the file ({size} bytes)")
    return int(first), min(int(last), size - 1) if last else size - 1


def reply(kind: str, range_header: str | None, size: int) -> tuple[HTTPStatus, dict[str, str], int, int]:
    """The status, headers, first byte and length to send; `ValueError` for an unsatisfiable range."""
    wanted = byte_range(range_header, size)
    start, end = wanted or (0, size - 1)
    headers = {"Content-Type": kind, "Content-Length": str(end - start + 1)} | FILE_HEADERS
    if wanted is None:
        return HTTPStatus.OK, headers, 0, size
    return (
        HTTPStatus.PARTIAL_CONTENT,
        headers | {"Content-Range": f"bytes {start}-{end}/{size}"},
        start,
        end - start + 1,
    )


def copy(source: BufferedIOBase, target: BufferedIOBase, length: int) -> None:
    """Copy `length` bytes from where `source` stands, a chunk at a time."""
    while length > 0:
        data = source.read(min(CHUNK, length))
        if not data:
            return
        target.write(data)
        length -= len(data)
