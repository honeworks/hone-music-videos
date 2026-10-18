"""Given lyrics timed by forced alignment to the vocals (change 0005, design §6 step 1c): the stage, the
cross-check with recognition (D-058), the lines timed from the aligned words (D-059) and the checks."""

from collections.abc import Sequence
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import stages_plan
from hone_music_video._jobs import Job
from hone_music_video.aligned_lyrics import (
    DISAGREE_MS,
    FAR_MS,
    ON_MIX,
    UNSURE,
    findings,
    started_where_heard,
    timed_where_heard,
)
from hone_music_video.events import EventLog
from hone_music_video.runs import song_item
from hone_music_video.testing import FakeModels
from hone_music_video.workflow import build_workflow

SONG = hmv.Song(duration_ms=20_000, sample_rate=44100, channels=1)
LYRICS = "[Verse 1: soft]\none two three\n\nfour five six\n[End]"


def job(project: hmv.Project, models: FakeModels, **roles: str | None) -> Job:
    settings = project.settings
    settings = settings.model_copy(update={"models": settings.models.model_copy(update=roles)})
    return Job(project, models, settings, EventLog(project.events_file))


def at(*words: tuple[str, int, int], score: float = 0.9) -> list[hmv.AlignedWord]:
    """Words as the aligner places them, each with `score`."""
    return [hmv.AlignedWord(text=t, start_ms=a, end_ms=b, score=score) for t, a, b in words]


def plain(words: list[hmv.AlignedWord]) -> list[hmv.Word]:
    return [hmv.Word(text=w.text, start_ms=w.start_ms, end_ms=w.end_ms) for w in words]


HEARD = plain(at(("one", 1000, 1400), ("two", 1500, 1900), ("three", 2000, 2400)))
HEARD += plain(at(("four", 6000, 6400), ("five", 6500, 6900), ("six", 7000, 7400)))


class Aligner(FakeModels):
    """Hears `HEARD` in the song; aligns the given words where `places` says (line by line)."""

    def __init__(self, places: list[list[hmv.AlignedWord]], heard: list[hmv.Word] = HEARD) -> None:
        super().__init__()
        self.places, self.heard = places, heard

    def transcribe(
        self, model_id: str, audio: Path, *, language: str | None, prompt: str | None
    ) -> hmv.Words:
        super().transcribe(model_id, audio, language=language, prompt=prompt)
        return hmv.Words(words=self.heard if not audio.name.startswith(("slice-", "vocals-")) else [])

    def align(self, model_id: str, audio: Path, lines: Sequence[str]) -> list[list[hmv.AlignedWord]]:
        super().align(model_id, audio, lines)
        return self.places


PLACES = [
    at(("one", 1100, 1400), ("two", 1500, 1900), ("three", 2000, 2400)),
    at(("four", 6100, 6400), ("five", 6500, 6900), ("six", 7000, 7400)),
]


# ------------------------------------------------------------------------------ the stage


def test_given_lyrics_are_aligned_to_the_vocals(project: hmv.Project, song: Path) -> None:
    models = Aligner(PLACES)
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    (aligned,) = models.calls_of("align")
    assert aligned.model == "MMS_FA"  # the default (0005)
    assert aligned.data == {"lines": ["one two three", "four five six"]}  # bracketed notes left out
    assert aligned.images[0].parent == project.vocals_dir  # the vocals the first listen heard
    assert words.words == HEARD  # recognition is made as before, and kept
    assert words.aligned is not None and words.aligned.model == "MMS_FA"
    assert words.aligned.words == plain(PLACES[0] + PLACES[1])
    assert words.aligned.disagree == words.aligned.unsure == [] and words.not_aligned is None
    assert words.not_listened == []  # aligned on the isolated vocals
    assert words.timing() == plain(PLACES[0] + PLACES[1])
    events, _ = EventLog(project.events_file).read()
    (logged,) = [e for e in events if e["event"] == "lyrics_aligned"]
    assert (logged["model"], logged["words"], logged["disagree"], logged["unsure"]) == ("MMS_FA", 6, 0, 0)


