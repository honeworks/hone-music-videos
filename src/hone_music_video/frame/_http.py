"""Helpers of the dashboard server: which requests are refused, thumbnails and multipart bodies.

Hone Frame: ported from `src/hone_frame/_http.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

from email.message import Message
from email.parser import BytesParser
from email.policy import default as email_policy
from http import HTTPStatus
from pathlib import Path
from typing import Any

from PIL import Image

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def refusal(method: str, path: str, headers: Message[str, str]) -> tuple[int, str] | None:
    """Why a request is refused, or None: another host name (DNS rebinding, decisions D-053); for a
    change, a page of another site or a body a plain HTML form could send (CSRF, decisions D-060)."""
    host = headers.get("Host") or ""
    if host.rsplit(":", 1)[0].strip("[]") not in LOCAL_HOSTS:
        return HTTPStatus.FORBIDDEN, "the dashboard answers 127.0.0.1 only"
    if method == "GET":
        return None
    origin = headers.get("Origin")
    if (origin is not None and origin != f"http://{host}") or headers.get("Sec-Fetch-Site") == "cross-site":
        return HTTPStatus.FORBIDDEN, "the dashboard takes changes from its own page only"
    upload = method == "POST" and "/items/" in path and path.endswith("/file")
    want = "multipart/form-data" if upload else "application/json"
    if not (headers.get("Content-Type") or "").startswith(want):
        return HTTPStatus.UNSUPPORTED_MEDIA_TYPE, f"send the body as {want}"
    return None


def thumbnail(source: Path, target: Path, size: int) -> Path:
    """A WebP thumbnail of `source` at `target`, made once."""
    if not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            small = image.convert("RGB")
            small.thumbnail((size, size))
            small.save(target, format="WEBP", quality=82)
    return target


def multipart(kind: str, raw: bytes) -> dict[str, Any]:
    """The fields of a multipart/form-data body; a file field is `(file name, bytes)`."""
    message = BytesParser(policy=email_policy).parsebytes(f"Content-Type: {kind}\r\n\r\n".encode() + raw)
    fields: dict[str, Any] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True)
        if not isinstance(name, str) or not isinstance(payload, bytes):
            continue
        filename = part.get_filename()
        fields[name] = (filename, payload) if filename else payload.decode("utf-8", "replace")
    return fields
