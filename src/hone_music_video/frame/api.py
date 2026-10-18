"""The dashboard's JSON API (design §12.2): `Api.call` matches the method and path to what it does.

Hone Frame: ported from `src/hone_frame/dashboard_api.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from pydantic import BaseModel

from hone_music_video.frame import actions
from hone_music_video.frame.errors import HoneFrameError, InvalidRequest, NotFound, Problem, RunStateError
from hone_music_video.frame.estimates import measured
from hone_music_video.frame.events import last_lines
from hone_music_video.frame.notifications import mark_read, notifications
from hone_music_video.frame.project import Project
from hone_music_video.frame.project_file import Format
from hone_music_video.frame.runner import Runner
from hone_music_video.frame.views import (
    item_view,
    model_view,
    project_summary,
    project_view,
    run_view,
)
from hone_music_video.frame.workspace import Workspace

Guide = Callable[[list[str], str | None], str]  # (model ids, project id) -> Markdown
Body = dict[str, Any]
CONTROLS = ("run", "pause", "resume", "stop")


class Api:
    """The routes' context: the workspace, its runner and the guide."""

    def __init__(self, ws: Workspace, runner: Runner, guide: Guide) -> None:
        self.ws, self.runner, self.guide = ws, runner, guide

    def call(self, method: str, path: str, body: Body, query: dict[str, str]) -> Any:
        """Answer `method /api/<path>`; `NotFound` for a route that does not exist."""
        parts = tuple(p for p in path.strip("/").split("/") if p)
        match (method, *parts):
            case ("GET", "projects"):
                answer = [project_summary(p) for p in self.ws.projects()]
            case ("POST", "projects"):
                fmt: Format = "json" if _field(body, "format", str, "toml") == "json" else "toml"
                answer = project_view(self.ws.import_text(_field(body, "text", str), fmt))
            case (_, "projects", project_id, *rest):
                answer = self._project(method, self.ws.project(project_id), tuple(rest), body, query)
            case ("GET", "queue"):
                answer = [run_view(self.ws.project(p)) for p in self.runner.queue()]
            case ("GET", "notifications"):
                answer = notifications(self.ws.root)
            case ("POST", "notifications", notification_id, "read"):
                answer = mark_read(self.ws.root, notification_id)
            case ("GET", "models"):
                durations = measured(self.ws.root)
                answer = [model_view(i, durations) for i in self.ws.models.available("image") if i.local]
            case ("GET", "guide"):
                models = [m for m in query.get("models", "").split(",") if m]
                answer = {"markdown": self.guide(models, query.get("project") or None)}
            case _:
                raise NotFound(f"no API route {method} /api/{'/'.join(parts)}")
        return answer

    def _project(
        self, method: str, project: Project, rest: tuple[str, ...], body: Body, query: dict[str, str]
    ) -> Any:
        match (method, *rest):
            case ("GET",):
                answer = project_view(project)
            case ("GET", "file"):
                answer = {"text": project.text(), "format": project.format}
            case ("PUT", "file"):
                actions.replace_file_text(project, _field(body, "text", str))
                answer = project_view(project)
            case ("GET", "events"):
                answer = last_lines(project.root / "events.jsonl", int(query.get("limit") or 200))
            case ("POST", action) if action in CONTROLS:
                getattr(self.runner, action)(project.id)
                answer = run_view(project)
            case (_, "items", item_id, *more):
                answer = self._item(method, project, item_id, tuple(more), body)
                if method != "GET":
                    self.runner.settle(project.id)  # a run waiting for this item may go on (D-074)
            case _:
                raise NotFound(f"no API route {method} /api/projects/{project.id}/{'/'.join(rest)}")
        return answer

    def _item(self, method: str, project: Project, item_id: str, rest: tuple[str, ...], body: Body) -> Any:
        dependants = bool(_field(body, "dependants", bool, False)) if rest != ("file",) else False
        match (method, *rest):
            case ("PATCH",):
                if not body:
                    raise InvalidRequest(
                        "the edit was not accepted", [Problem(item_id, "send {field: value}")]
                    )
                actions.edit(project, item_id, body)
            case ("GET", "dependants"):
                return actions.dependants(project.spec(), item_id)
            case ("POST", "mark"):
                return {"marked": actions.mark(project, item_id, with_dependants=dependants)}
            case ("POST", "unmark"):
                actions.unmark(project, item_id)
            case ("POST", "run-prompt"):  # hone-music-video 0033
                actions.run_prompt(project, item_id, _field(body, "prompt", int))
            case ("POST", "accept"):
                self.runner.accept(project.id, item_id, _field(body, "version", int, None))
            case ("POST", "use-version"):
                actions.use_version(
                    project, item_id, _field(body, "version", int), with_dependants=dependants
                )
            case ("POST", "file"):
                _provide(project, item_id, body)
            case _:
                raise NotFound(
                    f"no API route {method} /api/projects/{project.id}/items/{item_id}/{'/'.join(rest)}"
                )
        return item_view(project, item_id)


def _provide(project: Project, item_id: str, body: Body) -> None:
    upload: Any = body.get("file")
    if not isinstance(upload, tuple):
        raise InvalidRequest(
            "no file", [Problem(item_id, "send multipart/form-data with a field named file")]
        )
    name, data = cast(tuple[str | None, bytes], upload)
    with_dependants = str(body.get("dependants", "false")).lower() in ("1", "true", "yes", "on")
    actions.provide(project, item_id, data, str(name or "upload"), with_dependants=with_dependants)


def _field(body: Body, name: str, kind: type, default: Any = ...) -> Any:
    value = body.get(name, default)
    if value is ... or (value is not None and not isinstance(value, kind)):
        raise InvalidRequest(
            "the request was not accepted", [Problem(name, f"give {name} as {kind.__name__}")]
        )
    return value


def answer(api: Api, method: str, path: str, body: Body, query: dict[str, str]) -> tuple[int, Any]:
    """The HTTP status and JSON answer of `method /api/<path>`, as Hone Frame's server gives them (its
    `dashboard.Handler._api`): 400 for a refused request with its problems, 404, 409 for a state that does
    not allow it, 500 otherwise. Hone Frame: the server is this library's dashboard (0027)."""
    try:
        return 200, plain(api.call(method, path, body, query))
    except InvalidRequest as exc:
        return 400, _error(exc, exc.problems)
    except NotFound as exc:
        return 404, _error(exc)
    except RunStateError as exc:
        return 409, _error(exc)
    except (HoneFrameError, ValueError) as exc:
        return 400, _error(exc)


def _error(error: Exception, problems: list[Problem] | None = None) -> dict[str, Any]:
    return {"error": str(error), "items": [{"item": p.item, "message": p.message} for p in problems or []]}


def plain(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, dict):
        return {k: plain(v) for k, v in data.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(data, list):
        return [plain(d) for d in data]  # pyright: ignore[reportUnknownVariableType]
    return data


def sse_event(api: Api, kind: str, data: Any) -> bytes:
    """One server-sent event; an item or a run is sent as its current view."""
    try:
        if kind == "item":
            data = {"project": data[0], "item": item_view(api.ws.project(data[0]), data[1])}
        elif kind == "run":
            data = run_view(api.ws.project(data))
    except HoneFrameError as exc:  # gone, or the file is being edited: say so instead of failing
        kind, data = "event", {"kind": "view_unavailable", "item": None, "message": str(exc)}
    return f"event: {kind}\ndata: {json.dumps(plain(data), ensure_ascii=False)}\n\n".encode()
