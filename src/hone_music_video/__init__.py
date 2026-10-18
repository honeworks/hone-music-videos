"""hone-music-video: song in, music video out (design: design/current.md, accepted in change 0001; the
scenes the Hone Frame way since change 0027).

import hone_music_video as hmv
from hone_music_video.testing import FakeModels

project = hmv.create_project("projects", "My song", "song.wav", settings={"aspect_ratio": "9:16"})
state = hmv.start(project, FakeModels())      # runs until the first owner gate
hmv.lyrics_timing(project, {"L002": {"start_ms": 8200, "end_ms": 13600}})  # fix a line's times (0018)
hmv.approve(project)                          # the timed lyrics look right (or hmv.reject with a note)
state = hmv.resume(project, FakeModels())     # the frame plan in several calls, then review_plan
hmv.approve(project)                          # the project file and the shot list look right
state = hmv.resume(project, FakeModels())     # the frame run: the demo first, then waits at a hold
# accept, pick, redo, replace in the Scenes view (or `hone-music-video frame ...`), then:
hmv.approve(project)                          # review_scenes: every scene has its picture
state = hmv.resume(project, FakeModels())     # clips, finished clips, the video
hmv.remake(project, FakeModels())             # after a scene changed: only its clip again (0027 §7)
hmv.assemble(project, FakeModels())           # cut the video again from the finished clips (D-036)
hmv.export(project)                           # edit.xml and edit.edl for an editor (design §12.1)
hmv.costs(project)                            # what it cost: hosted calls, GPU time (design §13.5)
"""

from hone_music_video import frame
from hone_music_video.adapters.hone_models import HoneModels
from hone_music_video.dashboard import Dashboard
from hone_music_video.editor_files import export
from hone_music_video.errors import (
    InvalidInput,
    ModelFailure,
    MusicVideoError,
    NotFound,
    ProjectUnreadable,
    RunStateError,
    ToolMissing,
)
from hone_music_video.lyrics_check import check_lyrics
from hone_music_video.owner_timing import Reviewed
from hone_music_video.ports import Generated, ImageInfo, Models
from hone_music_video.project import (
    GivenSheet,
    Material,
    Project,
    ProjectFile,
    create_project,
    list_projects,
    open_project,
    set_approve_mode,
)
from hone_music_video.records import (
    AlignedWord,
    Alignment,
    Assembly,
    Disagreement,
    Line,
    ListenAgain,
    Made,
    Moved,
    Problem,
    Report,
    Retry,
    Section,
    Separation,
    Shot,
    ShotFiles,
    Shots,
    Song,
    Timeline,
    Unsure,
    Word,
    Words,
)
from hone_music_video.records_frame import Planned, Scenes, SceneShot, SceneShots
from hone_music_video.runs import RunState, Stage, approve, lyrics_timing, reject, resume, start, status
from hone_music_video.runs_redo import assemble, redo_clips, remake, set_motion
from hone_music_video.settings import ModelRoles, Settings, parse_settings
from hone_music_video.shots_check import check_shots
from hone_music_video.video_costs import Costs, costs
from hone_music_video.workflow import GATES, STAGES

__all__ = [
    "GATES",
    "STAGES",
    "AlignedWord",
    "Alignment",
    "Assembly",
    "Costs",
    "Dashboard",
    "Disagreement",
    "Generated",
    "GivenSheet",
    "HoneModels",
    "ImageInfo",
    "InvalidInput",
    "Line",
    "ListenAgain",
    "Made",
    "Material",
    "ModelFailure",
    "ModelRoles",
    "Models",
    "Moved",
    "MusicVideoError",
    "NotFound",
    "Planned",
    "Problem",
    "Project",
    "ProjectFile",
    "ProjectUnreadable",
    "Report",
    "Retry",
    "Reviewed",
    "RunState",
    "RunStateError",
    "SceneShot",
    "SceneShots",
    "Scenes",
    "Section",
    "Separation",
    "Settings",
    "Shot",
    "ShotFiles",
    "Shots",
    "Song",
    "Stage",
    "Timeline",
    "ToolMissing",
    "Unsure",
    "Word",
    "Words",
    "__version__",
    "approve",
    "assemble",
    "check_lyrics",
    "check_shots",
    "costs",
    "create_project",
    "export",
    "frame",
    "list_projects",
    "lyrics_timing",
    "open_project",
    "parse_settings",
    "redo_clips",
    "reject",
    "remake",
    "resume",
    "set_approve_mode",
    "set_motion",
    "start",
    "status",
]

__version__ = "0.0.1"
