"""Edits written back to the project file (design §5.4): TOML through `tomlkit`, keeping the owner's
comments and order (decisions D-042); JSON as JSON. A value of `None` removes the field.

Hone Frame: ported from `src/hone_frame/writeback.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import json
from typing import Any

import tomlkit

from hone_music_video.frame.errors import InvalidRequest, Problem
from hone_music_video.frame.project_file import Format


def set_fields(text: str, fmt: Format, path: tuple[str, ...], changes: dict[str, Any]) -> str:
    """`text` with the table at `path` changed: each key set to its value, or removed when `None`."""
    if fmt == "json":
        data: Any = json.loads(text)
        table = _walk(data, path)
        _apply(table, changes)
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    doc = tomlkit.parse(text)
    table = _walk(doc, path)
    _apply(table, {k: _toml(k, v) for k, v in changes.items()})
    return tomlkit.dumps(doc)


def set_entry(text: str, fmt: Format, path: tuple[str, ...], index: int, value: str) -> str:
    """`text` with entry `index` of the array at `path` (such as `[demo]` `prompts`) set to `value`;
    the array's other entries and comments stay as written (D-077)."""
    if fmt == "json":
        data: Any = json.loads(text)
        _walk(data, path)[index] = value
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    doc = tomlkit.parse(text)
    _walk(doc, path)[index] = value
    return tomlkit.dumps(doc)


def _walk(data: Any, path: tuple[str, ...]) -> Any:
    table = data
    for key in path:
        if key not in table:
            raise InvalidRequest("the item is not in the file", [Problem(".".join(path), "not found")])
        table = table[key]
    return table


def _apply(table: Any, changes: dict[str, Any]) -> None:
    for key, value in changes.items():
        if value is None:
            if key in table:
                del table[key]
        else:
            table[key] = value


def _toml(key: str, value: Any) -> Any:
    """Small tables (`inputs`) as inline tables, the way they are usually written; `prompts` as an
    array with one prompt per line (D-076)."""
    if key == "prompts" and isinstance(value, list):
        array = tomlkit.array()
        array.extend(value)  # pyright: ignore[reportUnknownMemberType]
        return array.multiline(True)
    if isinstance(value, dict):
        inline = tomlkit.inline_table()
        inline.update(value)  # pyright: ignore[reportUnknownMemberType]
        return inline
    return value
