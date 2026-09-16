"""Automated final-quality analysis of the rendered video (all local, free).

Checks: container/stream sanity, duration vs. plan, resolution/fps, integrated
loudness (EBU R128), true peak, long black frames, long silences. Produces a
pass/warn/fail report; optionally asks the LLM for a one-paragraph verdict.
"""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm import LlmClient, LlmError
from app.video import probe

logger = logging.getLogger(__name__)

_LOUDNESS_RE = re.compile(r"I:\s*(-?[\d.]+)\s*LUFS")
_PEAK_RE = re.compile(r"Peak:\s*(-?[\d.]+)\s*dBFS")
_BLACK_RE = re.compile(r"black_start:([\d.]+) black_end:([\d.]+) black_duration:([\d.]+)")
_SILENCE_RE = re.compile(r"silence_duration:\s*([\d.]+)")


def analyze(video: Path, expected_duration: float, scene_count: int) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    info = probe(video)
    fmt = info.get("format") or {}
    streams = info.get("streams") or []
    vstream = next((s for s in streams if s.get("codec_type") == "video"), {})
    astream = next((s for s in streams if s.get("codec_type") == "audio"), {})

    duration = float(fmt.get("duration") or 0)
    size_mb = round(int(fmt.get("size") or 0) / 1_048_576, 1)

    checks.append(_check(
        "container",
        bool(vstream) and bool(astream),
        f"video={vstream.get('codec_name')} audio={astream.get('codec_name')} · {size_mb} MB",
        "Video or audio stream missing",
    ))

    drift = abs(duration - expected_duration)
    checks.append(_check(
        "duration",
        drift <= max(3.0, expected_duration * 0.08),
        f"{duration:.1f}s rendered vs {expected_duration:.1f}s planned",
        f"Duration drifts {drift:.1f}s from the plan",
        warn=drift <= max(6.0, expected_duration * 0.15),
    ))

    width, height = int(vstream.get("width") or 0), int(vstream.get("height") or 0)
    checks.append(_check(
        "resolution",
        (width, height) == (1920, 1080),
        f"{width}x{height}",
        f"Expected 1920x1080, got {width}x{height}",
    ))

    fps = _fps(str(vstream.get("avg_frame_rate") or "0/1"))
    checks.append(_check(
        "framerate",
        abs(fps - 30.0) < 1.0,
        f"{fps:.2f} fps",
        f"Expected ~30 fps, got {fps:.2f}",
    ))

    audio_stats = _audio_stats(video)
    loudness = audio_stats.get("loudness")
    if loudness is not None:
        checks.append(_check(
            "loudness",
            -18.5 <= loudness <= -13.5,
            f"{loudness:.1f} LUFS integrated (target -16)",
            f"Loudness {loudness:.1f} LUFS is off the -16 target",
            warn=-21.0 <= loudness <= -11.0,
        ))
    peak = audio_stats.get("peak")
    if peak is not None:
        checks.append(_check(
            "true_peak",
            peak <= -0.8,
            f"{peak:.1f} dBFS peak",
            f"Peak {peak:.1f} dBFS risks clipping",
            warn=peak <= 0.0,
        ))

    black = _black_segments(video)
    long_black = [b for b in black if b["duration"] > 1.6 and b["start"] > 1.0]
    checks.append(_check(
        "black_frames",
        not long_black,
        "No unexpected black segments",
        f"{len(long_black)} black segment(s) mid-video, longest "
        f"{max((b['duration'] for b in long_black), default=0):.1f}s",
    ))

    silences = audio_stats.get("silences") or []
    long_silence = [s for s in silences if s > 3.0]
    checks.append(_check(
        "silence",
        not long_silence,
        "No dead air over 3s",
        f"{len(long_silence)} silence(s) over 3s, longest {max(long_silence, default=0):.1f}s",
    ))

    passed = sum(1 for c in checks if c["status"] == "pass")
    warned = sum(1 for c in checks if c["status"] == "warn")
    failed = sum(1 for c in checks if c["status"] == "fail")
    verdict = "pass" if failed == 0 and warned <= 1 else ("warn" if failed == 0 else "fail")

    return {
        "verdict": verdict,
        "summary": f"{passed} passed · {warned} warnings · {failed} failed "
                   f"· {duration:.0f}s · {scene_count} scenes · {size_mb} MB",
        "checks": checks,
        "duration": duration,
        "size_mb": size_mb,
    }


def llm_review(report: Dict[str, Any], project: Dict[str, Any]) -> Optional[str]:
    """One-paragraph editorial verdict from the LLM. Non-fatal if unavailable."""
    client = LlmClient()
    if not client.enabled:
        return None
    lines = [
        f"- {c['name']}: {c['status']} — {c['detail']}" for c in report.get("checks", [])
    ]
    try:
        return client.chat(
            "You are a video production QC lead. Given technical check results and the "
            "video's plan, write a 3-5 sentence verdict: is it ready to upload, what to "
            "fix first, and one concrete improvement for the next render. Plain text.",
            f"Title: {(project.get('titles') or ['?'])[0]}\n"
            f"Planned runtime: {project.get('runtime_seconds')}s, "
            f"{len(project.get('scenes') or [])} scenes.\n"
            f"Technical checks:\n" + "\n".join(lines),
            temperature=0.4,
        ).strip()
    except LlmError as exc:
        logger.warning("LLM QC review unavailable: %s", exc)
        return None


def _check(name: str, ok: bool, detail: str, fail_detail: str, warn: bool = False) -> Dict[str, Any]:
    if ok:
        status = "pass"
    elif warn:
        status = "warn"
    else:
        status = "fail"
    return {"name": name, "status": status, "detail": detail if ok else fail_detail}


def _audio_stats(video: Path) -> Dict[str, Any]:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
            "-map", "0:a:0",
            "-af", "ebur128=peak=true,silencedetect=noise=-38dB:d=1.5",
            "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    text = result.stderr or ""
    loudness_match = _LOUDNESS_RE.findall(text)
    peak_match = _PEAK_RE.findall(text)
    silences = [float(v) for v in _SILENCE_RE.findall(text)]
    return {
        "loudness": float(loudness_match[-1]) if loudness_match else None,
        "peak": float(peak_match[-1]) if peak_match else None,
        "silences": silences,
    }


def _black_segments(video: Path) -> List[Dict[str, float]]:
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
            "-vf", "blackdetect=d=1.0:pix_th=0.08",
            "-an", "-f", "null", "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    segments = []
    for match in _BLACK_RE.finditer(result.stderr or ""):
        segments.append(
            {
                "start": float(match.group(1)),
                "end": float(match.group(2)),
                "duration": float(match.group(3)),
            }
        )
    return segments


def _fps(rate: str) -> float:
    if "/" in rate:
        num, den = rate.split("/", 1)
        try:
            return float(num) / float(den or 1)
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(rate)
    except ValueError:
        return 0.0
