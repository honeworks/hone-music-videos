"""What a video cost (design §13.5, D-062): the hosted calls' recorded prices and every stage's time, split
into the first pass, reruns and redos. A run on fake models whose first transcription fails (the retry is
priced like the gateway's), the lyrics rejected once, a clip redone; then hone-models' span store gets the
planners' calls as hone-models records them, with the run named (0007) or not (before)."""

import itertools
import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import hone_flow as fk
import hone_models as mk
import pytest

import hone_music_video as hmv
from hone_music_video import video_costs
from hone_music_video.cli import main
from hone_music_video.records import HostedCall
from hone_music_video.testing import FakeModels, settle_scenes
from tests.conftest import new_project

PRICE = 0.0123  # the transcription's price, as the in-library client records it (D-002)
COST, RUN, STEP = "hone.models.cost_usd", "hone.run_id", "hone.step"
CHAT = "hone.models.chat"
NUMBERS = itertools.count(1)


class PricedModels(FakeModels):
    """The first transcription fails (the stage's attempt 1); the next ones are priced."""

    failed = False

    def transcribe(self, model_id: str, audio: Path, **asked: Any) -> hmv.Words:
        if not self.failed:
            self.failed = True
            raise hmv.ModelFailure("the transcriber is down (planted)")
        words = super().transcribe(model_id, audio, **asked)
        call = HostedCall(
            model=model_id, url="https://a.test", request={}, reply={}, took_ms=5, cost_usd=PRICE
        )
        return words.model_copy(update={"call": call})


@pytest.fixture(scope="module")
def made(tmp_path_factory: pytest.TempPathFactory) -> Iterator[hmv.Project]:
    """A finished video: transcription retried, lyrics run again with a note, one clip redone."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("HONE_HOME", str(tmp_path_factory.mktemp("no-store")))  # no hone-models records
        project, models = new_project(tmp_path_factory.mktemp("costs")), PricedModels()
        assert hmv.start(project, models).status == "failed"
        assert hmv.resume(project, models).waiting == "review_lyrics"
        hmv.reject(project, note="the second line is two lines")
        state = hmv.resume(project, models)
        while state.waiting:
            if state.waiting == "review_scenes":
                settle_scenes(project, models)
            hmv.approve(project)
            state = hmv.resume(project, models)
        hmv.redo_clips(project, ["S002"])
        hmv.remake(project, models)  # a fork: the redo part (0027 §7)
        yield project


def run_ids(project: hmv.Project) -> list[str]:
    """The run, then its fork (run ids sort by time)."""
    return sorted(p.name for p in (project.runs_dir / "video" / "runs").iterdir())


def step(project: hmv.Project, name: str) -> fk.StepRecord:
    return fk.open_runs(project.runs_dir, "video").open_run(run_ids(project)[0]).steps(name, "song")[0]


def span(at: str | None, attrs: dict[str, Any], name: str = CHAT) -> dict[str, Any]:
    assert at is not None
    number = next(NUMBERS)
    return {"trace_id": "a" * 32, "span_id": f"{number:016x}", "name": name, "start_time": at, "end_time": at,
            "attributes": attrs}  # fmt: skip


def store_with(path: Path, spans: list[dict[str, Any]]) -> Path:
    sink = mk.records.SqliteSpanSink(path)
    for found in spans:
        sink.emit(found)
    sink.close()
    return path


def parts(found: hmv.Costs, stage: str) -> dict[str, tuple[int, int, float]]:
    """A stage's parts as (calls, unknown calls, cost)."""
    row = next(s for s in found.stages if s.stage == stage)
    return {
        k: (p.calls, p.unknown_calls, p.cost_usd) for k, p in (("first", row.first), ("reruns", row.reruns))
    }


def test_spans_naming_the_run_are_its_stages_calls(made: hmv.Project, tmp_path: Path) -> None:
    original = run_ids(made)[0]
    plan, lyrics = step(made, "plan"), step(made, "lyrics")
    assert lyrics.attempt == 2 and step(made, "transcribe").attempt == 2  # each tried twice
    store = store_with(
        tmp_path / "spans.db",
        [
            span(plan.started_at, {RUN: original, STEP: "plan", COST: 0.5}),  # the frame plan's many calls
            span(plan.started_at, {RUN: original, STEP: "plan", COST: 0.1}),
            span(plan.started_at, {COST: 0.25}),  # another tool's call meanwhile: not this video's
            span(lyrics.started_at, {RUN: original, STEP: "lyrics"}),  # no price: unknown, never guessed
            span(lyrics.started_at, {RUN: "someone-else", STEP: "lyrics", COST: 9.0}),
            span(plan.started_at, {RUN: original, STEP: "scenes", COST: 1.0}, "hone.models.image"),
            span(plan.started_at, {RUN: original, STEP: "transcribe", COST: 5.0}, "hone.models.transcribe"),
            span("2020-01-01T00:00:00.000Z", {RUN: original, STEP: "plan", COST: 7.0}),  # outside the project
        ],
    )
    found = hmv.costs(made, store)
    assert parts(found, "plan")["first"] == (2, 0, 0.6)
    assert parts(found, "lyrics") == {"first": (1, 1, 0), "reruns": (1, 1, 0)}
    assert parts(found, "transcribe") == {"first": (1, 1, 0), "reruns": (1, 0, PRICE)}  # failed, then priced
    assert found.hosted_usd == round(0.6 + PRICE, 6) and found.unknown_calls == 3
    assert found.added_usd == PRICE and found.store_found
    by = {s.stage: s for s in found.stages}
    assert by["assemble"].redos.time_ms > 0 and by["measure"].redos.time_ms == 0  # copied by the fork
    assert found.added_ms == sum(s.reruns.time_ms + s.redos.time_ms for s in found.stages)
    gpu = [s for s in found.stages if s.where == "gpu"]
    assert [s.stage for s in gpu] == ["scenes", "clips", "finish"]
    assert found.gpu_ms == sum(p.time_ms for s in gpu for p in (s.first, s.reruns, s.redos))


