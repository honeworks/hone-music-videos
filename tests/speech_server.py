"""A stand-in for the gateway's `/audio/transcriptions` on 127.0.0.1: it keeps every request and answers
`verbose_json` with the words it is given (no model runs, nothing leaves the machine)."""

from __future__ import annotations

import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

KEY = "sk-planted-0123456789abcdef"  # a key that must never be written anywhere


@dataclass
class SpeechServer:
    """`words` are (text, start s, end s); `status` other than 200 answers that error; `extra` is added
    to the reply (Scribe's has no `duration`: `None` leaves it out)."""

    words: list[tuple[str, float, float]] = field(default_factory=list[tuple[str, float, float]])
    duration: float | None = 4.0
    extra: dict[str, Any] = field(default_factory=dict[str, Any])
    status: int = 200
    requests: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    url: str = ""

    def reply(self) -> dict[str, Any]:
        words = [{"word": t, "start": a, "end": b} for t, a, b in self.words]
        text = " ".join(t for t, _, _ in self.words)
        reply = {"text": text, "language": "english", "duration": self.duration, "words": words}
        return {k: v for k, v in reply.items() if v is not None} | self.extra


def _handler(server: SpeechServer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            server.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
            if server.status != 200:
                answer = json.dumps({"error": {"message": f"bad key {KEY}"}}).encode()
            else:
                answer = json.dumps(server.reply()).encode()
            self.send_response(server.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(answer)))
            self.end_headers()
            self.wfile.write(answer)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


@contextmanager
def serving(monkeypatch: pytest.MonkeyPatch, server: SpeechServer) -> Generator[SpeechServer]:
    """Serve `server` and point the shipped registry entries at it, with the planted key."""
    http = ThreadingHTTPServer(("127.0.0.1", 0), _handler(server))
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    server.url = f"http://127.0.0.1:{http.server_address[1]}/v1"
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", server.url)
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", KEY)
    try:
        yield server
    finally:
        http.shutdown()
        http.server_close()
