"""The prompt-writing guide (change 0008 §6): one Markdown document for the person who writes the prompts.

    from hone_models import guide as model_guide
    text = build_guide(["z-image-turbo", "qwen-image-edit-2511"], guide_of=model_guide)

It has three parts: how a project file works (`data/guide/project-file.md`); per stage the stage's text
(`data/guide/<stage>.md`) followed by each chosen model's notes for the situations that stage needs; and
per model its summary, prompt form, licence (a research-licence warning), sizes, references, pose support
and the measured time on this machine. Nothing here is sent to a model.

Hone Frame: ported from `src/hone_frame/guide.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import statistics
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from . import estimates

if TYPE_CHECKING:
    from .workspace import Workspace

GUIDE_DATA = Path(__file__).parent.parent / "data" / "frame_guide"  # Hone Frame: `data/guide/`

STAGES = ("hero", "views", "faces", "poses", "objects", "places", "scenes", "sheets")
STAGE_TITLES = {
    "hero": "Hero",
    "views": "Views and turnarounds",
    "faces": "Faces and expressions",
    "poses": "Poses",
    "objects": "Objects",
    "places": "Places",
    "scenes": "Scenes",
    "sheets": "Sheets",
}
# hone-models' situations (its change 0020) each stage shows; `general` is shown with the model itself.
STAGE_SITUATIONS: dict[str, tuple[str, ...]] = {
    "hero": ("people", "faces", "hands", "sizes"),
    "views": ("people", "references", "faces"),
    "faces": ("faces", "hands"),
    "poses": ("poses", "references", "hands", "people"),
    "objects": ("objects", "references", "text"),
    "places": ("places", "references", "sizes"),
    "scenes": ("scenes", "people", "references", "places"),
    "sheets": (),  # composed by Pillow: no model
}
POSE_SUPPORT = {
    "none": "none: pose pictures are not useful with this model; make poses with one that takes references",
    "reference": (
        "as a reference picture: a pose picture of your own (an item with `file`) goes into `refs` like any "
        'picture; say which image it is ("in exactly the body pose of the figure in image 2"). '
        "Less exact than a control"
    ),
    "control": "as a control: a pose skeleton is a control input of its own (see the model's inputs)",
}


class NoteLike(Protocol):
    """One of a model's guide notes (hone-models' `GuideNote`)."""

    @property
    def about(self) -> str: ...
    @property
    def says(self) -> str: ...
    @property
    def source(self) -> str | None: ...
    @property
    def checked(self) -> date | None: ...


class ModelGuideLike(Protocol):
    """What the guide reads from hone-models' `ModelGuide` (with its change 0020: `notes_about`, `pose`)."""

    @property
    def id(self) -> str: ...
    @property
    def summary(self) -> str | None: ...
    @property
    def prompt(self) -> str | None: ...
    @property
    def license(self) -> str | None: ...
    @property
    def commercial_use(self) -> bool | None: ...
    @property
    def sizes(self) -> Sequence[str] | None: ...
    @property
    def max_references(self) -> int | None: ...
    @property
    def pose(self) -> str | None: ...
    def notes_about(self, about: str) -> Sequence[NoteLike]: ...


def stage_text(stage: str) -> str:
    """The written text of one stage (`data/guide/<stage>.md`)."""
    return (GUIDE_DATA / f"{stage}.md").read_text(encoding="utf-8").strip()


def build_guide(
    model_ids: Sequence[str],
    *,
    guide_of: Callable[[str], ModelGuideLike],
    measured_s: Mapping[tuple[str, str], float] | None = None,
    project_name: str | None = None,
) -> str:
    """The whole guide for these models, as Markdown. `guide_of` gives a model's guide (hone-models'
    `guide`); `measured_s` is the median seconds per image by `(model, size)` on this machine."""
    guides = [guide_of(model_id) for model_id in dict.fromkeys(model_ids)]
    parts = [
        _title(guides, project_name),
        "## 1. How a project file works",
        (GUIDE_DATA / "project-file.md").read_text(encoding="utf-8").strip(),
        "## 2. Stages",
        *(_stage_section(stage, guides) for stage in STAGES),
        "## 3. Models",
        *(_model_section(g, measured_s or {}) for g in guides),
        *([] if guides else ["No model chosen: build the guide with `--models a,b` to see each model here."]),
    ]
    return "\n\n".join(parts) + "\n"


def guide_for(ws: Workspace, model_ids: Sequence[str], project_id: str | None = None) -> str:
    """The guide for these models, or, when none are given, for the models a project's items use; with the
    measured time per image on this machine (the CLI, the dashboard and a new project's `GUIDE.md`)."""
    ids, name = list(model_ids), None
    if project_id:
        spec = ws.project(project_id).spec()
        name = spec.name
        ids = ids or [str(i.model) for i in spec.items if i.kind == "image" and not i.file and i.model]
    medians = {k: statistics.median(v) for k, v in estimates.measured(ws.root).items() if v}
    return build_guide(ids, guide_of=ws.models.guide, measured_s=medians, project_name=name)


