"""Stages 5 and 6 of the run (change 0027): the frame plan written into the project's frame workspace,
and the frame run that makes its pictures; then the scenes as the clips take them.

- `install` writes the plan as the project file (`frame_toml`) into `<project>/frame/`: imported the
  first time (every item marked, given pictures copied in), written over the copy afterwards (new items
  marked, changed ones flagged "changed since made", Hone Frame's `write_text`). The shots' times and
  motion prompts go to the sidecar `<project>/frame/shots.json`.
- `run_scenes` drives the workspace's frame `Runner` until its run ends (Hone Frame's §8): in this thread
  when nobody else runs it (the command line), else waiting for the dashboard's runner. The owner's Pause
  and Stop (0022's request file) become the runner's pause and stop. An unattended project accepts each
  hold and takes each pick's first picture.
- `scenes_now` reads each shot's scene picture in use (no model is called) and keeps it as the shot's
  start frame: what `review_scenes`, the clips and a remake take."""

from __future__ import annotations

import hashlib
import shutil
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager, suppress
from pathlib import Path

from hone_music_video import frame_toml, pause
from hone_music_video._files import now, read_json, write_json
from hone_music_video._jobs import Job, copy_chosen
from hone_music_video._shot_jobs import shot_folder
from hone_music_video.errors import InvalidInput, ModelFailure, MusicVideoError, NotFound, Paused
from hone_music_video.frame import FrameModels, Runner, Workspace, actions
from hone_music_video.frame.making import next_up
from hone_music_video.frame.project import Project as FrameProject
from hone_music_video.frame.records import ProjectState, Version
from hone_music_video.frame.runner import ACTIVE
from hone_music_video.frame.workspace import copy_files
from hone_music_video.ports import Models
from hone_music_video.project import Project
from hone_music_video.records import Made, Shot, ShotFile, ShotFiles, Shots
from hone_music_video.records_frame import FramePlan, Planned, Scenes, SceneShot, SceneShots
from hone_music_video.settings import Settings

FOLDER = "frame"
SHOTS = "shots.json"
POLL_S = 0.5
DRIVES = 200  # rounds of run / accept an unattended stage may make before it gives up
READY = ("done", "provided")
_RUNNERS: dict[Path, Runner] = {}  # each project's frame runner in this process (the dashboard's)
_LOCK = threading.Lock()


def workspace(project: Project, models: Models | None = None) -> Workspace:
    """The project's frame workspace (Hone Frame's layout, format "2"); `models` None for reading only. A
    scene's takes never wait for a pick here (0028 §5)."""
    framed = FrameModels(models) if models is not None else None
    return Workspace(project.root / FOLDER, models=framed, scene_picks=False)


def frame_project(ws: Workspace) -> FrameProject:
    """The workspace's one frame project, the video's; refused before the plan is written."""
    found = ws.projects()
    if not found:
        raise NotFound("no frame plan yet: approve the lyrics and let the run plan the scenes")
    return found[0]


def has_plan(project: Project) -> bool:
    """The plan is written: the frame project and its shots' sidecar (written after it)."""
    projects = project.root / FOLDER / "projects"
    return (project.root / FOLDER / SHOTS).is_file() and projects.is_dir() and any(projects.iterdir())


def runner_for(project: Project, models: Models) -> Runner:
    """The project's frame runner in this process: the dashboard's background one, made on first use
    (Hone Frame's dashboard runs one per workspace, design §12.1)."""
    with _LOCK:
        found = _RUNNERS.get(project.root)
        if found is None:
            found = _RUNNERS[project.root] = Runner(workspace(project, models))
            found.recover()
            found.start()
        return found


def close_runners() -> None:
    """Stop every frame runner of this process (the dashboard closing)."""
    with _LOCK:
        runners = list(_RUNNERS.values())
        _RUNNERS.clear()
    for runner in runners:
        runner.close()


def image_notices(settings: Settings, models: Models) -> list[str]:
    """The frame's image models checked before anything is made: one the registry does not know is an
    error; one whose licence forbids commercial use a notice, never a block (0021 §4, 0027)."""
    lines: list[str] = []
    for model in settings.models.frame:
        found = models.image_info(model)  # NotFound: an unknown model, before the project is made
        if found.commercial_use is False:
            lines.append(
                f"notice: {model} is under {found.license or 'a research licence'}: not for commercial use"
            )
    return lines


# ------------------------------------------------------------------------------ stage 5: the file


def read_shots(project: Project) -> SceneShots:
    path = project.root / FOLDER / SHOTS
    if not path.is_file():
        raise InvalidInput(f"{project.id} has no frame plan yet ({FOLDER}/{SHOTS})")
    return read_json(path, SceneShots)


def write_shots(project: Project, shots: SceneShots) -> None:
    write_json(project.root / FOLDER / SHOTS, shots)


