"""The in-library hosted transcription client: the one temporary exception to "every model call goes
through hone-models" (decision D-002), until hone-models' change 0019 lands.

`transcribe` takes what hone-models' `Transcriber.transcribe` takes (the audio, `language`, `prompt`) and
returns its `mk.Transcript`, reading the URL, key variable and model name from the same registry entry,
so switching to `mk.transcriber(model_id)` changes one place (`HoneModels.transcribe`). It sends
`POST {base_url}/audio/transcriptions` (`verbose_json`, word timestamps, D-017) with the standard
library, and returns the call as a `HostedCall` too: the request without the key, the reply, the time
and the price."""

from __future__ import annotations

import hashlib
import http.client
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import hone_models as mk
from hone_models.registry import ModelConfig

from hone_music_video.errors import ModelFailure, ToolMissing
from hone_music_video.records import HostedCall

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # OpenAI's limit for /audio/transcriptions, assumed for the gateway
PRICE_PER_SECOND = 0.0001  # USD per second of audio: whisper-1's list price (0.006 per minute)
TIMEOUT_S = 600.0


def _form(fields: list[tuple[str, str]], audio: Path) -> tuple[bytes, str]:
    """A multipart/form-data body and its content type."""
    boundary = uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        for name, value in fields
    ]
    kind = mimetypes.guess_type(audio.name)[0] or "application/octet-stream"
    head = f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{audio.name}"\r\n'
    parts.append(f"{head}Content-Type: {kind}\r\n\r\n".encode() + audio.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def smaller_copy(audio: Path, folder: Path) -> Path:
    """A mono 64 kbit/s MP3 of `audio` in `folder` (a five-minute song is about 2.4 MB), for a file over
    the upload limit (D-017). Times are unchanged: the encoder's delay is written in the file's header."""
    if shutil.which("ffmpeg") is None:
        raise ToolMissing("ffmpeg is not installed; install it to send a song over 25 MB to the transcriber")
    out = folder / f"{audio.stem}-mono.mp3"
    done = subprocess.run(  # noqa: S603 - a fixed program and paths we made
        ["ffmpeg", "-v", "error", "-y", "-i", str(audio), "-vn", "-ac", "1", "-b:a", "64k", str(out)],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise ModelFailure(
            f"could not make a smaller copy of {audio.name} to transcribe: {done.stderr.strip()}"
        )
    return out


def api_key(config: ModelConfig) -> str:
    name = config.api_key_env
    key = os.environ.get(name) if name else None
    if not key:
        raise ModelFailure(f"model {config.id!r} needs an API key: set the environment variable {name}")
    return key


def transcribe(
    config: ModelConfig, audio: Path, *, language: str | None = None, prompt: str | None = None
) -> tuple[mk.Transcript, HostedCall]:
    """Every heard word with its times in seconds (`mk.Transcript.words`), and the call as it was made;
    `prompt` biases the words. A file over the upload limit is sent as a smaller copy (D-017)."""
    if not config.base_url:
        where = config.base_url_env or "base_url in the registry"
        raise ModelFailure(f"model {config.id!r} has no base URL; set {where}")
    if audio.stat().st_size <= MAX_UPLOAD_BYTES:
        return _send(config, audio, language, prompt)
    with tempfile.TemporaryDirectory(dir=audio.parent, prefix=".transcribe-") as tmp:
        return _send(config, smaller_copy(audio, Path(tmp)), language, prompt)


def _send(
    config: ModelConfig, audio: Path, language: str | None, prompt: str | None
) -> tuple[mk.Transcript, HostedCall]:
    # The gateway answers only the last granularity asked for, so words are asked for alone (D-017)
    fields = [
        ("model", config.name),
        ("response_format", "verbose_json"),
        ("timestamp_granularities[]", "word"),
    ]
    fields += [(name, value) for name, value in (("language", language), ("prompt", prompt)) if value]
    body, kind = _form(fields, audio)
    url = f"{str(config.base_url).rstrip('/')}/audio/transcriptions"
    key = api_key(config)
    request = urllib.request.Request(  # noqa: S310 - the registry's https URL
        url, data=body, method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": kind}
    )
    started = time.monotonic()
    reply = _reply(request, key)
    took_ms = round((time.monotonic() - started) * 1000)
    heard = _transcript(config, reply, language)
    cost = _cost(config, reply, heard.duration_s)
    sent = dict(fields) | {"file": _described(audio)}
    call = HostedCall(model=config.id, url=url, request=sent, reply=reply, took_ms=took_ms, cost_usd=cost)
    return heard, call


def _cost(config: ModelConfig, reply: dict[str, Any], duration_s: float | None) -> float | None:
    """the gateway's own estimate in USD when the reply has one (it matched whisper-1's list price, D-017;
    Scribe's replies have it, D-048), else whisper-1's list price for whisper-1, else unknown."""
    estimate: Any = reply.get("estimated_cost")
    try:
        return round(float(estimate["unit"]), 6)
    except (TypeError, KeyError, ValueError):
        pass
    return round(PRICE_PER_SECOND * duration_s, 6) if duration_s and config.name == "whisper-1" else None


def _described(audio: Path) -> dict[str, Any]:
    data = audio.read_bytes()
    return {"name": audio.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _reply(request: urllib.request.Request, key: str) -> dict[str, Any]:
    """The service's JSON reply; a failure names the status and the service's message, never the key."""
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as answer:  # noqa: S310
            text = answer.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", "replace")[:500].replace(key, "***")
        raise ModelFailure(f"the transcriber answered HTTP {error.code}: {message}") from None
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as error:
        raise ModelFailure(
            f"the transcriber could not be reached: {str(error).replace(key, '***')}"
        ) from None
    try:
        reply = json.loads(text)
    except ValueError:
        reply = None
    if not isinstance(reply, dict):
        raise ModelFailure(f"the transcriber sent no JSON object: {text[:200].replace(key, '***')!r}")
    return reply  # pyright: ignore[reportUnknownVariableType]


def _s(seconds: Any) -> float:
    return round(float(seconds), 3)


def _transcript(config: ModelConfig, reply: dict[str, Any], language: str | None) -> mk.Transcript:
    """The reply as hone-models' `Transcript` (seconds rounded to milliseconds, as hone-models does)."""
    found: list[dict[str, Any]] = reply.get("words") or []
    if not isinstance(reply.get("words"), list):
        raise ModelFailure("the transcriber sent no words (it ignored timestamp_granularities[]=word)")
    try:
        heard = [mk.Word(str(w["word"]).strip(), _s(w["start"]), _s(w["end"])) for w in found]
    except (KeyError, TypeError, ValueError):
        raise ModelFailure("the transcriber sent a word without its text, start or end") from None
    duration = reply.get("duration")
    return mk.Transcript(
        text=str(reply.get("text") or ""),
        language=language or reply.get("language"),
        duration_s=round(float(duration), 3) if duration is not None else None,
        segments=[],
        model=config.name,
        span_id="",
        words=heard,
    )