def test_without_the_vocals_the_mix_is_aligned(project: hmv.Project, song: Path) -> None:
    class NoVocals(Aligner):
        def separate_vocals(self, model_id: str, audio: Path, *, out: Path) -> Path:
            raise hmv.ToolMissing("demucs is not installed")

    models = NoVocals(PLACES)
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert models.calls_of("align")[0].images == [song]
    assert words.aligned is not None and words.not_listened[-1] == ON_MIX  # said, not skipped
    timeline = stages_plan.lyrics(job(project, models), SONG, words, LYRICS)
    report = hmv.check_lyrics(timeline, words, LYRICS)
    assert ("not-listened", ON_MIX) in [(p.rule, p.message) for p in report.warnings]


@pytest.mark.parametrize("lyrics", [None, "[only notes]", "\n\n"])
def test_without_sung_lines_nothing_is_aligned(project: hmv.Project, song: Path, lyrics: str | None) -> None:
    models = Aligner(PLACES)
    words = stages_plan.transcribe(job(project, models), song, SONG, lyrics)
    assert models.calls_of("align") == [] and words.aligned is None and words.not_aligned is None


def test_alignment_can_be_turned_off(project: hmv.Project, song: Path) -> None:
    models = Aligner(PLACES)
    words = stages_plan.transcribe(job(project, models, align=None), song, SONG, LYRICS)
    assert models.calls_of("align") == [] and words.aligned is None and words.not_aligned is None
    assert words.timing() == HEARD


@pytest.mark.parametrize("error", [hmv.ToolMissing("no torchaudio"), hmv.ModelFailure("too short")])
def test_an_aligner_that_cannot_run_leaves_the_heard_words(
    project: hmv.Project, song: Path, error: Exception
) -> None:
    class Failing(Aligner):
        def align(self, model_id: str, audio: Path, lines: Sequence[str]) -> list[list[hmv.AlignedWord]]:
            raise error

    words = stages_plan.transcribe(job(project, Failing(PLACES)), song, SONG, LYRICS)
    assert words.aligned is None and words.timing() == HEARD
    assert words.not_aligned == (
        f"the given lyrics were not aligned, so the lines are timed from the heard words: {error}"
    )


def test_lyrics_without_a_word_to_align_leave_the_heard_words(project: hmv.Project, song: Path) -> None:
    words = stages_plan.transcribe(job(project, Aligner([[], []])), song, SONG, LYRICS)
    assert words.aligned is None and words.timing() == HEARD
    assert words.not_aligned == (
        "the given lyrics were not aligned, so the lines are timed from the heard words: "
        "no given word has a letter the aligner knows"
    )


def test_aligned_words_are_kept_inside_the_song(project: hmv.Project, song: Path) -> None:
    late = [
        at(("one", 1000, 1500), ("two", 1400, 1800), ("three", 19_900, 20_400)),
        at(("four", 20_100, 20_200)),
    ]
    words = stages_plan.transcribe(job(project, Aligner(late)), song, SONG, "one two three\nfour")
    assert words.aligned is not None
    assert [(w.text, w.start_ms, w.end_ms) for w in words.aligned.words] == [
        ("one", 1000, 1400),  # an overlap is cut at the next word (D-017)
        ("two", 1400, 1800),
        ("three", 19_900, 20_000),  # past the end: ends there; starting after it: left out
    ]


# ------------------------------------------------------------------------------ the cross-check


def test_a_line_recognition_starts_elsewhere_is_named(project: hmv.Project, song: Path) -> None:
    moved = [PLACES[0], at(("four", 6000 + DISAGREE_MS + 1, 6800), ("five", 6900, 7000), ("six", 7000, 7400))]
    words = stages_plan.transcribe(job(project, Aligner(moved)), song, SONG, LYRICS)
    assert words.aligned is not None
    assert words.aligned.disagree == [hmv.Disagreement(line="four five six", aligned_ms=6751, heard_ms=6000)]


