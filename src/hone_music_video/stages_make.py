"""Stages 8 to 10 (design §3.1, before 0027 stages 12 to 14): a clip and a finished clip per shot, and
assembly; the sizes of the clips and the finished video.

Each stage makes the file of each shot inside one model session (D-005) and keeps it as a version with
its `Made` record (D-009). A version already made is not made again, so a run killed during a stage
resumes without redoing the shots it finished (guarantee 11), and a remake makes only the shots whose
start frame, motion prompt or clip seed changed (guarantee 12, 0027 §7)."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hone_music_video import editor_files
from hone_music_video._files import write_json
from hone_music_video._jobs import Job, ShotJob, Units, seed_for
from hone_music_video._shot_jobs import TaskSpec, by_shot, job_for, make_all, other_takes, shot_files
from hone_music_video._video import Clip, cut, join, probe, require_ffmpeg
from hone_music_video.errors import InvalidInput
from hone_music_video.records import Assembly, Cut, Shot, ShotFile, ShotFiles, Shots, Song
from hone_music_video.settings import Settings

REMAKE = (
    "redo the odd shots (`hone-music-video redo PROJECT SHOT --seed`) or put their files back, then resume"
)
CUTS_AT_ONCE = 4  # cuts at once: 60 1080p cuts take 55 s instead of 79 (D-035)
WAN_FPS = 16  # Wan 2.2's native frame rate (design §11.1)
# Per aspect ratio: the start frame, the clip, the clip of a shot with faces (design §10.2, §11.1, D-030).
SIZES = {
    "16:9": ("1024x576", "832x480", "960x544"),
    "9:16": ("576x1024", "480x832", "544x960"),
    "1:1": ("768x768", "624x624", "720x720"),
    "4:5": ("704x880", "576x720", "640x800"),
}
TaskOf = Callable[[Job, Shot, str], TaskSpec]  # the job, the shot, the file it is made from


FACE_MAX_FRAMES = 110  # the longest face clip that fit the 8 GB card at the larger size: 6760 ms (D-082)


def clip_size(settings: Settings, faces: bool, frames: int) -> str:
    """832x480 for 16:9, 960x544 when a face must be recognisable and the clip has at most
    `FACE_MAX_FRAMES` frames (design §11.1, guarantee 9, D-082)."""
    return SIZES[settings.aspect_ratio][2 if faces and frames <= FACE_MAX_FRAMES else 1]


def output_size(settings: Settings) -> str:
    """The finished clip: the aspect ratio with `resolution` as its short side, even (1920x1080)."""
    w, h = (int(n) for n in settings.aspect_ratio.split(":"))
    short = settings.resolution
    long = round(short * max(w, h) / min(w, h) / 2) * 2
    return f"{long}x{short}" if w >= h else f"{short}x{long}"


def clip_frames(duration_ms: int) -> int:
    """Frames of a clip at 16 fps: one more than the shot needs, 33 to 129 (design §11.1)."""
    return min(129, max(33, -(-duration_ms * WAN_FPS // 1000) + 1))


def _jobs(
    job: Job, shots: Shots, stage: str, sources: Mapping[str, str], task_of: TaskOf, *, chosen: bool = True
) -> dict[str, ShotJob]:
    """The job of every shot whose source file exists (0027: the seed is the shot's clip seed)."""
    jobs: dict[str, ShotJob] = {}
    for shot in shots.shots:
        if shot.id in sources:
            seed = seed_for(job.seed, shot.id, "clip", shot.clip_seed)
            task = task_of(job, shot, sources[shot.id])
            jobs[shot.id] = job_for(job, shot.id, stage, task, seed, chosen_copy=chosen)
    return jobs


def take_jobs(
    job: Job, shots: Shots, stage: str, takes: Mapping[str, list[str]], task_of: TaskOf
) -> list[ShotJob]:
    """The jobs of the other takes' files (0028 §5): the same seed and prompt as the shot's, so a take
    picked later finds its clip made and only the cut is made again."""
    found: list[ShotJob] = []
    for k in range(max((len(t) for t in takes.values()), default=0)):
        nth = {shot: files[k] for shot, files in takes.items() if k < len(files)}
        found += _jobs(job, shots, stage, nth, task_of, chosen=False).values()
    return found


def _per_shot(
    job: Job,
    shots: Shots,
    stage: str,
    *,
    sources: Mapping[str, str],
    task_of: TaskOf,
    takes: Mapping[str, list[str]] | None = None,
) -> ShotFiles:
    """The job of every shot whose source file exists, then the other takes', made in one session per
    model, the shots' first; the files."""
    jobs = _jobs(job, shots, stage, sources, task_of)
    others = take_jobs(job, shots, stage, takes or {}, task_of)
    units = Units(job, stage)
    units.count(stage, [*jobs.values(), *others])
    units.announce()
    make_all(units, stage, [*jobs.values(), *others])
    return shot_files(job, jobs, others)


def clip_task(job: Job, shot: Shot, source: str) -> TaskSpec:
    """A raw clip from the still `source` with the shot's motion prompt: the larger size when the shot
    has `faces` and is not too long (D-082)."""
    frames = clip_frames(shot.end_ms - shot.start_ms)
    size = clip_size(job.settings, shot.faces, frames)
    # the registry entry turns seconds into `round(s * 16 + 1)` frames: exactly `frames` (D-033)
    inputs = {"image": job.project.path(source), "size": size, "duration_s": (frames - 1) / WAN_FPS}
    return job.settings.models.clips, shot.motion_prompt, inputs


def finish_task(job: Job, _shot: Shot, source: str) -> TaskSpec:
    """The finishing job of the raw clip `source`, to the output size."""
    inputs = {"video": job.project.path(source), "size": output_size(job.settings)}
    return job.settings.models.finish, "", inputs


def clips(
    job: Job, shots: Shots, stills: ShotFiles, takes: Mapping[str, list[str]] | None = None
) -> ShotFiles:
    """Stage 8: a raw clip per shot from its start frame and motion prompt (design §11.1): the larger
    size exactly when the shot has `faces` (guarantee 9), one frame more than the shot at 16 fps; then
    one per other take of a scene (`takes`: the start frames by shot, 0028 §5)."""
    return _per_shot(job, shots, "clips", sources=by_shot(stills), task_of=clip_task, takes=takes)


def finish(job: Job, shots: Shots, clips: ShotFiles) -> ShotFiles:
    """Stage 9: one finishing job per clip: Real-ESRGAN x2, Lanczos to the output size, RIFE x2 to
    32 fps (design §11.3, D-032); then the other takes' clips (0028 §5)."""
    others = other_takes(clips)
    return _per_shot(job, shots, "finish", sources=by_shot(clips), task_of=finish_task, takes=others)


# ------------------------------------------------------------------------------ 14: assembly


def frame_at(ms: int, fps: int) -> int:
    """The output frame at an absolute time, rounded half up (design §5.3)."""
    return (ms * fps + 500) // 1000


def _clips(job: Job, finished: ShotFiles) -> dict[str, Clip]:
    """Each shot's finished clip measured. They must share one size and the video's frame rate: the cuts
    are joined without encoding them again (D-035)."""

    def measure(f: ShotFile) -> Clip:
        try:
            return probe(job.project.path(f.file))
        except InvalidInput as error:
            raise InvalidInput(f"{f.shot}'s finished clip: {error}; {REMAKE}") from None

    found = {f.shot: measure(f) for f in finished.shots}
    rate = f"{job.settings.fps}/1"
    if len({c.size for c in found.values()}) > 1 or any(c.rate != rate for c in found.values()):
        clips = "; ".join(f"{shot} is {c.size} at {c.rate} fps" for shot, c in found.items())
        raise InvalidInput(f"the finished clips must share one size and be {rate} fps: {clips}; {REMAKE}")
    return found


def _cuts(job: Job, shots: Shots, finished: ShotFiles, clips: dict[str, Clip]) -> list[Cut]:
    """Each shot's frames from its absolute times (design §5.3), taken from the start of the finished
    clip it uses; a clip shorter than that holds its last frame, with a `clip_short` event (D-035).
    `held_frames` is estimated from the clip's packets; the cut itself always makes exactly the frames."""
    fps, file = job.settings.fps, {f.shot: f.file for f in finished.shots}
    cuts: list[Cut] = []
    for shot in shots.shots:
        first, end = frame_at(shot.start_ms, fps), frame_at(shot.end_ms, fps)
        held = max(0, end - first - clips[shot.id].frames)
        cuts.append(
            Cut(shot=shot.id, clip=file[shot.id], first_frame=first, last_frame=end - 1, held_frames=held)
        )
        if held:
            job.events.write("clip_short", shot=shot.id, held_frames=held)
    return cuts


def assemble(job: Job, shots: Shots, finished: ShotFiles, audio: Song) -> Assembly:
    """Stage 10: each finished clip cut to its shot's frames, the cuts in order under the song as
    `current/video.mp4` (H.264, CRF 17), the edit list `current/edl.json` (design §5.3, §12, D-035) and
    the same edit for editors (`edit.xml`, `edit.edl`; D-063)."""
    require_ffmpeg()
    fps, project = job.settings.fps, job.project
    for left in project.root.glob(".assemble-*"):  # the work of an assembly killed midway
        shutil.rmtree(left, ignore_errors=True)
    clips = _clips(job, finished)
    cuts = _cuts(job, shots, finished, clips)
    video = project.current / "video.mp4"
    with tempfile.TemporaryDirectory(dir=project.root, prefix=".assemble-") as tmp:
        kept = [c for c in cuts if c.last_frame >= c.first_frame]  # a shot under half a frame has none
        parts = [Path(tmp) / f"{c.shot}.mp4" for c in kept]

        def cut_one(c: Cut, part: Path) -> None:
            cut(project.path(c.clip), c.last_frame - c.first_frame + 1, fps, part)

        with ThreadPoolExecutor(CUTS_AT_ONCE) as pool:
            list(pool.map(cut_one, kept, parts))
        song, made = project.path(project.record().inputs.song), Path(tmp) / "video.mp4"
        join(parts, Path(tmp) / "cuts.txt", song, made)
        made.replace(video)  # whole or not at all: the old video stays until the new one is made
    assembly = Assembly(fps=fps, edl=cuts, video=project.relative(video))
    write_json(project.current / "edl.json", assembly)
    _editor_files(job, assembly, clips, audio)
    return assembly


def _editor_files(job: Job, assembly: Assembly, clips: dict[str, Clip], song: Song) -> None:
    """The same edit for DaVinci Resolve and Premiere (design §12.1, D-063). The video is made by then, so
    a failure here is a warning event (`editor_files_failed`), never a failed assembly."""
    try:
        editor_files.write(job.project, assembly, clips, song)
    except Exception as error:  # whatever it is, the video stands; `export` tries again
        job.events.write("editor_files_failed", error=f"{type(error).__name__}: {error}")
