"""The settings of a video (design §2.3) and the model of each role (design §3.2).

Settings are data given with the song. They are validated here (unknown keys are rejected) and reach the
planners as data, never as words the owner has to write into a prompt (guarantee 13)."""

from __future__ import annotations

from typing import Any, Literal, cast, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from hone_music_video.errors import InvalidInput

AspectRatio = Literal["16:9", "9:16", "1:1", "4:5"]
Pace = Literal["calm", "balanced", "energetic"]  # how the shots are cut (0009, D-084)
TakeClips = Literal["picked", "all"]  # clips for the take in use only, or for every take (0031)
PACES: tuple[Pace, ...] = get_args(Pace)
RETIRED_ROLES = ("upscale", "interpolation")  # replaced by `finish` in M5 (D-032)
# the settings and roles of the scene pipeline before 0027 (cast, sheets, packs, references, the judges,
# the retries, best-of, the polish): a stored project's are read and dropped (0027 §8)
RETIRED_0027 = (
    "still_takes", "packs", "sheet_takes", "prop_sheet_takes", "polish", "face_refs", "quality_check",
    "rewrite_motion", "quality_gate", "pick_best_of", "pick_shots", "still_retries", "sheet_retries",
)  # fmt: skip
RETIRED_ROLES_0027 = ("cast", "shots", "quality", "sheets", "views", "stills", "polish")
OPUS = "claude-opus-5-5"  # the planner's model
HAIKU = "claude-haiku-5-5"  # the review of the shot list: a check, not a planner (0028)
QWEN_TURBO = "qwen-image-2.1-turbo"  # every picture of a new project (0021); not for commercial use


class ModelRoles(BaseModel):
    """The model id per role (design §3.2); each is a hone-models registry id but `vocals`, the Demucs
    model of the first listen's vocals (D-041, D-045), and `align`, the torchaudio bundle that aligns
    given lyrics to them (`None`: the lines are timed from the heard words; 0005).

    `planner` writes the frame plan in several calls (0026, 0027); `frame` lists the image models of the
    frame project: the first is `[defaults] model`, the others a picture may name (0027). The finish is one
    role: Real-ESRGAN, the resize and RIFE in one ComfyUI job per clip (design §11.3, D-032)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    speech: str = "scribe_v2"  # ElevenLabs Scribe on the gateway: steadier than whisper-1 (D-049)
    lyrics: str = OPUS
    planner: str = OPUS
    review: str = HAIKU  # reads the shot list for the feeling and sends it back with notes (0028 §2)
    frame: tuple[str, ...] = Field(default=(QWEN_TURBO,), min_length=1)
    clips: str = "wan2.2-i2v-14b"
    finish: str = "esrgan-rife-x2"
    vocals: str = "htdemucs"  # Demucs on the CPU, the first listen's vocals (D-045); not a registry id
    align: str | None = "MMS_FA"  # Meta's MMS forced aligner on the CPU (0005); not a registry id


class Settings(BaseModel):
    """What the video should look like, with the defaults of design §2.3."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    style: str = Field(default="photoreal live-action film, 35mm film look, natural film grain", min_length=1)
    aspect_ratio: AspectRatio = "16:9"
    resolution: int = Field(default=1080, gt=0, description="the short side of the final video, in pixels")
    fps: Literal[32] = Field(default=32, description="Wan's 16 fps doubled by RIFE (D-004)")
    min_shot_ms: int = Field(default=2000, gt=0, strict=True)
    max_shot_ms: int = Field(default=8000, gt=0, strict=True)
    language: str | None = None
    pace: Pace = "balanced"  # calm: long shots, cuts on lines; energetic: short shots (0009, D-084)
    mood: str = ""  # free words, any language: light, colour, camera speed, stillness, faces (0009)
    take_clips: TakeClips = "picked"  # "all": every take of a scene gets its clip overnight (0028 §5, 0031)
    models: ModelRoles = ModelRoles()

    @model_validator(mode="after")
    def _consistent(self) -> Settings:
        if self.min_shot_ms > self.max_shot_ms:
            raise ValueError(
                f"min_shot_ms ({self.min_shot_ms}) is larger than max_shot_ms ({self.max_shot_ms}); "
                "make the minimum at most the maximum"
            )
        return self

    def for_planner(self) -> dict[str, Any]:
        """The settings a planner needs, as data (design §7.1): everything but the model ids and which
        takes get clips."""
        return self.model_dump(mode="json", exclude={"models", "take_clips"})


def problems_of(error: ValidationError) -> list[str]:
    """`"<field>: <message>"` for each problem of a pydantic validation error."""
    return [f"{'.'.join(map(str, e['loc'])) or 'settings'}: {e['msg']}" for e in error.errors()]


def stored(data: Any) -> Any:
    """Settings as an earlier version stored them (a project's `project.json`, a run's `settings` param):
    the retired roles `upscale` and `interpolation` dropped, `finish` replaced them (D-032); without `align`
    (made before 0005) alignment off, so the lyrics keep being timed as they were (D-059). The settings of
    the scene pipeline before 0027 are dropped; its shot planner becomes the `planner`, its start-frame
    model the `frame` model (0027 §8)."""
    if not isinstance(data, dict):
        return data
    record = {k: v for k, v in cast(dict[str, Any], data).items() if k not in RETIRED_0027}
    models = record.get("models")
    if not isinstance(models, dict):
        return record
    given = cast(dict[str, Any], models)
    kept = {k: v for k, v in given.items() if k not in (*RETIRED_ROLES, *RETIRED_ROLES_0027)}
    older = {"planner": given["shots"]} if "shots" in given and "planner" not in given else {}
    older |= {"frame": [given["stills"]]} if "stills" in given and "frame" not in given else {}
    return record | {"models": {"align": None} | older | kept}


def parse_settings(data: dict[str, Any] | None) -> Settings:
    """Validate settings given as plain data; `InvalidInput` names every problem (unknown keys too, and
    the retired roles with what replaced them)."""
    models = (data or {}).get("models")
    retired = [k for k in RETIRED_ROLES if isinstance(models, dict) and k in models]
    if retired:
        problems = [f"models.{k}: replaced by models.finish in 0.1 (D-032)" for k in retired]
        raise InvalidInput("the settings do not fit: " + "; ".join(problems), problems)
    try:
        return Settings.model_validate(data or {})
    except ValidationError as error:
        problems = problems_of(error)
        raise InvalidInput(
            "the settings do not fit: " + "; ".join(problems) + " (see design §2.3 for every setting)",
            problems,
        ) from None
