"""The sheet compositor (design §10): Pillow only, no model call, the same bytes for the same recipe.

Hone Frame: ported from `src/hone_frame/sheets.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from PIL import Image, ImageColor, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field

from hone_music_video.frame.errors import InvalidRequest

AUTO_CELL_WIDTH = 768
HEADING_SIZE, LABEL_SIZE, META_SIZE, NOTE_SIZE = 40, 22, 14, 18
SWATCH = 56
MODEL_SHEET = "character-model-sheet"  # full figures in a row, faces below, notes (sheets_model.py)
# Each layout's defaults: columns (0: one row, -1: square-ish), the cell aspect (w/h), labels numbered,
# and whether the first image fills a row of its own.
LAYOUTS: dict[str, dict[str, Any]] = {
    "four-view-turnaround": {"columns": 4, "cell": 0.6},
    "expression-grid": {"columns": 4, "cell": 1.0},
    "pose-grid": {"columns": 3, "cell": 0.6},
    "object-detail-board": {"columns": 3, "cell": 1.0, "feature_first": True},
    "environment-board": {"columns": 2, "cell": 1.5},
    "before-after": {"columns": 2, "cell": 1.0},
    "sequence-strip": {"columns": 0, "cell": 1.0, "numbered": True},
    "contact-grid": {"columns": -1, "cell": 1.0},
    MODEL_SHEET: {"columns": 5, "cell": 0.58},
}


class SheetLayout(BaseModel):
    """A sheet's fields as the project file writes them (`[sheets.<name>]`); `images` are item ids."""

    model_config = ConfigDict(extra="forbid")

    layout: str = "contact-grid"
    images: list[str] = Field(default_factory=list[str])
    labels: list[str] = Field(default_factory=list[str])
    columns: int | None = None
    page: str = "auto"
    fit: Literal["contain", "cover"] = "contain"
    background: str = "#FFFFFF"
    spacing: int = Field(default=24, ge=0, le=400)
    margin: int = Field(default=48, ge=0, le=800)
    heading: str | None = None
    palette: list[str] = Field(default_factory=list[str])
    notes: str = ""
    show_meta: bool = False


class SheetRecipe(SheetLayout):
    """What the compositor draws: the sheet's fields and its `name` (the heading unless `heading` is set)."""

    name: str = ""


@dataclass(frozen=True)
class Grid:
    columns: int
    rows: int
    cell_w: int
    cell_h: int
    feature: bool  # the first image fills a row of its own, twice as tall
    label_h: int
    numbered: bool


def compose(recipe: SheetRecipe, paths: list[Path]) -> Image.Image:
    """The sheet as a Pillow image; `paths` are the files of `recipe.images`, in order. Images are fitted
    into cells and never enlarged past 1:1."""
    _check(recipe, paths)
    if recipe.layout == MODEL_SHEET:
        from hone_music_video.frame.sheets_model import model_sheet  # noqa: PLC0415 - that module imports this one

        return model_sheet(recipe, paths)
    return _draw(recipe, paths, [_size(p) for p in paths])


def _check(recipe: SheetRecipe, paths: list[Path]) -> None:
    if not recipe.images or len(paths) != len(recipe.images):
        raise InvalidRequest(f"sheet {recipe.name}: give one file per image (at least one image)")
    if recipe.labels and len(recipe.labels) != len(recipe.images):
        raise InvalidRequest(
            f"{len(recipe.labels)} labels for {len(recipe.images)} images: give one per image"
        )
    if recipe.layout not in LAYOUTS:
        raise InvalidRequest(f"no sheet layout {recipe.layout!r}: use one of {', '.join(LAYOUTS)}")


