"""AC-2: the prompt reaches the model byte for byte; `style` and `notes` never reach a model.

Hone Frame: ported from its `tests/e2e/test_ac2_prompt_verbatim.py` (change 0027)."""

from __future__ import annotations

import hashlib

import pytest

from hone_music_video import frame as hf
from hone_music_video.testing.frame_fakes import FakeFrameModels as FakeModels

from .conftest import run

pytestmark = pytest.mark.e2e

PROMPT = '  A woman,  café au lait — "quoted"\n\tsecond line with trailing space  '
TEXT = f'''
[project]
name = "Verbatim"
style = "STYLE-MARKER oil painting"
notes = "NOTES-MARKER do not send"

[characters.woman.hero]
model = "qwen-image-edit-2511"
prompt = """{PROMPT}"""
negative = "blurry,  extra fingers"
inputs = {{ steps = 9 }}
'''


def test_ac2_prompt_is_sent_exactly(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    assert fake.prompts == [PROMPT]
    sent = fake.calls[0]
    assert sent.inputs == {"steps": 9, "negative": "blurry,  extra fingers"}
    everything = repr([(c.prompt, c.inputs) for c in fake.calls])
    assert "STYLE-MARKER" not in everything and "NOTES-MARKER" not in everything
    version = project.state().items["woman.hero"].versions[0]
    assert version.prompt == PROMPT and version.model == "qwen-image-edit-2511"
    assert (version.negative, version.inputs) == ("blurry,  extra fingers", {"steps": 9})  # what was sent


def test_ac2_default_seed_comes_from_the_ids(ws: hf.Workspace, fake: FakeModels) -> None:
    project = ws.import_text(TEXT, "toml")
    run(ws, project)
    expected = int(hashlib.sha256(f"{project.id}:woman.hero".encode()).hexdigest()[:8], 16)
    assert fake.calls[0].seed == expected == project.spec().item("woman.hero").seed(project.id)


def test_ac2_an_input_written_into_the_prompt_is_refused(ws: hf.Workspace) -> None:
    """camera_angle is written into the prompt by hone-models: refused (D-073)."""
    text = TEXT.replace("inputs = { steps = 9 }", 'inputs = { camera_angle = "back" }')
    with pytest.raises(hf.errors.InvalidRequest) as raised:
        ws.import_text(text, "toml")
    message = str(raised.value)
    assert "woman.hero" in message and "camera_angle is written into the prompt" in message
    assert "write the words you want into the prompt yourself" in message
