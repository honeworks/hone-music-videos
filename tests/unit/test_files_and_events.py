"""Atomic writes and the progress log."""

from pathlib import Path

import pytest

from hone_music_video._files import slug, write_bytes, write_json
from hone_music_video.events import EventLog


def test_atomic_writes_leave_no_temporary_files(tmp_path: Path) -> None:
    write_json(tmp_path / "a" / "r.json", {"b": 1})
    write_bytes(tmp_path / "a" / "r.json", b"{}")
    assert [p.name for p in (tmp_path / "a").iterdir()] == ["r.json"]


def test_a_failed_write_keeps_the_old_file(tmp_path: Path) -> None:
    target = tmp_path / "r.json"
    write_json(target, {"old": True})
    with pytest.raises(TypeError):
        write_json(target, {"bad": object()})
    assert target.read_text() == '{\n  "old": true\n}\n'
    assert [p.name for p in tmp_path.iterdir()] == ["r.json"]


def test_slug() -> None:
    assert slug("Darvin & Loren: Part 2") == "darvin-loren-part-2"
    assert slug("!!!") == "video"


def test_events_are_read_from_where_the_reader_stopped(tmp_path: Path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    assert log.read() == ([], 0)
    log.write("run_started", run_id="r1")
    log.record({"event": "step_started", "step": "measure"})
    events, offset = log.read()
    assert [e["event"] for e in events] == ["run_started", "step_started"]
    assert events[1]["step"] == "measure" and "at" in events[0]
    with log.path.open("a") as handle:
        handle.write('{"event": "half')  # a line still being written waits
    assert log.read(offset) == ([], offset)
