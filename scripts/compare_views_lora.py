"""The views comparison before 0020's milestone 2: side and back views of two characters drawn by plain
Qwen-Image-Edit 2511 and by the same model with the multiple-angles LoRA at full strength (the registry
input `lora_strength`, node "2" of the workflow). The owner looks at the pictures and picks; the pick is a
decision, and the views' workflow input is set from it.

    uv run python scripts/compare_views_lora.py --dry-run          # prints what it would draw, no GPU
    scripts/gpu-lock.sh uv run python scripts/compare_views_lora.py   # the real run (GPU lock, ComfyUI)

Per character: one front picture (Z-Image Turbo, from a single-figure prompt made from the cast plan's cue
and sheet prompt of `projects/isolde-the-forgotten-wife-2`), then the side view and the back view each
drawn twice from that front with the same seed, once with `lora_strength` 0.0 and once with 1.0, by the
same prompt. Eight Qwen pictures and two Z-Image ones (about 25 minutes on the 8 GB card). Pictures go to
`.hone/test-media/views-lora/` (git-ignored); hone-models frees the models at the end of each session.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from hone_music_video.adapters.hone_models import HoneModels

CAST = Path("projects/isolde-the-forgotten-wife-2/current/cast.json")
OUT = Path(os.environ.get("HONE_TEST_MEDIA_DIR", ".hone/test-media")) / "views-lora"
CHARACTERS = ("morvane", "isolde")
FRONT_MODEL, VIEWS_MODEL = "z-image-turbo", "qwen-image-edit-2511-4step"
SEED = 7
STRENGTHS = (0.0, 1.0)
STUDIO = "plain seamless light-grey studio backdrop, even soft studio lighting, no props, no text"
VIEWS = {
    "side": "exact side profile facing left, full body head to toe",
    "back": "seen from directly behind, full body head to toe",
}


def single_figure(sheet_prompt: str) -> str:
    """The cast plan's four-figure sheet prompt as one figure facing the camera: its description part
    (from 'He plays' / 'She plays' on) with the single-figure opening in place of the turnaround one."""
    found = re.search(r"\b(He|She|It) plays\b.*", sheet_prompt, re.DOTALL)
    detail = found.group(0) if found else sheet_prompt
    detail = re.sub(r"The costume is identical in all four views\.\s*", "", detail)
    return (
        "Photographic character reference: one studio photograph of one person, full body head to toe, "
        f"facing the camera, neutral standing pose, arms relaxed at the sides, {STUDIO}. " + detail
    )


def view_prompt(noun: str, view: str) -> str:
    return (
        f"The same {noun} from image 1, {VIEWS[view]}, same face, same costume and every detail of it, "
        f"same colours, {STUDIO}. Real photograph."
    )


def plan() -> list[tuple[str, str, str, str, float | None]]:
    """(character, file stem, model, prompt, lora_strength) in drawing order."""
    cast = {c["id"]: c for c in json.loads(CAST.read_text())["characters"]}
    steps: list[tuple[str, str, str, str, float | None]] = []
    for name in CHARACTERS:
        one = cast[name]
        steps.append((name, f"{name}-front", FRONT_MODEL, single_figure(one["sheet_prompt"]), None))
        for view in VIEWS:
            for strength in STRENGTHS:
                stem = f"{name}-{view}-lora{strength:g}"
                steps.append((name, stem, VIEWS_MODEL, view_prompt(one["noun"], view), strength))
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print the prompts and files, draw nothing")
    args = parser.parse_args()
    steps = plan()
    for _, stem, model, prompt, strength in steps:
        extra = "" if strength is None else f", lora_strength={strength:g}"
        print(f"{stem}.png  [{model}{extra}]\n  {prompt}\n")
    if args.dry_run:
        return 0
    if os.environ.get("HONE_GPU_LOCK_HELD") != "1":
        print("run through scripts/gpu-lock.sh (the machine-wide GPU lock)", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    models = HoneModels()
    for model in (FRONT_MODEL, VIEWS_MODEL):  # one model session each: the fronts first, then every view
        with models.session(model):
            for name, stem, which, prompt, strength in steps:
                if which != model or (OUT / f"{stem}.png").is_file():
                    continue
                inputs: dict[str, object] = {"size": "1024x1024"}
                if strength is not None:
                    inputs |= {"references": [OUT / f"{name}-front.png"], "lora_strength": strength}
                models.generate(model, prompt, out=OUT / f"{stem}.png", seed=SEED, inputs=inputs)
                print(f"made {OUT / f'{stem}.png'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
