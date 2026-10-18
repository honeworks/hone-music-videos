"""The gateway key never reaches a record, an event, a log or a file (AGENTS.md rule 7, D-002): a run whose
transcription goes through the real adapter to a local stand-in for the gateway, once answered and once
refused with the key echoed back. In the refused case the adapter's own redaction of the error text is
tested in `test_hosted_speech.py`; here it matters only that nothing written holds the key."""

import json
import logging
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import runs
from hone_music_video.cli import main
from hone_music_video.testing import FakeModels
from tests.speech_server import KEY, SpeechServer, serving


class HostedSpeech(FakeModels):
    """Fake planners and media; the transcription through `HoneModels`, the real adapter."""

    def transcribe(
        self, model_id: str, audio: Path, *, language: str | None, prompt: str | None
    ) -> hmv.Words:
        return hmv.HoneModels().transcribe(model_id, audio, language=language, prompt=prompt)


def files_with_key(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and KEY.encode() in p.read_bytes()]


@pytest.mark.parametrize("status", [200, 401])
def test_the_key_is_written_nowhere(
    monkeypatch: pytest.MonkeyPatch,
    project: hmv.Project,
    status: int,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)
    events: list[dict[str, object]] = []
    with serving(monkeypatch, SpeechServer(words=[("she", 1.0, 1.5)], status=status)) as server:
        state = hmv.start(project, HostedSpeech(), on_event=events.append)
    assert server.requests and server.requests[0]["headers"]["Authorization"] == f"Bearer {KEY}"
    assert state.status == ("awaiting_review" if status == 200 else "failed")
    if status == 200:  # the call is kept in the stored words.json, without the key or any header
        words: hmv.Words = runs.stage_outputs(project, "transcribe")["transcribe"]
        call = words.call
        assert call is not None and call.model == "scribe_v2" and call.took_ms >= 0
        assert sorted(call.request) == [
            "file",
            "model",
            "prompt",
            "response_format",
            "timestamp_granularities[]",
        ]
        assert call.reply["words"] == [{"word": "she", "start": 1.0, "end": 1.5}]
        # the first listen found no line, so it was made again (D-047); the given lines not heard were
        # listened to again on a slice of the mix and of the vocals (D-040, D-046)
        assert len(server.requests) == 4 and [n.call is not None for n in words.listened_again] == [True] * 2
        assert words.retried is not None and words.retried.other is not None
        stored = json.dumps(words.model_dump()).lower()
        assert "authorization" not in stored and "bearer" not in stored and "header" not in stored
    else:
        transcribe = next(s for s in state.stages if s.name == "transcribe")
        assert "HTTP 401" in (transcribe.error or "")
    assert files_with_key(project.root.parent.parent) == []  # the projects and the given material
    assert KEY not in repr(events) + repr(state) + caplog.text + "".join(capsys.readouterr())


def test_the_key_stays_out_of_the_shot_plan_its_gate_and_check_shots(
    monkeypatch: pytest.MonkeyPatch, project: hmv.Project, capsys: pytest.CaptureFixture[str]
) -> None:
    models, events = HostedSpeech(), []
    with serving(monkeypatch, SpeechServer(words=[("she", 1.0, 1.5)], status=200)):
        state = hmv.start(project, models, on_event=events.append)
        while state.waiting != "review_plan":
            hmv.approve(project)
            state = hmv.resume(project, models, on_event=events.append)
        hmv.reject(project, note="more close-ups")
        state = hmv.resume(project, models, on_event=events.append)
    assert state.waiting == "review_plan"
    assert main(["check-shots", str(project.root)]) == 0
    assert files_with_key(project.root.parent.parent) == []
    assert KEY not in repr(events) + repr(state) + "".join(capsys.readouterr())
