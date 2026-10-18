"""Validation of a project file (design §5.3): every problem names the item and says what to do.

Hone Frame: ported from `src/hone_frame/checks.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from hone_music_video.frame._files import readable_image
from hone_music_video.frame.errors import InvalidRequest, NotFound, Problem
from hone_music_video.frame.ports import Models, license_warning
from hone_music_video.frame.project_file import (
    DEFAULT_FIELDS,
    DEMO_FIELDS,
    IMAGE_FIELDS,
    MANNEQUINS_REMOVED,
    PROJECT_FIELDS,
    SHEET_FIELDS,
    DemoFields,
    Format,
    ImageFields,
    ItemSpec,
    ProjectSpec,
    SheetFields,
    parse_text,
    read_items,
)
from hone_music_video.frame.sheets import LAYOUTS

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def load(text: str, fmt: Format, *, models: Models, files_root: Path) -> ProjectSpec:
    """Parse and check a project file; `InvalidRequest` lists every problem. `file` fields are read
    relative to `files_root`."""
    data = parse_text(text, fmt)
    items, problems = read_items(data, text, fmt)
    project: dict[str, Any] = data.get("project") or {}
    defaults: dict[str, Any] = data.get("defaults") or {}
    problems += _tables(project, defaults)
    if "demo" in data:
        problems += _demo(data["demo"], defaults)
    warnings: list[str] = []
    for item, above in zip(items, _above(items), strict=True):
        if item.group == "demo":  # its table is checked once; what its model says, once for all (D-077)
            found = [Problem("demo", p.message) for p in _model(item, models, warnings)]
            problems += [p for p in found if p not in problems]
            continue
        problems += _item(item, above)
        if item.kind == "image":
            problems += _model(item, models, warnings)
            problems += _file(item, files_root)
    if problems:
        raise InvalidRequest("the project file was not accepted", problems)
    return ProjectSpec(
        name=str(project["name"]),
        style=str(project.get("style") or ""),
        notes=str(project.get("notes") or ""),
        defaults=defaults,
        items=items,
        format=fmt,
        warnings=sorted(set(warnings)),
    )


def _above(items: list[ItemSpec]) -> list[set[str]]:
    """For each item, the ids written above it."""
    return [{i.id for i in items[:n]} for n in range(len(items))]


def _item(item: ItemSpec, above: set[str]) -> list[Problem]:
    problems = _fields(item) + _refs(item, above)
    if not all(NAME.match(part) for part in item.path[1:]):
        problems.append(Problem(item.id, "names use letters, digits, '-' and '_' only: rename it"))
    if item.id in above:
        problems.append(Problem(item.id, "this id is used twice: rename one of the items"))
    return problems


def _tables(project: dict[str, Any], defaults: dict[str, Any]) -> list[Problem]:
    problems = [
        Problem("project", f"unknown field {k!r}: [project] takes {', '.join(PROJECT_FIELDS)}")
        for k in project
        if k not in PROJECT_FIELDS
    ]
    problems += [
        Problem("defaults", f"unknown field {k!r}: [defaults] takes {', '.join(DEFAULT_FIELDS)}")
        for k in defaults
        if k not in DEFAULT_FIELDS
    ]
    if not str(project.get("name") or "").strip():
        problems.append(Problem("project", 'no name: add name = "..." under [project]'))
    return problems


def _demo(demo: Any, defaults: dict[str, Any]) -> list[Problem]:
    """`[demo]` (D-077): prompts, no references, and a model."""
    if not isinstance(demo, dict):
        return [Problem("demo", "expected a table: write [demo] with prompts = [...]")]
    table: dict[str, Any] = demo  # pyright: ignore[reportUnknownVariableType]
    problems = [
        Problem("demo", f"a demo has no references: remove {k} from [demo]")
        for k in ("refs", "file")
        if k in table
    ]
    try:
        DemoFields.model_validate({k: v for k, v in table.items() if k not in ("refs", "file")})
    except ValidationError as exc:
        problems += [_demo_problem(e) for e in exc.errors()]
    prompts: list[Any] = table["prompts"] if isinstance(table.get("prompts"), list) else []
    problems += [
        Problem("demo", f"prompt {k} is empty: write it, or remove it from prompts")
        for k, p in enumerate(prompts, 1)
        if isinstance(p, str) and not p.strip()
    ]
    if not table.get("model") and not defaults.get("model"):
        problems.append(Problem("demo", "no model: set model under [demo] or [defaults]"))
    return problems


def _demo_problem(error: Any) -> Problem:
    name = ".".join(str(part) for part in error["loc"])
    if error["type"] == "extra_forbidden":
        return Problem("demo", f"unknown field {name!r}: [demo] takes {', '.join(DEMO_FIELDS)}")
    if name == "prompts" and error["type"] == "missing":
        return Problem("demo", 'no prompts: write prompts = ["...", ...] under [demo], or remove [demo]')
    if name == "prompts" and error["type"] == "too_short":
        return Problem("demo", "prompts is empty: give at least one prompt, or remove [demo]")
    return Problem("demo", f"{name}: {error['msg']}")


def _fields(item: ItemSpec) -> list[Problem]:
    shape, allowed = (SheetFields, SHEET_FIELDS) if item.kind == "sheet" else (ImageFields, IMAGE_FIELDS)
    try:
        shape.model_validate(item.fields)
    except ValidationError as exc:
        return [_problem(item.id, e, allowed) for e in exc.errors()]
    if item.kind == "sheet":
        return _sheet(item)
    if "prompts" in item.fields:
        return _prompts(item)
    if not item.prompt and not item.file:
        return [Problem(item.id, 'no prompt: write prompt = "...", prompts = [...], or give file = "..."')]
    if not item.file and not item.model:
        return [Problem(item.id, "no model: set model on the item or under [defaults]")]
    return []


def _prompts(item: ItemSpec) -> list[Problem]:
    """`prompts` (D-076): not with `prompt`, no empty one, and an own `count` only when it matches."""
    prompts = item.prompts or []
    problems: list[Problem] = []
    if "prompt" in item.fields:
        problems.append(Problem(item.id, "set prompt or prompts, not both: remove one of them"))
    count = item.own.get("count")
    if count is not None and count != len(prompts):
        problems.append(
            Problem(
                item.id,
                f"count = {count}, but prompts has {len(prompts)}: one image is made per prompt; "
                "remove count or make it match",
            )
        )
    problems += [
        Problem(item.id, f"prompt {k} is empty: write it, or remove it from prompts")
        for k, p in enumerate(prompts, 1)
        if not p.strip()
    ]
    if not item.file and not item.model:
        problems.append(Problem(item.id, "no model: set model on the item or under [defaults]"))
    return problems


def _sheet(item: ItemSpec) -> list[Problem]:
    problems: list[Problem] = []
    if item.fields.get("layout", "contact-grid") not in LAYOUTS:
        problems.append(Problem(item.id, f"unknown layout: use one of {', '.join(LAYOUTS)}"))
    if not item.refs:
        problems.append(Problem(item.id, "a sheet needs images = [item ids]"))
    labels: list[Any] = item.fields.get("labels") or []
    if labels and len(labels) != len(item.refs):
        problems.append(Problem(item.id, f"{len(labels)} labels for {len(item.refs)} images: give one each"))
    return problems


def _problem(item_id: str, error: Any, allowed: tuple[str, ...]) -> Problem:
    name = ".".join(str(part) for part in error["loc"])
    if error["type"] == "extra_forbidden":
        return Problem(item_id, f"unknown field {name!r}: the fields are {', '.join(allowed)}")
    if name == "prompts" and error["type"] == "too_short":
        return Problem(item_id, 'prompts is empty: give at least one prompt, or write prompt = "..."')
    return Problem(item_id, f"{name}: {error['msg']}")


def _refs(item: ItemSpec, above: set[str]) -> list[Problem]:
    problems: list[Problem] = []
    for ref in item.refs:
        if ref.startswith("demo."):
            problems.append(
                Problem(item.id, f"refers to {ref!r}: demo pictures are a preview and cannot be references")
            )
            continue
        if ref in above:
            continue
        if ref.startswith("mannequin:"):
            problems.append(Problem(item.id, f"refers to {ref!r}: {MANNEQUINS_REMOVED}"))
        elif ref == item.id:
            problems.append(Problem(item.id, "an item cannot refer to itself"))
        else:
            problems.append(
                Problem(
                    item.id, f"refers to {ref!r}, which is not above it: refs point to items written above"
                )
            )
    return problems


def _model(item: ItemSpec, models: Models, warnings: list[str]) -> list[Problem]:
    if item.file or not item.model:
        return []
    try:
        info = models.info(item.model)
    except NotFound:
        return [Problem(item.id, f"unknown model {item.model!r}: the dashboard's Models page lists them")]
    problems: list[Problem] = []
    if info.kind != "image":
        problems.append(Problem(item.id, f"{item.model} is a {info.kind} model: choose an image model"))
    if not info.local:
        problems.append(Problem(item.id, f"{item.model} is not a local model: choose a local one"))
    refs = len(item.refs)
    if refs and info.max_references == 0:
        problems.append(Problem(item.id, f"{item.model} takes no references: remove refs or change model"))
    elif info.max_references and refs > info.max_references:
        problems.append(
            Problem(item.id, f"{refs} refs, but {item.model} takes at most {info.max_references}")
        )
    if item.size and info.sizes and item.size not in info.sizes:
        problems.append(Problem(item.id, f"size {item.size}: {item.model} makes {', '.join(info.sizes)}"))
    if info.inputs is None:  # not installed: hone-models cannot say; generate refuses at run time (D-067)
        warnings.append(f"{item.model}: install it to check its inputs; they are not known yet")
    else:
        problems += _inputs(item, info.inputs, info.prompt_inputs)
    if (warning := license_warning(info)) is not None:
        warnings.append(warning)
    return problems


def _inputs(item: ItemSpec, inputs: tuple[str, ...], written: tuple[str, ...] = ()) -> list[Problem]:
    """Every input sent must be one the model takes: nothing is dropped on the way (design §7.2). An
    input hone-models writes into the prompt is refused: the prompt is sent as written (D-073)."""
    in_prompt = [Problem(item.id, _in_prompt(item, k)) for k in item.inputs if k in written]
    if in_prompt:
        return in_prompt
    takes = [i for i in inputs if i != "references" and i not in written]
    sent = {"negative": item.negative, "size": item.size} | item.inputs
    return [
        Problem(item.id, _not_taken(item, k, takes))
        for k, v in sent.items()
        if v is not None and k not in takes
    ]


def _in_prompt(item: ItemSpec, key: str) -> str:
    return (
        f"{key} is written into the prompt by hone-models, so the prompt would not be sent as written: "
        f"remove {key} from inputs and write the words you want into the prompt yourself "
        f"(see {item.model}'s guide)"
    )


def _not_taken(item: ItemSpec, key: str, takes: list[str]) -> str:
    own_inputs: dict[str, Any] = item.own.get("inputs") or {}
    where = "" if key in item.own or key in own_inputs else " under [defaults]"
    if key == "negative":
        return f"{item.model} takes no negative prompt: remove negative{where} or choose another model"
    return (
        f"{key} is not an input of {item.model}: it takes {', '.join(takes) or 'none'}; remove {key}{where} "
        "or choose another model"
    )


def _file(item: ItemSpec, files_root: Path) -> list[Problem]:
    if not item.file:
        return []
    path = files_root / item.file
    if not path.is_file():
        return [Problem(item.id, f"file {item.file!r} does not exist (read from {files_root})")]
    if not readable_image(path):
        return [
            Problem(item.id, f"file {item.file!r} is not an image Pillow can read: give a PNG, JPEG or WebP")
        ]
    return []
