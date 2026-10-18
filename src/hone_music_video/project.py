"""The project folder (design §4): `project.json`, `input/`, `runs/`, `current/`."""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from hone_music_video._files import now, read_json, slug, write_json
from hone_music_video.errors import InvalidInput, NotFound, ProjectUnreadable
from hone_music_video.settings import Settings, parse_settings, problems_of, stored

SONG_TYPES = {  # design §2.1: the song's extensions and their content types
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
}
IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".webp")
ApproveMode = Literal["ask", "auto"]  # stop at each gate for the owner, or approve it unattended (0004)
APPROVE_MODES = ("ask", "auto")
SHEET_NAME = re.compile(r"^\w[\w .'-]{0,63}$")


@dataclass(frozen=True)
class GivenSheet:
    """A reference sheet or portrait the owner already has (design §2.2)."""

    name: str
    file: Path
    note: str = ""


@dataclass(frozen=True)
class Material:
    """What the owner gives with the song, all optional: lyrics, story notes, sheets (design §2.2)."""

    lyrics: str | None = None
    story: str = ""
    sheets: tuple[GivenSheet, ...] = ()
    poses: tuple[GivenSheet, ...] = ()  # pose pictures by name: a variant's body pose (0027)
    feeling: str = ""  # what the viewer should feel, and how it changes (0028)


class StoredSheet(BaseModel):
    """A given sheet as the project keeps it."""

    model_config = ConfigDict(extra="forbid")

    name: str
    file: str  # relative to the project folder
    note: str = ""


class Inputs(BaseModel):
    """The owner's material as the project keeps it."""

    model_config = ConfigDict(extra="forbid")

    song: str  # relative to the project folder
    lyrics: str | None = None  # the text, also in input/lyrics.txt
    story: str = ""
    sheets: list[StoredSheet] = []
    poses: list[StoredSheet] = []  # pose pictures (0027); a project made before has none
    feeling: str = ""  # what the viewer should feel, and how it changes (0028)


class ProjectFile(BaseModel):
    """`project.json`: name, created, settings, inputs (design §4)."""

    model_config = ConfigDict(extra="forbid")

    format_version: Literal["1"] = "1"
    id: str
    name: str = Field(min_length=1)
    created: str
    settings: Settings
    inputs: Inputs
    approve: ApproveMode = "ask"  # beside the settings, not in the run's parameter (0004, D-075)
    prepare: bool = False  # stop before the first local stage: the hosted calls only (0028 §6)

    @field_validator("settings", mode="before")
    @classmethod
    def _stored(cls, data: Any) -> Any:
        return stored(data)  # a project made before M5 (D-032)

    def as_stored(self) -> dict[str, Any]:
        """What `project.json` holds: `approve` only when it is "auto", so a project that asks stays
        readable by a version from before 0004 (D-075); `prepare` and the feeling likewise only when
        set (0028)."""
        found = self.model_dump(mode="json", exclude={"approve"} if self.approve == "ask" else set())
        if not self.prepare:
            del found["prepare"]
        if not self.inputs.feeling:
            del found["inputs"]["feeling"]
        return found


@dataclass(frozen=True)
class Project:
    """One video's folder. Open it with `open_project`; make it with `create_project`."""

    root: Path

    @property
    def id(self) -> str:
        return self.root.name

    def read(self) -> ProjectFile | str:
        """`project.json`, read now, or why this version cannot read it (D-032)."""
        try:
            return read_json(self.root / "project.json", ProjectFile)
        except ValidationError as error:
            return unreadable(error)

    def record(self) -> ProjectFile:
        """`project.json`, read now; `ProjectUnreadable` saying why when this version cannot read it."""
        found = self.read()
        if isinstance(found, str):
            raise ProjectUnreadable(f"{self.id} cannot be read: {found}")
        return found

    @property
    def settings(self) -> Settings:
        return self.record().settings

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    @property
    def current(self) -> Path:
        """The latest outputs, for the dashboard and for people (design §4)."""
        return self.root / "current"

    @property
    def vocals_dir(self) -> Path:
        """The song's isolated vocals, made once per song and model (D-045)."""
        return self.root / "vocals"

    @property
    def events_file(self) -> Path:
        return self.root / "events.jsonl"

    def path(self, relative: str) -> Path:
        """A path inside the project from a record's relative path."""
        return self.root / relative

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()


def _check_inputs(song: Path, sheets: list[GivenSheet]) -> list[str]:
    problems: list[str] = []
    if not song.is_file():
        problems.append(f"song: {song} is not a file")
    elif song.suffix.lower() not in SONG_TYPES:
        problems.append(f"song: {song.suffix or 'no extension'} is not one of {', '.join(SONG_TYPES)}")
    names = [s.name for s in sheets]
    for sheet in sheets:
        if not SHEET_NAME.match(sheet.name):
            problems.append(f"sheets: {sheet.name!r} is not a usable name (letters, digits, spaces, .'-)")
        if not sheet.file.is_file() or sheet.file.suffix.lower() not in IMAGE_TYPES:
            problems.append(f"sheets: {sheet.name!r} needs a picture file ({', '.join(IMAGE_TYPES)})")
        if names.count(sheet.name) > 1:
            problems.append(f"sheets: the name {sheet.name!r} is used twice; give each sheet its own name")
    return problems


def _free_id(projects_dir: Path, name: str) -> str:
    base = slug(name)
    candidate, n = base, 2
    while (projects_dir / candidate).exists():
        candidate, n = f"{base}-{n}", n + 1
    return candidate


