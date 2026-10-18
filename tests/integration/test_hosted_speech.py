"""The in-library transcription client (D-002, D-017) against a local stand-in gateway, with ffmpeg."""

import http.client
import urllib.request
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video.adapters import hosted_speech
from hone_music_video.adapters.hone_models import load_registry
from hone_music_video.testing import make_song
from tests.speech_server import KEY, SpeechServer, serving

WORDS = [("she", 0.5, 0.9004), ("waits", 1.0, 1.0), ("upon", 1.2, 1.75)]


def fields(body: bytes) -> dict[str, str]:
    """The text fields of a multipart body, by name (the file left out)."""
    found: dict[str, str] = {}
    for part in body.split(b"\r\n--")[:-1]:
        head, _, value = part.partition(b"\r\n\r\n")
        name = head.split(b'name="')[1].split(b'"')[0].decode()
        if b"filename=" not in head:
            found[name] = value.removesuffix(b"\r\n").decode()
    return found


def test_the_request_and_the_words_in_milliseconds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 2000)
    with serving(monkeypatch, SpeechServer(words=WORDS, duration=2.0)) as server:
        words = hmv.HoneModels().transcribe("whisper-1", song, language="en", prompt="she waits upon")
    request = server.requests[0]
    assert request["path"] == "/v1/audio/transcriptions"
    assert request["headers"]["Authorization"] == f"Bearer {KEY}"
    assert fields(request["body"]) == {
        "model": "whisper-1",
        "response_format": "verbose_json",
        "timestamp_granularities[]": "word",
        "language": "en",
        "prompt": "she waits upon",
    }
    assert song.read_bytes() in request["body"]
    # seconds become integer ms; a word heard without length gets 1 ms (D-017)
    assert [(w.text, w.start_ms, w.end_ms) for w in words.words] == [
        ("she", 500, 900),
        ("waits", 1000, 1001),
        ("upon", 1200, 1750),
    ]
    assert words.language == "en"
    call = words.call
    assert call is not None and call.model == "whisper-1" and call.url == server.url + "/audio/transcriptions"
    assert call.request["file"]["bytes"] == song.stat().st_size and call.request["prompt"] == "she waits upon"
    assert call.reply == server.reply() and call.took_ms >= 0 and call.cost_usd == pytest.approx(0.0002)