def _draw(recipe: SheetRecipe, paths: list[Path], sizes: list[tuple[int, int]]) -> Image.Image:
    grid = _grid(recipe, sizes)
    ink = sheet_ink(recipe.background)
    heading = recipe.heading if recipe.heading is not None else recipe.name
    head_h = HEADING_SIZE + 32 if heading else 0
    grid_w = grid.columns * grid.cell_w + (grid.columns - 1) * recipe.spacing
    grid_h = _grid_height(grid, recipe.spacing)
    foot = footer_lines(recipe, grid_w)
    foot_h = (
        (SWATCH + 40 if recipe.palette else 0)
        + len(foot) * (NOTE_SIZE + 8)
        + (32 if recipe.palette or foot else 0)
    )
    width, height = _page(recipe, grid_w + 2 * recipe.margin, head_h + grid_h + foot_h + 2 * recipe.margin)
    sheet = Image.new("RGB", (width, height), sheet_colour(recipe.background))
    draw = ImageDraw.Draw(sheet)
    x0 = (width - grid_w) // 2
    y = recipe.margin
    if heading:
        draw.text((x0, y), heading, fill=ink, font=sheet_font(HEADING_SIZE))
        y += head_h
    _draw_cells(
        sheet,
        draw,
        recipe=recipe,
        cells=list(zip(paths, sizes, strict=True)),
        grid=grid,
        origin=(x0, y),
        ink=ink,
    )
    y += grid_h
    _draw_footer(draw, recipe, foot, (x0, y + 32), ink)
    return sheet


def compose_to(recipe: SheetRecipe, paths: list[Path], out: Path) -> Path:
    """Compose and save as PNG at `out`: the same recipe and images give the same bytes."""
    out.parent.mkdir(parents=True, exist_ok=True)
    compose(recipe, paths).save(out, format="PNG", compress_level=6)
    return out


def _size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def _grid(recipe: SheetRecipe, sizes: list[tuple[int, int]]) -> Grid:
    values = LAYOUTS[recipe.layout]
    n = len(sizes)
    feature = bool(values.get("feature_first")) and n > 1
    cells = n - 1 if feature else n
    columns = recipe.columns if recipe.columns is not None else int(values["columns"])
    if columns == 0:
        columns = max(cells, 1)
    elif columns < 0:
        columns = math.ceil(math.sqrt(max(cells, 1)))
    columns = max(1, min(columns, max(cells, 1)))
    aspect = float(values["cell"])
    cell_w = min(AUTO_CELL_WIDTH, max(w for w, _ in sizes))
    numbered = bool(values.get("numbered"))
    label_h = (LABEL_SIZE + 12 if recipe.labels or numbered else 0) + (
        META_SIZE + 6 if recipe.show_meta else 0
    )
    return Grid(
        columns, math.ceil(cells / columns), cell_w, round(cell_w / aspect), feature, label_h, numbered
    )


def _grid_height(grid: Grid, spacing: int) -> int:
    row = grid.cell_h + grid.label_h
    feature = (2 * grid.cell_h + grid.label_h + spacing) if grid.feature else 0
    return feature + grid.rows * row + max(grid.rows - 1, 0) * spacing


def _page(recipe: SheetRecipe, need_w: int, need_h: int) -> tuple[int, int]:
    if recipe.page == "auto":
        return need_w, need_h
    try:
        w, h = (int(v) for v in recipe.page.lower().split("x"))
    except ValueError as exc:
        raise InvalidRequest(f"page must be 'auto' or 'WxH' in pixels, not {recipe.page!r}") from exc
    return max(w, need_w), max(h, need_h)  # a larger page is a larger canvas, never larger images


