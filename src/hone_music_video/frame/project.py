"""`Project`: one project folder (design §4.2): the copy of the project file, `state.json`, every version
of every item, `run.json` and `events.jsonl`.

Hone Frame: ported from `src/hone_frame/project.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Collection, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, UnidentifiedImageError

from hone_music_video.frame._files import now, project_lock, read_json, write_json, write_text
from hone_music_video.frame.errors import InvalidRequest, NotFound, Problem
from hone_music_video.frame.events import append_line
from hone_music_video.frame.project_file import Format, ItemSpec, ProjectSpec
from hone_music_video.frame.records import ItemState, ProjectState, RunRecord, Version

if TYPE_CHECKING:
    from hone_music_video.frame.workspace import Workspace


class Project:
    """One project of a workspace: its file (what to make), its state (what exists), its run and events."""

    def __init__(self, ws: Workspace, project_id: str) -> None:
        self.ws = ws
        self.id = project_id
        self.root = ws.root / "projects" / project_id
        if "/" in project_id or project_id.startswith(".") or not (self.root / "state.json").is_file():
            raise NotFound(f"no project {project_id!r}: `hone-frame projects` lists them")

    @property
    def file(self) -> Path:
        """The copy of the project file: the source of truth for what to make (design §5.1)."""
        toml = self.root / "project.toml"
        return toml if toml.is_file() else self.root / "project.json"

    @property
    def format(self) -> Format:
        return "toml" if self.file.suffix == ".toml" else "json"

    def text(self) -> str:
        return self.file.read_text(encoding="utf-8")

    def spec(self) -> ProjectSpec:
        """The project file, parsed and checked (once per text)."""
        return self._check(self.text())

    def _check(self, text: str) -> ProjectSpec:
        return self.ws.check(text, self.format, files_root=self.root, project_id=self.id)

    def write_text(self, text: str) -> ProjectSpec:
        """Check `text` and make it the project file; new items are marked to run, changed files become
        new versions. Nothing is written when the text is refused."""
        spec = self._check(text)
        with project_lock(self.root):
            write_text(self.file, text)
        self.sync()
        return spec

    def state(self) -> ProjectState:
        return ProjectState.model_validate(read_json(self.root / "state.json"))

    @contextmanager
    def editing(self) -> Generator[ProjectState]:
        """The state, saved afterwards; one writer at a time (decisions D-004)."""
        with project_lock(self.root):
            state = self.state()
            yield state
            write_json(self.root / "state.json", state.model_dump(mode="json"))

    def sync(self) -> None:
        """Give new items their state (`todo`, marked) and a changed `file` its new version. Called after
        every write, and before every action, so an item added to the file by hand has a state."""
        spec = self.spec()
        changed: list[str] = []
        with self.editing() as state:
            for item in spec.items:
                if item.id not in state.items:
                    state.items[item.id] = ItemState(marked=not item.file)
                    changed.append(item.id)
                if _provide_from_file(self, state, item):
                    changed.append(item.id)
        self.changed(*changed)

    def reset_running(self) -> None:
        """Items left `running` by a process that ended go back to `done` (with a current version) or
        `todo`; their marks stay (design §8.4)."""
        with self.editing() as state:
            stuck = [i for i, st in state.items.items() if st.status == "running"]
            for item_id in stuck:
                state.items[item_id].status = "done" if state.items[item_id].current is not None else "todo"
        self.changed(*stuck)

    def marked(self) -> list[ItemSpec]:
        """The items marked to run, in file order: the run takes the first."""
        state = self.state()
        return [i for i in self.spec().items if (st := state.items.get(i.id)) is not None and st.marked]

    def add_version(self, state: ProjectState, item_id: str, image: Path, **fields: Any) -> Version:
        """Move `image` in as the item's next version and make it current."""
        item = state.items.setdefault(item_id, ItemState())
        n = max((v.n for v in item.versions), default=0) + 1
        target = self.root / "items" / item_id / f"v{n:03d}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(image, target)
        version = Version(n=n, file=target.relative_to(self.root).as_posix(), at=now(), **fields)
        write_json(target.with_suffix(".json"), version.model_dump(mode="json"))
        item.versions.append(version)
        item.current = n
        return version

    def current_image(self, state: ProjectState, item_id: str) -> Path | None:
        """The current version's file of a project item, or `None` when it has none."""
        item = state.items.get(item_id)
        version = item.version(item.current) if item and item.current else None
        return self.root / version.file if version else None

    def work_file(self, item_id: str) -> Path:
        """Where an image is made before it becomes a version."""
        path = self.root / "items" / item_id / ".work.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def run(self) -> RunRecord:
        path = self.root / "run.json"
        return RunRecord.model_validate(read_json(path)) if path.is_file() else RunRecord()

    def save_run(self, record: RunRecord) -> None:
        """Replace `run.json` (a new or queued run); a change of some fields is `update_run`."""
        with project_lock(self.root):
            write_json(self.root / "run.json", record.model_dump(mode="json"))
        self.ws.hub.publish("run", self.id)

    def update_run(self, *, when: Collection[str] | None = None, **changes: Any) -> RunRecord:
        """Change fields of `run.json`, re-read under the project lock so that two threads never undo each
        other's change (decisions D-068); with `when`, only while the run's status is one of them."""
        with project_lock(self.root):
            record = self.run()
            if when is not None and record.status not in when:
                return record
            record = record.model_copy(update=changes)
            write_json(self.root / "run.json", record.model_dump(mode="json"))
        self.ws.hub.publish("run", self.id)
        return record

    def log(self, kind: str, item: str | None = None, message: str = "", **fields: Any) -> dict[str, Any]:
        """Write an event line (design §8.6) and publish it: `kind`, the item it is about, a message for
        people, and `error`, `elapsed_s`, `version` (None unless given) or other fields."""
        row = {
            "at": now(), "project": self.id, "kind": kind, "item": item, "message": message, "error": None,
            "elapsed_s": None, "version": None,
        } | fields  # fmt: skip
        append_line(self.root / "events.jsonl", row)
        self.ws.hub.publish("event", row)
        return row

    def changed(self, *item_ids: str) -> None:
        """Tell the dashboard these items changed."""
        for item_id in item_ids:
            self.ws.hub.publish("item", (self.id, item_id))


def _provide_from_file(project: Project, state: ProjectState, item: ItemSpec) -> bool:
    """A new `provided` version when the item's `file` is new or its bytes changed since it was last
    imported (not when another version is current: replacing or choosing a version is not undone)."""
    st = state.items[item.id]
    if not item.file:
        st.file_sha256 = None  # the same file given again later is imported again
        return False
    source = project.root / item.file
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if st.file_sha256 is None and any(v.source == "provided" and v.sha256 == digest for v in st.versions):
        st.file_sha256 = digest  # a state written before file_sha256: this file is already a version
        st.status, st.marked = "provided", False
        return True
    if st.file_sha256 == digest:
        return False
    work = to_png(source, project.work_file(item.id))
    project.add_version(state, item.id, work, source="provided", original=source.name, sha256=digest)
    st.status, st.marked, st.error, st.file_sha256 = "provided", False, None, digest
    return True


def to_png(source: Path, out: Path) -> Path:
    """A provided image as PNG at `out` (versions are PNG files); anything else is refused."""
    try:
        with Image.open(source) as image:
            image.save(out, format="PNG")
    except (UnidentifiedImageError, OSError) as exc:
        problem = Problem(source.name, "not an image Pillow can read: give a PNG, JPEG or WebP file")
        raise InvalidRequest("the file was not accepted", [problem]) from exc
    return out
