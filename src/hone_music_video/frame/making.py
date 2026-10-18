"""Making one item (design §8.2): `count` images, or one prompt of `prompts` (hone-music-video 0033),
through the Models port, or a sheet through Pillow.

The prompt and negative go to the model exactly as the file writes them; nothing else is sent.

Hone Frame: ported from `src/hone_frame/making.py` (its 0008 branch, 2026-10-16) for
change 0027; "design §N" and "D-NNN" here are Hone Frame's own. A difference is marked `Hone Frame:`."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

from hone_music_video.frame.errors import RunStateError
from hone_music_video.frame.ports import Cancelled, ModelFailure
from hone_music_video.frame.project import Project
from hone_music_video.frame.project_file import ItemSpec
from hone_music_video.frame.records import ProjectState, Status, Version
from hone_music_video.frame.sheets import SheetRecipe, compose_to

Outcome = Literal["done", "waiting", "cancelled"]
NOT_READY = {  # why a ref cannot be used yet, and what to do
    "todo": "has no image yet: mark it to run, or give it a file, then run again",
    "failed": "failed: fix it and mark it to run, then run again",
    "waiting": "is waiting for you: accept it (or pick one), then run again",
    "running": "is being made: run again when it is done",
}


def made_with(project_id: str, item: ItemSpec) -> dict[str, Any]:
    """The fields that decide an item's image: a version made with others is "changed since made"."""
    if item.kind == "sheet":
        return {k: v for k, v in item.fields.items() if k != "hold"}
    prompts = item.prompts  # the whole list: a change to any prompt changes the item (D-076)
    return {
        **({"prompts": prompts} if prompts else {"prompt": item.prompt}),
        "negative": item.negative,
        "model": item.model,
        "size": item.size,
        "seed": item.seed(project_id),
        "refs": item.refs,
        "inputs": item.inputs,
    }


def make(project: Project, item: ItemSpec, cancel: threading.Event) -> Outcome:
    """Make `item` and store its versions. A cancel puts back its status, current version and candidates
    exactly as they were (it stays marked; images already made stay in its versions). A failure does the
    same but marks it `failed` with the error, and is raised again."""
    with project.editing() as state:
        st = state.items[item.id]
        status, current, candidates, error = st.status, st.current, list(st.candidates), st.error
        asked = st.run_prompt if item.prompts else None
        used = st.version(current) if current else None
        prompt = asked if asked is not None else _prompt_in_use(item, used)
        st.status = "running"
    project.log("item_started", item.id, f"making {item.id}")
    project.changed(item.id)
    try:
        if item.kind == "sheet":
            made = _make_sheet(project, item)
        else:
            made = _make_images(project, item, cancel, [prompt] if item.prompts else range(item.count))
    except Cancelled:
        _settle(project, item.id, status=status, current=current, candidates=candidates, error=error)
        return "cancelled"
    except Exception as exc:  # a model failure, a ref that is not ready, a sheet image that cannot be read
        _settle(project, item.id, status="failed", current=current, candidates=candidates, error=str(exc))
        project.log("item_failed", item.id, f"{item.id} failed", error=str(exc))
        raise
    # hone-music-video's one change (0028 §5): without `scene_picks` a scene's takes never wait for a
    # pick; the first is used, the others stay in its versions (Hone Frame waits for every pick, D-075)
    picks = project.ws.scene_picks or item.group != "scenes"
    if asked is not None and current is not None:  # 0033: another prompt's picture waits to be used
        _settle(project, item.id, status=status, current=current, candidates=candidates, marked=False)
        return "done"
    waits = item.hold or (len(made) > 1 and picks)
    _settle(
        project,
        item.id,
        status="waiting" if waits else "done",
        current=made[0],
        candidates=made if waits and len(made) > 1 else [],
        marked=False,
    )
    return "waiting" if waits else "done"


def _prompt_in_use(item: ItemSpec, used: Version | None) -> int:
    """The prompt a make of an item with `prompts` uses when none was asked for: the one that made the
    picture in use, else the first (0033)."""
    prompts = item.prompts or []
    return prompts.index(used.prompt) if used is not None and used.prompt in prompts else 0


def _settle(
    project: Project,
    item_id: str,
    *,
    status: Status,
    current: int | None,
    candidates: list[int],
    error: str | None = None,
    marked: bool | None = None,
) -> None:
    with project.editing() as state:
        st = state.items[item_id]
        st.status, st.current, st.candidates, st.error = status, current, candidates, error
        st.marked = st.marked if marked is None else marked
        st.run_prompt = st.run_prompt if st.marked else None
    project.changed(item_id)


