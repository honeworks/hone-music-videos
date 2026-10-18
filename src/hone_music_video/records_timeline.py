"""The records of stages 1 to 4 (design §4.1, §6): the song, the heard words and the timeline, and the
field types every record shares: JSON with `format_version: "1"`, times in integer milliseconds.
`hone_music_video.records` imports them, so they are used from there."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Ms = Annotated[int, Field(ge=0, strict=True)]  # integer milliseconds from the start of the song
STRICT = ConfigDict(extra="forbid")
Version = Literal["1"]


def clock(ms: int) -> str:
    """A time as people read it, m:ss.mmm (D-007); records keep the milliseconds."""
    return f"{ms // 60000}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


# ---------------------------------------------------------------------------- stages 1 and 2


class Song(BaseModel):
    """`song.json` (stage `measure`): what ffprobe measured."""

    model_config = STRICT
    format_version: Version = "1"

    duration_ms: Ms
    sample_rate: int
    channels: int


class Word(BaseModel):
    """A word with its start and end."""

    model_config = STRICT
    text: str
    start_ms: Ms
    end_ms: Ms


class HostedCall(BaseModel):
    """What the in-library transcription client sent and got (D-002): the request without the key, the
    reply as the service sent it, how long it took and its price."""

    model_config = STRICT
    model: str
    url: str
    request: dict[str, Any]  # the form fields and the file sent (name, bytes, sha256), never the key
    reply: dict[str, Any]
    took_ms: int
    cost_usd: float | None = None


class Separation(BaseModel):
    """The song's vocals, isolated once for the first listen (D-045): the model, how long it took, and
    the song and the vocals by sha256. (Before D-045, a listen again isolated its slice's vocals: then
    `input_sha256` is the slice's.)"""

    model_config = STRICT
    model: str
    took_ms: int
    input_sha256: str
    output_sha256: str


class ListenAgain(BaseModel):
    """One more listen for given lines the first call did not hear (D-040): the lines, the gap between
    their found neighbours, the slice of the song sent (the gap with a margin), how many words it heard
    inside the gap, and the hosted call. A listen of a slice of the song's isolated vocals has their
    `vocals` (D-045, D-046); `rejected` says why its reply was not taken as heard (an echoed prompt, an
    invented time; D-040)."""

    model_config = STRICT
    lines: list[str]
    start_ms: Ms
    end_ms: Ms
    gap_start_ms: Ms
    gap_end_ms: Ms
    heard: int
    call: HostedCall | None = None
    vocals: Separation | None = None
    rejected: str | None = None


class Retry(BaseModel):
    """The first listen made again, because it found too few of the given sung lines (D-047): how many
    lines could be found, how many each listen found, whether the second's words were kept, the call of
    the one not kept (`Words.call` is the kept one's), and why either was not trusted (D-040's guard)."""

    model_config = STRICT
    lines: int
    first_found: int
    again_found: int
    kept_again: bool
    other: HostedCall | None = None
    first_rejected: str | None = None
    again_rejected: str | None = None


class AlignedWord(Word):
    """A word placed by the forced aligner, with its score: the mean probability of its letters over
    their frames, 0 to 1 (D-058)."""

    score: float = Field(ge=0, le=1)


class Unsure(BaseModel):
    """A given line the aligner placed with a low score (`aligned_lyrics.UNSURE`): its start and its
    score, the words' scores weighted by their length (D-058)."""

    model_config = STRICT
    line: str
    start_ms: Ms
    score: float


class Disagreement(BaseModel):
    """A given line whose aligned start is more than `aligned_lyrics.DISAGREE_MS` from the start of the
    heard words it was found in (D-058)."""

    model_config = STRICT
    line: str
    aligned_ms: Ms
    heard_ms: Ms


class Moved(BaseModel):
    """A given line whose first aligned word was stretched back into the pause before it: it starts
    where recognition heard that word (0030 §3); `whole`: a line the aligner lost (far from where it was
    heard, with a low score), all its words placed over the heard ones (0032)."""

    model_config = STRICT
    line: str
    from_ms: Ms
    to_ms: Ms
    whole: bool = False


class Alignment(BaseModel):
    """The given lyrics aligned to the song's vocals (change 0005): the aligner, how long it took, every
    given sung word that has letters to align with its times (the lines are timed from these, D-059),
    the lines recognition puts elsewhere and those placed with a low score (D-058)."""

    model_config = STRICT
    model: str
    took_ms: int
    words: list[Word]
    disagree: list[Disagreement] = []
    unsure: list[Unsure] = []
    moved: list[Moved] = []  # lines started where they were heard (0030 §3)


class Words(BaseModel):
    """`words.json` (stage `transcribe`): every heard word with its times, the hosted call that heard
    them (D-002; `None` once hone-models records the call itself), the listens again for given lines
    the first call did not hear (D-040, D-046), and why a listen that could help was not made. `vocals`
    is the separation the first listen heard (D-045; `None`: it heard the mix), `retried` the first
    listen made again (D-047). `aligned` is the given lyrics aligned to the vocals (0005), `not_aligned`
    why they could not be."""

    model_config = STRICT
    format_version: Version = "1"

    language: str | None = None
    words: list[Word]
    call: HostedCall | None = None
    listened_again: list[ListenAgain] = []
    not_listened: list[str] = []
    vocals: Separation | None = None
    retried: Retry | None = None
    aligned: Alignment | None = None
    not_aligned: str | None = None

    def timing(self) -> list[Word]:
        """The words the lines are timed from: the aligned words when the given lyrics were aligned,
        else the heard words (D-059)."""
        return self.aligned.words if self.aligned is not None else self.words


# ---------------------------------------------------------------------------- §4.1 timeline


class Section(BaseModel):
    """A part of the song: intro, verse, chorus..."""

    model_config = STRICT
    id: str
    kind: str
    start_ms: Ms
    end_ms: Ms
    notes: str = ""  # the lyrics' bracketed notes for this part, word for word: delivery, sounds (0028)


class Line(BaseModel):
    """A sung line with its words. `heard_first` and `heard_last` are the heard words (indices into
    `words.json`) its times come from (D-003, D-016)."""

    model_config = STRICT
    id: str
    section: str
    text: str
    start_ms: Ms
    end_ms: Ms
    words: list[Word]
    heard_first: int | None = None
    heard_last: int | None = None


class Instrumental(BaseModel):
    """A span without singing."""

    model_config = STRICT
    start_ms: Ms
    end_ms: Ms
    kind: str
    notes: str = ""  # as a section's (0028)


class Timeline(BaseModel):
    """`timeline.json` (design §4.1). `owner_timed`: the lines whose times the owner set by hand at the
    lyrics gate (0018, D-113); their words moved with them."""

    model_config = STRICT
    format_version: Version = "1"

    duration_ms: Ms
    language: str | None = None
    sections: list[Section]
    lines: list[Line]
    instrumental: list[Instrumental] = []
    owner_timed: list[str] = []