def _title(guides: Sequence[ModelGuideLike], project_name: str | None) -> str:
    head = f"# Prompt guide: {project_name}" if project_name else "# Prompt guide"
    lines = [head, ""]
    lines.append(
        "Hone Frame sends every prompt exactly as you write it. This guide is your help: how the file works, "
        "what each stage needs, what each model can and cannot do."
    )
    if guides:
        lines += ["", "Models in this guide: " + ", ".join(f"`{g.id}`" for g in guides) + "."]
    lines += [f"\n{_licence_warning(g)}" for g in guides if g.commercial_use is False]
    return "\n".join(lines)


def _stage_section(stage: str, guides: Sequence[ModelGuideLike]) -> str:
    text = stage_text(stage)
    situations = STAGE_SITUATIONS[stage]
    if not guides or not situations:
        return text
    lines = [f"#### What the models say ({', '.join(situations)})", ""]
    for g in guides:
        lines += _stage_notes(g, situations)
    return text + "\n\n" + "\n".join(lines).rstrip()


def _stage_notes(g: ModelGuideLike, situations: Sequence[str]) -> list[str]:
    found = [(about, note) for about in situations for note in g.notes_about(about)]
    if not found:
        return [f"- `{g.id}`: no notes for {', '.join(situations)} yet."]
    lines = [f"- `{g.id}`:"]
    lines += [f"  - {about}: {_note_text(note)}" for about, note in found]
    return lines


def _note_text(note: NoteLike) -> str:
    evidence = [x for x in (note.source, note.checked and f"checked {note.checked}") if x]
    return note.says + (f" ({', '.join(evidence)})" if evidence else "")


def _model_section(g: ModelGuideLike, measured: Mapping[tuple[str, str], float]) -> str:
    lines = [f"### `{g.id}`", ""]
    if g.summary:
        lines += [g.summary, ""]
    if g.commercial_use is False:
        lines += [_licence_warning(g), ""]
    lines += [
        f"- Prompt form: {g.prompt or 'not stated by hone-models'}",
        f"- Licence: {_licence_text(g)}",
        f"- Sizes: {', '.join(g.sizes) if g.sizes else 'not listed by hone-models'}",
        f"- References: {_references_text(g.max_references)}",
        f"- Pose support: {POSE_SUPPORT.get(g.pose or '', 'not stated by hone-models')}",
        f"- `inputs` it takes: {_inputs_text(g)}",
        f"- Time on this machine: {_measured_text(g.id, measured)}",
    ]
    general = g.notes_about("general")
    if general:
        lines += ["", "In general:", *(f"- {_note_text(note)}" for note in general)]
    return "\n".join(lines)


# Written by an item's own fields, so never under `inputs`; a "prompt" input would change the prompt.
FIELD_INPUTS = ("prompt", "negative", "size", "seed", "references")


def _inputs_text(g: ModelGuideLike) -> str:
    """The model's own inputs an item may set under `inputs`, with hone-models' note on each."""
    found: Mapping[str, Any] = getattr(g, "inputs", None) or {}
    usable = [
        f"`{name}` ({getattr(spec, 'note', None) or 'no note'})"
        for name, spec in found.items()
        if name not in FIELD_INPUTS and getattr(spec, "origin", "own") != "prompt"
    ]
    if not usable:
        return "none beyond the item's fields"
    return "; ".join(usable) + ". Write them as `inputs = { name = value }`; leave them out for the defaults"


def _licence_warning(g: ModelGuideLike) -> str:
    return (
        f"> **RESEARCH-LICENCE WARNING: `{g.id}`** is under {g.license or 'a research licence'}: commercial "
        "use is not allowed. Images it makes may not be used in commercial work; choose another model for "
        "anything you will sell or publish commercially."
    )


def _licence_text(g: ModelGuideLike) -> str:
    use = {
        True: "commercial use allowed",
        False: "commercial use NOT allowed (research licence)",
        None: "commercial use not stated: read the licence before commercial use",
    }[g.commercial_use]
    return f"{g.license or 'not stated'}; {use}"


def _references_text(most: int | None) -> str:
    if most is None:
        return "not stated by hone-models; try one reference first"
    if most == 0:
        return "no reference pictures: text only, so `refs` must be empty; describe everything in words"
    return (
        f"up to {most} reference pictures. They are sent in the order of `refs`: the first is image 1, the "
        'second image 2; name them that way in the prompt ("the woman from image 1")'
    )


def _measured_text(model_id: str, measured: Mapping[tuple[str, str], float]) -> str:
    found = sorted((size, s) for (model, size), s in measured.items() if model == model_id)
    if not found:
        return "no measurement on this machine yet"
    return (
        "; ".join(f"{size or 'default size'}: about {s:.0f} s" for size, s in found) + " per image (median)"
    )
