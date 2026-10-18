"""The scenes the Hone Frame way (change 0027): Hone Frame's behaviour up to the scenes, re-implemented
here. One project file of items is made top to bottom, one picture per step; every prompt is sent as
written, every version is kept, and the owner accepts, picks, redoes or replaces each picture.

Hone Frame: ported from `src/hone_frame/__init__.py` (its 0008 branch, 2026-10-16); each module names the
Hone Frame module it follows. `HoneModels` is replaced by `FrameModels`, the port over this library's
`Models`."""

from hone_music_video.frame import errors
from hone_music_video.frame.models import FrameModels
from hone_music_video.frame.ports import Cancelled, Generated, ModelFailure, ModelInfo, Models
from hone_music_video.frame.project import Project
from hone_music_video.frame.project_file import ItemSpec, ProjectSpec
from hone_music_video.frame.records import ItemState, ProjectState, RunRecord, Version
from hone_music_video.frame.runner import Runner
from hone_music_video.frame.sheets import SheetRecipe
from hone_music_video.frame.views import ItemView, ModelView, ProjectSummary, ProjectView, RunView
from hone_music_video.frame.workspace import Workspace

__all__ = [
    "Cancelled",
    "FrameModels",
    "Generated",
    "ItemSpec",
    "ItemState",
    "ItemView",
    "ModelFailure",
    "ModelInfo",
    "ModelView",
    "Models",
    "Project",
    "ProjectSpec",
    "ProjectState",
    "ProjectSummary",
    "ProjectView",
    "RunRecord",
    "RunView",
    "Runner",
    "SheetRecipe",
    "Version",
    "Workspace",
    "errors",
]