def install(job: Job, plan: FramePlan) -> Planned:
    """Write the plan as the frame project's file and the shots' sidecar; the project file is checked
    as an import is (Hone Frame's §5.3) and nothing is written when it is refused."""
    text = frame_toml.text(plan, job.project.record().name)
    ws = workspace(job.project, job.models)
    if not ws.projects():
        found = ws.import_text(text, "toml", files_root=job.project.root, source="the frame plan")
    else:
        found = frame_project(ws)
        spec = ws.check(text, "toml", files_root=job.project.root)
        found.write_text(copy_files(spec, text, job.project.root, found.root))
        found.log("edited", None, "the frame plan was written again")
    write_shots(job.project, SceneShots(shots=[_scene_shot(plan, s.id) for s in plan.shots]))
    digest = hashlib.sha256(found.text().encode()).hexdigest()
    return Planned(
        project=found.id, sha256=digest, shots=len(plan.shots), items=len(plan.items), problems=plan.problems
    )


def _scene_shot(plan: FramePlan, shot_id: str) -> SceneShot:
    s = next(x for x in plan.shots if x.id == shot_id)
    return SceneShot(
        scene=s.id, start_ms=s.start_ms, end_ms=s.end_ms, lines=s.lines, beat=s.beat, framing=s.framing,
        faces=s.faces, cast=[u.character for u in s.cast], location=s.place.place if s.place else "",
        camera=s.camera, motion_prompt=plan.motion.get(s.id, s.camera), feel=s.feel, evidence=s.evidence,
    )  # fmt: skip


def as_shots(shots: SceneShots, prompts: dict[str, str] | None = None) -> Shots:
    """The sidecar as the video's `Shots`; each still prompt the scene's prompt in use (or its beat)."""
    rows = [
        Shot(
            id=s.scene, start_ms=s.start_ms, end_ms=s.end_ms, lines=s.lines, beat=s.beat, framing=s.framing,
            faces=s.faces, cast=s.cast, location=s.location, camera=s.camera,
            still_prompt=(prompts or {}).get(s.scene, s.beat), motion_prompt=s.motion_prompt,
            clip_seed=s.clip_seed,
        )
        for s in shots.shots
    ]  # fmt: skip
    return Shots(shots=rows)


# ------------------------------------------------------------------------------ stage 6: the frame run


@contextmanager
def _stage_runner(project: Project, models: Models) -> Generator[Runner]:
    """The dashboard's runner when there is one; else one for this stage, which drains it."""
    with _LOCK:
        found = _RUNNERS.get(project.root)
        mine = found is None
        if found is None:
            found = _RUNNERS[project.root] = Runner(workspace(project, models))
    try:
        yield found
    finally:
        if mine:
            with _LOCK:
                _RUNNERS.pop(project.root, None)


def _go(runner: Runner, fp: FrameProject) -> None:
    """Let the frame run end: drain it here, or wait for the background runner."""
    if not runner.background:
        runner.drain()
        return
    while fp.run().status in ACTIVE:
        time.sleep(POLL_S)


@contextmanager
def _watch(project: Project, runner: Runner, fp: FrameProject) -> Generator[None]:
    """The owner's Pause or Stop (0022's request) as the frame runner's pause or stop: both cancel the
    picture being made (Hone Frame's §8.3)."""
    began, done = time.time(), threading.Event()

    def watch() -> None:
        while not done.wait(POLL_S):
            asked = pause.asked(project)
            if asked is None or asked.at < began:
                continue
            with suppress(MusicVideoError):  # nothing running to pause: the stage ends on its own
                (runner.stop if asked.now else runner.pause)(fp.id)
            return

    thread = threading.Thread(target=watch, name="hone-music-video-frame-watch", daemon=True)
    thread.start()
    try:
        yield
    finally:
        done.set()
        thread.join(timeout=5)


def _accept_waiting(runner: Runner, fp: FrameProject) -> bool:
    """Unattended: accept each item that waits, a pick's first picture; whether one was."""
    waiting = [(i, st) for i, st in fp.state().items.items() if st.status == "waiting" and not st.marked]
    for item_id, st in waiting:
        runner.accept(fp.id, item_id, st.candidates[0] if len(st.candidates) > 1 else None)
    return bool(waiting)


def _drive(runner: Runner, fp: FrameProject, *, unattended: bool) -> None:
    """One frame run, as the owner's Run (or Resume of a paused one) makes it: it ends at a hold, with
    picks left, done, paused or failed (Hone Frame's §8; a scene's takes never wait, 0028 §5).
    Unattended, each hold is accepted and each pick takes its first picture, and the run goes on until
    nothing waits."""
    for _ in range(DRIVES):
        status = fp.run().status
        if status in ACTIVE:
            _go(runner, fp)
        elif status == "paused" and fp.marked():
            runner.resume(fp.id)
            _go(runner, fp)
        elif next_up(fp)[0]:
            runner.run(fp.id)
            _go(runner, fp)
        if not unattended or fp.run().status in ("paused", "stopped", "failed"):
            return
        if not _accept_waiting(runner, fp) and not next_up(fp)[0]:
            return


