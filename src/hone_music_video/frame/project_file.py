"""The project file (design §5): the owner's TOML or JSON, read into items in file order.

Nothing here writes a prompt: an item's `prompt` and `negative` are kept exactly as written, and
`[project]` `style` / `notes` are reference only (never sent to a model).

Hone Frame: ported from `src/hone_frame/project_file.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from hone_music_video.frame.errors import InvalidRequest, NotFound, Problem
from hone_music_video.frame.sheets import SheetLayout

Format = Literal["toml", "json"]
GROUPS = ("characters", "objects", "places", "scenes", "sheets")


class ImageFields(BaseModel):
    """The fields of an image item, as stored (docs/project-file.md)."""

    model_config = ConfigDict(extra="forbid")

    prompt: str | None = None
    prompts: list[str] | None = Field(default=None, min_length=1, max_length=16)  # one image each (D-076)
    negative: str | None = None
    model: str | None = None
    size: str | None = Field(default=None, pattern=r"^\d+x\d+$")
    seed: int | None = Field(default=None, ge=0)
    count: int = Field(default=1, ge=1, le=16)
    refs: list[str] = Field(default_factory=list[str])
    file: str | None = None
    hold: bool = False
    inputs: dict[str, Any] = Field(default_factory=dict[str, Any])


class SheetFields(SheetLayout):
    """The fields of a sheet item: the layout's, and `hold`. A sheet's name is its table's name."""

    hold: bool = False


class DemoFields(BaseModel):
    """The fields of `[demo]` (D-077): reference-free prompts made first, one image each."""

    model_config = ConfigDict(extra="forbid")

    prompts: list[str] = Field(min_length=1, max_length=16)
    model: str | None = None
    size: str | None = Field(default=None, pattern=r"^\d+x\d+$")
    seed: int | None = Field(default=None, ge=0)
    negative: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict[str, Any])
    hold: bool = False


IMAGE_FIELDS = tuple(ImageFields.model_fields)
DEMO_FIELDS = tuple(DemoFields.model_fields)
SHEET_FIELDS = tuple(SheetFields.model_fields)
DEFAULT_FIELDS = ("model", "size", "hold", "negative", "count", "inputs")
PROJECT_FIELDS = ("name", "style", "notes")
MANNEQUINS_REMOVED = (  # D-072
    'mannequins were removed; give a pose picture as an item with `file = "..."` '
    "and refer to it like any item"
)
HEADER = re.compile(r"^\s*\[\s*([^\[\]]+?)\s*\]\s*(?:#.*)?$", re.M)
KEY_PART = re.compile(r'"[^"]*"|\'[^\']*\'|[^.\s]+')


@dataclass(frozen=True)
class ItemSpec:
    """One item: `own` is its table as the file writes it, `fields` the same with `[defaults]` applied.
    `path` is its table in the file."""

    id: str
    group: str
    subject: str
    name: str
    path: tuple[str, ...]
    kind: Literal["image", "sheet"]
    fields: dict[str, Any] = field(default_factory=dict[str, Any])
    own: dict[str, Any] = field(default_factory=dict[str, Any])

    @property
    def prompt(self) -> str:
        """The item's `prompt` ("" when it sets `prompts` instead)."""
        return str(self.fields.get("prompt") or "")

    @property
    def prompts(self) -> list[str] | None:
        """The item's `prompts`, one per image (D-076), or None when it sets `prompt`."""
        value: Any = self.fields.get("prompts")
        if not isinstance(value, list):
            return None
        found: list[Any] = value  # pyright: ignore[reportUnknownVariableType]
        return [str(p) for p in found]

    def prompt_for(self, k: int) -> str:
        """The prompt image `k` (from 0) is made with: `prompts[k]`, else `prompt`."""
        prompts = self.prompts
        return prompts[k] if prompts else self.prompt

    @property
    def negative(self) -> str | None:
        return self.fields.get("negative")

    @property
    def model(self) -> str | None:
        return self.fields.get("model")

    @property
    def size(self) -> str | None:
        return self.fields.get("size")

    @property
    def count(self) -> int:
        """How many images: one per prompt of `prompts`, else `count` (D-076)."""
        prompts = self.prompts
        return len(prompts) if prompts else int(self.fields.get("count") or 1)

    @property
    def per_run(self) -> int:
        """How many images one make makes: one prompt at a time for `prompts`, else `count`. Hone Frame:
        it makes one image per prompt (D-076); hone-music-video 0033 makes one."""
        return 1 if self.prompts else self.count

    @property
    def refs(self) -> list[str]:
        """The images this item is made from, in order: `refs`, or a sheet's `images`."""
        value: Any = self.fields.get("images" if self.kind == "sheet" else "refs")
        if not isinstance(value, list):
            return []
        found: list[Any] = value  # pyright: ignore[reportUnknownVariableType]
        return [str(r) for r in found]

    @property
    def file(self) -> str | None:
        return self.fields.get("file")

    @property
    def hold(self) -> bool:
        return bool(self.fields.get("hold"))

    @property
    def inputs(self) -> dict[str, Any]:
        return dict(self.fields.get("inputs") or {})

    def seed(self, project_id: str) -> int:
        """`seed`, else one derived from the project and item ids (decisions D-046)."""
        if self.fields.get("seed") is not None:
            return int(self.fields["seed"])
        return default_seed(project_id, self.id)


@dataclass(frozen=True)
class ProjectSpec:
    """A parsed project file: `items` in file order; `warnings` never refuse the file."""

    name: str
    style: str
    notes: str
    defaults: dict[str, Any]
    items: list[ItemSpec]
    format: Format
    warnings: list[str] = field(default_factory=list[str])

    def item(self, item_id: str) -> ItemSpec:
        for item in self.items:
            if item.id == item_id:
                return item
        raise NotFound(f"no item {item_id!r} in the project file; the items are listed by the dashboard")


