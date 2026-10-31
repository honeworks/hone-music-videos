"""Given lines matched against heard words despite Whisper's mishearings, the gaps of the lines not
heard, and replies that are not heard (design §6 step 1b, D-040)."""

import time

import hone_music_video as hmv
from hone_music_video.lyrics_match import (
    FOUND,
    SEARCH,
    Gap,
    Key,
    all_heard,
    find_line,
    found_starts,
    gaps,
    in_instrumental,
    latin_song,
    line_key,
    score,
    suspect,
)
from hone_music_video.records import Instrumental
from hone_music_video.timed_lyrics import plain

OTHER_SCRIPT = Gap(["a line"], 0, 1000, latin=False)
ENGLISH = Gap(["a line"], 0, 1000, latin=True)


def heard(*texts: str, at: int = 1000) -> list[hmv.Word]:
    """Words a second apart, each 800 ms long, from `at`."""
    return [hmv.Word(text=t, start_ms=at + 1000 * n, end_ms=at + 1000 * n + 800) for n, t in enumerate(texts)]


def test_a_line_key_has_no_marks_zwnj_or_punctuation_and_latin_letters_are_unknown() -> None:
    assert line_key("سینِه‌یِ او، را!", latin=False) == Key("سینهیاورا", 0)
    assert line_key("چُو Noh ماه… Kaa-ra-van!", latin=False) == Key("چوماه", 7)  # 3 + 8 letters, about 2/3
    assert line_key("She waits, upon the Balcony!", latin=True) == Key("shewaitsuponthebalcony", 0)


def test_the_script_is_decided_once_for_the_song() -> None:
    lyrics = "[Intro]\nمَن Celina هَستَم\nLo-ren-am… Lo-ren-am…"
    assert not latin_song(lyrics) and latin_song("[نکته]\nshe waits upon the balcony")
    # an all-Latin line of a song in another script is transliterations: unknown letters, never known ones
    assert line_key("Lo-ren-am… Lo-ren-am…", latin=False) == Key("", 9)
    assert gaps(lyrics, heard("من", "سلیمه", "هستم"), 20_000) == []  # it has no letters to miss


def test_whispers_mishearings_on_the_owners_song_still_match() -> None:
    pairs = [
        ("لَعنَت بِه آن اَسب و سِپَر، لَعنَت بِه غُرورَت!", "لعنت به آن عصف و سپر لعنت به غرورت"),
        ("غُرورَت کُور کَردِه To-raa، اُفتادی دَر این چاه!", "غرورت کور کرده تو را افتادی در این شاه"),
        ("اَمّا… دُو نَفَر را کُشتی…»", "اما دو نفر را گشتی"),
        ("«مَن Celina هَستَم… وَ این، قِصّه‌یِ خُونینِ مَن اَست…", "من صلینا هستم و این قسط خونین من است"),
    ]
    for given, misheard in pairs:
        assert score(line_key(given, latin=False), plain(misheard)) >= FOUND, given
    unrelated = plain("پدرت رفته بود و تنها یک نشان")
    assert score(line_key("چُو Noh ماه بُگذَشتْ، زادی چُو شیرْ!", latin=False), unrelated) < FOUND


def test_every_line_heard_means_no_gap() -> None:
    lyrics = "[Verse 1: drums]\nshe waits upon the balcony\n\n[Musical Drop: piano]\nthe wind is in her hair"
    words = heard("she", "weights", "upon", "the", "balcony", "the", "win", "is", "inner", "hair")
    assert gaps(lyrics, words, 20_000) == []  # bracketed notes are never missing
    assert all_heard(Gap(["she waits upon the balcony", "the wind is in her hair"], 0, 1, True), words)


def test_lines_not_heard_make_one_gap_between_their_found_neighbours() -> None:
    lyrics = "one two three four\nfive six seven eight\nnine ten eleven twelve\nthirteen fourteen fifteen"
    words = heard("one", "two", "three", "for", "thirteen", "fourteen", "fifteen", at=1000)
    missing = ["five six seven eight", "nine ten eleven twelve"]
    assert gaps(lyrics, words, 20_000) == [Gap(missing, start_ms=4800, end_ms=5000, latin=True)]
    assert gaps(lyrics, words[:4], 20_000) == [  # at the end, the gap runs to the song's end
        Gap([*missing, "thirteen fourteen fifteen"], 4800, 20_000, latin=True)
    ]
    assert gaps(lyrics, [], 20_000)[0].start_ms == 0  # nothing heard: the whole song
    assert not all_heard(Gap(["one two three four", "five six seven eight"], 0, 1, True), words)


def test_a_repeated_line_is_matched_in_order() -> None:
    lyrics = "the wind is in her hair\nshe waits upon the balcony\nthe wind is in her hair"
    words = heard("the", "wind", "is", "in", "her", "hair", "the", "wind", "is", "in", "her", "hair")
    assert gaps(lyrics, words, 20_000) == [Gap(["she waits upon the balcony"], 6800, 7000, latin=True)]