def test_lines_within_the_limit_or_not_heard_are_not_named(project: hmv.Project, song: Path) -> None:
    close = [at(("one", 1000 - DISAGREE_MS, 1400)), at(("four", 6000 + DISAGREE_MS, 6400))]
    words = stages_plan.transcribe(job(project, Aligner(close)), song, SONG, LYRICS)
    assert words.aligned is not None and words.aligned.disagree == []
    unheard = Aligner([PLACES[0], at(("four", 15_000, 15_400))], heard=HEARD[:3])  # line 2 never heard
    words = stages_plan.transcribe(job(project, unheard), song, SONG, LYRICS)
    assert words.aligned is not None and words.aligned.disagree == []


# ------------------------------------------------------------------------------ the lines and the checks


def test_the_lines_are_timed_from_the_aligned_words(project: hmv.Project, song: Path) -> None:
    models = Aligner(PLACES)
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    timeline = stages_plan.lyrics(job(project, models), SONG, words, LYRICS)
    sent = models.calls_of("plan")[0].data
    assert sent["aligned"] is True
    assert [(w["text"], w["start_ms"]) for w in sent["heard_words"]] == [
        (w.text, w.start_ms) for w in PLACES[0] + PLACES[1]
    ]
    assert [(ln.start_ms, ln.end_ms) for ln in timeline.lines] == [(1100, 7400)]  # the fake: lines of six
    report = hmv.check_lyrics(timeline, words, LYRICS)
    assert report.errors == []
    assert [p.rule for p in report.warnings] == []


def test_the_editor_is_not_told_of_an_alignment_that_was_not_made(project: hmv.Project, song: Path) -> None:
    models = Aligner(PLACES)
    words = stages_plan.transcribe(job(project, models, align=None), song, SONG, LYRICS)
    stages_plan.lyrics(job(project, models), SONG, words, LYRICS)
    assert "aligned" not in models.calls_of("plan")[0].data


def test_the_check_warns_of_disagreements_and_of_lyrics_not_aligned(project: hmv.Project, song: Path) -> None:
    moved = [PLACES[0], at(("four", 9000, 9400), ("five", 9500, 9900), ("six", 10_000, 10_400))]
    words = stages_plan.transcribe(job(project, Aligner(moved)), song, SONG, LYRICS)
    timeline = stages_plan.lyrics(job(project, Aligner(moved)), SONG, words, LYRICS)
    report = hmv.check_lyrics(timeline, words, LYRICS)
    assert [(p.rule, p.where, p.message) for p in report.warnings] == [
        (
            "align-disagrees",
            "four five six",
            "aligned at 0:09.000, heard at 0:06.000 (3000 ms apart, more than 750 ms); listen to it",
        )
    ]
    failed = words.model_copy(update={"aligned": None, "not_aligned": "the given lyrics were not aligned: x"})
    report = hmv.check_lyrics(
        stages_plan.lyrics(job(project, Aligner(moved)), SONG, failed, LYRICS), failed, LYRICS
    )
    assert ("not-aligned", "given lyrics", "the given lyrics were not aligned: x") in [
        (p.rule, p.where, p.message) for p in report.warnings
    ]


def test_a_line_is_checked_against_the_words_it_was_timed_from(project: hmv.Project, song: Path) -> None:
    words = stages_plan.transcribe(job(project, Aligner(PLACES)), song, SONG, LYRICS)
    timeline = stages_plan.lyrics(job(project, Aligner(PLACES)), SONG, words, LYRICS)
    heard_only = words.model_copy(update={"aligned": None})  # the heard "one" starts 100 ms earlier
    shifted = heard_only.model_copy(update={"words": [w.model_copy(update={"start_ms": 0}) for w in HEARD]})
    assert hmv.check_lyrics(timeline, heard_only, LYRICS).errors == []
    assert [p.rule for p in hmv.check_lyrics(timeline, shifted, LYRICS).errors] == ["moved"]


