"""Notifications (design §13.4, D-060): the owner's webhook hears when a gate waits, when a stage fails and
when the video is done; the message names the project, the gate or stage and the dashboard page. The
webhook URL (a Telegram bot token in it) is planted: it must reach no file of the project."""

import os
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from hone_flow.testing import WebhookServer

import hone_music_video as hmv
from hone_music_video import notify, runs_redo
from hone_music_video.notify import load_env_files  # the real one: conftest stubs it for other tests
from hone_music_video.testing import FakeModels
from tests.conftest import drive

TOKEN = "123456:planted-bot-token-AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"  # noqa: S105 - must be written nowhere
DASHBOARD = "http://studio.test:8794"


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> Iterator[WebhookServer]:
    """A webhook shaped like Telegram's `sendMessage`: the token in the path, the chat in the query."""
    with WebhookServer() as found:
        monkeypatch.setenv(notify.URL_ENV, f"{found.url}/bot{TOKEN}/sendMessage?chat_id=42")
        monkeypatch.setenv(notify.KIND_ENV, "telegram")
        monkeypatch.setenv(notify.DASHBOARD_ENV, DASHBOARD)
        yield found


def texts(server: WebhookServer) -> list[str]:
    return [r.json()["text"] for r in server.requests]


def written_anywhere(root: Path, secret: str) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and secret.encode() in p.read_bytes()]


def test_each_gate_and_the_finished_video_are_told(project: hmv.Project, server: WebhookServer) -> None:
    assert drive(project, FakeModels()).status == "completed"
    told = texts(server)
    gates = [g for g in hmv.GATES.values() if any(f"awaiting review at {g}" in t for t in told)]
    # every gate stop is told, those that then pass on their own too (design §15, D-060)
    assert gates == ["review_lyrics", "review_plan", "review_scenes"]
    assert "run.completed" not in told[0] and "completed" in told[-1].splitlines()[0]
    for text in told:
        assert "Balcony" in text.splitlines()  # the project, by its name
        assert f"{DASHBOARD}/#/p/balcony" in text.splitlines()  # its page on the dashboard
    first = server.requests[0]
    assert parse_qs(urlsplit(first.path).query) == {"chat_id": ["42"]}  # Telegram's chat, from the URL
    assert set(first.json()) == {"text"}  # the body Telegram's `sendMessage` takes
    assert written_anywhere(project.root, TOKEN) == []
    assert written_anywhere(project.root, "sendMessage?chat_id") == []


def test_a_remake_tells_the_finished_video_again(project: hmv.Project, server: WebhookServer) -> None:
    assert drive(project, FakeModels()).status == "completed"
    server.requests.clear()
    hmv.redo_clips(project, ["S001"])
    assert runs_redo.remake(project, FakeModels()).status == "completed"
    assert "completed" in texts(server)[-1].splitlines()[0]


class FailingCast(FakeModels):
    def plan(self, model_id: str, *, schema: type[Any], **asked: Any) -> Any:
        if schema.__name__ == "Bible":
            raise hmv.ModelFailure("the planner is down (planted failure)")
        return super().plan(model_id, schema=schema, **asked)


def test_a_failed_stage_is_told_with_its_error(project: hmv.Project, server: WebhookServer) -> None:
    models = FailingCast()
    hmv.start(project, models)
    hmv.approve(project)
    assert hmv.resume(project, models).status == "failed"
    failed = texts(server)[-1]
    assert "failed" in failed.splitlines()[0] and "plan" in failed and "the planner is down" in failed
    assert written_anywhere(project.root, TOKEN) == []


@pytest.mark.parametrize("kind", ["slack", "mattermost", "discord", "http"])
def test_the_other_kinds_post_their_own_body(
    project: hmv.Project, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    with WebhookServer() as server:
        monkeypatch.setenv(notify.URL_ENV, server.url)
        monkeypatch.setenv(notify.KIND_ENV, kind.upper())
        hmv.start(project, FakeModels())
    (sent,) = server.requests
    body: Mapping[str, Any] = sent.json()
    expected = {"slack": {"text"}, "mattermost": {"text"}, "discord": {"content"}}
    if kind == "http":
        assert body["label"] == "Balcony" and body["browse_url"] == "http://localhost:8794/#/p/balcony"
        assert body["event"] == "run.awaiting_review"
    else:
        assert set(body) == expected[kind]


def test_nothing_is_sent_without_a_url(project: hmv.Project, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(notify.URL_ENV, raising=False)
    assert notify.destinations(project) == []
    monkeypatch.setenv(notify.URL_ENV, "https://hooks.test/x")
    monkeypatch.setenv(notify.KIND_ENV, "pigeon")
    with pytest.raises(hmv.InvalidInput, match="pigeon"):
        notify.destinations(project)


def test_the_dashboard_link_takes_a_trailing_slash(
    project: hmv.Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(notify.DASHBOARD_ENV, "http://studio.test:8794/")
    assert notify.page(project) == "http://studio.test:8794/#/p/balcony"


def test_a_bad_kind_stops_every_way_a_run_goes_on(
    project: hmv.Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The kind is checked whenever the workflow is built: resume, redo and assembling again too."""
    assert drive(project, FakeModels()).status == "completed"
    monkeypatch.setenv(notify.URL_ENV, "https://hooks.test/x")
    monkeypatch.setenv(notify.KIND_ENV, "pigeon")
    for go_on in (
        lambda: hmv.resume(project, FakeModels()),
        lambda: runs_redo.remake(project, FakeModels()),
        lambda: hmv.assemble(project, FakeModels()),
    ):
        with pytest.raises(hmv.InvalidInput, match="pigeon"):
            go_on()


def test_the_settings_come_from_dotenv_when_not_set(
    project: hmv.Project, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """D-060: `$HONE_ENV_FILE`, then `./.env`, as hone-models reads them; the environment wins."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        f'export {notify.URL_ENV}="https://hooks.test/from-dotenv" \n{notify.KIND_ENV}=discord # a comment\n'
        f"{notify.DASHBOARD_ENV}=http://kept.test\nOTHER=not-read\n"
    )
    monkeypatch.setenv(notify.DASHBOARD_ENV, "http://set.test")
    for name in (notify.URL_ENV, notify.KIND_ENV, "OTHER"):  # set, then removed: restored after the test
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)
    monkeypatch.delenv("HONE_ENV_FILE", raising=False)
    load_env_files()
    assert os.environ[notify.URL_ENV] == "https://hooks.test/from-dotenv"
    assert os.environ[notify.KIND_ENV] == "discord"
    assert os.environ[notify.DASHBOARD_ENV] == "http://set.test" and "OTHER" not in os.environ
