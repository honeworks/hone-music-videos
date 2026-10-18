"""The frame plan's items worked out by code (0026): ids, references, sizes, holds, and the checks of a
shot list and of a prompt."""

from __future__ import annotations

from hone_music_video.frame_calls import images_named, prompt_problems
from hone_music_video.frame_items import (
    MAX_SCENE_REFS,
    asset_items,
    character_item,
    normalized,
    place_item,
    scene_refs,
    seed_of,
    shot_problems,
)
from hone_music_video.records_frame import Bible, CastUse, FrameShot, PlaceUse

KIND = "A frame from a feature-length stylised 3D animated film."


def bible() -> Bible:
    return Bible.model_validate(
        {
            "story": "Darvin kills a dragon.",
            "kind": KIND,
            "finish": "Painterly textures.",
            "world": "A legendary ancient kingdom.",
            "reference_light": "Mid-grey backdrop, one soft key light from the upper left.",
            "demo": ["a", "b", "c"],
            "characters": [
                {"id": "Darvin", "name": "Darvin", "kind": "person", "noun": "the hero", "look": "a big man",
                 "variants": [{"id": "sleeping", "look": "asleep, helmet off"}]},
                {"id": "ember", "name": "Ember", "kind": "animal", "noun": "the horse", "look": "a horse"},
            ],
            "objects": [{"id": "mace", "name": "the mace", "look": "ox-headed"},
                        {"id": "rug", "name": "the rug", "look": "leopard skin"}],
            "places": [{"id": "oasis", "name": "the oasis", "look": "a spring", "light": "moonlight",
                        "states": [{"id": "dawn", "look": "peach sky"}]}],
        }
    )  # fmt: skip


def shot(n: int, cast: list[CastUse], place: PlaceUse | None, objects: list[str] = []) -> FrameShot:  # noqa: B006
    return FrameShot(
        id=f"S{n:03d}", start_ms=0, end_ms=3000, beat="b", framing="medium", faces=True,
        camera="static camera", light="moonlight", cast=cast, place=place, objects=objects,
    )  # fmt: skip


def test_ids_are_made_safe_once_per_namespace() -> None:
    b = normalized(bible())
    assert [c.id for c in b.characters] == ["darvin", "ember"]


def test_each_shot_gets_the_picture_of_the_view_it_sees() -> None:
    b = normalized(bible())
    darvin, ember = b.characters
    assert character_item(darvin, CastUse(character="darvin")) == "darvin.hero"  # a person's hero: front
    assert character_item(darvin, CastUse(character="darvin", view="back")) == "darvin.back"
    assert character_item(darvin, CastUse(character="darvin", view="close")) == "darvin.close"
    assert character_item(darvin, CastUse(character="darvin", variant="sleeping")) == "darvin.sleeping"
    side = CastUse(character="darvin", variant="sleeping", view="side")
    assert character_item(darvin, side) == "darvin.sleeping-side"
    assert character_item(ember, CastUse(character="ember", view="side")) == "ember.hero"  # an animal's
    assert character_item(ember, CastUse(character="ember")) == "ember.front"
    assert place_item(PlaceUse(place="oasis")) == "oasis.wide"
    assert place_item(PlaceUse(place="oasis", state="dawn")) == "oasis.dawn"
    assert place_item(PlaceUse(place="oasis", view="high", state="dawn")) == "oasis.high-dawn"


def test_scene_refs_are_people_then_place_then_objects_within_the_limit() -> None:
    b = normalized(bible())
    s = shot(1, [CastUse(character="darvin"), CastUse(character="ember", view="side")],
             PlaceUse(place="oasis", state="dawn"), ["mace", "rug"])  # fmt: skip
    assert scene_refs(b, s) == ["darvin.hero", "ember.hero", "oasis.dawn", "mace.hero"]
    assert len(scene_refs(b, s)) == MAX_SCENE_REFS  # the rug is left to the words


def test_assets_are_made_from_their_hero_in_file_order() -> None:
    b = normalized(bible())
    shots = [
        shot(1, [CastUse(character="darvin", view="close")], PlaceUse(place="oasis")),
        shot(2, [CastUse(character="darvin", variant="sleeping", view="side")],
             PlaceUse(place="oasis", view="high", state="dawn")),
        shot(3, [], None, ["mace"]),
    ]  # fmt: skip
    items = {i.id: i for i in asset_items("p", b, shots, "1664x928")}
    assert list(items) == [
        "darvin.hero", "darvin.close", "darvin.sleeping", "darvin.sleeping-side",
        "mace.hero", "oasis.wide", "oasis.high", "oasis.high-dawn",
    ]  # fmt: skip
    assert items["darvin.close"].refs == ["darvin.hero"] and items["darvin.close"].size == "1024x1024"
    assert items["darvin.sleeping-side"].refs == ["darvin.sleeping"]
    assert items["oasis.high-dawn"].refs == ["oasis.high"] and items["oasis.high"].refs == ["oasis.wide"]
    assert items["darvin.hero"].size == "832x1248" and items["oasis.wide"].size == "1664x928"
    assert [i for i in items if items[i].hold] == ["darvin.hero", "mace.hero", "oasis.wide"]
    assert "ember.hero" not in items  # no shot shows him: no picture
    assert items["darvin.hero"].seed == seed_of("p", "darvin.hero")  # Hone Frame's derived seed
    assert items["oasis.wide"].uses == ["S001"]


def test_a_shot_list_naming_what_the_bible_lacks_is_sent_back() -> None:
    b = normalized(bible())
    wrong = shot(1, [CastUse(character="zeno"), CastUse(character="darvin", variant="armour")],
                 PlaceUse(place="oasis", state="noon"), ["sword"])  # fmt: skip
    wide = shot(2, [CastUse(character="darvin", view="close")], None).model_copy(update={"framing": "wide"})
    messages = [p.message for p in shot_problems(b, [wrong, wide])]
    assert any("'zeno', who is not a character" in m for m in messages)
    assert any("variant 'armour'" in m for m in messages)
    assert any("state 'noon'" in m for m in messages)
    assert any("'sword', which is not an object" in m for m in messages)
    assert any("close-up in a wide shot" in m for m in messages)


def test_a_prompt_names_each_of_its_pictures_and_begins_with_the_kind() -> None:
    assert images_named("The hero from image 1 by the horse from images 2 and 3, image 4") == {1, 2, 3, 4}
    assert images_named("the truss from image 2, 24mm lens; from image 1, 50 mm, 3 metres away") == {1, 2}
    good = f"{KIND} The hero from image 1 in the oasis from image 2. Painterly."
    assert prompt_problems("S001", good, 2, starts=KIND) == []
    bad = "Photorealistic 8k: the hero from image 1 and image 3."
    found = " ".join(p.message for p in prompt_problems("S001", bad, 2, starts=KIND))
    assert "'8k', 'photorealistic'" in found
    assert "names image 3, but has 2 pictures" in found
    assert "never names image 2" in found
    assert "does not begin with the kind of picture" in found
