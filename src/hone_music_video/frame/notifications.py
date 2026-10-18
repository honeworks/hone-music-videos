"""Notifications (design §9.2): when a run waits for the owner, fails or finishes, a line in
`<home>/notifications.jsonl` that the dashboard shows and rings for.

Hone Frame: ported from `src/hone_frame/notifications.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hone_music_video.frame._files import now, project_lock
from hone_music_video.frame.errors import NotFound
from hone_music_video.frame.events import append_line, read_lines

if TYPE_CHECKING:
    from hone_music_video.frame.project import Project


def notify(project: Project, kind: str, item: str | None, message: str) -> dict[str, Any]:
    """Add a notification about `project`: `kind` is `waiting`, `failed` or `done`."""
    at = now()
    nid = hashlib.sha256(f"{project.id}:{kind}:{at}".encode()).hexdigest()[:12]
    row = {
        "id": nid, "project": project.id, "project_name": project.state().name, "item": item, "kind": kind,
        "message": message, "at": at, "read": False,
    }  # fmt: skip
    append_line(project.ws.root / "notifications.jsonl", row)
    project.ws.hub.publish("notification", row)
    return row


def notifications(home: Path) -> list[dict[str, Any]]:
    """Every notification, newest first; a read one has `read: true`."""
    rows = read_lines(home / "notifications.jsonl")
    read = {r["read_id"] for r in rows if "read_id" in r}
    found = [r | {"read": r["id"] in read} for r in rows if "id" in r]
    return found[::-1]


def mark_read(home: Path, notification_id: str) -> dict[str, Any]:
    with project_lock(home):
        found = next((n for n in notifications(home) if n["id"] == notification_id), None)
        if found is None:
            raise NotFound(f"no notification {notification_id!r}: GET /api/notifications lists them")
        if not found["read"]:
            append_line(home / "notifications.jsonl", {"read_id": notification_id, "at": now()})
    return found | {"read": True}
