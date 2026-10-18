"""The project file: file order, inline tables, write-back, and small helpers.

Hone Frame: ported from its `tests/unit/test_project_file.py` (change 0027)."""

from __future__ import annotations

from pathlib import Path

import pytest

from hone_music_video.frame.errors import InvalidRequest
from hone_music_video.frame.events import last_lines
from hone_music_video.frame.project_file import file_format, parse_text, read_items
from hone_music_video.frame.writeback import set_fields

TEXT = """\
[characters.woman]
hero = { prompt = "a" }   # inline: sits where its subject's table is

[places.kitchen.wide]
prompt = "b"

[characters."woman".side]
prompt = "c"
"""


def test_order_follows_the_text() -> None:
    items, problems = read_items(parse_text(TEXT, "toml"), TEXT, "toml")
    assert not problems
    assert [i.id for i in items] == ["woman.hero", "kitchen.wide", "woman.side"]


def test_structure_problems() -> None:
    text = '[characters]\nwoman = "x"\n[scenes.s]\nx = 1\n[sheets]\nt = 2\n'
    _, problems = read_items(parse_text(text, "toml"), text, "toml")
    assert {p.item for p in problems} == {"characters.woman", "s.x", "sheets.t"}


def test_formats() -> None:
    assert file_format("a.TOML") == "toml" and file_format("b.json") == "json"
    with pytest.raises(InvalidRequest, match=r"\.toml or a \.json"):
        file_format("c.yaml")
    with pytest.raises(InvalidRequest):
        parse_text("[1, 2]", "json")


def test_writeback_keeps_comments_and_removes_fields() -> None:
    text = '# top\n[places.kitchen.wide]\nprompt = "b"  # keep me\nseed = 3\n'
    out = set_fields(text, "toml", ("places", "kitchen", "wide"), {"seed": None, "inputs": {"steps": 4}})
    assert out == '# top\n[places.kitchen.wide]\nprompt = "b"  # keep me\ninputs = {steps = 4}\n'
    with pytest.raises(InvalidRequest, match="not in the file"):
        set_fields(text, "toml", ("places", "hall", "wide"), {"seed": 1})


def test_last_lines(tmp_path: Path) -> None:
    path = tmp_path / "e.jsonl"
    path.write_text('{"a": 1}\n{"a": 2}\n{"a": 3')
    assert last_lines(path, 1) == [{"a": 2}] and last_lines(path, 0) == []
