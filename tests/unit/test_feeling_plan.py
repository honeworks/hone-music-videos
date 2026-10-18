"""Feeling-first planning (0028 §1 to §4): the song's shape measured from the audio and carried with the
lyrics' notes and the owner's feeling into the bible; the arc and the camera checked; the review call's
notes sent back to the shot list; each scene writer given the feeling, the evidence, the shot before's
end and the setup; poses and details as pictures of their own; variants and states as whole looks."""

from __future__ import annotations

import math
import shutil
import struct
import wave
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video import music
from hone_music_video.frame_items import asset_items, character_item, normalized, scene_refs
from hone_music_video.frame_prompts import describe
from hone_music_video.frame_review import arc_problems, camera_problems
from hone_music_video.records import Instrumental, Line, Section, Timeline, Word, Words
from hone_music_video.records_frame import ArcPart, Bible, CastUse, FrameShot, PlaceUse
from hone_music_video.testing import FakeModels, make_song
from hone_music_video.testing.frame_answers import shots_answer
from hone_music_video.timed_lyrics import LyricsEdit, build_timeline
from tests.conftest import LYRICS, drive

FFMPEG = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


def tone(path: Path, parts: list[tuple[int, float]], rate: int = 8000) -> Path:
    """A WAV of a 220 Hz tone, each `(ms, amplitude)` part in turn (0 is silence)."""
    frames = bytearray()
    for ms, amplitude in parts:
        for n in range(ms * rate // 1000):
            frames += struct.pack("<h", int(amplitude * 32767 * math.sin(2 * math.pi * 220 * n / rate)))
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(bytes(frames))
    return path


def timeline() -> Timeline:
    words = [Word(text=f"w{n}", start_ms=2000 + n * 250, end_ms=2200 + n * 250) for n in range(8)]
    return Timeline(
        duration_ms=4000,
        sections=[Section(id="verse-1", kind="verse", start_ms=2000, end_ms=4000, notes="Whispered, fast")],
        lines=[Line(id="L001", section="verse-1", text="w", start_ms=2000, end_ms=4000, words=words)],
        instrumental=[Instrumental(start_ms=0, end_ms=2000, kind="intro", notes="[Sound Effect: breathing]")],
    )


@FFMPEG
def test_the_songs_shape_is_measured_part_by_part(tmp_path: Path) -> None:
    song = tone(tmp_path / "song.wav", [(2000, 0.05), (2000, 0.6)])  # a quiet intro, then a loud verse
    found = music.shape(timeline(), song)
    assert [p["part"] for p in found] == ["instrumental-1", "verse-1"]  # in time order
    intro, verse = found
    assert intro["loudness_db"] < -10 < 0 < verse["loudness_db"]  # against the whole song
    assert intro["change_db"] is None and verse["change_db"] > 20  # the drop
    assert intro["notes"] == "[Sound Effect: breathing]" and verse["notes"] == "Whispered, fast"
    assert verse["words_per_s"] == 4.0 and intro["words_per_s"] == 0.0
    assert verse["voice_db"] is None  # no vocals kept
    voice = tone(tmp_path / "vocals.wav", [(2000, 0.0), (2000, 0.3)])
    assert music.shape(timeline(), song, voice)[0]["voice_db"] == music.FLOOR_DB  # silence: the floor


def test_the_lyrics_notes_reach_the_timeline() -> None:
    heard = Words(language="fa", words=[Word(text=f"w{n}", start_ms=1000 * n, end_ms=1000 * n + 500)
                                        for n in range(1, 5)])  # fmt: skip
    edit = LyricsEdit.model_validate(
        {
            "sections": [{"id": "verse-1", "kind": "verse", "notes": "Soft, emotional singing | piano"}],
            "lines": [{"section": "verse-1", "text": "w1 w2 w3 w4", "heard_first": 0, "heard_last": 3}],
            "instrumental": [{"after_line": 0, "kind": "intro", "notes": "[Intro: creeping cello]"}],
        }
    )
    built = build_timeline(edit, heard, 6000, "fa")
    assert built.sections[0].notes == "Soft, emotional singing | piano"
    assert built.instrumental[0].notes == "[Intro: creeping cello]"


def bible(**more: Any) -> Bible:
    return Bible.model_validate(
        {
            "story": "A queen lies awake beside the king who killed her father.",
            "kind": "A still from a film.", "finish": "Grain.", "world": "w", "reference_light": "grey",
            "demo": ["a", "b", "c"], "feeling": "dread under a calm surface",
            "characters": [
                {"id": "queen", "name": "Arna", "kind": "person", "noun": "the queen", "look": "a woman",
                 "presence": "fragile", "inner": "terror under a smile",
                 "variants": [{"id": "night", "look": "a woman in a white linen shift, her hair loose"}]},
                {"id": "king", "name": "Zak", "kind": "person", "noun": "the king", "look": "a gaunt man",
                 "presence": "menace: grey skin, sunken red-rimmed eyes"},
            ],
            "places": [{"id": "room", "name": "the room", "look": "a stone room", "light": "a lamp",
                        "states": [{"id": "dawn", "look": "the stone room in cold dawn light"}]}],
        } | more
    )  # fmt: skip


def test_the_arc_covers_every_part_of_the_song() -> None:
    parts = ["instrumental-1", "verse-1"]
    good = bible(arc=[ArcPart(part=p, feel="dread", intensity=2, evidence="her hand stops") for p in parts])
    assert arc_problems(good, parts) == []
    bad = bible(feeling="", arc=[ArcPart(part="verse-1", feel="", intensity=7), ArcPart(part="x", feel="f",
                intensity=1, evidence="e")])  # fmt: skip
    found = " | ".join(p.message for p in arc_problems(bad, parts))
    assert "no entry for the part 'instrumental-1'" in found and "the part 'x'" in found
    assert "intensity 7" in found and "verse-1: write its `feel`" in found and "`feeling` is empty" in found
    alone = bible(characters=[{"id": "q", "name": "Q", "kind": "person", "noun": "n", "look": "l"}])
    assert any("has no `presence`" in p.message for p in arc_problems(alone, []))


def shot(n: int, camera: str = "static camera", **more: Any) -> FrameShot:
    return FrameShot.model_validate(
        {"id": f"S{n:03d}", "start_ms": n * 3000, "end_ms": n * 3000 + 3000, "beat": "b", "framing": "medium",
         "faces": True, "camera": camera, "light": "l", "feel": "f", "evidence": "e", "motion": "m"} | more
    )  # fmt: skip


def test_the_camera_is_varied() -> None:
    varied = [shot(n, ("slow push-in", "static camera", "slow pan left")[n % 3]) for n in range(9)]
    assert camera_problems(varied) == []
    others = (
        "static camera",
        "slow pan left",
        "handheld drift",
        "slow pull-back",
        "static camera",
        "slow tilt up",
    )
    same = [shot(n, "Slow push-in, low") for n in range(4)] + [shot(4 + n, m) for n, m in enumerate(others)]
    found = camera_problems(same)
    assert [p.where for p in found] == ["S003"]  # the 4th push-in in a row (4 of 10 is not too many)
    many = [shot(n, "static camera" if n % 2 else "slow push-in") for n in range(10)]
    assert {p.where for p in camera_problems(many)} == {"shots"}  # 5 of 10 each: over 40%
    assert camera_problems(same[:5]) == []  # a short list is not checked


def test_poses_and_details_get_pictures_of_their_own() -> None:
    b = normalized(bible())
    king, queen = b.characters[1], b.characters[0]
    lying = CastUse(character="king", pose="lying", view="side")
    snake = CastUse(character="king", view="detail", part="The snake on his left shoulder")
    night = CastUse(character="queen", variant="night", pose="lying", view="back")
    assert character_item(king, lying) == "king.lying"  # a pose wins over the body view
    assert character_item(king, snake) == "king.detail-the-snake-on-his-left-shoulder"
    assert character_item(queen, night) == "queen.night-lying"
    shots = [shot(1, cast=[lying, night], place=PlaceUse(place="room")), shot(2, cast=[snake])]
    items = {i.id: i for i in asset_items("p", b, shots, "1664x928")}
    assert items["king.lying"].refs == ["king.hero"] and items["king.lying"].size == "1536x1024"
    assert items["queen.night-lying"].refs == ["queen.night"]
    detail = items["king.detail-the-snake-on-his-left-shoulder"]
    assert detail.refs == ["king.hero"] and "The snake on his left shoulder fills the frame" in detail.role
    assert scene_refs(b, shots[0]) == ["king.lying", "queen.night-lying", "room.wide"]


def test_variants_and_states_reach_the_writers_whole() -> None:
    b = normalized(bible())
    assert describe(b, "queen.night")["look"] == "a woman in a white linen shift, her hair loose"
    assert describe(b, "room.dawn")["look"] == "the stone room in cold dawn light"


def material() -> hmv.Material:
    return hmv.Material(lyrics=LYRICS, feeling="Start warm, end in cold dread.")


@FFMPEG
def test_the_bible_hears_the_music_the_notes_and_the_owners_feeling(tmp_path: Path) -> None:
    project = hmv.create_project(tmp_path / "p", "Walk", make_song(tmp_path / "s.wav", 30_000), material())
    models = FakeModels()
    drive(project, models)
    bible_call = next(c for c in models.calls_of("plan") if c.schema == "Bible")
    assert bible_call.data["feeling"] == "Start warm, end in cold dread."
    parts = [p["part"] for p in bible_call.data["music"]]
    assert parts and all({"loudness_db", "change_db", "words_per_s", "notes"} <= set(p)
                         for p in bible_call.data["music"])  # fmt: skip
    shots_call = next(c for c in models.calls_of("plan") if c.schema == "ShotList")
    assert shots_call.data["bible"]["feeling"] and shots_call.data["bible"]["arc"]
    assert "notes" in shots_call.data["timeline"]["sections"][0]
    scene = next(c for c in models.calls_of("plan") if c.schema == "ScenePrompts").data["shots"][1]
    assert scene["feel"] == "unease" and scene["evidence"] and scene["motion"]
    assert scene["before"] == "she stands under the lamp"  # the shot before's end, not its beat
    assert scene["arc"]["part"] in parts and scene["people"][0]["inner"]


def test_the_reviews_notes_go_back_to_the_shot_list(project: hmv.Project) -> None:
    reviewed: list[dict[str, Any]] = []

    def review(data: Mapping[str, Any]) -> dict[str, Any]:
        reviewed.append(dict(data))
        return {"notes": [{"where": "S002", "problem": "her face is calm in a moment of terror"}]}

    def shots(data: Mapping[str, Any]) -> dict[str, Any]:
        answer = shots_answer(data)
        answer["setups"] = [{"id": "street", "layout": "she walks on the left, the lamp on her right"}]
        for s in answer["shots"]:
            s["setup"] = "street"
        return answer

    models = FakeModels(answers={"ShotReview": review, "ShotList": shots})
    drive(project, models)
    plans = [c for c in models.calls_of("plan") if c.schema == "ShotList"]
    assert len(plans) == 2 and len(reviewed) == 1  # the list, then its repair with the notes
    sent = plans[1].data["problems"]
    assert {"where": "S002", "message": "her face is calm in a moment of terror"} in sent
    assert reviewed[0]["shots"][0]["sung"] is not None and reviewed[0]["arc"]
    scene = next(c for c in models.calls_of("plan") if c.schema == "ScenePrompts").data["shots"][0]
    assert scene["setup"] == "she walks on the left, the lamp on her right"
