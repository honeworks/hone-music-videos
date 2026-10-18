"""ffmpeg for the assembly (design §5.3, §12): a finished clip measured, cut to its frames, and the cuts
joined under the song.

Every frame of the video is encoded once: each cut is encoded with the same settings, then the cuts are
joined without encoding them again (D-035)."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from hone_music_video.errors import InvalidInput, MusicVideoError, ToolMissing

X264 = ("-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p")  # design §12
MP4_AUDIO = ("aac", "mp3")  # songs carried into the MP4 as they are; any other becomes AAC 320 kb/s


@dataclass(frozen=True)
class Clip:
    """What ffprobe finds in a video: its size (`1920x1080`), frame rate (`32/1`) and frame count."""

    size: str
    rate: str
    frames: int


def require_ffmpeg() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        verb = "is" if len(missing) == 1 else "are"
        tools = " and ".join(missing)
        raise ToolMissing(
            f"{tools} {verb} not installed; install ffmpeg (it brings ffprobe) and resume the run"
        )


def _probe(path: Path, *args: str) -> dict[str, object]:
    found = subprocess.run(  # noqa: S603 - a fixed program and a path we made
        ["ffprobe", "-v", "error", "-of", "json", *args, str(path)],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        streams = json.loads(found.stdout)["streams"]
        return dict(streams[0])
    except (ValueError, KeyError, IndexError, TypeError):
        why = found.stderr.strip() or "no stream found"
        raise InvalidInput(f"{path.name} is not a file ffprobe can read ({why})") from None


def probe(clip: Path) -> Clip:
    """The clip's size, frame rate and frames (its packets counted: no decoding)."""
    entries = "stream=width,height,r_frame_rate,nb_read_packets"
    found = _probe(clip, "-select_streams", "v:0", "-count_packets", "-show_entries", entries)
    return Clip(
        f"{found['width']}x{found['height']}", str(found["r_frame_rate"]), int(str(found["nb_read_packets"]))
    )


def audio_codec(song: Path) -> str:
    return str(_probe(song, "-select_streams", "a:0", "-show_entries", "stream=codec_name")["codec_name"])


def frame_rgb(clip: Path, n: int, size: tuple[int, int]) -> bytes:
    """Frame `n` (from 0) of `clip` as RGB bytes at `size`; a failure says what ffmpeg said."""
    found = subprocess.run(  # noqa: S603 - a fixed program and arguments we made
        [  # noqa: S607
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-i",
            str(clip),
            "-vf",
            f"select=eq(n\\,{n}),scale={size[0]}:{size[1]}",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        capture_output=True,
        check=False,
    )
    if found.returncode != 0 or not found.stdout:
        raise MusicVideoError(
            f"ffmpeg could not read frame {n} of {clip.name}: {found.stderr.decode()[-500:]}"
        )
    return found.stdout


def ffmpeg(*args: str | Path) -> None:
    """Run ffmpeg quietly, overwriting its output; a failure says what ffmpeg said."""
    found = subprocess.run(  # noqa: S603 - a fixed program and arguments we made
        ["ffmpeg", "-v", "error", "-nostdin", "-y", *map(str, args)],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if found.returncode != 0:
        raise MusicVideoError(f"ffmpeg failed: {found.stderr.strip()[-500:]}")


def cut(clip: Path, frames: int, fps: int, out: Path) -> None:
    """Exactly `frames` frames at `fps`: the clip's from its first, its last frame held as long as it is
    short (the clip may show fewer frames than it has packets, D-035); checked after the cut. Each frame
    gets the time `n / fps` (`settb`, `setpts`) and ffmpeg is not asked for a rate (`-r`), which would
    fill a gap in the clip's timestamps with copies of a frame instead of taking its next frames."""
    vf = f"tpad=stop_mode=clone:stop=-1,settb=1/{fps},setpts=N"
    ffmpeg("-i", clip, "-vf", vf, "-frames:v", str(frames), "-an", *X264, out)
    made = probe(out).frames
    if made != frames:
        raise MusicVideoError(f"ffmpeg cut {made} frames of {clip.name} instead of {frames}")


def join(cuts: list[Path], listing: Path, song: Path, out: Path) -> None:
    """The cuts one after another (not encoded again, listed in `listing` for ffmpeg's concat), the song
    under them, as `out` (an MP4)."""
    listing.write_text("".join(f"file '{c.name}'\n" for c in cuts), encoding="utf-8")
    copy = audio_codec(song) in MP4_AUDIO
    audio = ("-c:a", "copy") if copy else ("-c:a", "aac", "-b:a", "320k")
    inputs = ("-f", "concat", "-safe", "0", "-i", listing, "-i", song)
    ffmpeg(*inputs, "-map", "0:v", "-map", "1:a", "-c:v", "copy", *audio, "-movflags", "+faststart", out)
