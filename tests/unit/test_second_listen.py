"""Listening again (design §6 step 1b, D-040, D-046): each gap in windows of at most 30 s, each window's
slice to the same transcriber with the lines expected in it as the prompt, then the same slice of the
song's vocals when that is not enough; a warning where a given line still not heard may be sung in a
span marked instrumental."""

import sys
import wave
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video import second_listen, stages_plan
from hone_music_video._jobs import Job
from hone_music_video.adapters.vocals import INSTALL
from hone_music_video.events import EventLog
from hone_music_video.lyrics_match import Gap, lines_found
from hone_music_video.second_listen import MAX_LISTENS, windows
from hone_music_video.testing import Call, FakeModels, make_song

SONG = hmv.Song(duration_ms=20_000, sample_rate=44100, channels=1)
LYRICS = "first line here\n[Verse 1]\nthe missing line\n\nlast line here"


def heard(*texts: str, at: int = 1000) -> list[hmv.Word]:
    """Words a second apart, each 800 ms long, from `at`."""
    return [hmv.Word(text=t, start_ms=at + 1000 * n, end_ms=at + 1000 * n + 800) for n, t in enumerate(texts)]


FIRST_AND_LAST = heard("first", "line", "here") + heard("last", "line", "here", at=15000)


def job(project: hmv.Project, models: FakeModels) -> Job:
    """The stages as they time lines from the heard words: the given lyrics not aligned (0005)."""
    settings = project.settings
    settings = settings.model_copy(update={"models": settings.models.model_copy(update={"align": None})})
    return Job(project, models, settings, EventLog(project.events_file))


class Listener(FakeModels):
    """Hears `song_words` in the whole song (or its vocals); in a slice whose name starts with one of
    `hears` (`slice-`: of the mix, `vocals-`: of the vocals), the prompt's words (FakeModels); in any
    other slice, nothing."""

    def __init__(self, song_words: list[hmv.Word], hears: tuple[str, ...] = ("slice-",), **kwargs: Any):
        super().__init__(**kwargs)
        self.song_words, self.hears = song_words, hears

    def transcribe(
        self, model_id: str, audio: Path, *, language: str | None, prompt: str | None
    ) -> hmv.Words:
        found = super().transcribe(model_id, audio, language=language, prompt=prompt)
        if audio.name.startswith(self.hears):
            return found
        piece = audio.name.startswith(("slice-", "vocals-"))
        return hmv.Words(words=[] if piece else self.song_words)


def on_vocals(project: hmv.Project, call: Call) -> bool:
    """The call heard the whole song's vocals, kept in the project (D-045)."""
    return call.images[0].parent == project.vocals_dir


def listened(project: hmv.Project) -> list[str]:
    events, _ = EventLog(project.events_file).read()
    return [e["listen"] for e in events if e["event"] == "listened_again"]


# ------------------------------------------------------------------------------ the slice


def test_the_slice_is_cut_from_the_song(song: Path, tmp_path: Path) -> None:
    piece = second_listen.cut(song, 2500, 7000, tmp_path / "slice.wav")
    with wave.open(str(piece), "rb") as audio:
        assert (audio.getnchannels(), audio.getframerate(), audio.getnframes()) == (1, 16000, 4500 * 16)


def test_cutting_needs_ffmpeg(monkeypatch: pytest.MonkeyPatch, song: Path, tmp_path: Path) -> None:
    monkeypatch.setattr(second_listen.shutil, "which", lambda _name: None)
    with pytest.raises(hmv.ToolMissing, match="ffmpeg is not installed"):
        second_listen.cut(song, 0, 1000, tmp_path / "slice.wav")


def test_a_cut_that_fails_names_the_song(song: Path, tmp_path: Path) -> None:
    with pytest.raises(hmv.ModelFailure, match=r"could not cut song\.wav at 0-1000 ms"):
        second_listen.cut(song, 0, 1000, tmp_path / "missing" / "slice.wav")


# ------------------------------------------------------------------------------ the second listen