def create_project(
    projects_dir: str | Path,
    name: str,
    song: str | Path,
    material: Material = Material(),  # noqa: B008 - frozen, so sharing the default is safe
    settings: Settings | dict[str, Any] | None = None,
    *,
    approve: ApproveMode = "ask",
    prepare: bool = False,
) -> Project:
    """Make a project folder: copy the song and the given sheets into `input/`, write `project.json`.

    Raises `InvalidInput` naming every problem (unknown settings, a missing song, a bad sheet...). The
    folder appears whole or not at all, under an id no other project has (also when two processes make
    projects of the same name at once). `approve="auto"` runs it without stopping at the gates, unless a
    check reports errors (0004). `prepare=True` makes its run stop before the first local stage, every
    hosted call made (0028 §6)."""
    song = Path(song)
    if not isinstance(settings, Settings):
        settings = parse_settings(settings)
    problems = _check_inputs(song, [*material.sheets, *material.poses]) + (
        [] if name.strip() else ["name: give the video a name"]
    )
    if approve not in APPROVE_MODES:
        problems.append(f"approve: {approve!r} is not ask or auto")
    if problems:
        raise InvalidInput("the project cannot be made: " + "; ".join(problems), problems)
    projects = Path(projects_dir)
    projects.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=projects, prefix=f".new-{slug(name)}-"))
    try:
        inputs = _copy_inputs(work, song, material)
        record = ProjectFile(
            id="-", name=name.strip(), created=now(), settings=settings, inputs=inputs, approve=approve,
            prepare=prepare,
        )  # fmt: skip
        return _publish(work, projects, record)
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def _publish(work: Path, projects: Path, record: ProjectFile) -> Project:
    """Move the finished folder in under a free id; if another process takes that id first, the next."""
    while True:
        project_id = _free_id(projects, record.name)
        write_json(work / "project.json", record.model_copy(update={"id": project_id}).as_stored())
        try:
            work.rename(projects / project_id)  # fails when the id's folder exists (it is never empty)
        except OSError:
            if not (projects / project_id).exists():
                raise
            continue
        return Project(projects / project_id)


def _copy_inputs(work: Path, song: Path, material: Material) -> Inputs:
    inputs = work / "input"
    inputs.mkdir(parents=True)
    for folder in ("runs", "current"):
        (work / folder).mkdir()
    song_name = f"song{song.suffix.lower()}"
    shutil.copyfile(song, inputs / song_name)
    lyrics = material.lyrics.strip() if material.lyrics and material.lyrics.strip() else None
    if lyrics:
        (inputs / "lyrics.txt").write_text(lyrics + "\n", encoding="utf-8")
    sheets = _copy_pictures(work, inputs / "sheets", material.sheets)
    poses = _copy_pictures(work, inputs / "poses", material.poses)
    return Inputs(
        song=f"input/{song_name}", lyrics=lyrics, story=material.story.strip(), sheets=sheets, poses=poses,
        feeling=material.feeling.strip(),
    )  # fmt: skip


def _copy_pictures(work: Path, folder: Path, given: tuple[GivenSheet, ...]) -> list[StoredSheet]:
    folder.mkdir(parents=True, exist_ok=True)
    infos: list[StoredSheet] = []
    for sheet in given:
        target = folder / f"{sheet.name}{sheet.file.suffix.lower()}"
        shutil.copyfile(sheet.file, target)
        infos.append(StoredSheet(name=sheet.name, file=target.relative_to(work).as_posix(), note=sheet.note))
    return infos


def set_approve_mode(project: Project, approve: ApproveMode) -> None:
    """Ask the owner at each gate (`"ask"`) or approve each gate unattended (`"auto"`, 0004). It is read
    when the run reaches a gate, so it applies to a run already started; `resume` then passes a gate
    that is waiting."""
    if approve not in APPROVE_MODES:
        raise InvalidInput(f"approve: {approve!r} is not ask or auto", [f"approve: {approve!r}"])
    write_json(
        project.root / "project.json", project.record().model_copy(update={"approve": approve}).as_stored()
    )


def set_prepare(project: Project, prepare: bool) -> None:
    """Make the run stop before its first local stage (`True`), or go on through it (0028 §6)."""
    write_json(
        project.root / "project.json", project.record().model_copy(update={"prepare": prepare}).as_stored()
    )


def open_project(path: str | Path) -> Project:
    """The project at `path`; `NotFound` if it has no `project.json`."""
    root = Path(path)
    if not (root / "project.json").is_file():
        raise NotFound(f"no project at {root}: it has no project.json (make one with `hone-music-video new`)")
    return Project(root)


def unreadable(error: ValidationError) -> str:
    """Why `project.json` does not load: keys this version does not know mean a newer version made it."""
    unknown = [".".join(map(str, e["loc"])) for e in error.errors() if e["type"] == "extra_forbidden"]
    if unknown and len(unknown) == len(error.errors()):
        return f"made by a newer version of hone-music-video: {', '.join(unknown)}"
    return "project.json does not fit: " + "; ".join(problems_of(error))


def read_projects(projects_dir: str | Path) -> list[tuple[Project, ProjectFile | str]]:
    """Every project in a folder with its `project.json` read once (or why it cannot be read), newest
    first; the ones this version cannot read come last."""
    folder = Path(projects_dir)
    if not folder.is_dir():
        return []
    found = [(p, p.read()) for p in map(Project, folder.iterdir()) if (p.root / "project.json").is_file()]
    return sorted(found, key=lambda f: ("" if isinstance(f[1], str) else f[1].created, f[0].id), reverse=True)


def list_projects(projects_dir: str | Path) -> list[Project]:
    """Every project in a folder, newest first; one this version cannot read is listed too (last)."""
    return [project for project, _ in read_projects(projects_dir)]
