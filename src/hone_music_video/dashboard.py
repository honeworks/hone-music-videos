"""The dashboard (design §13): a standard-library HTTP server on localhost, a small JSON API, server-sent
events for live progress and the static page in `dashboard_page/` (no build step)."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import signal
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import hone_flow as fk

from hone_music_video import frame_stages, runs_pause
from hone_music_video._dashboard_api import project_at, route
from hone_music_video._dashboard_files import copy, frame_thumbnail, reply, servable
from hone_music_video._dashboard_frame import frame_route
from hone_music_video._dashboard_runner import Runner
from hone_music_video.errors import (
    InvalidInput,
    MusicVideoError,
    NotFound,
    ProjectUnreadable,
    RunStateError,
)
from hone_music_video.events import EventLog
from hone_music_video.ports import Models
from hone_music_video.project import Project, open_project

PAGE = resources.files("hone_music_video") / "dashboard_page"
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}
PAGE_CSP = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'"
LOG = logging.getLogger("hone_music_video")
CLOSE_WAIT_S = 60  # the runner's time to end after Stop, so each session stops its ComfyUI (0025 §3)
MAX_BODY = 256 * 1024 * 1024  # a song and its sheets, base64-encoded
STATUS: dict[type[Exception], HTTPStatus] = {
    InvalidInput: HTTPStatus.BAD_REQUEST,
    NotFound: HTTPStatus.NOT_FOUND,
    RunStateError: HTTPStatus.CONFLICT,
    ProjectUnreadable: HTTPStatus.UNPROCESSABLE_ENTITY,
}


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    projects: Path
    runner: Runner
    stopping: threading.Event


class Dashboard:
    """The server over one projects folder on localhost (design §13.1), with its runner thread.

    dashboard = Dashboard("projects", HoneModels()).start()   # serving in background threads
    dashboard.wait()                                          # until Ctrl-C, then closed
    """

    def __init__(self, projects: str | Path, models: Models, port: int = 8794) -> None:
        self.server = _Server(("127.0.0.1", port), Handler)
        self.server.projects = Path(projects)
        self.server.projects.mkdir(parents=True, exist_ok=True)
        self.server.runner = Runner(self.server.projects, models)
        self.server.stopping = threading.Event()
        self._serving = False

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}/"

    def start(self) -> Dashboard:
        """Start the runner and serve, both in background threads."""
        self._serving = True
        restored = self.server.runner.restore()  # the queue a stopped dashboard left (0028 §6)
        if restored:
            LOG.info("queued again from %s: %s", self.server.projects, ", ".join(restored))
        self.server.runner.thread.start()
        threading.Thread(target=self.server.serve_forever, name="hone-music-video-http", daemon=True).start()
        LOG.info("dashboard at %s (projects in %s)", self.url, self.server.projects)
        return self

    def wait(self) -> None:
        """Block until interrupted (Ctrl-C or SIGTERM) or closed, then close; a second Ctrl-C while
        closing exits at once."""
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, _interrupt)
        with contextlib.suppress(KeyboardInterrupt):
            self.server.stopping.wait()
        try:
            self.close()
        except KeyboardInterrupt:
            LOG.warning("closed at once: a ComfyUI started by this dashboard may still be running")

    def close(self) -> None:
        """Stop the busy project (0022) and wait up to `CLOSE_WAIT_S` for the runner, so every open
        session's ComfyUI is stopped (0025 §3); then stop serving."""
        if self.server.stopping.is_set():
            return
        self.server.stopping.set()
        runner = self.server.runner
        runner.closing.set()
        runner.jobs.put(None)
        if runner.current is not None:
            with contextlib.suppress(MusicVideoError):  # not running (at a gate): nothing to stop
                runs_pause.pause(open_project(self.server.projects / runner.current), now=True)
        if runner.thread.is_alive():
            runner.thread.join(CLOSE_WAIT_S)
        frame_stages.close_runners()  # each project's frame runner (0027)
        if self._serving:  # shutdown waits for serve_forever, which only start() runs
            self.server.shutdown()
            self.server.server_close()


def _interrupt(_signal: int, _frame: object) -> None:
    raise KeyboardInterrupt


class _FrameEvents:
    """The frame project's `events.jsonl` lines written since the stream opened (0027 §6)."""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.log: EventLog | None = None
        self.offset = 0
        self.seen: list[dict[str, Any]] = []

    def new(self) -> list[dict[str, Any]]:
        if self.log is None:
            if not frame_stages.has_plan(self.project):
                return []
            fp = frame_stages.frame_project(frame_stages.workspace(self.project))
            self.log = EventLog(fp.root / "events.jsonl")
            self.offset = self.log.path.stat().st_size if self.log.path.is_file() else 0
        self.seen, self.offset = self.log.read(self.offset)
        return self.seen