def default_seed(project_id: str, item_id: str) -> int:
    return int(hashlib.sha256(f"{project_id}:{item_id}".encode()).hexdigest()[:8], 16)


def file_format(name: str) -> Format:
    """`toml` or `json` from a file name; anything else is refused."""
    if name.lower().endswith(".toml"):
        return "toml"
    if name.lower().endswith(".json"):
        return "json"
    raise InvalidRequest(f"{name}: a project file is a .toml or a .json file")


def parse_text(text: str, fmt: Format) -> dict[str, Any]:
    """The file's tables, or `InvalidRequest` naming the line that does not parse."""
    try:
        data: Any = tomllib.loads(text) if fmt == "toml" else json.loads(text)
    except (tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
        raise InvalidRequest("the project file does not parse", [Problem("file", f"{exc}")]) from exc
    if not isinstance(data, dict):
        raise InvalidRequest("the project file does not parse", [Problem("file", "expected tables")])
    return data  # pyright: ignore[reportUnknownVariableType]


def read_items(data: dict[str, Any], text: str, fmt: Format) -> tuple[list[ItemSpec], list[Problem]]:
    """Every item in file order, with the problems of the file's structure (unknown groups and so on)."""
    defaults: dict[str, Any] = data.get("defaults") or {}
    found: list[ItemSpec] = []
    problems: list[Problem] = []
    for group, tables in data.items():
        if group in ("project", "defaults", "demo"):
            continue
        if group == "mannequins":
            problems.append(Problem(group, MANNEQUINS_REMOVED))
            continue
        if group not in GROUPS or not isinstance(tables, dict):
            problems.append(Problem(group, f"unknown group: the groups are {', '.join(GROUPS)}"))
            continue
        for key, table in tables.items():  # pyright: ignore[reportUnknownVariableType]
            found += _group_items(group, str(key), table, defaults, problems)  # pyright: ignore[reportUnknownArgumentType]
    order = _header_order(text) if fmt == "toml" else {}
    end = len(order)  # an item in an inline table sits where its subject's table is
    found.sort(key=lambda i: order.get(i.path, order.get(i.path[:-1], end)))  # stable: JSON keeps its order
    return demo_items(data.get("demo"), defaults) + found, problems


def demo_items(demo: Any, defaults: dict[str, Any]) -> list[ItemSpec]:
    """`[demo]` as items `demo.1`, `demo.2`... (D-077), made before every other item: prompt k (from 0)
    with seed `seed + k`, and only the last one holds. Its `own` is the `[demo]` table, which all share."""
    if not isinstance(demo, dict):
        return []
    table: dict[str, Any] = demo  # pyright: ignore[reportUnknownVariableType]
    if not isinstance(table.get("prompts"), list):
        return []
    prompts: list[Any] = table["prompts"]
    own = {key: v for key, v in table.items() if key != "prompts"}
    base = {key: v for key, v in defaults.items() if key in DEFAULT_FIELDS and key != "count"} | own
    if "inputs" in defaults and "inputs" in own:
        base["inputs"] = dict(defaults["inputs"]) | dict(own["inputs"])
    seed = own.get("seed")
    items: list[ItemSpec] = []
    for k, prompt in enumerate(prompts):
        fields = base | {"prompt": prompt, "hold": bool(base.get("hold")) and k == len(prompts) - 1}
        if isinstance(seed, int):
            fields["seed"] = seed + k
        items.append(
            ItemSpec(
                f"demo.{k + 1}", "demo", "demo", "", ("demo",), "image", fields, own | {"prompt": prompt}
            )
        )
    return items


def _group_items(
    group: str, key: str, table: Any, defaults: dict[str, Any], problems: list[Problem]
) -> list[ItemSpec]:
    if not isinstance(table, dict):
        problems.append(Problem(f"{group}.{key}", "expected a table of fields"))
        return []
    fields: dict[str, Any] = table  # pyright: ignore[reportUnknownVariableType]
    if group == "sheets":
        return [ItemSpec(key, group, key, "", (group, key), "sheet", dict(fields), dict(fields))]
    if group == "scenes" and (set(fields) & set(IMAGE_FIELDS) or not fields):
        return [_image(key, (group, key), fields, defaults)]
    items: list[ItemSpec] = []
    for name, sub in fields.items():
        if not isinstance(sub, dict):
            what = "an item" if group == "scenes" else "a subject"
            problems.append(
                Problem(f"{key}.{name}", f"{name} = ... is not a table: {key} in {group} is {what}")
            )
            continue
        items.append(_image(f"{key}.{name}", (group, key, name), sub, defaults))  # pyright: ignore[reportUnknownArgumentType]
    return items


def _image(item_id: str, path: tuple[str, ...], fields: dict[str, Any], defaults: dict[str, Any]) -> ItemSpec:
    """An image item at `path` (group, subject[, name]) with the defaults it does not set itself."""
    merged = {k: v for k, v in defaults.items() if k in DEFAULT_FIELDS} | fields
    if "inputs" in defaults and "inputs" in fields:
        merged["inputs"] = dict(defaults["inputs"]) | dict(fields["inputs"])
    group, subject, *name = path
    return ItemSpec(item_id, group, subject, "".join(name), path, "image", merged, dict(fields))


def _header_order(text: str) -> dict[tuple[str, ...], int]:
    """Each table header's position in the text: the file order of the items (topmost first)."""
    order: dict[tuple[str, ...], int] = {}
    for match in HEADER.finditer(text):
        parts = tuple(p.strip("\"'") for p in KEY_PART.findall(match.group(1)))
        order.setdefault(parts, len(order))
    return order
