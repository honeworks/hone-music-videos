"""What the owner does to items (design §6): edit, mark, unmark, accept or pick, use a version, replace
with a file. Each returns what the dependants question needs; the question itself is the caller's.

Hone Frame: ported from `src/hone_frame/actions.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import hashlib
from typing import Any

from hone_music_video.frame.errors import InvalidRequest, NotFound, Problem, RunStateError
from hone_music_video.frame.project import Project, to_png
from hone_music_video.frame.project_file import IMAGE_FIELDS, SHEET_FIELDS, ItemSpec, ProjectSpec
from hone_music_video.frame.records import Status, Version
from hone_music_video.frame.writeback import set_entry, set_fields

DEMO_EDITS = ("prompt", "negative", "model", "size", "seed", "hold", "inputs")


def dependants(spec: ProjectSpec, item_id: str) -> list[str]:
    """The items below that were made from `item_id`, directly or through another (file order)."""
    spec.item(item_id)
    found = {item_id}
    below: list[str] = []
    for item in spec.items:
        if item.id not in found and found & set(item.refs):
            found.add(item.id)
            below.append(item.id)
    return below


def settled_status(item: ItemSpec) -> Status:
    """The status of a made item that needs nothing more: `provided` for a file, else `done`."""
    return "provided" if item.file else "done"


def edit(project: Project, item_id: str, changes: dict[str, Any]) -> None:
    """Write the item's changed fields to the project file (`None` removes one); refused when the
    file would not be valid, naming the problem."""
    item = _spec(project).item(item_id)
    if item.group == "demo":
        return _edit_demo(project, item, changes)
    allowed = SHEET_FIELDS if item.kind == "sheet" else IMAGE_FIELDS
    unknown = [k for k in changes if k not in allowed]
    if unknown:
        problems = [
            Problem(item_id, f"unknown field {k!r}: the fields are {', '.join(allowed)}") for k in unknown
        ]
        raise InvalidRequest("the edit was not accepted", problems)
    project.write_text(set_fields(project.text(), project.format, item.path, changes))
    project.log("edited", item_id, f"edited {', '.join(sorted(changes))}")
    project.changed(item_id)


def _edit_demo(project: Project, item: ItemSpec, changes: dict[str, Any]) -> None:
    """A demo item's `prompt` is its entry of `[demo]` `prompts`; its other fields are the `[demo]`
    table's, shared by every demo item (D-077)."""
    problems = [
        Problem(item.id, f"{k}: a demo item takes {', '.join(DEMO_EDITS)}; a demo has no references")
        for k in changes
        if k not in DEMO_EDITS
    ]
    if "prompt" in changes and not str(changes["prompt"] or "").strip():
        problems.append(Problem(item.id, "the prompt is empty: write it, or remove it from [demo] prompts"))
    if problems:
        raise InvalidRequest("the edit was not accepted", problems)
    text, shared = project.text(), {k: v for k, v in changes.items() if k != "prompt"}
    if "prompt" in changes:
        index = int(item.id.removeprefix("demo.")) - 1
        text = set_entry(text, project.format, ("demo", "prompts"), index, str(changes["prompt"]))
    if shared:
        text = set_fields(text, project.format, ("demo",), shared)
    project.write_text(text)
    project.log("edited", item.id, f"edited {', '.join(sorted(changes))}")
    demo = [i.id for i in project.spec().items if i.group == "demo"]
    project.changed(*(demo if shared else [item.id]))


def replace_file_text(project: Project, text: str) -> None:
    """Replace the whole project file with `text` (checked first; nothing is written when refused)."""
    project.write_text(text)
    project.log("edited", None, "the project file was replaced")
    project.changed(*(i.id for i in project.spec().items))


def mark(project: Project, item_id: str, *, with_dependants: bool = False) -> list[str]:
    """Mark the item (and, when asked, its dependants) to run; returns the ids marked."""
    spec = _spec(project)
    if spec.item(item_id).file:
        raise RunStateError(f"{item_id} is a provided file and is never made: replace its file instead")
    return _mark(project, spec, item_id, [item_id] + (dependants(spec, item_id) if with_dependants else []))


def mark_dependants(project: Project, item_id: str) -> list[str]:
    """Mark the items made from `item_id` to run again (not the item itself); returns the ids marked."""
    spec = _spec(project)
    return _mark(project, spec, item_id, dependants(spec, item_id))