def test_a_line_not_heard_is_heard_on_its_slice(project: hmv.Project, song: Path) -> None:
    models = Listener(FIRST_AND_LAST)
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    first, again = models.calls_of("transcribe")
    assert first.prompt.startswith("first line here the missing line") and on_vocals(project, first)
    assert (again.prompt, again.images[0].name) == ("the missing line", "slice-3300-15500.wav")
    sliced = [w.start_ms for w in words.words if w.text in {"the", "missing"}]
    assert len(sliced) == 2 and all(3800 <= a < 15000 for a in sliced)  # inside the gap, in song time
    texts = [w.text for w in words.words]
    assert texts == ["first", "line", "here", "the", "missing", "line", "last", "line", "here"]
    assert [(n.lines, n.gap_start_ms, n.gap_end_ms, n.heard, n.vocals) for n in words.listened_again] == [
        (["the missing line"], 3800, 15000, 3, None)
    ]
    assert len(models.calls_of("separate")) == 1 and words.not_listened == []  # the song's, once
    assert len(models.calls_of("transcribe")) == 2  # found: no third listen
    assert listened(project) == ["second"]
    assert not list(song.parent.glob(".listen-again-*"))  # the slices are not kept


def test_nothing_more_happens_when_every_line_is_heard(project: hmv.Project, song: Path) -> None:
    models = FakeModels()  # hears the prompt: every given line
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert [c.kind for c in models.calls] == ["separate", "transcribe"]
    assert words.listened_again == [] and words.not_listened == [] and words.retried is None


def short_gaps(groups: int) -> tuple[str, list[hmv.Word]]:
    """Lyrics of `groups` found lines each followed by a missing one, and the words of the found ones:
    gaps of 300 ms, so a slice (with its 500 ms margins) is mostly margin."""
    lines = [f"found {n} here\nmissing {n} words" for n in range(groups)]
    found = [
        hmv.Word(text=t, start_ms=2000 * n + 600 * k, end_ms=2000 * n + 600 * k + 500)
        for n in range(groups)
        for k, t in enumerate(("found", str(n), "here"))
    ]
    return "\n".join(lines), found


