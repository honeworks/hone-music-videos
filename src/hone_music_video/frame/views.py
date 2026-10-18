"""What the dashboard and the CLI show (design §12.3): items, projects, runs and models as plain records.

Hone Frame: ported from `src/hone_frame/views.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

from datetime import UTC, datetime
from statistics import median
from typing import Any
from urllib.parse import quote

from pydantic import BaseModel, Field

from hone_music_video.frame.actions import dependants
from hone_music_video.frame.errors import NotFound
from hone_music_video.frame.estimates import Key, done_at, item_estimate, measured, run_estimate
from hone_music_video.frame.making import made_with
from hone_music_video.frame.ports import ModelInfo, license_warning
from hone_music_video.frame.project import Project
from hone_music_video.frame.project_file import ItemSpec, ProjectSpec
from hone_music_video.frame.records import ItemState, ProjectState, RunStatus, Status, Version


class VersionView(BaseModel):
    n: int
    url: str
    thumb: str
    at: str
    model: str | None
    seed: int | None
    elapsed_s: float | None
    made_from: dict[str, int]
    source: str
    prompt: str | None
    negative: str | None
    refs: list[str]
    inputs: dict[str, Any]


class ItemView(BaseModel):
    """An item as the dashboard shows it. `model`, `size`, `seed`, `hold`, `count`, `negative` and
    `inputs` are the item's own values in the file (None when it leaves them to `[defaults]`);
    `effective` holds what is used (`effective["prompts"]`: the prompt of each image, in order)."""

    id: str
    group: str
    subject: str
    name: str
    kind: str
    status: Status
    marked: bool
    hold: bool | None
    count: int | None
    model: str | None
    size: str | None
    seed: int | None
    refs: list[str]
    prompt: str
    prompts: list[str] | None  # one per image, when the item sets `prompts` (D-076)
    negative: str | None
    inputs: dict[str, Any] | None
    file: str | None
    thumb: str | None  # the current version's thumbnail, or None
    layout: str | None
    images: list[str] | None
    labels: list[str] | None
    effective: dict[str, Any]
    versions: list[VersionView]
    current: int | None
    candidates: list[int]
    run_prompt: int | None  # the prompt (from 0) asked for by "Run this prompt", until it is made (0033)
    changed_since_made: bool
    older_refs: list[str]
    dependants: list[str]
    estimate: dict[str, float] | None
    license_warning: str | None
    error: str | None


class RunView(BaseModel):
    project: str
    status: RunStatus
    current: dict[str, Any] | None
    made: list[str]
    remaining: list[str]
    estimate: dict[str, Any] | None
    done_at: str | None
    reason: str
    item: str | None = None  # the item the run ended on: the one it waits for, or that failed


class ProjectView(BaseModel):
    id: str
    name: str
    style: str
    notes: str
    defaults: dict[str, Any]
    items: list[ItemView]
    run: RunView
    warnings: list[str]


class ProjectSummary(BaseModel):
    id: str
    name: str
    counts: dict[str, int]
    run_status: RunStatus


class ModelView(BaseModel):
    id: str
    local: bool
    installed: str
    max_references: int | None
    sizes: list[str]
    inputs: list[str] | None  # None: not known until the model is installed
    pose: str | None
    license: str | None
    commercial_use: bool | None
    median_s: float | None
    warning: str | None = Field(default=None)


def item_view(project: Project, item_id: str) -> ItemView:
    spec, state = project.spec(), project.state()
    return _item(project, spec, state, spec.item(item_id), measured(project.ws.root))


def _item(
    project: Project,
    spec: ProjectSpec,
    state: ProjectState,
    item: ItemSpec,
    durations: dict[Key, list[float]],
) -> ItemView:
    st = state.items.get(item.id) or ItemState()
    base = _base(project, item.id)
    current = st.version(st.current) if st.current else None
    versions = [_version(v, base) for v in st.versions]
    older = [r for r, v in (current.made_from if current else {}).items() if _current(state, r) != v]
    changed = bool(current and current.made_with and current.made_with != made_with(project.id, item))
    own, sheet = item.own, item.kind == "sheet"
    return ItemView(
        id=item.id, group=item.group, subject=item.subject, name=item.name, kind=item.kind,
        status=st.status, marked=st.marked, hold=own.get("hold"), count=own.get("count"),
        model=own.get("model"), size=own.get("size"), seed=own.get("seed"), refs=item.refs,
        prompt=item.prompt, prompts=item.prompts, negative=own.get("negative"), inputs=own.get("inputs"),
        file=item.file,
        thumb=next((v.thumb for v in versions if v.n == st.current), None),
        layout=own.get("layout", "contact-grid") if sheet else None,
        images=item.refs if sheet else None, labels=own.get("labels", []) if sheet else None,
        effective={
            "model": item.model, "size": item.size, "seed": None if sheet else item.seed(project.id),
            "hold": item.hold, "count": item.count, "per_run": item.per_run, "negative": item.negative,
            "inputs": item.inputs,
            "prompts": None if sheet else [item.prompt_for(k) for k in range(item.count)],
        },
        versions=versions,
        current=st.current,
        candidates=st.candidates if st.status == "waiting" else [],
        run_prompt=st.run_prompt if st.marked else None,
        changed_since_made=changed,
        older_refs=older,
        dependants=dependants(spec, item.id),
        estimate=item_estimate(item, durations),
        license_warning=_warning(project, item.model) if item.kind == "image" and not item.file else None,
        error=st.error,
    )  # fmt: skip


def _version(v: Version, base: str) -> VersionView:
    return VersionView(
        n=v.n, url=base % ("items", v.n, "png"), thumb=base % ("thumbs", v.n, "webp"), at=v.at,
        model=v.model, seed=v.seed, elapsed_s=v.elapsed_s, made_from=v.made_from, source=v.source,
        prompt=v.prompt, negative=v.negative, refs=v.refs, inputs=v.inputs,
    )  # fmt: skip


def _current(state: ProjectState, item_id: str) -> int | None:
    st = state.items.get(item_id)
    return st.current if st else None


def _warning(project: Project, model: str | None) -> str | None:
    try:
        return license_warning(project.ws.models.info(str(model)))
    except NotFound:
        return None


def run_view(project: Project) -> RunView:
    record = project.run()
    remaining = project.marked()
    estimate = run_estimate(remaining, measured(project.ws.root))
    current = None
    if record.current and record.current_started_at:
        started = datetime.fromisoformat(record.current_started_at.replace("Z", "+00:00"))
        elapsed = round((datetime.now(UTC) - started).total_seconds(), 1)
        current = {"item": record.current, "started_at": record.current_started_at, "elapsed_s": elapsed}
    return RunView(
        project=project.id,
        status=record.status,
        current=current,
        made=record.made,
        remaining=[i.id for i in remaining if i.id != record.current],
        estimate=estimate,
        done_at=done_at(estimate),
        reason=record.reason,
        item=record.item,
    )


def project_view(project: Project) -> ProjectView:
    spec, state, durations = project.spec(), project.state(), measured(project.ws.root)
    return ProjectView(
        id=project.id,
        name=spec.name,
        style=spec.style,
        notes=spec.notes,
        defaults=spec.defaults,
        items=[_item(project, spec, state, item, durations) for item in spec.items],
        run=run_view(project),
        warnings=licence_warnings(project, project.marked()),
    )


def licence_warnings(project: Project, items: list[ItemSpec]) -> list[str]:
    """One warning per research-licence model that a marked item uses (design §7.3)."""
    models = dict.fromkeys(i.model for i in items if i.kind == "image" and not i.file and i.model)
    return [w for m in models if (w := _warning(project, m)) is not None]


def project_summary(project: Project) -> ProjectSummary:
    state = project.state()
    counts: dict[str, int] = dict.fromkeys(("done", "waiting", "marked", "failed", "todo", "provided"), 0)
    for st in state.items.values():
        counts["marked"] += st.marked
        if st.status in counts:
            counts[st.status] += 1
    return ProjectSummary(id=project.id, name=state.name, counts=counts, run_status=project.run().status)


def model_view(info: ModelInfo, durations: dict[Key, list[float]]) -> ModelView:
    values = [s for (model, _), found in durations.items() if model == info.id for s in found]
    return ModelView(
        id=info.id,
        local=info.local,
        installed=info.installed,
        max_references=info.max_references,
        sizes=list(info.sizes),
        inputs=None if info.inputs is None else [i for i in info.inputs if i != "references"],
        pose=info.pose,
        license=info.license,
        commercial_use=info.commercial_use,
        median_s=round(median(values), 1) if values else None,
        warning=license_warning(info),
    )


def _base(project: Project, item_id: str) -> str:
    """The URL of an item's images: `% (folder, version, extension)`. Hone Frame: `/files/<project>/...`
    of its own server; here the video project's files, the frame workspace being `<video project>/frame`
    (0027), served by this library's dashboard (thumbnails made there on first use)."""
    video = quote(project.ws.root.parent.name)
    return f"/files/{video}/frame/projects/{quote(project.id)}/%s/{quote(item_id, safe='')}/v%03d.%s"