def run_scenes(job: Job, *, unattended: bool) -> Scenes:
    """Stage 6: the frame run until it ends; the scenes as they are then. A paused or stopped frame run
    pauses the video's run (`resume` goes on), a failed one fails the stage with its reason."""
    ws = workspace(job.project, job.models)
    fp = frame_project(ws)
    with _stage_runner(job.project, job.models) as runner:
        if not runner.background:
            runner.recover([fp.id])
        with _watch(job.project, runner, fp):
            _drive(runner, fp, unattended=unattended)
    end = fp.run()
    if end.status in ("paused", "stopped"):
        raise Paused(pause.MESSAGE)
    if end.status == "failed":
        raise ModelFailure(f"the scenes stopped: {end.reason}")
    return scenes_now(job.project, job=job)


# ------------------------------------------------------------------------------ the scenes in use


def _in_use(state: ProjectState, item_id: str) -> Version | None:
    st = state.items.get(item_id)
    if st is None or st.status not in READY or st.current is None or st.marked:
        return None
    return st.version(st.current)


def not_ready(project: Project) -> list[str]:
    """The scenes without a picture in use (made, accepted, nothing marked), in order."""
    fp = frame_project(workspace(project))
    state, shots = fp.state(), read_shots(project)
    return [s.scene for s in shots.shots if _in_use(state, s.scene) is None]


def pictures_in_use(project: Project) -> dict[str, Path]:
    """Each scene's picture in use in the frame workspace, before the shots keep them as start frames."""
    fp = frame_project(workspace(project))
    state = fp.state()
    versions = {s.scene: _in_use(state, s.scene) for s in read_shots(project).shots}
    return {scene: fp.root / v.file for scene, v in versions.items() if v is not None}


def scenes_now(project: Project, *, job: Job | None = None) -> Scenes:
    """The scenes as they are: when every shot's scene has a picture in use, the shots with its prompt
    and each picture kept as the shot's start frame (`job` given: the versions are written)."""
    fp = frame_project(workspace(project))
    state, shots, end = fp.state(), read_shots(project), fp.run()
    versions = {s.scene: _in_use(state, s.scene) for s in shots.shots}
    missing = [i for i, v in versions.items() if v is None]
    if missing:
        more = f" and {len(missing) - 5} more" if len(missing) > 5 else ""
        reason = f"no picture in use yet for {', '.join(missing[:5])}{more}"
        return Scenes(run=end.status, reason=reason)
    found = {i: v for i, v in versions.items() if v is not None}
    stills = ShotFiles(shots=[_start_frame(project, fp, i, v, job) for i, v in found.items()])
    prompts = {i: v.prompt or "" for i, v in found.items()}
    return Scenes(run=end.status, reason=end.reason, shots=as_shots(shots, prompts), stills=stills)


def takes_now(project: Project, job: Job) -> dict[str, list[str]]:
    """The other takes of each scene with several (`count` or `prompts`, 0028 §5): its latest pictures
    of one run but the one in use, each kept as a start frame of the shot (not `still.png`), so their
    clips can be made beside the one in use and a later pick only cuts again."""
    fp = frame_project(workspace(project))
    state, spec = fp.state(), {i.id: i for i in fp.spec().items}
    found: dict[str, list[str]] = {}
    for shot in read_shots(project).shots:
        item, st = spec.get(shot.scene), state.items.get(shot.scene)
        used = _in_use(state, shot.scene)
        if item is None or st is None or used is None or item.per_run < 2:
            continue  # an item with `prompts` makes one take at a time (0033)
        latest = [v for v in st.versions if v.source == "generated"][-item.per_run :]
        others = [v for v in latest if v.n != used.n]
        found[shot.scene] = [_start_frame(project, fp, shot.scene, v, job, chosen=False).file for v in others]
    return found


def _start_frame(
    project: Project, fp: FrameProject, shot: str, version: Version, job: Job | None, *, chosen: bool = True
) -> ShotFile:
    """The scene's picture in use as the shot's start frame version, with its `Made` record, and its
    `still.png` (what stage 8 reads); another take (`chosen=False`) keeps only the version."""
    source = fp.root / version.file
    key = hashlib.sha256(source.read_bytes()).hexdigest()
    folder = project.current / "shots" / shot
    out = folder / "versions" / f"stills-{key[:12]}.png"
    if job is not None:
        shot_folder(job, shot)  # the id is a safe folder name
    if not out.is_file():
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, out)
        made = Made(
            stage="stills", subject=shot, file=project.relative(out), key=key, model=version.model or "",
            prompt=version.prompt or "", seed=version.seed or 0,
            inputs={"frame_item": shot, "frame_version": version.n, "refs": version.refs},
            settings=project.settings.model_dump(mode="json"), made_at=now(),
        )  # fmt: skip
        write_json(out.with_suffix(".json"), made)
    if chosen:
        copy_chosen(out, folder / "still.png")
    return ShotFile(shot=shot, file=project.relative(out), key=key)


def accept_scene(project: Project, item_id: str, version: int | None = None) -> None:
    """Accept or pick a scene from the command line, as the dashboard does (Hone Frame's `accept`)."""
    actions.accept(frame_project(workspace(project)), item_id, version)
