# pyright: reportUnnecessaryIsInstance=false
# (an implementation under test may break its declared types; that is what the checks catch)
"""The contract of the `Models` port: what every implementation (the fake included) must do."""

from __future__ import annotations

import itertools
from pathlib import Path

from hone_music_video.errors import NotFound
from hone_music_video.ports import Generated, Models
from hone_music_video.records import AlignedWord, Word, Words
from hone_music_video.testing.media import make_song
from hone_music_video.timed_lyrics import LyricsEdit

HEARD = [Word(text=t, start_ms=500 + 800 * n, end_ms=1100 + 800 * n) for n, t in enumerate(("one", "two"))]


def _expect(condition: bool, rule: str) -> None:
    if not condition:
        raise AssertionError(f"Models contract: {rule}")


def check_transcribe(models: Models, folder: Path, model_id: str = "test-model") -> None:
    """Transcription gives every heard word with start before end, in milliseconds."""
    song = make_song(folder / "contract-song.wav", 4000)
    heard = models.transcribe(model_id, song, language="en", prompt="one two three")
    _expect(isinstance(heard, Words), "transcribe returns Words")
    _expect(all(w.start_ms < w.end_ms for w in heard.words), "every heard word has start_ms < end_ms")


def check_plan(models: Models, folder: Path, model_id: str = "test-model") -> None:
    """A planner call returns an instance of the schema it was given."""
    heard = [{"i": i} | w.model_dump() for i, w in enumerate(HEARD)]
    data = {"duration_ms": 4000, "language": "en", "heard_words": heard}
    plan = models.plan(model_id, system="Edit the lyrics.", data=data, images=[], schema=LyricsEdit)
    _expect(isinstance(plan, LyricsEdit), "plan returns an instance of the schema")


def check_generate(models: Models, folder: Path, model_id: str = "test-model") -> None:
    """A media job inside a session writes its file to `out` and reports the seed it used."""
    out = folder / "contract-image.png"
    with models.session(model_id):
        made = models.generate(model_id, "a lighthouse", out=out, seed=7, inputs={"size": "64x64"})
    _expect(isinstance(made, Generated), "generate returns Generated")
    _expect(made.path == out and out.is_file(), "generate writes its file to `out`")
    _expect(made.seed == 7, "generate reports the seed it used")


def check_separate(models: Models, folder: Path, model_id: str = "test-model") -> None:
    """Vocal isolation writes the vocals of the audio to `out` and returns that path (D-041, D-045)."""
    piece = make_song(folder / "contract-slice.wav", 2000)
    out = folder / "contract-vocals.wav"
    vocals = models.separate_vocals(model_id, piece, out=out)
    _expect(vocals == out and out.is_file(), "separate_vocals writes the vocals to `out`")


def check_align(models: Models, folder: Path, model_id: str = "test-model") -> None:
    """Alignment gives each line's words in order, with start before end, in milliseconds (0005)."""
    song = make_song(folder / "contract-sung.wav", 4000)
    timed = models.align(model_id, song, ["one two", "three"])
    _expect(isinstance(timed, list) and len(timed) == 2, "align returns one list of words per line")
    _expect([len(line) for line in timed] == [2, 1], "align gives each line its own words")
    _expect(models.align(model_id, song, []) == [], "align of no lines gives no lines")
    words = [w for line in timed for w in line]
    _expect(all(w.start_ms < w.end_ms for w in words), "every aligned word has start_ms < end_ms")
    _expect(all(isinstance(w, AlignedWord) for w in words), "every aligned word has its score")
    _expect(all(a.start_ms <= b.start_ms for a, b in itertools.pairwise(words)), "aligned words are in order")


def check_image_models(models: Models) -> None:
    """The frame's image models (0027): each listed once, each one's info the same as `image_info`'s, no
    negative reference limit, sizes written WxH; an unknown id is `NotFound`."""
    found = models.image_models()
    ids = [i.id for i in found]
    _expect(len(set(ids)) == len(ids), "image_models lists each model once")
    _expect(all(models.image_info(i.id) == i for i in found), "image_info agrees with image_models")
    _expect(all((i.max_references or 0) >= 0 for i in found), "a model's reference limit is not negative")
    _expect(all("x" in s for i in found for s in i.sizes), "a size is written WxH")
    try:
        models.image_info("no-such-model-for-the-contract")
    except NotFound:
        pass
    else:
        raise AssertionError("image_info of an unknown id raises NotFound")


def check_models(models: Models, folder: Path, *, model_id: str = "test-model") -> None:
    """Raise `AssertionError` when `models` breaks the port's contract. Writes only inside `folder`."""
    check_transcribe(models, folder, model_id)
    check_plan(models, folder, model_id)
    check_generate(models, folder, model_id)
    check_separate(models, folder, model_id)
    check_align(models, folder, model_id)
    check_image_models(models)