def test_a_line_placed_with_a_low_score_is_named(project: hmv.Project, song: Path) -> None:
    # the second line: "four" (300 ms) at 0.1 and "five six" (800 ms) at 0.2 weigh 0.173 < UNSURE
    low = [at(("four", 6000, 6300), score=0.1)[0], *at(("five", 6500, 6900), ("six", 7000, 7400), score=0.2)]
    sure = at(("one", 1000, 1400), ("two", 1500, 1900), ("three", 2000, 2400), score=UNSURE)  # not under it
    models = Aligner([sure, low])
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert words.aligned is not None
    assert words.aligned.unsure == [hmv.Unsure(line="four five six", start_ms=6000, score=0.173)]
    timeline = stages_plan.lyrics(job(project, models), SONG, words, LYRICS)
    report = hmv.check_lyrics(timeline, words, LYRICS)
    assert [(p.rule, p.where, p.message) for p in report.warnings] == [
        (
            "align-unsure",
            "four five six",
            "aligned at 0:06.000 with a low score (0.17, under 0.3); listen to it",
        )
    ]


def test_lines_without_words_or_length_are_neither_disagreeing_nor_unsure() -> None:
    zero = at(("a", 1000, 1000), ("b", 1000, 1000), score=0.0)  # no length to weigh the score by
    disagree, unsure = findings(["", "a b", "c"], [[], zero, at(("c", 9000, 9100), score=0.0)], [5, 0, 1])
    assert disagree == [hmv.Disagreement(line="c", aligned_ms=9000, heard_ms=1)]
    assert unsure == [hmv.Unsure(line="c", start_ms=9000, score=0.0)]


def test_a_run_whose_stored_settings_have_no_align_times_from_the_heard_words(project: hmv.Project) -> None:
    """A run started before 0005 stored its settings without `models.align`: it stays off (D-059)."""
    settings = project.settings.model_dump(mode="json")
    del settings["models"]["align"]
    models = FakeModels()
    run = build_workflow(project, models).run([song_item(project)], params={"settings": settings})
    assert run.status != "failed"
    assert models.calls_of("transcribe") and models.calls_of("align") == []


# ------------------------------------------------------------------------------ line starts (0030 §3)


def test_a_first_word_stretched_into_the_pause_starts_where_it_was_heard(
    project: hmv.Project, song: Path
) -> None:
    """This too shall pass, L013: the aligner starts "اَگِه" 913 ms before the voice; the rest agrees."""
    stretched = at(("four", 4800, 6400), ("five", 6500, 6900), ("six", 7000, 7400))
    models = Aligner([PLACES[0], stretched])
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert words.aligned is not None and words.aligned.disagree == []
    assert words.aligned.moved == [hmv.Moved(line="four five six", from_ms=4800, to_ms=6000)]
    assert [(w.text, w.start_ms, w.end_ms) for w in words.aligned.words[3:4]] == [("four", 6000, 6400)]
    timeline = stages_plan.lyrics(job(project, models), SONG, words, LYRICS)
    assert words.timing()[3].start_ms == 6000  # the lines are timed from these (D-059)
    report = hmv.check_lyrics(timeline, words, LYRICS)
    assert [(p.rule, p.where, p.message) for p in report.warnings] == [
        ("start-from-heard", "four five six",
         "its first word started 1200 ms before it was heard: it starts at 0:06.000, where it was heard; "
         "listen to it"),
    ]  # fmt: skip


