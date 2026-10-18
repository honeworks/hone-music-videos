"""What happened: `events.jsonl` per project (design §8.6) and the in-process hub the dashboard's
server-sent events listen to.

Hone Frame: ported from `src/hone_frame/events.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import Any

_WRITE = threading.Lock()


class Hub:
    """Publishes changes to every listener in this process: `(kind, data)` with kind `item`, `run`,
    `event` or `notification`. A slow listener drops nothing; a listener that went away is removed."""

    def __init__(self) -> None:
        self._listeners: list[queue.Queue[tuple[str, Any]]] = []
        self._lock = threading.Lock()

    def listen(self) -> queue.Queue[tuple[str, Any]]:
        listener: queue.Queue[tuple[str, Any]] = queue.Queue()
        with self._lock:
            self._listeners.append(listener)
        return listener

    def leave(self, listener: queue.Queue[tuple[str, Any]]) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def publish(self, kind: str, data: Any) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            listener.put((kind, data))


def append_line(path: Path, row: dict[str, Any]) -> None:
    """Append one JSON object as a line (whole lines only, one writer at a time in this process)."""
    with _WRITE:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_lines(path: Path) -> list[dict[str, Any]]:
    """Every line of a JSONL file; a half-written last line is left for the next read."""
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            break
    return rows


def last_lines(path: Path, limit: int) -> list[dict[str, Any]]:
    """The last `limit` lines, oldest first."""
    rows = read_lines(path)
    return rows[-limit:] if limit > 0 else []
