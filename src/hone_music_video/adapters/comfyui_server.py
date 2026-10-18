"""The ComfyUI a model is about to use: its command line, and the SageAttention it has (0025 §2, §5)."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, cast

PYTHON = "HONE_COMFYUI_PYTHON"  # ComfyUI's Python, for the SageAttention version (0025 §5, D-157)
VERSION_CODE = "import importlib.metadata as m; print(m.version('sageattention'))"
COMFYUI_URL = "http://127.0.0.1:8188"  # hone-models' default; ModelConfig has no URL of its own
SAGE_SERVER = (
    "ComfyUI at {url} runs with --use-sage-attention, which makes {model}'s pictures black: let its job "
    "end, or restart it without the flag"
)


def comfy_url() -> str:
    """The server hone-models uses (`HONE_COMFYUI_URL`, else `http://127.0.0.1:8188`)."""
    return (os.environ.get("HONE_COMFYUI_URL") or COMFYUI_URL).rstrip("/")


def server_argv(url: str) -> list[str] | None:
    """The command line of the ComfyUI answering at `url` (`/system_stats`), or None when none answers."""
    try:
        with urllib.request.urlopen(f"{url}/system_stats", timeout=2) as answer:  # noqa: S310 - the registry's ComfyUI URL
            raw = cast(object, json.load(answer))
    except (OSError, ValueError):
        return None
    return _argv(raw)


def _argv(data: object) -> list[str] | None:
    if not isinstance(data, dict):
        return None
    system = cast(dict[str, Any], data).get("system")
    if not isinstance(system, dict):
        return None
    argv = cast(dict[str, Any], system).get("argv")
    if not isinstance(argv, list):
        return None
    return [str(item) for item in cast(list[object], argv)]


def _interpreter(start: str) -> str | None:
    """`HONE_COMFYUI_PYTHON`, else the start command's first word when it is a Python."""
    if given := os.environ.get(PYTHON):
        return given
    words = shlex.split(start) if start else []
    first = os.path.expanduser(words[0]) if words else ""
    return first if Path(first).name.startswith("python") else None


def sage_version(start: str) -> str:
    """The sageattention version ComfyUI's Python has, or "unknown" (never a refusal: 1.x works too)."""
    python = _interpreter(start)
    if python is None:
        return "unknown"
    try:
        found = subprocess.run(  # noqa: S603 - the owner's ComfyUI Python, a fixed script
            [python, "-c", VERSION_CODE], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return found.stdout.strip() if found.returncode == 0 and found.stdout.strip() else "unknown"