def _draw_cells(
    sheet: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    recipe: SheetRecipe,
    cells: list[tuple[Path, tuple[int, int]]],
    grid: Grid,
    origin: tuple[int, int],
    ink: tuple[int, int, int],
) -> None:
    x0, y = origin
    full_w = grid.columns * grid.cell_w + (grid.columns - 1) * recipe.spacing
    for i, (path, size) in enumerate(cells):
        if grid.feature and i == 0:
            box = (x0, y, full_w, 2 * grid.cell_h)
        else:
            k = i - 1 if grid.feature else i
            top = y + ((2 * grid.cell_h + grid.label_h + recipe.spacing) if grid.feature else 0)
            col, row = k % grid.columns, k // grid.columns
            box = (
                x0 + col * (grid.cell_w + recipe.spacing),
                top + row * (grid.cell_h + grid.label_h + recipe.spacing),
                grid.cell_w,
                grid.cell_h,
            )
        place_image(sheet, path, box, recipe.fit)
        meta = f"{recipe.images[i]}  {size[0]} x {size[1]}"
        _label(draw, recipe, meta, index=i, grid=grid, at=(box[0], box[1] + box[3] + 8), ink=ink)


def place_image(sheet: Image.Image, path: Path, box: tuple[int, int, int, int], fit: str) -> None:
    x, y, w, h = box
    with Image.open(path) as source:
        picture: Image.Image = source.convert("RGB")
    if fit == "cover":
        scale = min(max(w / picture.width, h / picture.height), 1.0)
    else:
        scale = min(w / picture.width, h / picture.height, 1.0)
    size = (max(1, round(picture.width * scale)), max(1, round(picture.height * scale)))
    if size != picture.size:
        picture = picture.resize(size, Image.Resampling.LANCZOS)  # pyright: ignore[reportUnknownMemberType]
    left, top = max((picture.width - w) // 2, 0), max((picture.height - h) // 2, 0)
    picture = picture.crop((left, top, left + min(w, picture.width), top + min(h, picture.height)))
    sheet.paste(picture, (x + (w - picture.width) // 2, y + (h - picture.height) // 2))


def _label(
    draw: ImageDraw.ImageDraw,
    recipe: SheetRecipe,
    meta: str,
    *,
    index: int,
    grid: Grid,
    at: tuple[int, int],
    ink: tuple[int, int, int],
) -> None:
    x, y = at
    text = recipe.labels[index] if recipe.labels else ""
    if grid.numbered:
        text = f"{index + 1}  {text}".rstrip()
    if text:
        draw.text((x, y), text, fill=ink, font=sheet_font(LABEL_SIZE))
        y += LABEL_SIZE + 12
    if recipe.show_meta:
        draw.text((x, y), meta, fill=ink, font=sheet_font(META_SIZE))


def footer_lines(recipe: SheetRecipe, width: int) -> list[str]:
    chars = max(20, width // (NOTE_SIZE // 2 + 1))
    return [line for para in recipe.notes.splitlines() for line in textwrap.wrap(para, chars) or [""]]


def _draw_footer(
    draw: ImageDraw.ImageDraw,
    recipe: SheetRecipe,
    notes: list[str],
    at: tuple[int, int],
    ink: tuple[int, int, int],
) -> None:
    x, y = at
    if recipe.palette:
        for i, colour in enumerate(recipe.palette):
            left = x + i * (SWATCH + 72)
            draw.rectangle((left, y, left + SWATCH, y + SWATCH), fill=sheet_colour(colour), outline=ink)
            draw.text((left, y + SWATCH + 6), colour.upper(), fill=ink, font=sheet_font(META_SIZE))
        y += SWATCH + 40
    for line in notes:
        draw.text((x, y), line, fill=ink, font=sheet_font(NOTE_SIZE))
        y += NOTE_SIZE + 8


def sheet_colour(value: str) -> tuple[int, int, int]:
    try:
        rgb = ImageColor.getrgb(value)
    except ValueError as exc:
        raise InvalidRequest(f"{value!r} is not a colour; use a hex value such as #F4F6F9") from exc
    return rgb[0], rgb[1], rgb[2]


def sheet_ink(background: str) -> tuple[int, int, int]:
    r, g, b = sheet_colour(background)
    return (20, 24, 33) if 0.2126 * r + 0.7152 * g + 0.0722 * b > 140 else (238, 241, 246)


def sheet_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size)