def test_a_run_made_before_0007_has_its_calls_found_by_time(made: hmv.Project, tmp_path: Path) -> None:
    plan, measure = step(made, "plan"), step(made, "measure")
    store = store_with(
        tmp_path / "spans.db",
        [
            span(plan.started_at, {COST: 0.5}),
            span(measure.started_at, {COST: 3.0}),
        ],  # measure: another tool's
    )
    found = hmv.costs(made, store)
    assert parts(found, "plan")["first"] == (1, 0, 0.5)
    assert parts(found, "lyrics") == {"first": (1, 1, 0), "reruns": (1, 1, 0)}
    assert found.hosted_usd == round(0.5 + PRICE, 6) and found.unknown_calls == 3


def test_without_a_store_every_planner_attempt_is_unknown(
    made: hmv.Project, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    found = hmv.costs(made, tmp_path / "no-store.db")
    assert not found.store_found and found.store == str(tmp_path / "no-store.db")
    assert (
        found.hosted_usd == PRICE and found.unknown_calls == 4
    )  # lyrics twice, the plan and a transcription
    monkeypatch.setenv("HONE_HOME", str(tmp_path))
    assert main(["costs", str(made.root)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("balcony: $0.01 of hosted calls and 4 calls without a price, 0.0 h of GPU\n")
    assert f"no hone-models records found at {tmp_path / 'models' / 'spans.db'}" in out
    assert main(["costs", str(made.root), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["unknown_calls"] == 4


def test_every_stage_is_timed_from_its_attempts(made: hmv.Project, tmp_path: Path) -> None:
    """Each part's time is the sum of its attempts' times in the run records, in integer ms."""
    found = hmv.costs(made, tmp_path / "no-store.db")
    measure = step(made, "measure")
    assert measure.started_at and measure.ended_at
    start, end = (datetime.fromisoformat(t) for t in (measure.started_at, measure.ended_at))
    stage = next(s for s in found.stages if s.stage == "measure")
    assert stage.first.time_ms == round((end - start).total_seconds() * 1000)
    assert all(isinstance(p.time_ms, int) for s in found.stages for p in (s.first, s.reruns, s.redos))


def test_costs_json_follows_the_runs_and_reading_writes_nothing(made: hmv.Project, tmp_path: Path) -> None:
    written = hmv.Costs.model_validate_json((made.current / "costs.json").read_bytes())  # after the remake
    assert written.unknown_calls == 4 and written.stages[-1].redos.time_ms > 0
    (made.current / "costs.json").unlink()
    hmv.costs(made, tmp_path / "no-store.db")
    assert not (made.current / "costs.json").exists()
    video_costs.write_costs(made)
    assert (made.current / "costs.json").is_file()


def test_a_retired_transcription_is_read_from_its_attempt(tmp_path: Path) -> None:
    """A transcription whose result was retired (replaced) keeps its words under `attempts/<n>/output/`."""
    run = tmp_path / "run"
    output = run / "transcribe" / "item_song" / "attempts" / "1" / "output"
    output.mkdir(parents=True)
    call = HostedCall(model="m", url="https://a.test", request={}, reply={}, took_ms=1, cost_usd=0.02)
    (output / "transcribe.json").write_text(hmv.Words(words=[], call=call).model_dump_json())
    at = datetime.fromisoformat("2026-10-10T10:00:00.000Z")
    retired = video_costs.Attempt("r", "transcribe", 1, "first", at, at)
    assert video_costs._heard(run, retired, current=False) == [(retired, 0.02)]  # pyright: ignore[reportPrivateUsage]
    other = video_costs.Attempt("r", "transcribe", 2, "reruns", at, at)  # failed: nothing written
    assert video_costs._heard(run, other, current=False) == [(other, None)]  # pyright: ignore[reportPrivateUsage]


def test_a_project_not_started_cost_nothing(project: hmv.Project, tmp_path: Path) -> None:
    found = hmv.costs(project, tmp_path / "no-store.db")
    assert (found.hosted_usd, found.gpu_ms, found.cpu_ms, found.unknown_calls) == (0, 0, 0, 0)
    assert len(found.stages) == 10