def test_scribe_on_the_gateway_has_the_same_request_and_reply(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    song = make_song(tmp_path / "song.wav", 2000)
    scribe = [{"word": "she", "start": 0.64, "end": 0.8, "speaker_id": "speaker_0"}]
    estimate = {"unit": "0.0006110000", "irt": 162.5}
    server = SpeechServer(
        duration=None, extra={"words": scribe, "language": "fas", "estimated_cost": estimate}
    )
    with serving(monkeypatch, server):
        words = hmv.HoneModels().transcribe("scribe_v2", song, language=None, prompt="she")
    assert fields(server.requests[0]["body"])["model"] == "scribe_v2"  # the same fields as whisper-1 (D-048)
    assert [(w.text, w.start_ms, w.end_ms) for w in words.words] == [("she", 640, 800)]
    assert words.language == "fas" and words.call is not None
    assert words.call.cost_usd == pytest.approx(0.000611)  # the gateway's own estimate, when it sends one


def test_without_the_gateways_estimate_only_whisper_1_is_priced(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    song = make_song(tmp_path / "song.wav", 2000)
    with serving(monkeypatch, SpeechServer(words=WORDS, duration=2.0)):
        words = hmv.HoneModels().transcribe("groq.whisper-large-v3", song, language=None, prompt=None)
    assert words.call is not None and words.call.cost_usd is None  # its price is not whisper-1's


def test_a_song_over_the_upload_limit_is_sent_as_a_smaller_mp3(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    song = make_song(tmp_path / "song.wav", 3000)
    monkeypatch.setattr(hosted_speech, "MAX_UPLOAD_BYTES", song.stat().st_size - 1)
    with serving(monkeypatch, SpeechServer(words=WORDS)) as server:
        words = hmv.HoneModels().transcribe("whisper-1", song, language=None, prompt=None)
    assert words.call is not None and words.call.request["file"]["name"] == "song-mono.mp3"
    assert words.call.request["file"]["bytes"] < song.stat().st_size
    assert b"audio/mpeg" in server.requests[0]["body"]
    assert "language" not in fields(server.requests[0]["body"])
    assert words.language == "english"  # as the service named it, when none was asked for
    assert sorted(p.name for p in tmp_path.iterdir()) == ["song.wav"]  # the copy is gone


def test_failures_name_the_cause_and_never_the_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 1000)
    with serving(monkeypatch, SpeechServer(status=401)), pytest.raises(hmv.ModelFailure) as caught:
        hmv.HoneModels().transcribe("whisper-1", song, language=None, prompt=None)
    assert "HTTP 401" in str(caught.value) and KEY not in str(caught.value) and "***" in str(caught.value)


def test_a_reply_without_words_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 1000)
    server = SpeechServer(words=WORDS)
    monkeypatch.setattr(server, "reply", lambda: {"text": "x", "segments": [], "words": None})
    with (
        serving(monkeypatch, server),
        pytest.raises(hmv.ModelFailure, match="ignored timestamp_granularities"),
    ):
        hmv.HoneModels().transcribe("whisper-1", song, language=None, prompt=None)
    monkeypatch.setattr(server, "reply", lambda: {"words": [{"word": "x"}]})
    with (
        serving(monkeypatch, server),
        pytest.raises(hmv.ModelFailure, match="without its text, start or end"),
    ):
        hmv.HoneModels().transcribe("whisper-1", song, language=None, prompt=None)


def test_a_missing_key_or_service_is_named(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 1000)
    with serving(monkeypatch, SpeechServer()):
        monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY")
        with pytest.raises(hmv.ModelFailure, match="set the environment variable OPENAI_COMPATIBLE_API_KEY"):
            hmv.HoneModels().transcribe("whisper-1", song, language=None, prompt=None)
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", KEY)
    monkeypatch.setenv("OPENAI_COMPATIBLE_BASE_URL", "http://127.0.0.1:9/v1")  # the discard port
    with pytest.raises(hmv.ModelFailure, match="could not be reached"):
        hmv.HoneModels().transcribe("whisper-1", song, language=None, prompt=None)


def test_ffmpeg_missing_or_failing_is_named(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 1000)
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(hmv.ToolMissing, match="ffmpeg is not installed; install it to send a song over"):
        hosted_speech.smaller_copy(song, tmp_path)
    monkeypatch.undo()
    broken = tmp_path / "broken.wav"
    broken.write_bytes(b"not audio")
    with pytest.raises(hmv.ModelFailure, match=r"could not make a smaller copy of broken\.wav to transcribe"):
        hosted_speech.smaller_copy(broken, tmp_path)


def test_no_base_url_is_named(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = load_registry().get("whisper-1").model_copy(update={"base_url": None})
    no_url = "model 'whisper-1' has no base URL; set OPENAI_COMPATIBLE_BASE_URL"
    with pytest.raises(hmv.ModelFailure, match=no_url):
        hosted_speech.transcribe(config, make_song(tmp_path / "song.wav", 1000))


def test_a_reply_that_is_no_json_object_fails_without_the_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    song = make_song(tmp_path / "song.wav", 1000)
    server = SpeechServer()
    monkeypatch.setattr(server, "reply", lambda: [f"echo {KEY}"])
    with serving(monkeypatch, server), pytest.raises(hmv.ModelFailure) as caught:
        hmv.HoneModels().transcribe("whisper-1", song, language=None, prompt=None)
    assert "sent no JSON object" in str(caught.value) and KEY not in str(caught.value)


def test_a_cut_off_reply_is_a_model_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 1000)

    def cut_off(*_args: object, **_kwargs: object) -> object:
        raise http.client.IncompleteRead(b"{")

    with serving(monkeypatch, SpeechServer()):
        monkeypatch.setattr(urllib.request, "urlopen", cut_off)
        with pytest.raises(hmv.ModelFailure, match="could not be reached: IncompleteRead"):
            hmv.HoneModels().transcribe("whisper-1", song, language=None, prompt=None)
