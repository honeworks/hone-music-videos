"""`Workspace`: the folder that holds every project (design §4.1), and importing a project file.

Hone Frame: ported from `src/hone_frame/workspace.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from hone_music_video.frame._files import (
    FORMAT_VERSION,
    now,
    project_lock,
    read_json,
    slug,
    write_json,
    write_text,
)
from hone_music_video.frame.checks import load
from hone_music_video.frame.events import Hub
from hone_music_video.frame.guide import guide_for
from hone_music_video.frame.models import FrameModels
from hone_music_video.frame.ports import Models
from hone_music_video.frame.project import Project
from hone_music_video.frame.project_file import Format, ProjectSpec, file_format
from hone_music_video.frame.records import ProjectState
from hone_music_video.frame.writeback import set_fields


class Workspace:
    """`HONE_FRAME_HOME`, else `~/hone-frame` (decisions D-018). Created on first use; a workspace of
    format "1" is refused (decisions D-044)."""

    def __init__(
        self, path: str | Path | None = None, *, models: Models | None = None, scene_picks: bool = True
    ) -> None:
        self.root = Path(path or os.environ.get("HONE_FRAME_HOME") or "~/hone-frame").expanduser().resolve()
        marker = self.root / "workspace.json"
        if marker.is_file():
            read_json(marker)  # refuses format "1"
        else:
            write_json(marker, {"format_version": FORMAT_VERSION, "created_at": now()})
        (self.root / "projects").mkdir(parents=True, exist_ok=True)
        self._models = models
        # hone-music-video's one change (0028 §5): False, a scene's takes never wait for a pick
        self.scene_picks = scene_picks
        self.hub = Hub()
        self._specs: dict[str, tuple[str, ProjectSpec]] = {}  # project id -> (text, spec): checked once

    @property
    def models(self) -> Models:
        """The `Models` port; hone-models unless the workspace was made with another (design §7.2)."""
        if self._models is None:
            # Hone Frame: hone-models with `<home>/hone-models.toml`; here the library's port (0027)
            from hone_music_video.adapters.hone_models import HoneModels  # noqa: PLC0415 - only when used

            self._models = FrameModels(HoneModels())
        return self._models

    def check(
        self, text: str, fmt: Format, *, files_root: Path, project_id: str | None = None
    ) -> ProjectSpec:
        """Parse and check a project file with this workspace's models (design §5.3). With
        `project_id`, the result is kept for that project until its text changes."""
        cached = self._specs.get(project_id or "")
        if cached is not None and cached[0] == text:
            return cached[1]
        spec = load(text, fmt, models=self.models, files_root=files_root)
        if project_id:
            self._specs[project_id] = (text, spec)
        return spec

    def import_file(self, path: str | Path) -> Project:
        """Copy a TOML or JSON project file into a new project (design §5.1). `file` fields are read
        relative to the file's folder and copied into the project's `assets/`."""
        source = Path(path).expanduser()
        if not source.is_file():
            raise FileNotFoundError(f"{source}: no such project file")
        text = source.read_text(encoding="utf-8")
        return self.import_text(text, file_format(source.name), files_root=source.parent, source=source.name)

    def import_text(
        self, text: str, fmt: Format, *, files_root: Path | None = None, source: str = ""
    ) -> Project:
        """Like `import_file`, from the file's text (`files_root` defaults to the workspace folder). Nothing
        is left behind when the import fails."""
        root = (files_root or self.root).resolve()
        spec = self.check(text, fmt, files_root=root)
        with project_lock(self.root / "projects"):
            project_id = self._new_id(spec.name)
            folder = self.root / "projects" / project_id
            folder.mkdir(parents=True)
        try:
            write_text(folder / f"project.{fmt}", copy_files(spec, text, root, folder))
            state = ProjectState(id=project_id, name=spec.name, created_at=now(), source=source)
            write_json(folder / "state.json", state.model_dump(mode="json"))
            project = Project(self, project_id)
            project.sync()
            write_text(folder / "GUIDE.md", guide_for(self, [], project_id))
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            self._specs.pop(project_id, None)
            raise
        project.log("imported", message=f"imported {source or f'project.{fmt}'}: {len(spec.items)} items")
        return project

    def _new_id(self, name: str) -> str:
        base, n = slug(name), 1
        project_id = base
        while (self.root / "projects" / project_id).exists():
            n += 1
            project_id = f"{base}-{n}"
        return project_id

    def projects(self) -> list[Project]:
        folders = sorted(p for p in (self.root / "projects").iterdir() if (p / "state.json").is_file())
        return [Project(self, p.name) for p in folders]

    def project(self, project_id: str) -> Project:
        return Project(self, project_id)


def copy_files(spec: ProjectSpec, text: str, root: Path, folder: Path) -> str:
    """Copy each item's `file` into `assets/` and point the copy of the project file at it."""
    for item in spec.items:
        if not item.file:
            continue
        source = (root / item.file).resolve()
        target = folder / "assets" / source.name
        n = 1
        while target.exists() and target.read_bytes() != source.read_bytes():
            n += 1
            target = folder / "assets" / f"{source.stem}-{n}{source.suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        relative = target.relative_to(folder).as_posix()
        if relative != item.file:
            text = set_fields(text, spec.format, item.path, {"file": relative})
    return text
