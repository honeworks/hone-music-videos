"""AC-6: versions are never deleted; "use this version" switches the current one.

Hone Frame: ported from its `tests/e2e/test_ac6_versions.py` (change 0027)."""

from __future__ import annotations

import pytest

from hone_music_video import frame as hf
from hone_music_video.frame import actions
from hone_music_video.frame.errors import NotFound
from hone_music_video.frame.views import item_view

from .conftest import run

pytestmark = pytest.mark.e2e

TEXT = """
[project]
name = "Versions"

[places.kitchen.wide]
model = "z-image-turbo"
prompt = "kitchen"

[scenes.morning]
model = "qwen-image-edit-2511"
refs = ["kitchen.wide"]
prompt = "morning"
"""


def test_ac6_versions_are_kept_and_switched(ws: hf.Workspace) -> None:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    for _ in range(2):
        actions.mark(project, "kitchen.wide")
        run(ws, project)
    view = item_view(project, "kitchen.wide")
    assert [v.n for v in view.versions] == [1, 2, 3] and view.current == 3
    files = sorted(p.name for p in (project.root / "items" / "kitchen.wide").glob("v*"))
    assert files == ["v001.json", "v001.png", "v002.json", "v002.png", "v003.json", "v003.png"]
    # Hone Frame: `/files/<project>/items/<item>/v1.png` of its own server, which finds v001.png; here the
    # video project's files, served as they are on disk (0027)
    base = f"/files/{project.ws.root.parent.name}/frame/projects/{project.id}"
    assert view.versions[0].url == f"{base}/items/kitchen.wide/v001.png"
    assert view.versions[0].thumb == f"{base}/thumbs/kitchen.wide/v001.webp"

    assert item_view(project, "morning").older_refs == ["kitchen.wide"]  # made from v1, now v3
    marked = actions.use_version(project, "kitchen.wide", 1, with_dependants=True)
    assert marked == ["morning"]
    assert item_view(project, "kitchen.wide").current == 1
    assert len(item_view(project, "kitchen.wide").versions) == 3
    assert item_view(project, "morning").older_refs == []  # v1 is current again
    with pytest.raises(NotFound, match="no version 9"):
        actions.use_version(project, "kitchen.wide", 9)

    folder = project.root / "items" / "kitchen.wide"
    before = {p.name: p.read_bytes() for p in folder.glob("v00[123].*")}
    actions.mark(project, "kitchen.wide")
    run(ws, project)  # a redo after using v1 is v4: nothing is overwritten
    view = item_view(project, "kitchen.wide")
    assert [v.n for v in view.versions] == [1, 2, 3, 4] and view.current == 4
    assert {p.name: p.read_bytes() for p in folder.glob("v00[123].*")} == before
