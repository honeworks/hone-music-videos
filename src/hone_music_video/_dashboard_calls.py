"""The calls to hosted models, for the Plan and Lyrics views (0030 §2): the frame planner's calls as they
are kept in `<project>/frame/calls/` (what was sent, the reply, the problems the code found in it), in
the order made, and the lyrics' transcriptions with their price. Read only."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from hone_music_video import frame_stages, runs
from hone_music_video.errors import NotFound
from hone_music_video.project import Project
from hone_music_video.records import Words

NAME = re.compile(r"[a-z0-9][a-z0-9-]*")  # a kept call's file name, without `.json`


def _read(path: Path) -> dict[str, Any]:
    try:
        found: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return cast("dict[str, Any]", found) if isinstance(found, dict) else {}


def _row(path: Path, kept: dict[str, Any]) -> dict[str, Any]:
    request: dict[str, Any] = kept.get("request") or {}
    data: dict[str, Any] = request.get("data") or {}
    return {
        "name": path.stem,
        "label": kept.get("label", path.stem),
        "model": kept.get("model", ""),
        "took_ms": kept.get("took_ms", 0),
        "at": kept.get("at"),
        "problems": len(kept.get("problems") or []),  # what the code found in the reply
        "sent_back": len(data.get("problems") or []),  # a repair: the problems it was asked to fix
    }


def _made_at(path: Path, row: dict[str, Any]) -> str:
    """When a call was made: its start, kept since 0030, else when its reply was kept."""
    return row["at"] or datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(timespec="microseconds")


def _plan_calls(project: Project) -> list[dict[str, Any]]:
    folder = project.root / frame_stages.FOLDER / "calls"
    rows = [(path, _row(path, _read(path))) for path in folder.glob("*.json")] if folder.is_dir() else []
    return [row for _, row in sorted(rows, key=lambda r: _made_at(*r))]


def _lyrics_calls(project: Project) -> list[dict[str, Any]]:
    """The first listen and each listen again of the latest run's heard words, with their price."""
    try:
        words = runs.stage_outputs(project, "transcribe")["transcribe"]
    except (FileNotFoundError, ValueError, KeyError):
        return []
    if not isinstance(words, Words):
        return []
    made = [("first listen", words.call)]
    made += [(f"listen again {n}", a.call) for n, a in enumerate(words.listened_again, 1)]
    return [
        {"label": label, "model": call.model, "took_ms": call.took_ms, "cost_usd": call.cost_usd,
         "text": str(call.reply.get("text", ""))}
        for label, call in made
        if call is not None
    ]  # fmt: skip


def calls(project: Project) -> dict[str, Any]:
    """Every kept planner call and the lyrics' calls, with the plan's totals."""
    plan = _plan_calls(project)
    lyrics = _lyrics_calls(project)
    return {
        "plan": plan,
        "lyrics": lyrics,
        "total": {"calls": len(plan), "took_ms": sum(c["took_ms"] for c in plan)},
    }


def one_call(project: Project, name: str) -> dict[str, Any]:
    """A kept planner call whole, with its system prompt's text (None for a call kept before 0030)."""
    folder = project.root / frame_stages.FOLDER / "calls"
    path = folder / f"{name}.json"
    if not NAME.fullmatch(name) or not path.is_file():
        raise NotFound(f"no kept call {name!r}")
    kept = _read(path)
    request = kept.get("request")
    system = folder / request["system"] if request and NAME.fullmatch(Path(request["system"]).stem) else None
    text = system.read_text(encoding="utf-8") if system and system.is_file() else None
    return _row(path, kept) | {
        "request": request,
        "reply": kept.get("reply"),
        "found": kept.get("problems") or [],
        "system_text": text,
    }
