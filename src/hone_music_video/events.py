"""A project's progress log, `events.jsonl`: hone-flow's run events plus one event per finished shot.

The dashboard streams it as server-sent events, so what it shows is what the run did (design §13.3)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from hone_music_video._files import now

_LOCK = threading.Lock()


class EventLog:
    """Append-only JSON lines; readers continue from the byte offset they reached."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, event: str, **fields: Any) -> None:
        line = json.dumps({"event": event, "at": now(), **fields}, ensure_ascii=False, default=str)
        with _LOCK, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def record(self, event: dict[str, Any]) -> None:
        """Keep one hone-flow progress event (`on_event`) as it is."""
        self.write(str(event.get("event", "flow")), **{k: v for k, v in event.items() if k != "event"})

    def read(self, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        """The whole events after `offset` and the offset to continue from (a half-written line waits)."""
        if not self.path.is_file():
            return [], offset
        with self.path.open("rb") as handle:
            handle.seek(offset)
            data = handle.read()
        complete = data[: data.rfind(b"\n") + 1]
        events = [json.loads(line) for line in complete.splitlines() if line.strip()]
        return events, offset + len(complete)
