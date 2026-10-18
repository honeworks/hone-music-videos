"""Workspace files: atomic JSON, the stored format version and the per-project lock (design §4.1).

Hone Frame: ported from `src/hone_frame/_files.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import fcntl
import json
import os
import re
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from hone_music_video.frame.errors import HoneFrameError

FORMAT_VERSION = "2"
OLD_FORMAT = (
    "this workspace was made by an older Hone Frame; start a new workspace and import your project file"
)


def now() -> str:
    """The current UTC time, ISO-8601 with microseconds and a Z (it orders runs submitted together)."""
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    """Write `text` atomically: readers see the old file or the new one, never half of one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, data: Any) -> None:
    """Write `data` as JSON atomically."""
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def readable_image(path: Path) -> bool:
    """True when `path` is an image file Pillow can read (not empty, not cut short, not something else)."""
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception:  # Pillow raises many kinds (OSError, SyntaxError, ValueError...) for a bad file
        return False
    return True


def read_json(path: Path) -> dict[str, Any]:
    """Read a workspace JSON file and check its `format_version` (format "1" is refused, D-044)."""
    loaded: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise HoneFrameError(f"{path} is not a hone-frame record (expected a JSON object)")
    data: dict[str, Any] = loaded  # pyright: ignore[reportUnknownVariableType]
    version = data.get("format_version", "1")
    if version == "1":
        raise HoneFrameError(f"{path}: {OLD_FORMAT}")
    if version != FORMAT_VERSION:
        raise HoneFrameError(
            f"{path} has format_version {version!r}; this hone-frame reads {FORMAT_VERSION!r}: "
            "upgrade hone-frame"
        )
    return data


def slug(name: str) -> str:
    """A safe folder name from a display name: lowercase words joined by hyphens."""
    words = re.findall(r"[a-z0-9]+", name.lower())
    return "-".join(words) or "project"


@contextmanager
def running(folder: Path) -> Generator[None]:
    """Held by the process that runs this project, for the whole run (decisions D-069): another process
    sees it (`running_elsewhere`), and it goes away when that process ends, however it ends."""
    with (folder / ".running").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def running_elsewhere(folder: Path) -> bool:
    """True while a run of this project holds `running` (in another process, or another open of it)."""
    with (folder / ".running").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle, fcntl.LOCK_UN)
    return False


_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()
_HELD = threading.local()


@contextmanager
def project_lock(folder: Path) -> Generator[None]:
    """One writer per project: a re-entrant thread lock plus an `fcntl` lock across processes (D-004)."""
    key = str(folder.resolve())
    with _LOCKS_GUARD:
        lock = _LOCKS.setdefault(key, threading.RLock())
    with lock:
        depth: dict[str, int] = getattr(_HELD, "depth", {})
        _HELD.depth = depth
        if depth.get(key, 0):
            depth[key] += 1
            try:
                yield
            finally:
                depth[key] -= 1
            return
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / ".lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            depth[key] = 1
            try:
                yield
            finally:
                depth[key] = 0
                fcntl.flock(handle, fcntl.LOCK_UN)
