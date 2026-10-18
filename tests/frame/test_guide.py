"""The prompt-writing guide (change 0008 §6): built from the stage texts, each chosen model's guide from
hone-models (faked here).

Hone Frame: ported from its `tests/unit/test_guide.py` (change 0027)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import pytest

from hone_music_video.frame import guide
from hone_music_video.frame.guide import STAGE_SITUATIONS, STAGES, build_guide


@dataclass(frozen=True)
class Note:
    about: str
    says: str
    source: str | None = None
    checked: date | None = None


@dataclass(frozen=True)
class FakeGuide:
    id: str
    summary: str | None = None
    prompt: str | None = None
    license: str | None = None
    commercial_use: bool | None = None
    sizes: list[str] | None = None
    max_references: int | None = None
    pose: str | None = None
    notes: list[Note] = field(default_factory=list[Note])

    def notes_about(self, about: str) -> list[Note]:
        return [n for n in self.notes if n.about == about]


EDIT = FakeGuide(
    id="edit-model",
    summary="Edits pictures from references.",
    prompt="Say what changes, then what stays.",
    license="Apache-2.0",
    commercial_use=True,
    sizes=["1024x1024", "832x1248"],
    max_references=3,
    pose="reference",
    notes=[
        Note("faces", "EDIT-FACE: faces drift at small sizes.", "own test", date(2026, 10, 3)),
        Note("hands", "EDIT-HANDS: hands holding small things break."),
        Note("scenes", "EDIT-SCENES: two people become twins."),
        Note("places", "EDIT-PLACES: a place view keeps the place."),
        Note("general", "EDIT-GENERAL: sentences, not tags."),
    ],
)
RESEARCH = FakeGuide(
    id="research-model",
    summary="Many references.",
    license="Qwen Research License",
    commercial_use=False,
    max_references=10,
    pose="control",
    notes=[Note("poses", "RESEARCH-POSES: a skeleton works as a control.")],
)
TEXT = FakeGuide(id="text-model", max_references=0, pose="none", commercial_use=None)


def of(*guides: FakeGuide):
    by_id = {g.id: g for g in guides}
    return lambda model_id: by_id[model_id]


def section(text: str, start: str, end: str) -> str:
    """The text from the heading `start` to the next heading `end`."""
    return text.split(start, 1)[1].split(end, 1)[0]


def stage_text(text: str, stage: str) -> str:
    title = guide.STAGE_TITLES[stage]
    rest = text.split(f"### {title}", 1)[1]
    return rest.split("\n### ", 1)[0]


def test_every_stage_has_its_section_and_text() -> None:
    text = build_guide([], guide_of=of())
    assert STAGES == ("hero", "views", "faces", "poses", "objects", "places", "scenes", "sheets")
    for stage in STAGES:
        assert f"### {guide.STAGE_TITLES[stage]}" in text
        assert guide.stage_text(stage).strip() in text


def test_the_document_has_its_three_parts_in_order() -> None:
    text = build_guide(["edit-model"], guide_of=of(EDIT))
    heads = [
        "## 1. How a project file works",
        "## 2. Stages",
        "## 3. Models",
    ]
    positions = [text.index(h) for h in heads]
    assert positions == sorted(positions)


def test_project_file_section_explains_the_rules() -> None:
    part = section(build_guide([], guide_of=of()), "## 1. How a project file works", "## 2. Stages")
    for words in (
        "image 1",
        "reference only",
        "hold",
        "count",
        "refs",
        "above",
        "version",
        "mark",
        "file",
        "inputs",
        "negative",
        "seed",
        "byte for byte",
        "prompts",
        "Prompt 2",
        "Start with a demo (recommended)",
        "[demo]",
    ):
        assert words in part, words


def test_notes_go_to_the_stages_that_need_them() -> None:
    text = build_guide(["edit-model"], guide_of=of(EDIT))
    faces = stage_text(text, "faces")
    assert "EDIT-FACE" in faces and "EDIT-HANDS" in faces
    assert "(own test, checked 2026-10-03)" in faces
    assert "EDIT-SCENES" not in faces
    scenes = stage_text(text, "scenes")
    assert "EDIT-SCENES" in scenes and "EDIT-PLACES" in scenes
    assert "EDIT-FACE" not in scenes
    assert "EDIT-HANDS" in stage_text(text, "poses")
    assert "EDIT-PLACES" in stage_text(text, "places")
    assert "EDIT-GENERAL" not in stage_text(text, "hero")


def test_general_notes_are_in_the_model_section() -> None:
    text = build_guide(["edit-model"], guide_of=of(EDIT))
    models = text.split("## 3. Models", 1)[1]
    assert "EDIT-GENERAL" in models


def test_every_situation_reaches_a_stage() -> None:
    routed = {about for situations in STAGE_SITUATIONS.values() for about in situations}
    situations = {"general", "faces", "hands", "people", "poses", "objects", "places", "scenes", "text"}
    assert routed | {"general"} == situations | {"references", "sizes"}  # hone-models' situations
    assert STAGE_SITUATIONS["faces"] == ("faces", "hands")
    assert set(STAGE_SITUATIONS["scenes"]) >= {"scenes", "people", "references", "places"}
    assert set(STAGE_SITUATIONS["poses"]) >= {"poses", "references", "hands"}
    assert STAGE_SITUATIONS["sheets"] == ()


def test_notes_are_named_by_model() -> None:
    text = build_guide(["edit-model", "research-model"], guide_of=of(EDIT, RESEARCH))
    poses = stage_text(text, "poses")
    assert "`research-model`" in poses and "RESEARCH-POSES" in poses
    assert "`edit-model`" in poses


def test_a_model_without_notes_for_a_stage_says_so() -> None:
    text = build_guide(["text-model"], guide_of=of(TEXT))
    assert "no notes for" in stage_text(text, "faces")


def test_research_licence_warning() -> None:
    text = build_guide(["edit-model", "research-model"], guide_of=of(EDIT, RESEARCH))
    models = text.split("## 3. Models", 1)[1]
    research = models.split("### `research-model`", 1)[1]
    edit = models.split("### `edit-model`", 1)[1].split("### `research-model`", 1)[0]
    assert "RESEARCH-LICENCE WARNING" in research and "Qwen Research License" in research
    assert "RESEARCH-LICENCE WARNING" not in edit
    assert "commercial use allowed" in edit
    assert "RESEARCH-LICENCE WARNING" in text.split("## 1.", 1)[0]  # also at the top
    unstated = build_guide(["text-model"], guide_of=of(TEXT))
    assert "not stated" in unstated and "RESEARCH-LICENCE WARNING" not in unstated


def test_pose_support_text() -> None:
    text = build_guide(["edit-model", "research-model", "text-model"], guide_of=of(EDIT, RESEARCH, TEXT))
    models = text.split("## 3. Models", 1)[1]
    assert "Pose support: as a reference picture" in models
    assert "Pose support: as a control" in models
    assert "Pose support: none" in models
    missing = build_guide(["m"], guide_of=of(FakeGuide(id="m")))
    assert "Pose support: not stated" in missing


def test_references_sizes_summary_and_prompt_form() -> None:
    text = build_guide(["edit-model", "text-model"], guide_of=of(EDIT, TEXT))
    models = text.split("## 3. Models", 1)[1]
    assert "Edits pictures from references." in models
    assert "Say what changes, then what stays." in models
    assert "1024x1024, 832x1248" in models
    assert "up to 3 reference pictures" in models and "image 1" in models
    assert "no reference pictures" in models


def test_measured_time() -> None:
    measured = {("edit-model", "1024x1024"): 31.4, ("edit-model", "832x1248"): 40.0, ("other", "1x1"): 9.0}
    text = build_guide(["edit-model"], guide_of=of(EDIT), measured_s=measured)
    models = text.split("## 3. Models", 1)[1]
    assert "1024x1024: about 31 s" in models and "832x1248: about 40 s" in models
    assert "1x1" not in models
    assert "no measurement on this machine yet" in build_guide(["edit-model"], guide_of=of(EDIT))


def test_title_names_the_project_and_models() -> None:
    text = build_guide(["edit-model", "edit-model"], guide_of=of(EDIT), project_name="Morning at home")
    first = text.splitlines()[0]
    assert first == "# Prompt guide: Morning at home"
    assert text.count("### `edit-model`") == 1  # a model named twice is shown once
    assert "No model chosen" in build_guide([], guide_of=of())


@pytest.mark.parametrize("stage", STAGES)
def test_stage_examples_use_the_default_model_first(stage: str) -> None:
    """D-071: every stage's examples are written for qwen-image-2.1-turbo; another model appears only under
    "For commercial work", where a model whose licence allows it is shown in its own form."""
    text = guide.stage_text(stage)
    assert text.startswith(f"### {guide.STAGE_TITLES[stage]}")
    assert "```toml" in text
    if stage == "sheets":
        return
    default, _, commercial = text.partition("##### For commercial work")
    assert set(re.findall(r'^model = "([^"]+)"', default, re.M)) == {"qwen-image-2.1-turbo"}, stage
    others = set(re.findall(r'^model = "([^"]+)"', commercial, re.M))
    assert others and "qwen-image-2.1-turbo" not in others, stage


# Hone Frame: `test_the_docs_table_matches_the_routing` checks its own docs/guide.md: not ported.


@pytest.mark.parametrize("stage", [*STAGES, "project-file"])
def test_stage_texts_state_no_model_facts(stage: str) -> None:
    """Model limits, timings and inputs come from hone-models' notes, never from hone-frame's texts."""
    text = (guide.GUIDE_DATA / f"{stage}.md").read_text(encoding="utf-8")
    for fact in ("<sks>", "lora_strength", "Multiple-Angles", "camera_angle", "8 GB", "slots"):
        assert fact not in text, (stage, fact)
    assert not re.search(r"\b\d+ s\b|\b\d+ to \d+ words\b", text), stage