def run_prompt(project: Project, item_id: str, prompt: int) -> None:
    """Mark an item with several prompts to make the picture of one of them (from 0), and nothing made
    from it: its picture in use stays until the owner uses the new one (hone-music-video 0033)."""
    prompts = _spec(project).item(item_id).prompts
    if not prompts or len(prompts) < 2:
        raise InvalidRequest("the item has one prompt", [Problem(item_id, "Mark to run makes its picture")])
    if not 0 <= prompt < len(prompts):
        raise NotFound(f"{item_id} has no prompt {prompt + 1}: it has {len(prompts)}")
    with project.editing() as state:
        st = state.items[item_id]
        if st.status == "running":
            raise RunStateError(f"{item_id} is being made: run its prompt when it is done")
        st.marked, st.run_prompt = True, prompt
    project.log("marked", item_id, f"marked {item_id}, prompt {prompt + 1}")
    project.changed(item_id)


def unmark(project: Project, item_id: str) -> None:
    """Clear the item's mark: the run leaves it as it is."""
    _spec(project).item(item_id)
    with project.editing() as state:
        state.items[item_id].marked = False
        state.items[item_id].run_prompt = None
    project.log("unmarked", item_id, f"unmarked {item_id}")
    project.changed(item_id)


def accept(project: Project, item_id: str, version: int | None = None) -> None:
    """Accept a waiting item, or pick one of its `count` versions: it becomes `done`."""
    _spec(project).item(item_id)
    with project.editing() as state:
        st = state.items[item_id]
        if st.status != "waiting":
            raise RunStateError(f"{item_id} is {st.status}, not waiting: use a version instead")
        if version is not None:
            _check_version(st.versions, item_id, version)
            st.current = version
        st.status, st.candidates = "done", []
    kind = "picked" if version is not None else "accepted"
    project.log(kind, item_id, f"{kind} {item_id}" + (f" v{version}" if version else ""), version=version)
    project.changed(item_id)


def use_version(project: Project, item_id: str, version: int, *, with_dependants: bool = False) -> list[str]:
    """Make an older (or newer) version current; returns the dependants marked, when asked."""
    item = _spec(project).item(item_id)
    with project.editing() as state:
        st = state.items[item_id]
        _check_version(st.versions, item_id, version)
        st.current = version
        if st.status in ("waiting", "failed", "todo"):
            st.status, st.candidates = settled_status(item), []
    project.log("version_used", item_id, f"{item_id}: v{version} is current", version=version)
    project.changed(item_id)
    return mark_dependants(project, item_id) if with_dependants else []


def provide(
    project: Project, item_id: str, data: bytes, name: str, *, with_dependants: bool = False
) -> list[str]:
    """Replace the item's image with a file: a new `provided` version, the item unmarked."""
    item = _spec(project).item(item_id)
    upload = project.work_file(item_id).with_name(".upload")
    upload.write_bytes(data)
    work = to_png(upload, project.work_file(item_id))
    upload.unlink()
    with project.editing() as state:
        project.add_version(
            state, item_id, work, source="provided", original=name, sha256=hashlib.sha256(data).hexdigest()
        )
        st = state.items[item_id]
        st.status, st.marked, st.error = settled_status(item), False, None
    project.log("file_replaced", item_id, f"{item_id}: replaced with {name}")
    project.changed(item_id)
    return mark_dependants(project, item_id) if with_dependants else []


def _spec(project: Project) -> ProjectSpec:
    """The project's spec, after giving any item added to the file by hand its state (design §5.4)."""
    project.sync()
    return project.spec()


def _mark(project: Project, spec: ProjectSpec, about: str, ids: list[str]) -> list[str]:
    ids = [i for i in ids if not spec.item(i).file]
    if ids:
        with project.editing() as state:
            for i in ids:
                state.items[i].marked, state.items[i].run_prompt = True, None
        project.log("marked", about, f"marked {', '.join(ids)}")
        project.changed(*ids)
    return ids


def _check_version(versions: list[Version], item_id: str, n: int) -> None:
    if not any(v.n == n for v in versions):
        raise NotFound(f"{item_id} has no version {n}: its versions are {[v.n for v in versions]}")
