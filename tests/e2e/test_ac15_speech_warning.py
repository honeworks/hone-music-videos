"""AC-15: a motion prompt with a word of speech or of the mouth is sent back to the scene writer once
(the code check of 0026), and what is still there is listed in the plan's problems and warned by
`check_shots`, never on expressions (0014, D-078, D-088; design §5.2, §14). Public API and CLI only."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from hone_music_video import frame_stages, runs
from hone_music_video.cli import main
from hone_music_video.testing import FakeModels
from hone_music_video.testing.frame_answers import scenes_answer
from tests.conftest import drive, new_project

pytestmark = pytest.mark.e2e

# the first two warn: a word of speech, then only a word of the mouth (D-088)
PROMPTS = ("She whispers the line.", "She keeps her lips closed.", "She smiles.",
           "He laughs, then a roar.")  # fmt: skip


def speaking(data: Mapping[str, Any]) -> Mapping[str, Any]:
    """The fake scene writer's scenes, their motion prompts as above in turn, whatever it is told."""
    reply = scenes_answer(data)
    for scene in reply["scenes"]:
        scene["motion_prompt"] = PROMPTS[int(scene["id"][1:]) % len(PROMPTS)]
    return reply


def test_speech_is_sent_back_once_then_warned(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = new_project(tmp_path)
    models = FakeModels(answers={"ScenePrompts": speaking})
    assert drive(project, models).status == "completed"  # what remains does not stop the run
    calls = [c for c in models.calls_of("plan") if c.schema == "ScenePrompts"]
    assert len(calls) == 2 and "problems" in calls[1].data  # sent back once
    planned = runs.stage_outputs(project, "plan")["plan"]
    assert any("'lips'" in p for p in planned.problems)

    assert main(["check-shots", str(project.root)]) == 0
    lines = [
        line.split(None, 3) for line in capsys.readouterr().out.splitlines() if line.startswith("warning")
    ]
    warned = {(where, rule): message for _, where, rule, message in lines}
    shots = frame_stages.read_shots(project).shots
    speech = {s.scene for s in shots if s.motion_prompt in PROMPTS[:2]}
    assert {where for where, rule in warned if rule == "speech"} == speech and speech
    mouth = next(s.scene for s in shots if s.motion_prompt == PROMPTS[1])
    assert warned[mouth, "speech"].startswith("the motion prompt has 'lips':")
    assert warned[mouth, "speech"].endswith("say the face stays still")
