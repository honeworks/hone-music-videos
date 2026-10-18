"""The words a prompt must not use (design §8.3, 0014, D-078, D-088): words of speech, and in a motion
prompt the words of the mouth, negated or not. `check_shots` warns on them, and an edited motion prompt
that has them is answered with a warning (`runs_redo.set_motion`, 0027)."""

from __future__ import annotations

import re

# A word of speech in a prompt: the video model would move the lips (0014, D-078). Expressions (smile,
# laugh, shout, roar, gasp, cry) are not speech.
SPEECH = re.compile(
    r"\b(?:speak(?:s|ing)?|spoke|say(?:s|ing)?|said|sing(?:s|ing)?|sang|sung|whisper(?:s|ing|ed)?"
    r"|talk(?:s|ing|ed)?|call(?:s|ing|ed)? out|recit(?:e|es|ing|ed)|chant(?:s|ing|ed)?"
    r"|mouth(?:s|ing|ed)? the words|lips (?:move|moving|form|forming)(?: words)?)\b",
    re.IGNORECASE,
)
# What a motion prompt never names, not even negated ("she does not speak", "lips closed"): Wan runs at
# cfg 1, so negations do nothing, and naming the mouth makes it move (D-088).
MOUTH = re.compile(
    r"\b(?:mouths?|lips?|jaws?|teeth|tooth|breath(?:s|e|es|ed|ing)?|voices?|words?)\b", re.IGNORECASE
)
MOTION_WORDS = re.compile(f"{SPEECH.pattern}|{MOUTH.pattern}", re.IGNORECASE)


def words_of_speech(text: str, *, motion: bool) -> list[str]:
    """The words of speech in a prompt, each once; in a motion prompt also the words of the mouth
    (`MOUTH`), negated or not (§8.3, D-078, D-088)."""
    pattern = MOTION_WORDS if motion else SPEECH
    return list(dict.fromkeys(m.group(0).lower() for m in pattern.finditer(text)))