class Handler(BaseHTTPRequestHandler):
    """`/api/*` JSON, `/api/projects/<id>/events` server-sent events, `/files/*` pictures, else the page."""

    server_version = "hone-music-video"

    @property
    def app(self) -> _Server:
        return self.server  # pyright: ignore[reportReturnType]

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet: the page asks often."""

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")

    def _dispatch(self, method: str) -> None:
        parts = urlsplit(self.path)
        path, query = unquote(parts.path), {k: v[-1] for k, v in parse_qs(parts.query).items()}
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):  # the page went away
            self._route(method, path, query)

    def _route(self, method: str, path: str, query: dict[str, str]) -> None:
        match method, path.split("/"):
            case "GET", ["", "api", "projects", project_id, "events"]:
                self._events(project_id)
            case _, ["", "api", "projects", project_id, "frame", *rest]:
                self._frame(method, project_id, rest, query)
            case _, ["", "api", *_]:
                self._api(method, path.removeprefix("/api"))
            case "GET", ["", "files", *_]:
                self._file(path.removeprefix("/files/"))
            case "GET", _:
                self._static(path)
            case _:
                self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"})

    def _api(self, method: str, path: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "the upload is too large"})
            return
        try:
            result = route(self.app.projects, self.app.runner, method, path, self._body(length))
        except (MusicVideoError, fk.HoneFlowError) as error:
            status = STATUS.get(type(error), HTTPStatus.BAD_REQUEST)
            self._json(status, {"error": str(error), "problems": getattr(error, "problems", [])})
        except Exception as error:
            LOG.exception("dashboard API %s %s failed", method, path)
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"internal error: {type(error).__name__}"})
        else:
            self._json(HTTPStatus.OK, result)

    def _frame(self, method: str, project_id: str, rest: list[str], query: dict[str, str]) -> None:
        """The frame workspace's API (Hone Frame's routes and answers, 0027 §6)."""
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "the upload is too large"})
            return
        try:
            body: Any = self._body(length)
            sent: dict[str, Any] = body if isinstance(body, dict) else {}  # pyright: ignore[reportUnknownVariableType]
            found = project_at(self.app.projects, project_id)
            status, data = frame_route(found, self.app.runner.models, method, rest, body=sent, query=query)
        except (MusicVideoError, fk.HoneFlowError) as error:
            status = STATUS.get(type(error), HTTPStatus.BAD_REQUEST)
            data: Any = {"error": str(error), "items": []}
        except Exception as error:
            LOG.exception("dashboard frame API %s %s failed", method, rest)
            status, data = (
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"internal error: {type(error).__name__}"},
            )
        self._json(status, data)

    def _body(self, length: int) -> Any:
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw) if raw else None
        except json.JSONDecodeError:
            raise InvalidInput("send a JSON body") from None

    def _events(self, project_id: str) -> None:
        """Server-sent events: every line of the project's progress log, then new ones as they come."""
        try:
            project = project_at(self.app.projects, project_id)
        except NotFound as error:
            self._json(HTTPStatus.NOT_FOUND, {"error": str(error)})
            return
        log = EventLog(project.events_file)
        offset = int(self.headers.get("Last-Event-ID") or 0)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        quiet, frame = 0.0, _FrameEvents(project)
        while not self.app.stopping.is_set():
            events, offset = log.read(offset)
            for event in events:
                self.wfile.write(f"id: {offset}\ndata: {json.dumps(event)}\n\n".encode())
            for event in frame.new():  # the frame run's events, as `frame` events (no id: new ones only)
                self.wfile.write(f"data: {json.dumps({'event': 'frame', **event})}\n\n".encode())
            events = events or frame.seen
            if not events and quiet > 15:  # a comment keeps the connection open through proxies
                self.wfile.write(b": still here\n\n")
                quiet = 0.0
            self.wfile.flush()
            quiet += 0.0 if events else 0.25
            time.sleep(0.25)

    def _file(self, relative: str) -> None:
        """A project file the dashboard may serve (`_dashboard_files`), with byte ranges for seeking."""
        frame_thumbnail(self.app.projects, relative)  # a frame version's thumbnail, made once (0027)
        found = servable(self.app.projects, relative)
        try:
            handle = found[0].open("rb") if found else None
        except FileNotFoundError:  # removed since it was found
            handle = None
        if found is None or handle is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        with handle:
            size = os.fstat(handle.fileno()).st_size  # the size of what is open, not of what the path is now
            try:
                status, headers, start, length = reply(found[1], self.headers.get("Range"), size)
            except ValueError as error:
                range_headers = {"Content-Range": f"bytes */{size}"}
                self._send(
                    HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE,
                    str(error).encode(),
                    "text/plain",
                    range_headers,
                )
                return
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            handle.seek(start)
            copy(handle, self.wfile, length)

    def _static(self, path: str) -> None:
        parts = [p for p in path.split("/") if p]
        node = PAGE.joinpath(*parts) if parts and ".." not in parts else PAGE / "index.html"
        if not node.is_file():
            node = PAGE / "index.html"  # the page's own routes
        kind = STATIC_TYPES.get(Path(node.name).suffix, "application/octet-stream")
        self._send(HTTPStatus.OK, node.read_bytes(), kind, {"Content-Security-Policy": PAGE_CSP})

    def _json(self, status: int, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode()
        self._send(status, body, "application/json; charset=utf-8", {"Cache-Control": "no-store"})

    def _send(self, status: int, body: bytes, kind: str, headers: dict[str, str]) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)