@pytest.mark.parametrize(
    "placed",
    [
        at(("four", 4800, 5200), ("five", 5300, 6900), ("six", 7000, 7400)),  # the second word disagrees too
        at(("lala", 4800, 5800), ("four", 6000, 6400), ("five six", 6500, 7400)),  # not the word heard first
    ],
)
def test_a_line_that_disagrees_otherwise_stays_with_its_warning(
    project: hmv.Project, song: Path, placed: list[hmv.AlignedWord]
) -> None:
    """Isolde (feeling), L014: recognition left out the sung "لالا لالا", so the aligner is right there."""
    words = stages_plan.transcribe(job(project, Aligner([PLACES[0], placed])), song, SONG, LYRICS)
    assert words.aligned is not None and words.aligned.moved == []
    assert [d.aligned_ms for d in words.aligned.disagree] == [4800]


def test_a_line_found_from_its_second_word_starts_where_its_first_was_heard() -> None:
    """This too shall pass, L015: recognition found the line at "تا", the aligner put "کِه" in the pause."""
    own = at(("ke", 117_536, 118_297), ("ta", 119_357, 119_517), ("sobh", 119_800, 120_300))
    heard = plain(at(("ke", 119_200, 119_350), ("ta", 119_380, 119_500), ("sobh", 119_820, 120_300)))
    moved = started_where_heard(["ke ta sobh"], [own], heard, [1])
    assert moved == [hmv.Moved(line="ke ta sobh", from_ms=117_536, to_ms=119_200)]
    assert (own[0].start_ms, own[0].end_ms) == (119_200, 119_350)  # the whole word was in the pause


# ------------------------------------------------------------------------------ lines the aligner lost (0032)


def test_a_line_the_aligner_lost_is_timed_from_its_heard_words(project: hmv.Project, song: Path) -> None:
    """Midnight Mambo Shoes, L030: the aligner put the line 32 s early, in the solo, with a low score."""
    lost = at(("four", 3000, 3200), ("five", 3200, 3600), ("six", 3600, 4000), score=0.1)
    models = Aligner([PLACES[0], lost])
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert words.aligned is not None and words.aligned.disagree == []
    assert words.aligned.moved == [hmv.Moved(line="four five six", from_ms=3000, to_ms=6000, whole=True)]
    # the same words over the heard ones (6000 to 7400), their lengths in the same proportions
    assert [(w.text, w.start_ms, w.end_ms) for w in words.aligned.words[3:]] == [
        ("four", 6000, 6280), ("five", 6280, 6840), ("six", 6840, 7400),
    ]  # fmt: skip
    timeline = stages_plan.lyrics(job(project, models), SONG, words, LYRICS)
    report = hmv.check_lyrics(timeline, words, LYRICS)
    assert report.errors == []
    assert ("timed-from-heard", "four five six") in [(p.rule, p.where) for p in report.warnings]


def test_a_lost_line_is_not_moved_over_its_neighbour() -> None:
    """The heard words of the first line lie where the second is aligned: the move is not made."""
    lines = ["one two", "three four"]
    lost = at(("one", 100, 300), ("two", 300, 500), score=0.1)
    timed = [lost, at(("three", 2000, 2400), ("four", 2400, 2800))]
    heard = plain(at(("one", 2100, 2300), ("two", 2300, 2500), ("three", 2600, 2700), ("four", 2700, 2800)))
    assert timed_where_heard(lines, timed, heard, [(0, 1), (2, 3)]) == []
    assert timed[0][0].start_ms == 100


def test_a_confident_line_far_from_where_it_was_heard_is_an_error(project: hmv.Project, song: Path) -> None:
    """A good score keeps the aligned times; over `FAR_MS` apart the check stops the gate (0032)."""
    far = at(("four", 6000 + FAR_MS + 1, 9400), ("five", 9500, 9900), ("six", 10_000, 10_400))
    models = Aligner([PLACES[0], far])
    words = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert words.aligned is not None and words.aligned.moved == []
    timeline = stages_plan.lyrics(job(project, models), SONG, words, LYRICS)
    report = hmv.check_lyrics(timeline, words, LYRICS)
    assert [(p.rule, p.where) for p in report.errors] == [("align-disagrees", "four five six")]
