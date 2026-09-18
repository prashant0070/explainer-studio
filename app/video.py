"""Professional-grade assembly with FFmpeg (free, local, unlimited).

Editing decisions baked in:
- 1920x1080 at 30 fps, H.264 + AAC (YouTube-ready).
- A hard cut on every scene boundary (the explainer format cuts with the script).
- Ken Burns motion on stills — alternating push-in / pull-back with drift,
  so still images read as footage.
- Stock video clips are looped/trimmed to the narration and center-cropped.
- Music bed (optional) is side-chain ducked under the voice.
- Word-timed captions burned in, fade from black in, fade to black out.
- Final loudness normalized to -16 LUFS (YouTube standard).
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

WIDTH, HEIGHT, FPS = 1920, 1080, 30
TAIL_PAD = 0.35  # breathing room after each scene's last word


class VideoError(RuntimeError):
    pass


def _run(args: List[str], label: str) -> None:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        tail = (result.stderr or "")[-2000:]
        logger.error("ffmpeg failed at %s:\n%s", label, tail)
        raise VideoError(f"{label} failed: {tail.splitlines()[-1] if tail else 'unknown'}")


def build_scene_clip(
    visual: Dict[str, str],
    audio: Path,
    duration: float,
    index: int,
    dest: Path,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = duration + TAIL_PAD
    if visual["kind"] == "video":
        vf = (
            f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1,format=yuv420p"
        )
        args = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", visual["path"],
            "-i", str(audio),
            "-t", f"{total:.3f}",
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", vf,
            "-af", "apad,aresample=48000,pan=stereo|c0=c0|c1=c0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-shortest",
            str(dest),
        ]
    else:
        frames = max(2, int(round(total * FPS)))
        vf = f"{_ken_burns(index, frames)},setsar=1,format=yuv420p"
        args = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", str(FPS), "-i", visual["path"],
            "-i", str(audio),
            "-t", f"{total:.3f}",
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", vf,
            "-af", "apad,aresample=48000,pan=stereo|c0=c0|c1=c0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-shortest",
            str(dest),
        ]
    _run(args, f"scene {index} clip")
    return dest


def _ken_burns(index: int, frames: int) -> str:
    """Alternating cinematic move per cut so consecutive scenes feel edited."""
    # Upscale first: zoompan on a large canvas avoids sub-pixel jitter.
    pre = "scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800"
    speed = 0.10 / max(frames, 1)  # ~10% zoom across the scene
    mode = index % 4
    if mode == 0:  # push in, center
        z = f"min(zoom+{speed:.6f},1.12)"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == 1:  # pull back from tight
        z = f"if(eq(on,1),1.12,max(1.0,zoom-{speed:.6f}))"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == 2:  # push in, drift right-down
        z = f"min(zoom+{speed:.6f},1.12)"
        x, y = "(iw-iw/zoom)*on/{d}".format(d=frames), "(ih-ih/zoom)*on/{d}".format(d=frames)
    else:  # push in, drift left-up
        z = f"min(zoom+{speed:.6f},1.12)"
        x = "(iw-iw/zoom)*(1-on/{d})".format(d=frames)
        y = "(ih-ih/zoom)*(1-on/{d})".format(d=frames)
    return (
        f"{pre},zoompan=z='{z}':x='{x}':y='{y}'"
        f":d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS}"
    )


def concat_scenes(clips: List[Path], dest: Path) -> Path:
    list_file = dest.with_suffix(".txt")
    lines = [f"file '{clip.resolve().as_posix()}'" for clip in clips]
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(dest),
        ],
        "scene concat",
    )
    return dest


def finalize(
    base: Path,
    dest: Path,
    total_duration: float,
    captions: Optional[Path] = None,
    music: Optional[Path] = None,
) -> Path:
    """Burn captions, mix + duck music, fades, loudness-normalize, encode."""
    fade_out_start = max(0.0, total_duration - 0.9)
    video_chain: List[str] = []
    if captions and captions.exists():
        video_chain.append(f"ass={_escape_filter_path(captions)}")
    video_chain.append("fade=t=in:st=0:d=0.6")
    video_chain.append(f"fade=t=out:st={fade_out_start:.2f}:d=0.9")
    vf = ",".join(video_chain)

    args: List[str] = ["ffmpeg", "-y", "-i", str(base)]
    if music and music.exists():
        args += ["-stream_loop", "-1", "-i", str(music)]
        music_fade = max(0.0, total_duration - 2.0)
        filter_complex = (
            f"[0:v]{vf}[v];"
            f"[1:a]atrim=0:{total_duration:.3f},volume=0.5,"
            f"afade=t=in:st=0:d=1.5,afade=t=out:st={music_fade:.2f}:d=2.0[m];"
            f"[m][0:a]sidechaincompress=threshold=0.02:ratio=10:attack=5:release=500[duck];"
            f"[0:a][duck]amix=inputs=2:duration=first:dropout_transition=3,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11[a]"
        )
        args += ["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"]
    else:
        args += [
            "-vf", vf,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        ]
    args += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        "-t", f"{total_duration:.3f}",
        str(dest),
    ]
    _run(args, "final master")
    return dest


def probe(path: Path) -> Dict[str, Any]:
    import json as _json

    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "format=duration,size,bit_rate:stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise VideoError(f"ffprobe failed for {path.name}")
    return _json.loads(result.stdout)


def _escape_filter_path(path: Path) -> str:
    text = path.resolve().as_posix()
    return text.replace(":", "\\:").replace("'", "\\'")
