"""AC-51, AC-56 and AC-57: a plain-server model is refused on SageAttention; only Wan 14B wants it;
a clips session records the version (0025 §1, §2, §5)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

import hone_music_video as hmv
from hone_music_video.adapters import comfyui_server
from hone_music_video.adapters import hone_models as adapter
from tests.unit.test_hone_models_adapter import Media

pytestmark = pytest.mark.e2e


def _media(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[hmv.HoneModels, Media]:
    client = Media(tmp_path / "out.png")
    monkeypatch.setattr(adapter.mk, "image", lambda _model, registry: client)
    monkeypatch.setattr(adapter.mk, "video", lambda _model, registry: client)
    return hmv.HoneModels(), client


def test_ac51_an_image_model_on_a_sage_attention_server_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(adapter, "server_argv", lambda _url: ["main.py", "--use-sage-attention"])
    models, client = _media(monkeypatch, tmp_path)
    with (
        pytest.raises(hmv.ModelFailure, match="runs with --use-sage-attention"),
        models.session("qwen-image-edit-2511-4step"),
    ):
        pass
    assert client.opened == 0
    out = tmp_path / "made.png"
    with pytest.raises(hmv.ModelFailure, match="runs with --use-sage-attention"):
        models.generate("qwen-image-edit-2511-4step", "x", out=out, seed=1, inputs={})
    assert not out.exists()


def test_ac51_wan_runs_on_the_same_server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(adapter, "server_argv", lambda _url: ["main.py", "--use-sage-attention"])
    models, client = _media(monkeypatch, tmp_path)
    with models.session("wan2.2-i2v-14b"):
        pass
    assert client.opened == 1


def test_ac51_a_plain_server_or_none_is_used(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    models, client = _media(monkeypatch, tmp_path)
    monkeypatch.setattr(adapter, "server_argv", lambda _url: ["main.py"])
    with models.session("qwen-image-edit-2511-4step"):
        pass
    monkeypatch.setattr(adapter, "server_argv", lambda _url: None)
    with models.session("qwen-image-edit-2511-4step"):
        pass
    assert client.opened == 2


def test_server_argv_reads_system_stats_and_a_silence_is_none() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = (
                b"not-json"
                if self.path.startswith("/bad")
                else b'{"system": {"argv": ["main.py", "--use-sage-attention"]}}'
            )
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        assert comfyui_server.server_argv(url) == ["main.py", "--use-sage-attention"]
        assert comfyui_server.server_argv("http://127.0.0.1:9") is None
        assert comfyui_server.server_argv(url + "/bad") is None  # /bad/system_stats is not JSON
    finally:
        server.shutdown()
        server.server_close()


def test_ac56_only_the_wan_14b_workflow_wants_sage_attention(tmp_path: Path) -> None:
    models = hmv.HoneModels()
    assert models._sage_attention("wan2.2-i2v-14b")
    for model in (
        "esrgan-rife-x2",
        "qwen-image-edit-2511-4step",
        "qwen-image-2.1-turbo",
    ):
        assert not models._sage_attention(model)
    workflow = tmp_path / "wan5b.json"
    workflow.write_text(
        json.dumps(
            {"1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors"}}}
        )
    )
    config = SimpleNamespace(provider="comfyui", kind="video", workflow=workflow)
    models.__dict__["registry"] = SimpleNamespace(get=lambda _model: config)
    assert not models._sage_attention("wan-5b")


def test_ac57_a_clips_session_records_the_sage_attention_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def python(version: str) -> Path:
        script = tmp_path / f"python-{version}"
        script.write_text(f"#!/bin/sh\necho {version}\n")
        script.chmod(0o755)
        return script

    models, _client = _media(monkeypatch, tmp_path)
    monkeypatch.setenv(comfyui_server.PYTHON, str(python("2.2.0")))
    out = tmp_path / "clip.mp4"
    with models.session("wan2.2-i2v-14b"):
        made = models.generate("wan2.2-i2v-14b", "x", out=out, seed=1, inputs={})
    assert made.recorded == {"sage_attention": "2.2.0"}
    monkeypatch.setenv(comfyui_server.PYTHON, str(python("1.0.6")))
    with models.session("wan2.2-i2v-14b"):
        again = models.generate("wan2.2-i2v-14b", "x", out=out, seed=1, inputs={})
    assert again.recorded == {"sage_attention": "1.0.6"}
    monkeypatch.delenv(comfyui_server.PYTHON)
    monkeypatch.setenv(adapter.START, "~/start_comfyui.sh")
    with models.session("wan2.2-i2v-14b"):
        unknown = models.generate("wan2.2-i2v-14b", "x", out=out, seed=1, inputs={})
    assert unknown.recorded == {"sage_attention": "unknown"}
    image = models.generate("qwen-image-edit-2511-4step", "x", out=tmp_path / "pic.png", seed=1, inputs={})
    assert image.recorded is None
