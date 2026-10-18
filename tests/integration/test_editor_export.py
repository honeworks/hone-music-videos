"""The edit for editors (design §12.1, D-063, D-064): `edit.xml` (FCP7 XML) and `edit.edl` (CMX3600)
beside `edl.json`, read back and checked frame by frame against the edit list."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

import hone_music_video as hmv
from hone_music_video import editor_files
from hone_music_video._video import Clip
from hone_music_video.cli import main
from hone_music_video.testing import FakeModels
from tests.conftest import drive, new_project

SONG = hmv.Song(duration_ms=20_000, sample_rate=44_100, channels=2)
TIMECODE = re.compile(r"(\d\d):(\d\d):(\d\d):(\d\d)")


@pytest.fixture(scope="module")
def finished(tmp_path_factory: pytest.TempPathFactory) -> hmv.Project:
    project = new_project(tmp_path_factory.mktemp("ویدیو my clips é"))  # spaces, not ASCII: encoded
    assert drive(project, FakeModels()).status == "completed"
    return project


def edl(project: hmv.Project) -> hmv.Assembly:
    return hmv.Assembly.model_validate_json((project.current / "edl.json").read_bytes())


def path_of(url: str) -> Path:
    """The path of a `file://localhost/...` URL, which is ASCII with no space (percent-encoded)."""
    assert url.startswith("file://localhost/") and url.isascii() and " " not in url and "%20" in url
    return Path(unquote(urlsplit(url).path))


def number(element: ET.Element, tag: str) -> int:
    return int(element.findtext(tag) or "")


def test_the_xml_has_every_clip_at_its_frames_and_the_song_under_them(finished: hmv.Project) -> None:
    assembly = edl(finished)
    root = ET.parse(finished.current / "edit.xml").getroot()  # noqa: S314 - the file we wrote
    assert root.tag == "xmeml" and root.get("version") == "4"
    sequence = root.find("sequence")
    assert sequence is not None and sequence.findtext("name") == "Balcony"
    assert sequence.findtext("rate/timebase") == str(assembly.fps) == "32"
    assert sequence.findtext("rate/ntsc") == "FALSE"
    end = assembly.edl[-1].last_frame + 1
    assert number(sequence, "duration") == end == (20_000 * 32 + 500) // 1000  # the 20 s song, in frames
    tracks = sequence.findall("media/video/track")
    assert len(tracks) == 1
    items = tracks[0].findall("clipitem")
    assert [i.findtext("name") for i in items] == [c.shot for c in assembly.edl]
    for item, cut in zip(items, assembly.edl, strict=True):
        length = cut.last_frame - cut.first_frame + 1
        assert (number(item, "start"), number(item, "end")) == (cut.first_frame, cut.last_frame + 1)
        assert (number(item, "in"), number(item, "out")) == (0, length)
        assert path_of(item.findtext("file/pathurl") or "") == finished.path(cut.clip).resolve()
        assert number(item, "file/duration") >= length  # the clip is long enough: nothing held
    width, height = (
        number(sequence, f"media/video/format/samplecharacteristics/{k}") for k in ("width", "height")
    )
    assert (width, height) == (64, 36)  # the fake's finished clips: small, 16:9
    (song,) = sequence.findall("media/audio/track/clipitem")
    assert (number(song, "start"), number(song, "end"), number(song, "in"), number(song, "out")) == (
        0,
        end,
        0,
        end,
    )
    assert (
        path_of(song.findtext("file/pathurl") or "") == finished.path(finished.record().inputs.song).resolve()
    )
    assert song.findtext("sourcetrack/mediatype") == "audio"
    assert song.findtext("file/media/audio/channelcount") == "1"


def frames(timecode: str, fps: int) -> int:
    match = TIMECODE.fullmatch(timecode)
    assert match is not None, timecode
    h, m, s, f = map(int, match.groups())
    assert f < fps
    return ((h * 60 + m) * 60 + s) * fps + f


def test_the_edl_cuts_are_the_edit_lists_frames(finished: hmv.Project) -> None:
    assembly = edl(finished)
    text = (finished.current / "edit.edl").read_text()
    assert text.startswith("TITLE: Balcony\nFCM: NON-DROP FRAME\n")
    rows = [line.split() for line in text.splitlines() if re.match(r"^\d{3}  ", line)]
    assert [r[1] for r in rows] == [*(c.shot for c in assembly.edl), "SONG"]
    assert [r[2] for r in rows] == ["V"] * len(assembly.edl) + ["A"]  # the fake song is mono
    for row, cut in zip(rows[:-1], assembly.edl, strict=True):
        src_in, src_out, rec_in, rec_out = (frames(t, assembly.fps) for t in row[4:8])
        assert (rec_in, rec_out) == (cut.first_frame, cut.last_frame + 1)
        assert (src_in, src_out) == (0, cut.last_frame - cut.first_frame + 1)
    assert [frames(t, 32) for t in rows[-1][6:8]] == [0, assembly.edl[-1].last_frame + 1]
    named = [
        line.removeprefix("* FROM CLIP NAME: ") for line in text.splitlines() if "FROM CLIP NAME" in line
    ]
    assert named[:-1] == [Path(c.clip).name for c in assembly.edl]


def test_timecodes_count_frames_at_the_videos_rate() -> None:
    assert editor_files.timecode(0, 32) == "00:00:00:00"
    assert editor_files.timecode(33, 32) == "00:00:01:01"
    assert editor_files.timecode(32 * 3661 + 31, 32) == "01:01:01:31"


def test_a_short_clip_ends_where_it_does_and_its_held_frames_are_a_gap(finished: hmv.Project) -> None:
    """D-063: the video holds a short clip's last frame; the editor's timeline cannot, so the clip ends
    at its own last frame there. A shot under half a frame has no clip at all."""
    assembly = edl(finished)
    first = assembly.edl[0]
    tiny = assembly.edl[1].model_copy(update={"last_frame": assembly.edl[1].first_frame - 1})
    short = assembly.model_copy(update={"edl": [first, tiny, *assembly.edl[2:]]})
    clips = {c.shot: Clip("640x360", "32/1", 100) for c in assembly.edl}
    edit = editor_files.edit_of(finished, short, clips, SONG)
    assert [e.name for e in edit.shots] == [first.shot, *(c.shot for c in assembly.edl[2:])]
    assert (edit.shots[0].start, edit.shots[0].end) == (first.first_frame, first.first_frame + 100)


def test_export_writes_them_again_for_a_video_assembled_before(
    finished: hmv.Project, capsys: pytest.CaptureFixture[str]
) -> None:
    before = (finished.current / "edit.xml").read_bytes()
    for name in ("edit.xml", "edit.edl"):
        (finished.current / name).unlink()
    assert main(["export", str(finished.root)]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed == [str(finished.current / "edit.xml"), str(finished.current / "edit.edl")]
    assert (finished.current / "edit.xml").read_bytes() == before


def test_export_needs_an_assembled_video(project: hmv.Project, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["export", str(project.root)]) == 1
    assert "no assembled video yet" in capsys.readouterr().err
    assert json.loads((project.root / "project.json").read_text())["name"] == "Balcony"


def test_a_stereo_song_is_two_audio_channels_in_the_edl(finished: hmv.Project) -> None:
    assembly = edl(finished)
    clips = {c.shot: Clip("64x36", "32/1", 200) for c in assembly.edl}
    text = editor_files.cmx3600(editor_files.edit_of(finished, assembly, clips, SONG)).decode()
    (song,) = [line.split() for line in text.splitlines() if line[:3].isdigit() and " SONG " in line]
    assert song[2] == "AA"


def test_export_names_a_deleted_clip(finished: hmv.Project, capsys: pytest.CaptureFixture[str]) -> None:
    clip = finished.path(edl(finished).edl[1].clip)
    kept = clip.read_bytes()
    clip.unlink()
    try:
        assert main(["export", str(finished.root)]) == 1
        assert f"{edl(finished).edl[1].shot}'s finished clip" in capsys.readouterr().err
    finally:
        clip.write_bytes(kept)


def test_an_empty_edit_list_has_nothing_to_export(finished: hmv.Project) -> None:
    empty = edl(finished).model_copy(update={"edl": []})
    with pytest.raises(hmv.RunStateError, match="no shots"):
        editor_files.edit_of(finished, empty, {}, SONG)
