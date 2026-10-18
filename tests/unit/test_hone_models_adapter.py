"""`HoneModels` sends each call to the right hone-models client (the clients are stood in for here)."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.adapters import hone_models as adapter


class Text:
    def __init__(self, parsed: Any, error: str | None = None) -> None:
        self.parsed, self.error = parsed, error
        self.sent: Any = None
        self.trace: Any = None

    def complete(self, messages: Any, *, schema: Any, trace: Any) -> Any:
        self.sent, self.trace = messages, trace
        return SimpleNamespace(parsed=self.parsed, error=self.error)


class Media:
    def __init__(self, path: Path | None, error: str | None = None) -> None:
        self.path, self.error, self.opened = path, error, 0
        self.traces: list[Any] = []

    def generate(self, prompt: str, *, out: Path, seed: int, trace: Any, **inputs: Any) -> Any:
        self.traces.append(trace)
        return SimpleNamespace(path=self.path, seed=seed, error=self.error, error_kind="failed")

    @contextmanager
    def session(self) -> Generator[None]:
        self.opened += 1
        yield


def test_plan_sends_data_as_json_and_images_as_parts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    text = Text({"shots": []})
    monkeypatch.setattr(adapter.mk, "text", lambda _model, registry: text)
    plan = hmv.HoneModels().plan(
        "planner",
        system="rules",
        data={"settings": {"fps": 32}},
        images=[tmp_path / "a.png"],
        schema=hmv.Shots,
    )
    assert plan == hmv.Shots(shots=[])
    system, user = text.sent
    assert system == {"role": "system", "content": "rules"}
    assert user["content"] == [
        {"type": "text", "text": '{"settings": {"fps": 32}}'},
        {"type": "image", "path": str(tmp_path / "a.png")},
    ]
    assert text.trace is None  # outside a run's step: no context, hone-models uses its own


STEP_TRACE = {
    "traceparent": "00-" + "a" * 32 + "-" + "b" * 16 + "-01",
    "hone.run_id": "r1",
    "hone.step": "lyrics",
}


def test_calls_pass_the_steps_trace_so_their_records_name_the_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """D-061: inside a step, hone-flow's trace context goes to hone-models, so its span of the call
    carries `hone.run_id` and `hone.step` (the cost summary finds the call by them)."""
    text, media = Text({"shots": []}), Media(tmp_path / "out.png")
    monkeypatch.setattr(adapter.mk, "text", lambda _model, registry: text)
    monkeypatch.setattr(adapter.mk, "image", lambda _model, registry: media)
    monkeypatch.setattr(adapter.fk, "current_trace", lambda: dict(STEP_TRACE))
    models = hmv.HoneModels()
    models.plan("planner", system="s", data={}, images=[], schema=hmv.Shots)
    models.generate("z-image-turbo", "x", out=tmp_path / "out.png", seed=1, inputs={})
    assert text.trace == STEP_TRACE and media.traces == [STEP_TRACE]


def test_plan_keeps_the_calls_cost_from_the_registry_price(monkeypatch: pytest.MonkeyPatch) -> None:
    """A re-plan stores what its calls cost (0008, D-073): the model's price times the call's usage."""
    usage = {"input_tokens": 200_000, "output_tokens": 10_000}
    reply = SimpleNamespace(parsed={"shots": []}, error=None, usage=usage)
    client = SimpleNamespace(complete=lambda _messages, schema, trace=None: reply)
    monkeypatch.setattr(adapter.mk, "text", lambda _model, registry: client)
    models = hmv.HoneModels()
    price = SimpleNamespace(input_per_mtok=1.25, output_per_mtok=10.0)
    config = SimpleNamespace(capabilities=SimpleNamespace(price=price))
    models.__dict__["registry"] = SimpleNamespace(get=lambda _model: config)  # the cached registry
    models.plan("planner", system="rules", data={}, images=[], schema=hmv.Shots)
    assert models.last_plan_cost_usd == pytest.approx(0.35)  # 0.2 M in at $1.25, 0.01 M out at $10
    reply.usage = {}
    models.plan("planner", system="rules", data={}, images=[], schema=hmv.Shots)
    assert models.last_plan_cost_usd is None  # no usage: not known


FAILURES = [(None, "too long", "too long"), ({"shots": 3}, None, "invalid")]


@pytest.mark.parametrize(("parsed", "error", "match"), FAILURES)
def test_plan_failures_raise(
    monkeypatch: pytest.MonkeyPatch, parsed: Any, error: str | None, match: str
) -> None:
    monkeypatch.setattr(adapter.mk, "text", lambda _model, registry: Text(parsed, error))
    with pytest.raises(hmv.ModelFailure, match=match):
        hmv.HoneModels().plan("planner", system="s", data={}, images=[], schema=hmv.Shots)


def test_generate_and_session_use_the_media_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    made_clients: list[Media] = []

    def image(_model: str, registry: Any) -> Media:
        made_clients.append(Media(tmp_path / "out.png"))
        return made_clients[-1]

    monkeypatch.setattr(adapter.mk, "image", image)
    models = hmv.HoneModels()
    with models.session("z-image-turbo"):
        for seed in (3, 4):
            made = models.generate(
                "z-image-turbo", "a lighthouse", out=tmp_path / "out.png", seed=seed, inputs={}
            )
    assert made == hmv.Generated(path=tmp_path / "out.png", seed=4)
    assert len(made_clients) == 1 and made_clients[0].opened == 1  # one load for the stage (D-005)
    monkeypatch.setattr(adapter.mk, "image", lambda _model, registry: Media(None, "out of memory"))
    with pytest.raises(hmv.ModelFailure, match="out of memory"):
        models.generate("z-image-turbo", "x", out=tmp_path / "x.png", seed=1, inputs={})


def test_the_registry_is_catalog_library_user_then_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    models = hmv.HoneModels()
    assert models._media("wan2.2-i2v-14b").kind == "video"  # pyright: ignore[reportPrivateUsage]
    assert models._media("z-image-turbo").kind == "image"  # pyright: ignore[reportPrivateUsage]
    home, folder = tmp_path / "home", tmp_path / "folder"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(tmp_path)  # neither file yet
    found = adapter.load_registry()
    assert found.get("qwen-image-edit-2511-4step").workflow.endswith("qwen-image-edit-2511-4step.json")
    assert found.get("claude-opus-5-5").api_key_env == "OPENAI_COMPATIBLE_API_KEY"  # the library's entries
    judge = found.get("claude-sonnet-5-5")  # the start-frame check of new projects (D-110)
    assert judge.api_key_env == "OPENAI_COMPATIBLE_API_KEY" and judge.capabilities.vision
    assert (judge.capabilities.price.input_per_mtok, judge.capabilities.price.output_per_mtok) == (2.0, 10.0)
    assert judge.defaults["max_tokens"] == 32000 and judge.max_timeout_s == 900.0  # a check takes ~110 s
    cheap = found.get("claude-haiku-5-5")  # still there for projects that choose it (D-086)
    assert cheap.capabilities.vision and cheap.capabilities.price.input_per_mtok == 0.10
    user = home / ".config" / "hone" / "models.toml"
    user.parent.mkdir(parents=True)
    polish, planner = '[models."esrgan-rife-x2"]', '[models."claude-opus-5-5"]'
    user.write_text(f"{polish}\nmax_timeout_s = 7.0\n{planner}\nmax_timeout_s = 8.0\n")
    folder.mkdir()
    (folder / "hone-models.toml").write_text('[models."esrgan-rife-x2"]\nmax_timeout_s = 9.0\n')
    monkeypatch.chdir(folder)
    found = adapter.load_registry()
    assert found.get("claude-opus-5-5").max_timeout_s == 8.0  # the user's file wins over the library
    assert found.get("esrgan-rife-x2").max_timeout_s == 9.0  # the folder's file wins over both
    assert found.get("esrgan-rife-x2").workflow  # what they leave out stays


def test_the_planner_has_time_to_write_a_whole_song_plan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)  # only the catalog and the library's entries
    planner = adapter.load_registry().get("claude-opus-5-5")
    timeout_s = min(
        planner.max_timeout_s, 2 * planner.defaults["max_tokens"] / planner.capabilities.speed_tok_s
    )
    assert timeout_s >= 1200  # hone-models gives a hosted model without a speed 120 s (D-028)
    assert planner.defaults["max_tokens"] >= 60_000  # a 50-shot plan is ~25k tokens; room for a repair


def test_a_wan_session_starts_comfyui_with_sage_attention(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-033: the flag is added to HONE_COMFYUI_START while a Wan session starts the server; the finish
    (no diffusion model, no attention to speed up) and the image models start ComfyUI as configured."""
    seen: list[str] = []

    class Seen(Media):
        @contextmanager
        def session(self) -> Generator[None]:
            seen.append(adapter.os.environ.get(adapter.START, ""))
            yield

    monkeypatch.setattr(adapter.mk, "video", lambda _model, registry: Seen(None))
    monkeypatch.setattr(adapter.mk, "image", lambda _model, registry: Seen(None))
    monkeypatch.setenv(adapter.START, "~/start_comfyui.sh --port 8188")
    models = hmv.HoneModels()
    for model in ("wan2.2-i2v-14b", "esrgan-rife-x2", "qwen-image-edit-2511-4step"):
        with models.session(model):
            pass
    flagged, plain = "~/start_comfyui.sh --port 8188 --use-sage-attention", "~/start_comfyui.sh --port 8188"
    assert seen == [flagged, plain, plain]
    assert adapter.os.environ[adapter.START] == "~/start_comfyui.sh --port 8188"  # put back
    monkeypatch.setenv(adapter.START, flagged)
    with models.session("wan2.2-i2v-14b"):
        pass
    assert seen[-1] == flagged  # never twice


class NoStart(Media):
    @contextmanager
    def session(self) -> Generator[None]:
        raise adapter.mk.errors.ProviderError("HONE_COMFYUI_START exited with code 1 before answering")
        yield


def test_comfyui_that_does_not_start_with_sage_attention_says_what_to_do(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter.mk, "video", lambda _model, registry: NoStart(None))
    monkeypatch.setenv(adapter.START, "~/start_comfyui.sh")
    models = hmv.HoneModels()
    sage = "install sageattention in ComfyUI's Python"
    with pytest.raises(hmv.ModelFailure, match=sage), models.session("wan2.2-i2v-14b"):
        pass
    no_flag = pytest.raises(adapter.mk.errors.ProviderError, match="exited with code 1")
    with no_flag, models.session("esrgan-rife-x2"):  # no flag added: the error as it is
        pass
