"""The frame workspace's JSON API in the dashboard (0027 §6): Hone Frame's `dashboard_api` routes
(`frame/api.py`), mounted under `/api/projects/<id>/frame/...` with the same answers and statuses, on
the project's frame runner (`frame_stages.runner_for`). The Scenes view of the page calls them.

    /api/projects/<id>/frame                      -> projects/<frame project>  (the project view)
    /api/projects/<id>/frame/items/<item>/accept  -> projects/<frame project>/items/<item>/accept
    /api/projects/<id>/frame/notifications        -> notifications             (and models, guide, queue)
    /api/projects/<id>/frame/guide?project=this   -> guide?project=<frame project>

Hone Frame: its server takes a file as multipart/form-data; the dashboard's page sends JSON, so a file is
`{"file": {"name", "data_b64"}}` here, turned into the same `(name, bytes)`."""

from __future__ import annotations

import base64
import binascii
from functools import partial
from typing import Any

from hone_music_video import frame_stages
from hone_music_video.errors import InvalidInput
from hone_music_video.frame.api import Api, answer
from hone_music_video.frame.guide import guide_for
from hone_music_video.ports import Models
from hone_music_video.project import Project

WORKSPACE_ROUTES = ("notifications", "models", "guide", "queue")  # not one project's: the workspace's


def _file(body: dict[str, Any]) -> dict[str, Any]:
    upload = body.get("file")
    if not isinstance(upload, dict) or "data_b64" not in upload:
        return body
    try:
        data = base64.b64decode(str(upload["data_b64"]), validate=True)  # pyright: ignore[reportUnknownArgumentType]
    except (binascii.Error, ValueError):
        raise InvalidInput("file: not valid base64", ["file: not valid base64"]) from None
    return body | {"file": (str(upload.get("name") or "upload"), data)}  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]


def frame_route(
    project: Project,
    models: Models,
    method: str,
    rest: list[str],
    *,
    body: dict[str, Any],
    query: dict[str, str],
) -> tuple[int, Any]:
    """The HTTP status and answer of a frame route."""
    runner = frame_stages.runner_for(project, models)
    fp = frame_stages.frame_project(runner.ws)
    api = Api(runner.ws, runner, partial(guide_for, runner.ws))
    if query.get("project") == "this":  # the guide for the models of this video's frame project
        query = query | {"project": fp.id}
    path = "/".join(rest) if rest and rest[0] in WORKSPACE_ROUTES else "/".join(["projects", fp.id, *rest])
    return answer(api, method, path, _file(body), query)