def test_listens_again_are_capped(project: hmv.Project, song: Path) -> None:
    lyrics, found = short_gaps(MAX_LISTENS // 2 + 2)  # a second and a third listen each: two too many
    models = Listener(found, hears=())  # the slices of the mix and of the vocals hear nothing
    words = stages_plan.transcribe(job(project, models), song, SONG, lyrics)
    assert len(words.listened_again) == MAX_LISTENS  # and the first listen, made twice (D-047)
    assert len(models.calls_of("transcribe")) == 2 + MAX_LISTENS
    gap_lines = [n.lines for n in words.listened_again[::2]]
    assert gap_lines == [[f"missing {n} words"] for n in range(MAX_LISTENS // 2)]
    assert words.not_listened == [
        "windows 0:17.700-0:18.000, 0:19.700-0:20.000 not listened to again (at most 16 listens per song)"
    ]


def test_the_vocals_listen_dropped_by_the_cap_is_named(
    monkeypatch: pytest.MonkeyPatch, project: hmv.Project, song: Path
) -> None:
    monkeypatch.setattr(second_listen, "MAX_LISTENS", 3)
    lyrics, found = short_gaps(2)
    words = stages_plan.transcribe(job(project, Listener(found, hears=())), song, SONG, lyrics)
    assert [n.vocals is not None for n in words.listened_again] == [False, True, False]
    assert words.not_listened == [
        "the vocals listen of window 0:03.700-0:20.000 not made (at most 3 listens per song)"
    ]


def test_a_line_heard_whole_in_the_slices_margin_needs_no_vocals_listen(
    project: hmv.Project, song: Path
) -> None:
    lyrics, found = short_gaps(3)
    models = Listener(found)  # the mix slices hear the prompt, mostly in the margins of the 300 ms gaps
    words = stages_plan.transcribe(job(project, models), song, SONG, lyrics)
    assert [n.vocals for n in words.listened_again] == [None, None, None]  # one listen per window
    # the fake heard each short window's line whole, all in the margins (none kept): heard, so no more
    assert [n.heard for n in words.listened_again[:2]] == [0, 0]


def test_a_gap_is_cut_into_windows_with_the_lines_expected_in_each() -> None:
    lines = [f"line {n}" for n in range(8)]
    found = windows(Gap(lines, 4000, 140_000, latin=True))
    assert [(w.start_ms, w.end_ms) for w in found] == [
        (4000, 31200),
        (31200, 58400),
        (58400, 85600),
        (85600, 112_800),
        (112_800, 140_000),
    ]
    # 8 lines over 5 windows in order: 1.6 a window; a line on a boundary is expected in both
    expected = [[0, 1], [1, 2, 3], [3, 4], [4, 5, 6], [6, 7]]
    assert [[int(t.split()[1]) for t in w.lines] for w in found] == expected
    assert windows(Gap(lines[:1], 0, 30_000, latin=True)) == [Gap(lines[:1], 0, 30_000, latin=True)]
    assert [w.lines for w in windows(Gap(lines[:1], 0, 30_001, latin=True))] == [lines[:1], lines[:1]]


LONG_LYRICS = "\n".join(["first line here", *(f"sung line {w}" for w in "abcdefgh"), "last line here"])


def test_two_minutes_of_music_only_are_listened_to_in_windows(project: hmv.Project, tmp_path: Path) -> None:
    long_song = make_song(tmp_path / "long.wav", 150_000)
    measured = hmv.Song(duration_ms=150_000, sample_rate=8000, channels=1)
    # the bad first listen: "music" from 0:04 to 2:20, then the last line (D-046)
    music = [hmv.Word(text="موسیقی", start_ms=5000 + 10_000 * n, end_ms=5800 + 10_000 * n) for n in range(13)]
    first = heard("first", "line", "here") + music + heard("last", "line", "here", at=140_000)
    models = Listener(first, hears=("vocals-",))  # the mix slices hear nothing, the vocals the prompt
    words = stages_plan.transcribe(job(project, models), long_song, measured, LONG_LYRICS)
    prompts = [c.prompt for c in models.calls_of("transcribe") if c.images[0].name.startswith("vocals-")]
    assert prompts == [
        "sung line a sung line b",
        "sung line b sung line c sung line d",
        "sung line d sung line e",
        "sung line e sung line f sung line g",
        "sung line g sung line h",
    ]
    assert [(n.gap_start_ms, n.gap_end_ms, n.vocals is not None) for n in words.listened_again[:2]] == [
        (3800, 31040, False),
        (3800, 31040, True),
    ]
    assert lines_found(LONG_LYRICS, words.words) == (10, 10)
    assert "موسیقی" not in [w.text for w in words.words]  # replaced in every window
    retried = words.retried  # 8 of 10 missing: heard twice
    assert retried is not None and (retried.first_found, retried.again_found) == (2, 2)
    assert words.not_listened == []


# ------------------------------------------------------------------------------ the third listen


def test_a_line_not_heard_on_its_slice_is_heard_in_the_vocals_slice(
    monkeypatch: pytest.MonkeyPatch, project: hmv.Project, song: Path
) -> None:
    cut_from: list[str] = []
    real_cut = second_listen.cut

    def cut(audio: Path, start_ms: int, end_ms: int, out: Path) -> Path:
        cut_from.append(audio.name)
        return real_cut(audio, start_ms, end_ms, out)

    monkeypatch.setattr(second_listen, "cut", cut)
    models = Listener(FIRST_AND_LAST, hears=("vocals-",))
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    _, second, third = models.calls_of("transcribe")
    (separate,) = models.calls_of("separate")  # the whole song, once: no separation of a slice
    assert (separate.model, separate.images) == ("htdemucs", [song])
    assert (second.prompt, second.images[0].name) == ("the missing line", "slice-3300-15500.wav")
    assert (third.prompt, third.images[0].name) == ("the missing line", "vocals-3300-15500.wav")
    assert cut_from[0] == "song.wav" and cut_from[1].startswith("htdemucs-")  # the mix, then the vocals
    assert [w.text for w in words.words][3:6] == ["the", "missing", "line"]
    assert all(3800 <= w.start_ms < 15000 for w in words.words[3:6])
    mix_again, vocals_again = words.listened_again
    assert (mix_again.heard, mix_again.vocals, vocals_again.heard) == (0, None, 3)
    assert vocals_again.vocals == words.vocals and words.vocals is not None
    assert listened(project) == ["second", "third"]


class NoSeparation(Listener):
    """As without the `separate` extra."""

    def separate_vocals(self, model_id: str, audio: Path, *, out: Path) -> Path:
        raise hmv.ToolMissing(f"demucs is not installed: {INSTALL}")


def editor(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sections": [{"id": "v", "kind": "verse"}],
        "lines": [
            {"section": "v", "text": "first line here", "heard_first": 0, "heard_last": 2},
            {"section": "v", "text": "last line here", "heard_first": 3, "heard_last": 5},
        ],
        "instrumental": [{"after_line": 1, "kind": "break"}, {"after_line": 2, "kind": "outro"}],
    }


@pytest.mark.parametrize("models", [Listener, NoSeparation])
def test_a_line_still_not_heard_is_named_where_an_instrumental_span_is_marked(
    project: hmv.Project, song: Path, models: type[Listener]
) -> None:
    deaf = models(FIRST_AND_LAST, hears=(), answers={"LyricsEdit": editor})
    words = stages_plan.transcribe(job(project, deaf), song, SONG, LYRICS)
    assert words.words == FIRST_AND_LAST and all(n.heard == 0 for n in words.listened_again)
    timeline = stages_plan.lyrics(job(project, deaf), SONG, words, LYRICS)
    # the editor's spans are kept; the break is where the missing line belongs, so the owner is told
    assert [(i.kind, i.start_ms, i.end_ms) for i in timeline.instrumental] == [
        ("break", 3800, 15000),
        ("outro", 17800, 20_000),
    ]
    report = hmv.check_lyrics(timeline, words, LYRICS)
    sung_there = report.warnings[-1]
    assert (sung_there.rule, sung_there.where) == ("line-in-instrumental", "instrumental 0:03.800-0:15.000")
    assert sung_there.message == (
        "'the missing line' may be sung in 0:03.800-0:15.000, which is marked instrumental; listen to it"
    )
    if models is NoSeparation:  # skipped with a warning that says how to get it, never a crash
        assert len(words.listened_again) == 1
        rules = ["lyrics-not-found", "not-listened", "line-in-instrumental"]
        assert [w.rule for w in report.warnings] == rules
        assert report.warnings[1].message == (
            "first listen on the mix, not the isolated vocals: "
            "demucs is not installed: install hone-music-video[separate] to listen to the isolated vocals"
        )
    else:
        assert len(words.listened_again) == 2
        assert [w.rule for w in report.warnings] == ["lyrics-not-found", "line-in-instrumental"]


def test_without_the_extra_every_listen_is_on_the_mix(project: hmv.Project, song: Path) -> None:
    lyrics = "one two three\nfour five six\nseven eight nine\nten eleven twelve\nthirteen fourteen"
    found = heard("one", "two", "three") + heard("seven", "eight", "nine", at=8000)
    found += heard("thirteen", "fourteen", at=15000)
    models = NoSeparation(found, hears=())
    words = stages_plan.transcribe(job(project, models), song, SONG, lyrics)
    assert models.calls_of("transcribe")[0].images == [song] and words.vocals is None
    assert [n.vocals for n in words.listened_again] == [None, None]  # one listen per window: the mix
    assert words.not_listened == [  # named once, not per window
        "first listen on the mix, not the isolated vocals: "
        "demucs is not installed: install hone-music-video[separate] to listen to the isolated vocals"
    ]


# ------------------------------------------------------------------------------ the Demucs adapter


def test_without_the_extra_the_adapter_says_how_to_install_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(sys.modules, "demucs.api", None)  # import fails
    with pytest.raises(hmv.ToolMissing, match=r"install hone-music-video\[separate\]"):
        hmv.HoneModels().separate_vocals("htdemucs", tmp_path / "a.wav", out=tmp_path / "v.wav")


class Separator:
    """Demucs' `Separator`, without a model: asked for the CPU, gives the slice's "vocals"."""

    samplerate = 44100

    def __init__(self, *, model: str, device: str, progress: bool) -> None:
        assert (model, device, progress) == ("htdemucs", "cpu", False)

    def separate_audio_file(self, audio: Path) -> tuple[None, dict[str, str]]:
        if not audio.is_file():
            raise RuntimeError("no such file")
        return None, {"vocals": audio.name}


def save_audio(vocals: str, out: Path, *, samplerate: int) -> None:
    out.write_text(f"{vocals} at {samplerate}")


def test_the_adapter_runs_demucs_on_the_cpu(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "demucs.audio", SimpleNamespace(save_audio=save_audio))
    monkeypatch.setitem(sys.modules, "demucs.api", SimpleNamespace(Separator=Separator))
    (tmp_path / "a.wav").write_bytes(b"slice")
    out = hmv.HoneModels().separate_vocals("htdemucs", tmp_path / "a.wav", out=tmp_path / "v.wav")
    assert out.read_text() == "a.wav at 44100"
    with pytest.raises(hmv.ModelFailure, match=r"htdemucs could not isolate the vocals of b\.wav"):
        hmv.HoneModels().separate_vocals("htdemucs", tmp_path / "b.wav", out=tmp_path / "v.wav")


# ------------------------------------------------------------------------------ echoes and invented times

FA_LYRICS = "اول بار اینجا\n[Outro]\nآخ… Lo-ren-am…\n\nسلام دوباره"  # noqa: RUF001
FA_SONG = heard("اول", "بار", "اینجا") + heard("سلام", "دو", "باره", at=15000)


class Echo(Listener):
    """FakeModels hears its prompt: on a slice, "آخ… Lo-ren-am…" comes back as it was written (an
    echo). The vocals, when `honest`, are heard as Whisper writes them; else they echo too."""

    def __init__(self, *, honest: bool, **kwargs: Any) -> None:
        super().__init__(FA_SONG, hears=("slice-", "vocals-"), **kwargs)
        self.honest = honest

    def transcribe(
        self, model_id: str, audio: Path, *, language: str | None, prompt: str | None
    ) -> hmv.Words:
        found = super().transcribe(model_id, audio, language=language, prompt=prompt)
        if self.honest and audio.name.startswith("vocals-"):
            return hmv.Words(words=heard("آخ", "لورنم", at=2000))
        return found


def test_an_echoed_prompt_is_not_heard_and_the_vocals_are_tried(project: hmv.Project, song: Path) -> None:
    models = Echo(honest=True)
    words = stages_plan.transcribe(job(project, models), song, SONG, FA_LYRICS)
    second, third = words.listened_again
    assert second.heard == 0 and "the prompt echoed back" in (second.rejected or "")
    assert (third.rejected, third.heard) == (None, 2)
    assert [w.text for w in words.words][3:5] == ["آخ", "لورنم"]
    assert not any("Soh" in w.text for w in words.words)


def fa_editor(_data: Mapping[str, Any]) -> dict[str, Any]:
    lines = [("اول بار اینجا", 0, 2), ("سلام دوباره", 3, 5)]
    return {
        "sections": [{"id": "v", "kind": "verse"}],
        "lines": [{"section": "v", "text": t, "heard_first": a, "heard_last": b} for t, a, b in lines],
        "instrumental": [{"after_line": 1, "kind": "break"}],
    }


def test_an_echo_on_both_listens_leaves_the_line_missing(project: hmv.Project, song: Path) -> None:
    models = Echo(honest=False, answers={"LyricsEdit": fa_editor})
    words = stages_plan.transcribe(job(project, models), song, SONG, FA_LYRICS)
    assert words.words == FA_SONG and len(words.listened_again) == 2
    assert all(n.rejected for n in words.listened_again)
    timeline = stages_plan.lyrics(job(project, models), SONG, words, FA_LYRICS)
    assert len(timeline.instrumental) == 1  # kept, and named with the line that may be sung there
    report = hmv.check_lyrics(timeline, words, FA_LYRICS)
    assert [w.rule for w in report.warnings] == ["lyrics-not-found", "line-in-instrumental"]


class Drawn(Listener):
    """On a slice, the line with one word lasting six seconds (an invented time)."""

    def transcribe(
        self, model_id: str, audio: Path, *, language: str | None, prompt: str | None
    ) -> hmv.Words:
        found = super().transcribe(model_id, audio, language=language, prompt=prompt)
        if audio.name.startswith("slice-"):
            drawn = hmv.Word(text="line", start_ms=3000, end_ms=9001)
            return hmv.Words(words=[*heard("the", "missing"), drawn])
        return found


def test_a_word_too_long_is_an_invented_time_and_the_vocals_are_tried(
    project: hmv.Project, song: Path
) -> None:
    models = Drawn(FIRST_AND_LAST, hears=("slice-", "vocals-"))
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    second, third = words.listened_again
    assert second.rejected == "'line' lasts 6001 ms (at most 5000 ms)" and second.heard == 0
    assert third.rejected is None and third.heard == 3


# ------------------------------------------------------------------------------ the test audit


class Scripted(Listener):
    """Hears `song_words` in the song, `on_slice` in a slice and `on_vocals` in the vocals (slice times)."""

    def __init__(self, song_words: list[hmv.Word], on_slice: list[hmv.Word], on_vocals: list[hmv.Word]):
        super().__init__(song_words, hears=())
        self.on_slice, self.on_vocals = on_slice, on_vocals

    def transcribe(
        self, model_id: str, audio: Path, *, language: str | None, prompt: str | None
    ) -> hmv.Words:
        found = super().transcribe(model_id, audio, language=language, prompt=prompt)
        if audio.name.startswith("slice-"):
            return hmv.Words(words=self.on_slice)
        return hmv.Words(words=self.on_vocals) if audio.name.startswith("vocals-") else found


def test_first_listen_words_in_the_gap_are_replaced(project: hmv.Project, song: Path) -> None:
    stray = hmv.Word(text="uh", start_ms=8000, end_ms=8300)  # misheard in the gap
    models = Scripted([*FIRST_AND_LAST[:3], stray, *FIRST_AND_LAST[3:]], heard("the", "missing", "line"), [])
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    texts = [w.text for w in words.words]
    assert "uh" not in texts and texts[3:6] == ["the", "missing", "line"]


def test_the_second_listens_words_stay_when_the_third_hears_nothing(project: hmv.Project, song: Path) -> None:
    models = Scripted(FIRST_AND_LAST, heard("the"), [])  # part of the line, then nothing
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert [n.heard for n in words.listened_again] == [1, 0]
    assert [(w.text, w.start_ms) for w in words.words][3] == ("the", 4300)  # 1000 ms into the slice


def test_merged_words_are_tidied(project: hmv.Project, song: Path) -> None:
    on_slice = [
        hmv.Word(text="the", start_ms=1000, end_ms=2500),
        hmv.Word(text="missing", start_ms=2000, end_ms=3000),  # overlaps the word before it
        hmv.Word(text="line", start_ms=16000, end_ms=18000),  # runs past the song's end
    ]
    models = Scripted(heard("first", "line", "here"), on_slice, [])
    words = stages_plan.transcribe(job(project, models), song, SONG, "first line here\nthe missing line")
    assert [(w.text, w.start_ms, w.end_ms) for w in words.words][3:] == [
        ("the", 4300, 5300),
        ("missing", 5300, 6300),
        ("line", 19300, 20_000),
    ]


def test_a_gap_without_room_is_not_listened_to(project: hmv.Project, song: Path) -> None:
    touching = [*heard("first", "line", "here"), hmv.Word(text="last", start_ms=3800, end_ms=4500)]
    touching += heard("line", "here", at=5000)
    models = Listener(touching)
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert len(models.calls_of("transcribe")) == 1 and words.listened_again == [] and words.not_listened == []


class FailedSeparation(Listener):
    """The separation fails (offline at the first download, out of memory)."""

    def separate_vocals(self, model_id: str, audio: Path, *, out: Path) -> Path:
        raise hmv.ModelFailure("htdemucs could not isolate the vocals: no network")


def test_a_failed_separation_puts_the_first_listen_on_the_mix_not_the_stage(
    project: hmv.Project, song: Path
) -> None:
    models = FailedSeparation(FIRST_AND_LAST, hears=())
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert models.calls_of("transcribe")[0].images == [song] and len(words.listened_again) == 1
    assert words.not_listened == [
        "first listen on the mix, not the isolated vocals: htdemucs could not isolate the vocals: no network"
    ]
    assert list(project.vocals_dir.iterdir()) == []  # nothing that looks made


def test_words_json_of_before_listening_again_loads() -> None:
    old = hmv.Words.model_validate({"format_version": "1", "language": "english", "words": []})
    assert old.listened_again == [] and old.not_listened == [] and old.vocals is old.retried is None