def next_up(project: Project) -> tuple[list[ItemSpec], list[str]]:
    """The marked items the run can make now, in file order, and the waiting items that hold the others
    back (decisions D-075). An item is held back when one of its refs waits for the owner (a pick, a
    hold), or is itself held back; a waiting item marked again is made anew, so it holds nothing back."""
    state = project.state()
    waiting = {i for i, st in state.items.items() if st.status == "waiting" and not st.marked}
    held: set[str] = set()
    ready: list[ItemSpec] = []
    waits: list[str] = []
    for item in project.marked():
        blocking = [r for r in item.refs if r in waiting or r in held]
        if blocking:
            held.add(item.id)
            waits += [r for r in blocking if r in waiting and r not in waits]
        else:
            ready.append(item)
    return ready, waits


def rest_of(project: Project) -> tuple[Literal["waiting", "done"], str, str | None]:
    """How a run ends when it can make nothing more (status, reason, item): waiting for the owner's picks
    or accepts, or done (D-075)."""
    state = project.state()
    waits = [i.id for i in project.spec().items if (st := state.items.get(i.id)) and st.status == "waiting"]
    if not waits:
        return "done", "nothing more is marked", None
    more = f" and {len(waits) - 3} more" if len(waits) > 3 else ""
    return "waiting", f"made all it can; waiting for you: {', '.join(waits[:3])}{more}", waits[0]


def references(project: Project, state: ProjectState, item: ItemSpec) -> tuple[list[Path], dict[str, int]]:
    """The files of the item's refs, in order (image 1, image 2...), and the versions used. A project item
    is used only when it is done or provided; anything else fails the item with what to do (D-057)."""
    paths: list[Path] = []
    made_from: dict[str, int] = {}
    for ref in item.refs:
        st = state.items.get(ref)
        if st is not None and st.status not in ("done", "provided"):
            raise RunStateError(f"{ref} {NOT_READY[st.status]}")
        path = project.current_image(state, ref)
        if st is None or path is None:
            raise RunStateError(f"{ref} {NOT_READY['todo']}")
        made_from[ref] = st.current or 0
        paths.append(path)
    return paths, made_from


def _make_images(
    project: Project, item: ItemSpec, cancel: threading.Event, which: Iterable[int]
) -> list[int]:
    paths, made_from = references(project, project.state(), item)
    seed = item.seed(project.id)
    inputs = {
        k: v
        for k, v in (item.inputs | {"size": item.size, "negative": item.negative}).items()
        if v is not None
    }
    made: list[int] = []
    for k in which:
        started = time.monotonic()
        prompt = item.prompt_for(k)
        result = project.ws.models.generate(
            str(item.model),
            prompt,
            out=project.work_file(item.id),
            seed=seed + k,
            references=paths,
            inputs=inputs,
            cancel=cancel,
        )
        if result.path is None or result.error:
            raise ModelFailure(f"{item.model}: {result.error or 'no image was returned'}")
        elapsed = round(result.elapsed_s or time.monotonic() - started, 2)
        with project.editing() as state:
            version = project.add_version(
                state, item.id, result.path, source="generated", model=item.model, prompt=prompt,
                negative=item.negative, seed=seed + k, size=item.size, inputs=item.inputs, refs=item.refs,
                made_from=made_from, made_with=made_with(project.id, item), elapsed_s=elapsed,
            )  # fmt: skip
        made.append(version.n)
        project.log(
            "item_made", item.id, f"made {item.id} v{version.n}", version=version.n, elapsed_s=elapsed,
            model=item.model, size=item.size,
        )  # fmt: skip
        project.changed(item.id)
    return made


def _make_sheet(project: Project, item: ItemSpec) -> list[int]:
    state = project.state()
    paths, made_from = references(project, state, item)
    fields = {k: v for k, v in item.fields.items() if k != "hold"}
    recipe = SheetRecipe.model_validate({"name": item.subject} | fields)
    started = time.monotonic()
    work = compose_to(recipe, paths, project.work_file(item.id))
    elapsed = round(time.monotonic() - started, 2)
    with project.editing() as state:
        version = project.add_version(
            state, item.id, work, source="composed", refs=item.refs, made_from=made_from,
            made_with=made_with(project.id, item), elapsed_s=elapsed,
        )  # fmt: skip
    project.log(
        "item_made", item.id, f"composed {item.id} v{version.n}", version=version.n, elapsed_s=elapsed
    )
    return [version.n]
