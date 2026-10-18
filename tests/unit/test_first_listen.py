"""The first listen (design §6 step 1): the song's vocals, isolated once and kept in the project (D-045),
heard with the opening of the lyrics; made once more when it finds too few given lines (D-047)."""

import hashlib
from pathlib import Path

import pytest

import hone_music_video as hmv
from hone_music_video import stages_plan
from hone_music_video._jobs import Job
from hone_music_video.events import EventLog
from hone_music_video.records import HostedCall
from hone_music_video.testing import FakeModels

SONG = hmv.Song(duration_ms=20_000, sample_rate=44100, channels=1)
LYRICS = "one two three\nfour five six\nseven eight nine"


def job(project: hmv.Project, models: FakeModels) -> Job:
    return Job(project, models, project.settings, EventLog(project.events_file))


def words(*texts: str) -> list[hmv.Word]:
    return [hmv.Word(text=t, start_ms=1000 * n, end_ms=1000 * n + 800) for n, t in enumerate(texts)]


def call(n: int) -> HostedCall:
    return HostedCall(model="whisper-1", url="u", request={"n": n}, reply={}, took_ms=n)


class Varying(FakeModels):
    """Whisper varies run to run: the first listens of the whole song hear `listens` in turn (each with
    its own call, words not tidied); a slice hears nothing."""

    def __init__(self, *listens: list[hmv.Word]) -> None:
        super().__init__()
        self.listens = list(listens)

    def transcribe(
        self, model_id: str, audio: Path, *, language: str | None, prompt: str | None
    ) -> hmv.Words:
        super().transcribe(model_id, audio, language=language, prompt=prompt)
        if audio.name.startswith(("slice-", "vocals-")) or not self.listens:
            return hmv.Words(words=[])
        n = len(self.calls_of("transcribe"))
        return hmv.Words(words=self.listens.pop(0), call=call(n))


def first_listens(project: hmv.Project) -> list[dict[str, object]]:
    events, _ = EventLog(project.events_file).read()
    return [{k: e[k] for k in ("found", "lines")} for e in events if e["event"] == "first_listen"]


# ------------------------------------------------------------------------------ the vocals


def test_the_vocals_are_isolated_once_and_kept(project: hmv.Project, song: Path) -> None:
    models = FakeModels()
    first = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    again = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)  # a run made again
    (separate,) = models.calls_of("separate")
    assert separate.images == [song] and separate.model == "htdemucs"
    (kept,) = sorted(project.vocals_dir.glob("*.wav"))
    made = first.vocals
    assert made is not None and again.vocals == made
    assert made.input_sha256 == hashlib.sha256(song.read_bytes()).hexdigest()
    assert made.output_sha256 == hashlib.sha256(kept.read_bytes()).hexdigest()
    assert kept.read_bytes() == song.read_bytes() + b"vocals"  # what the fake wrote
    assert [c.images for c in models.calls_of("transcribe")] == [[kept], [kept]]


def test_vocals_without_their_record_are_made_again(project: hmv.Project, song: Path) -> None:
    models = FakeModels()
    stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    (record,) = project.vocals_dir.glob("*.json")
    record.unlink()  # a crash between the vocals and their record
    stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert len(models.calls_of("separate")) == 2 and record.is_file()


def test_another_vocals_model_makes_other_vocals(project: hmv.Project, song: Path) -> None:
    models, settings = FakeModels(), project.settings
    other = settings.model_copy(update={"models": settings.models.model_copy(update={"vocals": "mdx"})})
    stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    stages_plan.transcribe(Job(project, models, other, EventLog(project.events_file)), song, SONG, LYRICS)
    assert [c.model for c in models.calls_of("separate")] == ["htdemucs", "mdx"]
    assert len(list(project.vocals_dir.glob("*.wav"))) == 2


# ------------------------------------------------------------------------------ made again when poor

ALL = words("one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
TWO = words("one", "two", "three", "four", "five", "six")  # the last line missing: a third
ONE = words("one", "two", "three")


def test_a_first_listen_missing_a_third_is_not_made_again(project: hmv.Project, song: Path) -> None:
    models = Varying(TWO, ALL)
    heard = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert heard.retried is None and heard.call == call(1)
    assert first_listens(project) == [{"found": 2, "lines": 3}]


def test_a_poor_first_listen_is_made_again_and_the_better_kept(project: hmv.Project, song: Path) -> None:
    models = Varying(ONE, ALL)
    heard = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert [w.text for w in heard.words] == [w.text for w in ALL] and heard.listened_again == []
    retry = hmv.Retry(lines=3, first_found=1, again_found=3, kept_again=True, other=call(1))
    assert heard.retried == retry
    assert heard.call == call(2)  # both calls recorded: the kept one here, the other in `retried`
    assert first_listens(project) == [{"found": 1, "lines": 3}, {"found": 3, "lines": 3}]


@pytest.mark.parametrize("second", [ONE, []])
def test_a_retry_no_better_keeps_the_first(project: hmv.Project, song: Path, second: list[hmv.Word]) -> None:
    models = Varying(ONE, second)
    heard = stages_plan.transcribe(job(project, models), song, SONG, LYRICS)
    assert heard.call == call(1) and heard.retried is not None
    assert (heard.retried.kept_again, heard.retried.other) == (False, call(2))
    assert (heard.retried.first_found, heard.retried.again_found) == (1, 1 if second else 0)


FA_LYRICS = "اول بار اینجا\nسلام Darvin دوباره\nخط سوم هم"  # noqa: RUF001
FA_ONE = words("اول", "بار", "اینجا")


def test_a_retry_that_echoes_the_prompt_is_not_kept(project: hmv.Project, song: Path) -> None:
    echo = words("اول", "بار", "اینجا", "سلام", "Darvin", "دوباره", "خط", "سوم", "هم")  # the prompt copied
    heard = stages_plan.transcribe(job(project, Varying(FA_ONE, echo)), song, SONG, FA_LYRICS)
    retry = heard.retried
    assert retry is not None and not retry.kept_again and retry.first_rejected is None
    assert retry.again_found == 3 and "the prompt echoed back" in (retry.again_rejected or "")


def test_a_first_listen_with_an_invented_time_gives_way(project: hmv.Project, song: Path) -> None:
    drawn = [*FA_ONE[:2], hmv.Word(text="اینجا", start_ms=2000, end_ms=7001)]  # 5001 ms: invented
    heard = stages_plan.transcribe(job(project, Varying(drawn, [])), song, SONG, FA_LYRICS)
    retry = heard.retried  # the second found nothing, yet it is the one to trust
    assert retry is not None and retry.kept_again and (retry.first_found, retry.again_found) == (1, 0)
    assert retry.first_rejected == "'اینجا' lasts 5001 ms (at most 5000 ms)"


def test_without_given_lyrics_the_first_listen_is_made_once(project: hmv.Project, song: Path) -> None:
    models = Varying([])
    heard = stages_plan.transcribe(job(project, models), song, SONG, None)
    assert len(models.calls_of("transcribe")) == 1 and heard.retried is None
