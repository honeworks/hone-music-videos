"""The dashboard over real HTTP (design §13, 0027): the page, the JSON API, a video added and run to the end
on fake models with every gate approved and the scenes settled from the dashboard (the frame API: accept,
run, an edit written back keeping the file's comments, pictures and thumbnails served), live progress as
server-sent events, the remakes after the video, and the project views' records and media (content
types, byte ranges for seeking, what is never served)."""

import json
import threading
import time
import urllib.error
import urllib.request
from base64 import b64encode
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.testing import FakeModels, make_picture, make_song


@pytest.fixture
def base(tmp_path: Path) -> Iterator[str]:
    dashboard = hmv.Dashboard(tmp_path / "projects", FakeModels(), port=0).start()
    yield dashboard.url.rstrip("/")
    dashboard.close()


GATES = ("review_lyrics", "review_plan", "review_scenes")  # the scenes settled before their gate (0027)


def call(
    base: str, path: str, body: Any = None, method: str | None = None
) -> tuple[int, Any, dict[str, str]]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(  # noqa: S310 - our own server on 127.0.0.1
        base + path,
        data=data,
        method=method or ("POST" if data else "GET"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            raw, kind = response.read(), response.headers.get("Content-Type", "")
            return response.status, json.loads(raw) if "json" in kind else raw, dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}"), dict(error.headers)


def upload(path: Path) -> dict[str, str]:
    return {"name": path.name, "data_b64": b64encode(path.read_bytes()).decode()}


def wait_for(base: str, project_id: str, check: str) -> dict[str, Any]:
    deadline, found = time.monotonic() + 20, {}
    while time.monotonic() < deadline:
        found = call(base, f"/api/projects/{project_id}")[1]
        assert "error" not in found, found
        if found["status"] == check or found["waiting"] == check:
            return found
        time.sleep(0.05)
    raise AssertionError(f"{project_id} never reached {check}: {found}")


def settle(base: str, project_id: str) -> dict[str, Any]:
    """What the owner does in the Scenes view (0027): accept what waits (the first of several pictures),
    run what is marked, until nothing waits and nothing is marked; the frame project's view then."""
    frame = f"/api/projects/{project_id}/frame"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        view = call(base, frame)[1]
        if view["run"]["status"] in ("queued", "running", "pausing"):
            time.sleep(0.05)
            continue
        waiting = [i for i in view["items"] if i["status"] == "waiting"]
        for item in waiting:  # a run waiting for it goes on by itself (Hone Frame D-074)
            body = {"version": item["candidates"][0]} if item["candidates"] else {}
            assert call(base, f"{frame}/items/{item['id']}/accept", body)[0] == 200
        if waiting:
            continue
        if not any(i["marked"] for i in view["items"]):
            return view
        assert call(base, f"{frame}/run", {})[0] == 200
    raise AssertionError(f"the scenes of {project_id} never settled")


def to_the_end(base: str, project_id: str) -> dict[str, Any]:
    """Every gate approved from the dashboard, the scenes settled first."""
    for gate in GATES:
        wait_for(base, project_id, gate)
        if gate == "review_scenes":
            settle(base, project_id)
        assert call(base, f"/api/projects/{project_id}/approve", {"gate": gate})[1] == {"approved": gate}
    return wait_for(base, project_id, "completed")


def test_a_project_this_version_cannot_read_is_listed_not_fatal(base: str, tmp_path: Path) -> None:
    """A project.json with a key this version does not know (made by a newer one) shows as unreadable
    with the reason; the other projects still list, and opening it is a 422, not a 500."""
    good = hmv.create_project(tmp_path / "projects", "Good", make_song(tmp_path / "song.wav", 3000))
    newer = tmp_path / "projects" / "newer"
    newer.mkdir()
    record = json.loads((good.root / "project.json").read_text())
    record["id"] = "newer"
    record["settings"]["models"]["singer"] = "a-future-model"
    (newer / "project.json").write_text(json.dumps(record))
    (tmp_path / "projects" / "broken").mkdir()
    (tmp_path / "projects" / "broken" / "project.json").write_text("{not json")

    status, listed, _ = call(base, "/api/projects")
    assert status == 200 and [p["id"] for p in listed] == ["good", "newer", "broken"]
    assert listed[0]["status"] == "not_started"
    assert listed[1]["status"] == "unreadable"
    assert listed[1]["problem"] == "made by a newer version of hone-music-video: settings.models.singer"
    assert listed[2]["problem"].startswith("project.json does not fit")
    status, error, _ = call(base, "/api/projects/newer")
    assert status == 422 and "newer cannot be read: made by a newer version" in error["error"]
    with pytest.raises(hmv.ProjectUnreadable, match=r"settings\.models\.singer"):
        hmv.open_project(newer).record()
    assert isinstance(hmv.open_project(good.root).read(), hmv.ProjectFile)


def test_the_page_and_its_files(base: str) -> None:
    status, page, headers = call(base, "/")
    assert status == 200 and b"hone" in page and "script-src 'self'" in headers["Content-Security-Policy"]
    page_files = Path(hmv.__file__).parent / "dashboard_page"
    names = sorted(p.relative_to(page_files).as_posix() for p in page_files.rglob("*.*"))
    assert {"app.js", "base.css", "views.css", "player.js", "views/overview.js"} <= set(names)
    for name in names:
        status, _, headers = call(base, f"/{name}")
        assert status == 200 and headers["X-Content-Type-Options"] == "nosniff", name
    assert call(base, "/p/some/route")[0] == 200  # the page's own routes
    assert call(base, "/api/nothing")[0] == 404
    defaults = call(base, "/api/settings")[1]["defaults"]
    assert defaults == hmv.Settings().model_dump(mode="json")


def test_a_video_is_added_and_runs_to_the_end_from_the_dashboard(base: str, tmp_path: Path) -> None:
    song = make_song(tmp_path / "in" / "song.wav", 20_000)
    sheet = make_picture(tmp_path / "in" / "darvin.png")
    body = {
        "name": "From the dashboard",
        "lyrics": "one two three four five six seven eight",
        "story": "a hero rides",
        "settings": {"aspect_ratio": "9:16"},
        "song": upload(song),
        "sheets": [{"name": "Darvin", "note": "the hero", "file": upload(sheet)}],
    }
    status, made, _ = call(base, "/api/projects", body)
    assert status == 200 and made["id"] == "from-the-dashboard"
    project_id = made["id"]
    assert wait_for(base, project_id, "review_lyrics")["duration_ms"] == 20_000
    found = to_the_end(base, project_id)
    assert [s["status"] for s in found["run"]["stages"]] == ["done"] * 10
    assert found["project"]["settings"]["aspect_ratio"] == "9:16"
    assert found["thumbnail"].startswith(f"/files/{project_id}/current/")
    status, picture, headers = call(base, found["thumbnail"])
    assert status == 200 and headers["Content-Type"] == "image/png" and picture.startswith(b"\x89PNG")
    listed = call(base, "/api/projects")[1]
    assert [(p["id"], p["status"]) for p in listed] == [(project_id, "completed")]
    check_costs_and_edit_files(base, project_id)


def check_costs_and_edit_files(base: str, project_id: str) -> None:
    """What the video cost (design §13.5) and the edit for editors (design §12.1), as the Video view
    reads them."""
    status, spent, _ = call(base, f"/api/projects/{project_id}/costs")
    assert status == 200 and spent["project"] == project_id and len(spent["stages"]) == 10
    assert spent["cpu_ms"] > 0 and spent["hosted_usd"] == 0  # fake models record no price
    records = call(base, f"/api/projects/{project_id}/records")[1]
    for key, kind, start in (
        ("edit_xml", "application/xml", b"<?xml"),
        ("edit_edl", "text/plain", b"TITLE:"),
    ):
        status, data, headers = call(base, records[key])
        assert status == 200 and headers["Content-Type"].startswith(kind) and data.startswith(start)


def test_the_lyrics_are_rerun_with_a_note_from_the_dashboard(base: str, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 10_000)
    project_id = call(base, "/api/projects", {"name": "Rerun", "lyrics": "one two", "song": upload(song)})[1][
        "id"
    ]
    wait_for(base, project_id, "review_lyrics")
    blank = call(base, f"/api/projects/{project_id}/reject", {"gate": "review_lyrics", "note": " "})
    assert blank[0] == 400 and "say what should change" in blank[1]["error"]
    body = {"gate": "review_lyrics", "note": "split the first line"}
    assert call(base, f"/api/projects/{project_id}/reject", body)[1] == {"rejected": "review_lyrics"}
    wait_for(base, project_id, "review_lyrics")  # the lyrics stage ran again and stopped at the gate
    events = (tmp_path / "projects" / project_id / "events.jsonl").read_text()
    assert '"gate_rejected"' in events and "split the first line" in events
    assert events.count('"step": "lyrics"') >= 4  # started and finished twice
    lyrics_check = call(base, f"/api/projects/{project_id}/records")[1]["lyrics_check"]
    assert lyrics_check == {"format_version": "1", "errors": [], "warnings": lyrics_check["warnings"]}


def test_the_plan_is_made_again_with_a_note_from_the_dashboard(base: str, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 10_000)
    body = {"name": "Plan", "lyrics": "one two", "song": upload(song)}
    project_id = call(base, "/api/projects", body)[1]["id"]
    wait_for(base, project_id, "review_lyrics")
    call(base, f"/api/projects/{project_id}/approve", {"gate": "review_lyrics"})
    wait_for(base, project_id, "review_plan")
    note = {"gate": "review_plan", "note": "more close-ups in the chorus"}
    assert call(base, f"/api/projects/{project_id}/reject", note)[1] == {"rejected": "review_plan"}
    wait_for(base, project_id, "review_plan")  # planned and checked again, then stopped at the gate
    events = (tmp_path / "projects" / project_id / "events.jsonl").read_text()
    assert '"gate_rejected"' in events and "more close-ups in the chorus" in events
    assert events.count('"step": "plan"') >= 4  # started and finished twice
    records = call(base, f"/api/projects/{project_id}/records")[1]
    assert records["plan_check"]["errors"] == [] and records["shots"]["shots"] and records["frame"]


def test_progress_streams_as_server_sent_events(base: str, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 10_000)
    project_id = call(base, "/api/projects", {"name": "Live", "song": upload(song)})[1]["id"]
    wait_for(base, project_id, "review_lyrics")
    with urllib.request.urlopen(f"{base}/api/projects/{project_id}/events", timeout=10) as stream:  # noqa: S310
        assert stream.headers["Content-Type"] == "text/event-stream"
        seen: list[str] = []
        while "run_finished" not in seen:
            line = stream.readline().decode()
            if line.startswith("data: "):
                seen.append(json.loads(line[6:])["event"])
    assert seen[0] == "run_started" and "step_finished" in seen


def test_refusals(base: str, tmp_path: Path) -> None:
    song = make_song(tmp_path / "song.wav", 5000)
    assert call(base, "/api/projects/missing")[0] == 404
    status, error, _ = call(base, "/api/projects", {"name": "", "song": upload(song)})
    assert status == 400 and error["problems"] == ["name: give the video a name"]
    status, error, _ = call(base, "/api/projects", {"name": "x", "song": {"name": "a.wav", "data_b64": "!!"}})
    assert status == 400 and "base64" in error["error"]
    assert call(base, "/api/projects", [1])[0] == 400
    project_id = call(base, "/api/projects", {"name": "Refused", "song": upload(song)})[1]["id"]
    wait_for(base, project_id, "review_lyrics")
    status, error, _ = call(base, f"/api/projects/{project_id}/approve", {"gate": "review_plan"})
    assert status == 409 and "waiting: review_lyrics" in error["error"]
    assert call(base, f"/files/{project_id}/project.json")[0] == 404
    assert call(base, f"/files/{project_id}/input/lyrics.txt")[0] == 404
    assert call(base, f"/files/{project_id}/events.jsonl")[0] == 404
    assert call(base, "/files/../../etc/passwd")[0] == 404
    assert call(base, f"/api/projects/{project_id}/resume", {})[1] == {"resuming": project_id}


def test_a_project_waiting_its_turn_is_queued(tmp_path: Path) -> None:
    gate = threading.Event()
    models = FakeModels(on_call=lambda _call: gate.wait(10))  # the first run holds the runner
    dashboard = hmv.Dashboard(tmp_path / "projects", models, port=0).start()
    base = dashboard.url.rstrip("/")
    try:
        song = upload(make_song(tmp_path / "song.wav", 5000))
        first = call(base, "/api/projects", {"name": "First", "song": song})[1]["id"]
        second = call(base, "/api/projects", {"name": "Second", "song": song})[1]
        assert second["status"] == "queued"
        assert call(base, f"/api/projects/{second['id']}")[1]["run"]["status"] == "queued"
        gate.set()
        wait_for(base, first, "review_lyrics")
        assert wait_for(base, second["id"], "review_lyrics")["status"] == "awaiting_review"
    finally:
        gate.set()
        dashboard.close()


def test_the_event_stream_of_an_unknown_project_is_not_found(base: str) -> None:
    for path in ("/api/projects/missing/events", "/api/projects/Bad%20Id/events"):
        status, error, headers = call(base, path)
        assert status == 404 and "no project" in error["error"] and "json" in headers["Content-Type"]


# ---------------------------------------------------------------- the project views' records and media


def get(base: str, path: str, headers: dict[str, str] | None = None) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(base + path, headers=headers or {})  # noqa: S310 - our own server
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def new_video(base: str, tmp_path: Path, settings: dict[str, Any] | None = None) -> str:
    song = make_song(tmp_path / "in" / "song.wav", 12_000)
    sheet = make_picture(tmp_path / "in" / "darvin.png")
    body = {"name": "Records", "lyrics": "one two three four five six seven", "song": upload(song),
            "sheets": [{"name": "Darvin", "note": "the hero", "file": upload(sheet)}],
            "settings": settings or {}}  # fmt: skip
    return call(base, "/api/projects", body)[1]["id"]


def test_the_records_follow_the_run(base: str, tmp_path: Path) -> None:
    project_id = new_video(base, tmp_path)
    wait_for(base, project_id, "review_lyrics")
    status, found, _ = call(base, f"/api/projects/{project_id}/records")
    assert (
        status == 200 and found["timeline"]["duration_ms"] == 12_000 and found["lyrics_check"]["errors"] == []
    )
    assert (
        found["frame"] is None
        and found["shots"] is None
        and found["video"] is None
        and found["shot_files"] == {}
        and found["characters"] == {}
    )
    assert found["song"].startswith(f"/files/{project_id}/input/song.wav?v=")
    status, error, _ = call(base, f"/api/projects/{project_id}/assemble", {})
    assert status == 409 and "no finished clips yet" in error["error"]  # D-036
    assert found["given"][0]["name"] == "Darvin" and found["given"][0]["url"].startswith(
        f"/files/{project_id}/input/"
    )
    to_the_end(base, project_id)
    found = call(base, f"/api/projects/{project_id}/records")[1]
    shots = [s["id"] for s in found["shots"]["shots"]]
    assert list(found["shot_files"]) == shots and found["scenes"]["shots"]["shots"]
    files = found["shot_files"][shots[0]]
    assert files["versions"] == {"stills": 1, "clips": 1, "finish": 1}
    pictures = [c["picture"] for c in found["characters"].values()]
    assert pictures and all(p.startswith(f"/files/{project_id}/frame/projects/") for p in pictures)
    assert [c["shot"] for c in found["assembly"]["edl"]] == shots and found["edl"] is not None
    kinds = {"stills": "image/png", "finish": "video/mp4"}
    for stage, kind in kinds.items():
        status, _, headers = get(base, files[stage])
        assert status == 200 and headers["Content-Type"] == kind and headers["Accept-Ranges"] == "bytes"
    assert get(base, found["edl"])[2]["Content-Type"] == "application/json"
    assert get(base, found["given"][0]["url"])[2]["Content-Type"] == "image/png"
    assert found["assembly"]["video"] == "current/video.mp4" and get(base, found["video"])[0] == 200
    assert call(base, f"/api/projects/{project_id}/assemble", {})[:2] == (200, {"assemble": project_id})
    deadline = time.monotonic() + 20
    while call(base, f"/api/projects/{project_id}/records")[1]["video"] == found["video"]:
        assert time.monotonic() < deadline, "the video was never assembled again"
        time.sleep(0.05)


def test_the_song_is_served_in_ranges(base: str, tmp_path: Path) -> None:
    project_id = new_video(base, tmp_path)
    song_path = f"/files/{project_id}/input/song.wav"
    whole = get(base, song_path)
    assert whole[0] == 200 and whole[2]["Content-Type"] == "audio/wav"
    size = len(whole[1])
    status, part, headers = get(base, song_path, {"Range": "bytes=10-19"})
    assert status == 206 and part == whole[1][10:20] and headers["Content-Range"] == f"bytes 10-19/{size}"
    status, part, headers = get(base, song_path, {"Range": "bytes=-4"})
    assert (
        status == 206
        and part == whole[1][-4:]
        and headers["Content-Range"] == f"bytes {size - 4}-{size - 1}/{size}"
    )
    status, part, _ = get(base, song_path, {"Range": f"bytes={size - 2}-"})
    assert status == 206 and part == whole[1][-2:]
    for unsatisfiable in (f"bytes={size}-", f"bytes={size + 5}-{size + 9}", "bytes=-0"):
        status, _, headers = get(base, song_path, {"Range": unsatisfiable})
        assert status == 416 and headers["Content-Range"] == f"bytes */{size}", unsatisfiable
    for ignored in ("bytes=5-2", "lines=1-2", "bytes=1-2,4-5", "bytes= 1-2", "bytes=-"):  # RFC 9110 §14.2
        status, body, headers = get(base, song_path, {"Range": ignored})
        assert status == 200 and body == whole[1] and "Content-Range" not in headers, ignored


def test_records_refuse_unknown_projects_and_files(base: str, tmp_path: Path) -> None:
    project_id = new_video(base, tmp_path)
    for path in (
        "/api/projects/missing/records",
        "/api/projects/Bad%20Id/records",
        "/api/projects/..%2F/records",
    ):
        assert call(base, path)[0] == 404, path
    for path in (
        f"/files/{project_id}/project.json",
        f"/files/{project_id}/input/lyrics.txt",
        f"/files/{project_id}/input/sheets",
        f"/files/{project_id}/runs/video/manifest.json",
        f"/files/{project_id}/current",
        "/files/../../etc/passwd",
        f"/files/{project_id}/input/../project.json",
    ):
        assert get(base, path)[0] == 404, path


def test_unattended_runs_from_the_dashboard(base: str, tmp_path: Path) -> None:
    """0004: a video added with "Run without stopping for my approval" runs to the end on its own; one
    waiting at a gate is switched to it and continues; the gates show they passed unattended."""
    song = upload(make_song(tmp_path / "song.wav", 10_000))
    status, error, _ = call(base, "/api/projects", {"name": "Odd", "song": song, "approve": "always"})
    assert status == 400 and "approve: 'always' is not ask or auto" in error["error"]
    alone = call(base, "/api/projects", {"name": "Alone", "song": song, "approve": "auto"})[1]
    assert alone["approve"] == "auto"
    done = wait_for(base, alone["id"], "completed")  # the scenes accepted unattended too (0027)
    assert {s["gate"]: s["gate_auto"] for s in done["run"]["stages"] if s["gate"]} == {
        "review_lyrics": True, "review_plan": True, "review_scenes": True,
    }  # fmt: skip
    asking = call(base, "/api/projects", {"name": "Asking", "song": song})[1]
    assert asking["approve"] == "ask"
    wait_for(base, asking["id"], "review_lyrics")
    route = f"/api/projects/{asking['id']}/approve-mode"
    assert call(base, route, {"approve": "sometimes"})[0] == 400
    assert call(base, route, {"approve": "auto"})[1] == {"approve": "auto"}
    assert wait_for(base, asking["id"], "completed")["approve"] == "auto"
    events = (tmp_path / "projects" / asking["id"] / "events.jsonl").read_text()
    assert events.count('"event": "gate_auto_approved"') == 3


def test_a_resume_of_a_running_or_queued_project_is_refused(tmp_path: Path) -> None:
    """A second resume would wait behind the run it duplicates, show the running project as `queued`
    and run once more after it: it is refused (409) while the project runs or waits its turn."""
    gate = threading.Event()
    models = FakeModels(on_call=lambda _call: gate.wait(10))  # the first run holds the runner
    dashboard = hmv.Dashboard(tmp_path / "projects", models, port=0).start()
    base = dashboard.url.rstrip("/")
    try:
        song = upload(make_song(tmp_path / "song.wav", 5000))
        running = call(base, "/api/projects", {"name": "First", "song": song})[1]["id"]
        queued = call(base, "/api/projects", {"name": "Second", "song": song})[1]["id"]
        while dashboard.server.runner.current != running:
            time.sleep(0.01)
        status, error, _ = call(base, f"/api/projects/{running}/resume", {})
        assert status == 409 and "already running" in error["error"]
        assert call(base, f"/api/projects/{queued}/resume", {})[0] == 409
        assert call(base, f"/api/projects/{running}")[1]["run"]["status"] == "running"
        assert dashboard.server.runner.queued == {queued}
        gate.set()
        wait_for(base, queued, "review_lyrics")
        assert call(base, f"/api/projects/{running}/resume", {})[1] == {"resuming": running}
    finally:
        gate.set()
        dashboard.close()


def test_a_running_or_queued_project_switched_to_auto_is_not_resumed_twice(tmp_path: Path) -> None:
    """Switching while the run runs (or waits its turn) only changes the mode: the run reads it at its
    next gate, so both videos go to the end without an approval (0004, D-075)."""
    gate = threading.Event()
    models = FakeModels(on_call=lambda _call: gate.wait(10))  # the first run holds the runner
    dashboard = hmv.Dashboard(tmp_path / "projects", models, port=0).start()
    base = dashboard.url.rstrip("/")
    try:
        song = upload(make_song(tmp_path / "song.wav", 5000))
        running = call(base, "/api/projects", {"name": "First", "song": song})[1]["id"]
        queued = call(base, "/api/projects", {"name": "Second", "song": song})[1]
        assert queued["status"] == "queued"
        for project_id in (running, queued["id"]):
            route = f"/api/projects/{project_id}/approve-mode"
            assert call(base, route, {"approve": "auto"})[1] == {"approve": "auto"}
        gate.set()
        for project_id in (running, queued["id"]):
            assert wait_for(base, project_id, "completed")["approve"] == "auto"
            events = (tmp_path / "projects" / project_id / "events.jsonl").read_text()
            assert events.count('"event": "gate_auto_approved"') == 3
    finally:
        gate.set()
        dashboard.close()


def test_the_lyrics_timing_is_saved_checked_and_kept_through_a_rerun(base: str, tmp_path: Path) -> None:
    """The Lyrics view's "Save timing" (0018): refusals name every problem; a save answers the edited
    timeline and its check, the records show it, and a rerun's answer says which edits it keeps."""
    song = make_song(tmp_path / "song.wav", 10_000)
    project_id = call(base, "/api/projects", {"name": "Timing", "lyrics": "one two", "song": upload(song)})[
        1
    ]["id"]
    wait_for(base, project_id, "review_lyrics")
    route = f"/api/projects/{project_id}/lyrics-timing"
    first = call(base, f"/api/projects/{project_id}/records")[1]["timeline"]["lines"][0]
    status, error, _ = call(base, route, {"L001": {"start_ms": "0:01", "end_ms": 2000}})
    assert status == 400 and error["problems"] == [
        "L001: give start_ms and end_ms as whole milliseconds from 0"
    ]
    status, error, _ = call(base, route, {"L001": {"start_ms": 500, "end_ms": 10_001}})
    assert status == 400 and error["problems"] == ["L001: ends at 0:10.001, after the song ends (0:10.000)"]
    status, error, _ = call(base, route, [])  # {} is "send the timing as ...", tested in unit
    assert status == 400 and "send a JSON object" in error["error"]

    moved = {"start_ms": first["start_ms"] + 100, "end_ms": first["end_ms"]}
    status, saved, _ = call(base, route, {"L001": moved})
    assert status == 200 and saved["lyrics_timing"] == {
        "kept": ["L001"],
        "dropped": {},
        "measured": {"L001": [first["start_ms"], first["end_ms"]]},
        "errors": 0,
        "warnings": 0,
    }
    assert saved["timeline"]["lines"][0]["start_ms"] == moved["start_ms"]
    assert saved["lyrics_check"]["errors"] == []
    records = call(base, f"/api/projects/{project_id}/records")[1]
    assert records["timeline"] == saved["timeline"] and records["lyrics_timing"]["kept"] == ["L001"]

    body = {"gate": "review_lyrics", "note": "split the first line"}
    answer = call(base, f"/api/projects/{project_id}/reject", body)[1]
    assert answer == {"rejected": "review_lyrics", "timing_kept_for": ["L001"]}
    wait_for(base, project_id, "review_lyrics")
    records = call(base, f"/api/projects/{project_id}/records")[1]
    assert records["timeline"]["lines"][0]["start_ms"] == moved["start_ms"]  # applied again after the rerun
    assert call(base, f"/api/projects/{project_id}/approve", {"gate": "review_lyrics"})[1] == {
        "approved": "review_lyrics"
    }
    wait_for(base, project_id, "review_plan")
    records = call(base, f"/api/projects/{project_id}/records")[1]
    assert records["timeline"]["owner_timed"] == ["L001"] and records["lyrics_check"]["errors"] == []
    assert call(base, route, {"L001": None})[0] == 409  # the gate is decided


def test_the_overview_card_sends_a_gate_back_and_approve_keeps_a_note_it_is_sent(
    base: str, tmp_path: Path
) -> None:
    """The Overview's gate card posts what the gate's own page posts (0018): reject with the note at
    `review_plan`, then approve with a note."""
    song = make_song(tmp_path / "song.wav", 10_000)
    project_id = call(base, "/api/projects", {"name": "Card", "lyrics": "one two", "song": upload(song)})[1][
        "id"
    ]
    wait_for(base, project_id, "review_lyrics")
    call(base, f"/api/projects/{project_id}/approve", {"gate": "review_lyrics"})
    wait_for(base, project_id, "review_plan")
    body = {"gate": "review_plan", "note": "Darvin rides a black horse"}
    assert call(base, f"/api/projects/{project_id}/reject", body)[1] == {"rejected": "review_plan"}
    wait_for(base, project_id, "review_plan")
    body = {"gate": "review_plan", "note": "good now"}
    assert call(base, f"/api/projects/{project_id}/approve", body)[1] == {"approved": "review_plan"}
    found = [
        json.loads(e) for e in (tmp_path / "projects" / project_id / "events.jsonl").read_text().splitlines()
    ]
    decided = [(e["event"], e["note"]) for e in found if e["event"] in ("gate_rejected", "gate_approved")]
    assert decided[1:] == [("gate_rejected", "Darvin rides a black horse"), ("gate_approved", "good now")]


def test_the_scenes_are_edited_made_and_served_through_the_frame_api(base: str, tmp_path: Path) -> None:
    """The Scenes view's API (0027 §6): Hone Frame's routes under the project; an edit written back to the
    project file keeping its comments, the picture and its thumbnail served, the guide, refusals."""
    project_id = new_video(base, tmp_path)
    frame = f"/api/projects/{project_id}/frame"
    assert call(base, frame)[0] == 404  # no plan yet: no frame project
    for gate in GATES[:2]:
        wait_for(base, project_id, gate)
        call(base, f"/api/projects/{project_id}/approve", {"gate": gate})
    wait_for(base, project_id, "review_scenes")
    view = settle(base, project_id)
    scene = next(i for i in view["items"] if i["group"] == "scenes")
    text = call(base, f"{frame}/file")[1]["text"]
    assert "# used by" in text  # the planner's comments
    status, item, _ = call(base, f"{frame}/items/{scene['id']}", {"prompt": "a quiet hall at dawn"}, "PATCH")
    assert status == 200 and item["prompt"] == "a quiet hall at dawn" and item["changed_since_made"]
    again = call(base, f"{frame}/file")[1]["text"]
    assert "a quiet hall at dawn" in again and again.count("# used by") == text.count("# used by")
    status, error, _ = call(base, f"{frame}/items/{scene['id']}", {"count": 0}, "PATCH")
    assert status == 400 and error["items"]  # refused like Hone Frame's import, by item
    version = scene["versions"][-1]
    status, picture, headers = get(base, version["url"])
    assert status == 200 and headers["Content-Type"] == "image/png" and picture.startswith(b"\x89PNG")
    status, _, headers = get(base, version["thumb"])
    assert status == 200 and headers["Content-Type"] == "image/webp"
    assert call(base, f"{frame}/items/{scene['id']}/dependants")[1] == ["storyboard"]  # its sheet
    status, guide, _ = call(base, f"{frame}/guide?project=this")
    assert status == 200 and "qwen" in guide["markdown"].lower()
    assert call(base, f"{frame}/models")[1][0]["id"] == "qwen-image-2.1-turbo"
    assert call(base, f"{frame}/items/nothing/accept", {})[0] == 404
    upload_body = {"file": {"name": "x.png", "data_b64": "***"}}
    assert call(base, f"{frame}/items/{scene['id']}/file", upload_body)[0] == 400


def test_a_clip_is_remade_from_the_dashboard_after_the_video(base: str, tmp_path: Path) -> None:
    """After the video (0027 §7): a motion prompt saved, a new clip seed, and the remake: only the
    changed shots' clips are made again; refusals before the scenes and for unknown shots."""
    project_id = new_video(base, tmp_path)
    wait_for(base, project_id, "review_lyrics")
    status, error, _ = call(base, f"/api/projects/{project_id}/remake", {})
    assert status == 409 and "approve the scenes first" in error["error"]
    to_the_end(base, project_id)
    records = call(base, f"/api/projects/{project_id}/records")[1]
    first, second = [s["id"] for s in records["shots"]["shots"]][:2]
    route = f"/api/projects/{project_id}"
    status, saved, _ = call(base, f"{route}/motion", {"shot": first, "motion_prompt": "she sings softly"})
    assert status == 200 and saved["motion"] == first and saved["warnings"]  # speech moves the mouth
    assert call(base, f"{route}/motion", {"shot": "S999", "motion_prompt": "wind"})[0] == 404
    assert call(base, f"{route}/redo-clip", {"shots": [second], "now": False})[1] == {"clip_seeds": [second]}
    assert call(base, f"{route}/remake", {})[1] == {"remake": project_id}
    deadline = time.monotonic() + 20
    while True:
        found = call(base, f"/api/projects/{project_id}/records")[1]["shot_files"]
        if found[first]["versions"]["clips"] == 2 and call(base, route)[1]["status"] == "completed":
            break
        assert time.monotonic() < deadline, "the clips were never remade"
        time.sleep(0.05)
    assert found[second]["versions"]["clips"] == 2
    others = [s for s in found if s not in (first, second)]
    assert all(found[s]["versions"]["clips"] == 1 for s in others)  # the other clips are kept


def test_a_project_made_without_starting_starts_on_resume(tmp_path: Path) -> None:
    """A project made by `new` (or `create_project`) has no run: the dashboard's Start (the resume
    route) starts it rather than failing for want of a run."""
    made = hmv.create_project(tmp_path / "projects", "Later", make_song(tmp_path / "song.wav", 5000))
    dashboard = hmv.Dashboard(tmp_path / "projects", FakeModels(), port=0).start()
    base = dashboard.url.rstrip("/")
    try:
        assert call(base, f"/api/projects/{made.id}")[1]["status"] == "not_started"
        assert call(base, f"/api/projects/{made.id}/resume", {})[1] == {"resuming": made.id}
        wait_for(base, made.id, "review_lyrics")
    finally:
        dashboard.close()


def test_the_preview_shows_a_scene_as_soon_as_its_picture_is_in_use(base: str, tmp_path: Path) -> None:
    """While the scenes are made, a shot's start frame is its scene's picture in use in the frame
    workspace; the shot's own `still.png` is written only once every scene has one."""
    project_id = new_video(base, tmp_path)
    for gate in GATES[:2]:
        wait_for(base, project_id, gate)
        call(base, f"/api/projects/{project_id}/approve", {"gate": gate})
    wait_for(base, project_id, "review_scenes")
    settle(base, project_id)
    shots = [s["id"] for s in call(base, f"/api/projects/{project_id}/records")[1]["shots"]["shots"]]
    assert call(base, f"/api/projects/{project_id}/frame/items/{shots[-1]}/mark", {})[0] == 200
    for still in (tmp_path / "projects" / project_id / "current" / "shots").glob("*/still.png"):
        still.unlink()  # as while the scenes are made: no shot's start frame is kept yet
    files = call(base, f"/api/projects/{project_id}/records")[1]["shot_files"]
    picture = files[shots[0]]["stills"]
    assert picture.startswith(f"/files/{project_id}/frame/projects/") and get(base, picture)[0] == 200
    assert files[shots[0]]["newest"] == {"kind": "stills", "url": picture}
    assert files[shots[-1]]["stills"] is None  # marked: made again, so no picture in use
