"""A shot's focus (change 0035): what the shot is of, one of five simple pictures the models draw well,
each with the one thing that carries its feeling. Code checks a shot against its focus and gives it the
views its focus needs; a shot planned before 0035 gets the focus its framing and cast imply."""

from __future__ import annotations

from hone_music_video.records_frame import Focus, FrameShot

FOCUSES: tuple[Focus, ...] = ("face", "figure", "pair", "place", "detail")
# how many characters each focus holds, at least and at most
CAST = {"face": (1, 1), "figure": (1, 1), "pair": (2, 2), "place": (0, 0), "detail": (0, 1)}
FRAMINGS = {
    "face": ("medium", "close-up", "extreme-close-up"),
    "figure": ("medium", "wide", "extreme-wide"),
    "pair": ("medium", "wide"),
    "place": ("wide", "extreme-wide"),
    "detail": ("insert", "extreme-close-up", "close-up"),
}


def focus_of(shot: FrameShot) -> Focus:
    """The shot's focus, or for a shot planned before 0035 the one its framing and cast imply."""
    if shot.focus is not None:
        return shot.focus
    views = {u.view for u in shot.cast}
    if shot.framing == "insert" or "detail" in views:
        return "detail"
    if not shot.cast:
        return "place"
    if len(shot.cast) > 1:
        return "pair"
    if "close" in views or shot.framing in ("close-up", "extreme-close-up"):
        return "face"
    return "figure"


def focus_problems(shot: FrameShot) -> list[str]:
    """A shot without a focus, or one whose characters, framing or faces its focus does not allow."""
    if shot.focus is None:
        return [f"has no `focus`: give it one of {', '.join(FOCUSES)}"]
    least, most = CAST[shot.focus]
    found: list[str] = []
    if not least <= len(shot.cast) <= most:
        want = str(least) if least == most else f"{least} or {most}"
        found.append(
            f"is a {shot.focus} with {len(shot.cast)} characters in `cast`; a {shot.focus} has {want}"
        )
    if shot.framing not in FRAMINGS[shot.focus]:
        allowed = ", ".join(FRAMINGS[shot.focus])
        found.append(f"is a {shot.focus} in a {shot.framing} framing; a {shot.focus} is {allowed}")
    if shot.faces and shot.focus in ("place", "detail"):
        found.append(f"is a {shot.focus} with `faces` true: no face is recognised in it")
    if shot.focus == "detail" and shot.cast and not shot.cast[0].part.strip():
        found.append("is a detail of a character without its `part`: name the part that fills the frame")
    return found


def with_focus_views(shots: list[FrameShot]) -> list[FrameShot]:
    """Each shot with the views its focus needs: a face's character its close-up, a detail's the part."""
    for shot in shots:
        focus = focus_of(shot)
        for use in shot.cast:
            if focus == "face":
                use.view, use.pose, use.part = "close", "", ""
            elif focus == "detail":
                use.view, use.pose = "detail", ""
    return shots
