"""The rules the frame planner's prompts carry (0009, 0026, 0027, D-084 to D-088): what a motion prompt
never names, the story's world, the pace and mood, Hone Frame's guide in each call; and the code check
of a scene sends back a motion prompt that names the mouth."""

import hone_music_video as hmv
from hone_music_video.frame_calls import system
from hone_music_video.frame_prompts import scene_problems
from hone_music_video.prompt_words import words_of_speech
from hone_music_video.records_frame import Bible, FrameShot, ScenePrompt
from hone_music_video.stages_plan import system_prompt

LIMITS, BIBLE, SHOTS, SCENES = (
    " ".join(system_prompt(n).split()) for n in ("limits", "frame_bible", "frame_shots", "frame_scenes")
)


def test_a_motion_prompt_never_names_the_mouth_and_negations_are_useless() -> None:
    """D-088: Wan runs the 4-step LoRA at cfg 1, so negations do nothing and naming the mouth moves it."""
    assert "never** names the mouth, lips, jaw, teeth, breath or breathing" in LIMITS
    assert "not even negated" in LIMITS and "her face stays still" in LIMITS
    assert "Negations do nothing in a motion prompt" in LIMITS
    assert "never name the mouth, lips, jaw, teeth, breath or breathing" in SCENES
    example = "her eyes glisten, a single tear runs down her cheek, she slowly lowers her gaze"
    assert example in LIMITS and not words_of_speech(example, motion=True)  # its own example follows it


def test_the_world_comes_from_the_story() -> None:
    """0009, D-085: nothing hard-codes a period; a story set today is drawn as today."""
    assert "a story set today is drawn as today" in BIBLE
    assert "historical" not in SHOTS and "historical" not in hmv.Settings().style


def test_the_pace_and_the_mood_steer_the_shot_list() -> None:
    assert "`calm` long shots within `pace_shot_ms`" in SHOTS and "`energetic` short shots" in SHOTS
    assert "The arc and `settings.mood` shape **what happens and how it is staged**" in SHOTS


def test_each_call_carries_its_part_of_hone_frames_guide() -> None:
    assert "### Hero" in system("frame_bible", guides=("hero", "objects", "places", "models"))
    scenes = system("frame_scenes", guides=("scenes", "models"), limits=True)
    assert "### Scenes" in scenes and "qwen-image-2.1-turbo" in scenes


def test_a_scene_whose_motion_names_the_mouth_is_sent_back() -> None:
    bible = Bible(story="s", kind="A frame from a film.", finish="Grain.", world="w", reference_light="l",
                  demo=["a", "b", "c"])  # fmt: skip
    shot = FrameShot(id="S001", start_ms=0, end_ms=3000, beat="b", framing="wide", faces=False,
                     camera="static camera", light="l")  # fmt: skip
    scene = ScenePrompt(id="S001", prompts=["A frame from a film. A field. Grain."],
                        motion_prompt="Static camera. She keeps her lips closed.")  # fmt: skip
    found = [p.message for p in scene_problems(bible, shot, scene)]
    assert any("'lips'" in m for m in found)
