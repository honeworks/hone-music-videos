"""Small file helpers: atomic writes, JSON records, UTC time, safe ids."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)
_SLUG = re.compile(r"[^a-z0-9]+")


def now() -> str:
    """The current time as ISO-8601 UTC."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def slug(text: str, fallback: str = "video") -> str:
    """A safe folder name from free text: lowercase letters, digits and dashes."""
    return _SLUG.sub("-", text.lower()).strip("-")[:48] or fallback


def write_bytes(path: Path, data: bytes) -> None:
    """Write `data` so that no reader ever sees a half-written file (temporary file, fsync, replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_json(path: Path, value: BaseModel | dict[str, Any] | list[Any]) -> None:
    """Write a record (a pydantic model or plain JSON) atomically, UTF-8, 2-space indent."""
    data = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    write_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())


def read_json(path: Path, model: type[M]) -> M:
    """Read and validate a record written by `write_json`."""
    return model.model_validate_json(path.read_bytes())


def newest(where: Path, pattern: str) -> Path | None:
    """The newest file matching a pattern (a draft, a portrait draft), by the time it was written."""
    return max(where.glob(pattern), key=lambda p: p.stat().st_mtime_ns, default=None)
