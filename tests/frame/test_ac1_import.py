"""AC-1: importing a TOML and a JSON file copies it into the project and lists every item in file order;
a ref to an item below, an unknown field, an unknown model, too many refs and a missing file are each
refused with a message naming the item.

Hone Frame: ported from its `tests/e2e/test_ac1_import.py` (change 0027)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from hone_music_video import frame as hf
from hone_music_video.frame.errors import InvalidRequest
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

pytestmark = pytest.mark.e2e

TOML = """\
# my morning project
[project]
name = "Morning"
style = "soft light"   # reference only

[defaults]
model = "z-image-turbo"

[characters.woman.hero]
prompt = "a woman"

[objects.mug.hero]
file = "mug.png"

[characters.woman.kneeling]
model = "qwen-image-edit-2511"
refs = ["woman.hero"]
prompt = "the woman in image 1, kneeling"

[scenes.coffee]
model = "qwen-image-edit-2511"
refs = ["woman.hero", "mug.hero"]
prompt = "she drinks"

[scenes.walk.start]
prompt = "a street"

[sheets.woman-views]
images = ["woman.hero", "woman.kneeling"]
"""
ORDER = [
    "woman.hero", "mug.hero", "woman.kneeling", "coffee", "walk.start", "woman-views",
]  # fmt: skip


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    folder = tmp_path / "files"
    folder.mkdir()
    Image.new("RGB", (40, 40), "white").save(folder / "mug.png")
    return folder


def test_ac1_toml_is_copied_and_listed_in_file_order(ws: hf.Workspace, folder: Path) -> None:
    (folder / "morning.toml").write_text(TOML)
    project = ws.import_file(folder / "morning.toml")
    assert [i.id for i in project.spec().items] == ORDER
    copy = project.root / "project.toml"
    assert copy.read_text().replace('"assets/mug.png"', '"mug.png"') == TOML  # the copy is the file
    assert (project.root / "assets" / "mug.png").is_file()
    state = project.state().items
    assert state["mug.hero"].status == "provided" and not state["mug.hero"].marked
    assert all(state[i].status == "todo" and state[i].marked for i in ORDER if i != "mug.hero")
    groups = {i.id: (i.group, i.subject, i.name, i.kind) for i in project.spec().items}
    assert groups["coffee"] == ("scenes", "coffee", "", "image")
    assert groups["walk.start"] == ("scenes", "walk", "start", "image")
    assert groups["woman-views"][3] == "sheet"


def test_ac1_json_is_copied_and_listed_in_file_order(ws: hf.Workspace, folder: Path) -> None:
    data = {
        "project": {"name": "Morning JSON"},
        "places": {"kitchen": {"wide": {"model": "z-image-turbo", "prompt": "a kitchen"}}},
        "characters": {"woman": {"hero": {"model": "z-image-turbo", "prompt": "a woman"}}},
    }
    (folder / "p.json").write_text(json.dumps(data))
    project = ws.import_file(folder / "p.json")
    assert (project.root / "project.json").read_text() == json.dumps(data)
    assert [i.id for i in project.spec().items] == ["kitchen.wide", "woman.hero"]


def refused(ws: hf.Workspace, text: str, folder: Path) -> dict[str, str]:
    with pytest.raises(InvalidRequest) as raised:
        ws.import_text(text, "toml", files_root=folder)
    found: dict[str, str] = {}
    for problem in raised.value.problems:
        found[problem.item] = f"{found.get(problem.item, '')}; {problem.message}"
    return found


HEAD = '[project]\nname = "P"\n[defaults]\nmodel = "qwen-image-edit-2511"\n'


@pytest.mark.parametrize(
    ("body", "item", "says"),
    [
        (
            '[characters.a.one]\nprompt = "x"\nrefs = ["b.two"]\n[characters.b.two]\nprompt = "y"\n',
            "a.one",
            "not above",
        ),
        ('[characters.a.one]\npromt = "x"\n', "a.one", "unknown field 'promt'"),
        ('[characters.a.one]\nprompt = "x"\nmodel = "no-such-model"\n', "a.one", "unknown model"),
        (
            '[characters.a.one]\nprompt = "x"\n[characters.a.two]\nprompt = "y"\nmodel = "flux.2-klein-4b"\n'
            'refs = ["a.one", "a.one", "a.one"]\n',
            "a.two",
            "takes at most 2",
        ),
        ('[objects.mug.hero]\nfile = "missing.png"\n', "mug.hero", "does not exist"),
        ('[characters.a.one]\nprompt = "x"\nmodel = "hosted-image"\n', "a.one", "not a local model"),
        (
            '[objects.mug.hero]\nprompt = "x"\nmodel = "z-image-turbo"\n'
            '[characters.a.one]\nprompt = "x"\nmodel = "z-image-turbo"\nrefs = ["mug.hero"]\n',
            "a.one",
            "takes no references",
        ),
        ('[characters.a.one]\nprompt = "x"\nmodel = "z-image-turbo"\nsize = "10x10"\n', "a.one", "10x10"),
        ('[charcters.a.one]\nprompt = "x"\n', "charcters", "unknown group"),
        ('[characters.a.one]\nnegative = "x"\n', "a.one", "no prompt"),
        ('[characters.a.one]\nprompt = "x"\nrefs = ["mannequin:x"]\n', "a.one", "mannequins were removed"),
        ('[sheets.s]\nimages = ["a.one"]\n', "s", "not above"),
        ('[sheets.s]\nlayout = "zigzag"\nimages = []\n', "s", "unknown layout"),
        (
            '[characters.a.one]\nprompt = "x"\nmodel = "z-image-turbo"\nnegative = "blur"\n',
            "a.one",
            "z-image-turbo takes no negative prompt",
        ),
        (
            '[characters.a.one]\nprompt = "x"\nmodel = "z-image-turbo"\ninputs = { camera_angle = "a" }\n',
            "a.one",
            "camera_angle is not an input of z-image-turbo: it takes size, steps",
        ),
        ('[sheets.s]\nname = "x"\nimages = []\n', "s", "unknown field 'name'"),
        ('[mannequins.standing]\nprompt = "x"\n', "mannequins", "mannequins were removed"),
    ],
)  # fmt: skip
def test_ac1_problems_name_the_item(ws: hf.Workspace, folder: Path, body: str, item: str, says: str) -> None:
    problems = refused(ws, HEAD + body, folder)
    assert item in problems, problems
    assert says in problems[item]
    assert not ws.projects()  # nothing was imported


def test_ac1_a_default_negative_is_refused_for_a_model_without_one(ws: hf.Workspace, folder: Path) -> None:
    text = (
        '[project]\nname = "P"\n[defaults]\nmodel = "z-image-turbo"\nnegative = "blur"\n'
        '[characters.a.one]\nprompt = "x"\n[characters.a.two]\nprompt = "y"\nmodel = "qwen-image-edit-2511"\n'
    )
    problems = refused(ws, text, folder)
    assert set(problems) == {"a.one"} and "[defaults]" in problems["a.one"]


def test_ac1_inputs_of_a_model_not_installed_are_not_checked(tmp_path: Path, folder: Path) -> None:
    """hone-models cannot say what a model not yet installed takes: its inputs are not refused (D-067)."""
    unknown = hf.ModelInfo("not-installed", "image", True, installed="no", sizes=(), inputs=None)
    ws = hf.Workspace(tmp_path / "s", models=FakeModels(infos={"not-installed": unknown}))
    text = '[project]\nname = "P"\n[defaults]\nmodel = "not-installed"\nsize = "1024x1024"\n'
    project = ws.import_text(text + '[characters.a.one]\nprompt = "x"\nnegative = "y"\n', "toml")
    assert any("not-installed" in w and "install" in w for w in project.spec().warnings)


def test_ac1_a_file_that_is_not_an_image_is_refused(ws: hf.Workspace, folder: Path) -> None:
    (folder / "notes.png").write_text("not a picture")
    problems = refused(ws, HEAD + '[objects.mug.hero]\nfile = "notes.png"\n', folder)
    assert "not an image" in problems["mug.hero"]
    assert folders(ws) == []  # no half-made project


def test_ac1_a_failed_import_leaves_no_folder(
    ws: hf.Workspace, folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hone_music_video.frame import workspace

    def broken(*_args: object) -> str:
        raise OSError("disk full")

    monkeypatch.setattr(workspace, "guide_for", broken)
    with pytest.raises(OSError, match="disk full"):
        ws.import_text(HEAD + '[characters.a.one]\nprompt = "x"\n', "toml")
    assert folders(ws) == []


def folders(ws: hf.Workspace) -> list[str]:
    return [p.name for p in (ws.root / "projects").iterdir() if not p.name.startswith(".")]


def test_ac1_every_problem_is_listed_at_once(ws: hf.Workspace, folder: Path) -> None:
    text = HEAD + '[characters.a.one]\npromt = "x"\n[objects.b.two]\nfile = "nope.png"\nextra = 1\n'
    problems = refused(ws, text, folder)
    assert set(problems) == {"a.one", "b.two"}


def test_ac1_project_and_defaults_are_checked(ws: hf.Workspace, folder: Path) -> None:
    problems = refused(ws, '[project]\ncolour = "red"\n[defaults]\nseed = 3\n', folder)
    assert "colour" in problems["project"] and "seed" in problems["defaults"]
    with pytest.raises(InvalidRequest, match="does not parse"):
        ws.import_text("[project\n", "toml")


def test_ac1_the_same_name_makes_another_project(ws: hf.Workspace, folder: Path) -> None:
    text = HEAD + '[characters.a.one]\nprompt = "x"\n'
    first, second = ws.import_text(text, "toml"), ws.import_text(text, "toml")
    assert (first.id, second.id) == ("p", "p-2")
    assert [p.id for p in ws.projects()] == ["p", "p-2"]
