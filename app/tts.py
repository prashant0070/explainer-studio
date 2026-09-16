"""Free neural narration via Microsoft Edge TTS (no API key, no cost).

Each scene gets its own MP3 plus word-level timings, which later drive
scene durations, cut points, and word-timed captions.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import edge_tts

# 100-nanosecond units per second (edge-tts offset/duration unit).
_TICKS = 10_000_000

STYLE_VOICES = {
    "odyssey": "en-US-AndrewNeural",
    "dark_vault": "en-US-ChristopherNeural",
}
DEFAULT_VOICE = "en-US-AndrewNeural"

# A curated menu for the UI; any edge-tts voice name also works.
VOICE_MENU = [
    {"id": "en-US-AndrewNeural", "label": "Andrew — warm storyteller (US)"},
    {"id": "en-US-ChristopherNeural", "label": "Christopher — deep documentary (US)"},
    {"id": "en-US-GuyNeural", "label": "Guy — energetic explainer (US)"},
    {"id": "en-US-AriaNeural", "label": "Aria — clear narrator (US)"},
    {"id": "en-US-JennyNeural", "label": "Jenny — friendly (US)"},
    {"id": "en-GB-RyanNeural", "label": "Ryan — British documentary"},
    {"id": "en-GB-SoniaNeural", "label": "Sonia — British narrator"},
    {"id": "en-AU-WilliamNeural", "label": "William — Australian"},
    {"id": "en-IN-PrabhatNeural", "label": "Prabhat — Indian English"},
    {"id": "en-IN-NeerjaNeural", "label": "Neerja — Indian English"},
    {"id": "hi-IN-MadhurNeural", "label": "Madhur — Hindi"},
    {"id": "hi-IN-SwaraNeural", "label": "Swara — Hindi"},
]


class TtsError(RuntimeError):
    pass


def voice_for_style(style: str) -> str:
    return STYLE_VOICES.get(style, DEFAULT_VOICE)


def synthesize_scene(
    text: str,
    dest: Path,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    pitch: str = "+0Hz",
) -> Dict[str, Any]:
    """Synthesize one scene. Returns {duration, words:[{text,start,end}]}."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        words = asyncio.run(_synthesize(text, dest, voice, rate, pitch))
    except Exception as exc:  # noqa: BLE001 - surface any network/protocol error
        raise TtsError(f"Narration failed ({voice}): {exc}") from exc
    if not dest.exists() or dest.stat().st_size == 0:
        raise TtsError("Narration produced no audio")
    duration = probe_duration(dest)
    return {"duration": duration, "words": words}


async def _synthesize(
    text: str, dest: Path, voice: str, rate: str, pitch: str
) -> List[Dict[str, Any]]:
    communicate = edge_tts.Communicate(
        text, voice, rate=rate, pitch=pitch, boundary="WordBoundary"
    )
    words: List[Dict[str, Any]] = []
    with dest.open("wb") as handle:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                handle.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / _TICKS
                words.append(
                    {
                        "text": str(chunk["text"]).strip(),
                        "start": round(start, 3),
                        "end": round(start + chunk["duration"] / _TICKS, 3),
                    }
                )
    return words


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise TtsError(f"Could not read audio duration for {path.name}") from exc