def test_a_missed_chorus_line_does_not_drag_the_alignment_past_a_verse() -> None:
    chorus = "oh the night comes down"
    verse = [f"verse word{n} after word{n} sung clearly here" for n in range(7)]  # 7 x 7 > SEARCH words
    lyrics = "\n".join(["first line is heard", chorus, *verse, chorus])
    texts = ["first", "line", "is", "heard", *" ".join(verse).split(), *chorus.split()]
    assert len(texts) - 4 - 5 > SEARCH
    words = heard(*texts, at=0)
    # the first chorus was not heard: it is missing where it belongs, and the verse is still found
    assert gaps(lyrics, words, 100_000) == [Gap([chorus], 3800, 4000, latin=True)]


def test_a_line_after_a_long_run_of_hallucinated_words_is_found_again() -> None:
    # the owner's bad run: "موسیقی" heard over two minutes in place of the lines sung there
    lyrics = "\n".join(["اول بار اینجا", "خط گم شده یک", "خط گم شده دو", "سلام دوباره من"])
    words = heard("اول", "بار", "اینجا", *["موسیقی"] * 62, "سلام", "دوباره", "من", at=0)
    key = line_key("سلام دوباره من", latin=False)
    assert find_line(key, [plain(w.text) for w in words], 3) is None  # beyond SEARCH from the cursor
    found = gaps(lyrics, words, 100_000)
    # two lines missed in a row widen the search for the third: it is found, the gap ends there
    assert found == [Gap(["خط گم شده یک", "خط گم شده دو"], 2800, 65_000, latin=False)]


def test_each_given_line_has_the_start_of_the_words_it_was_found_in() -> None:
    lyrics = "سلام دنیا\nDarvin… Kaa-ra-van\nخوب بود\nشب شد"
    words = heard("سلام", "دنیا", "دروین", "کاروان", "خوب", "بود")
    # the second line is transliterations only (it cannot be matched), the last is not heard
    assert found_starts(lyrics, words) == [1000, None, 5000, None]
    assert found_starts(None, words) == []


def test_lines_not_heard_in_an_instrumental_span_are_named() -> None:
    timeline = hmv.Timeline(
        duration_ms=20_000,
        sections=[],
        lines=[],
        instrumental=[
            Instrumental(start_ms=0, end_ms=3000, kind="intro"),
            Instrumental(start_ms=5000, end_ms=9000, kind="break"),
        ],
    )
    gap = Gap(["a line"], 3000, 5001, latin=True)
    assert in_instrumental(timeline, [gap]) == [(gap, 5000, 9000)]  # touching is not overlapping


def test_an_echo_or_an_invented_time_is_suspect() -> None:
    prompt = "آخ… Lo-ren-am…"
    # the real check's reply to that prompt (gateway whisper-1, 2026-10-10), in slice times
    echo = [
        hmv.Word(text="آخ…", start_ms=7520, end_ms=8920),
        hmv.Word(text="Lo", start_ms=8920, end_ms=10320),
        hmv.Word(text="ren", start_ms=10320, end_ms=10560),
        hmv.Word(text="am…", start_ms=10560, end_ms=21000),
    ]
    assert suspect(echo, OTHER_SCRIPT, prompt) == "'am…' lasts 10440 ms (at most 5000 ms)"
    short = [*echo[:3], hmv.Word(text="am…", start_ms=10560, end_ms=11000)]  # the same, without the 10 s
    assert suspect(short, OTHER_SCRIPT, prompt) == (
        "the prompt echoed back (its transliteration 'lorenam'): 'آخ… Lo ren am…'"
    )
    # the re-run's third listen of it, on the vocals: "Ah, Lo-ren-am…" is the given spelling
    vocals = [
        hmv.Word(text=t, start_ms=1000 * n, end_ms=1000 * n + 500)
        for n, t in enumerate(("Ah,", "Lo-ren-am…"))
    ]
    assert "'lorenam'" in (suspect(vocals, OTHER_SCRIPT, prompt) or "")
    assert suspect(heard("آخ", "لورنم"), OTHER_SCRIPT, prompt) is None  # what Whisper writes: no Latin
    assert suspect(heard("she", "waits"), ENGLISH, "she waits") is None  # a Latin song may echo Latin
    assert suspect(heard("Darvin", "came"), OTHER_SCRIPT, "چُو Noh ماه بُگذَشتْ") is None  # Latin, not given


def test_the_threshold_and_the_later_start_are_pinned() -> None:
    key = Key("abcdefghij", 0)
    assert find_line(key, ["abcdefxyzw"], 0) == (0, 0)  # 6 of 10 letters in 10: 0.600, found
    assert find_line(key, ["abcdefxyzwv"], 0) is None  # in 11: 0.571, not found
    line = Key("abcdefgh", 0)
    assert find_line(line, ["ab", "x", "abcdefgh"], 0) == (2, 2)  # found from word 0, best from word 2
    assert find_line(line, ["ab", "x", "y", "z", "abcdefgh"], 0) == (3, 4)  # at most LOOK = 3 words on


def test_a_long_unbroken_line_is_matched_quickly() -> None:
    words = heard(*["la"] * 300)
    paragraph = " ".join(f"word{n}" for n in range(80))  # 80 words pasted as one line
    began = time.monotonic()
    assert gaps("la " * 300, words, 400_000) == []  # longer than LONGEST_LINE letters: not matched
    gaps(paragraph + "\n" + "la " * 60, words, 400_000)
    assert time.monotonic() - began < 2.0  # quadratic matching took minutes; a shared CI runner ~0.6 s
