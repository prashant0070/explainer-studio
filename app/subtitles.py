"""Word-timed captions built from Edge-TTS word boundaries (no Whisper needed).

Captions are grouped into short phrases (TikTok/YouTube-Shorts style), rendered
as an ASS file and burned in during the final encode.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

MAX_WORDS_PER_CAPTION = 4
MAX_CAPTION_SECONDS = 2.6

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,96,1
Style: Accent,DejaVu Sans,64,&H0066D9F2,&H00FFFFFF,&H00101010,&H96000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,96,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def build_captions(scene_timeline: List[Dict[str, Any]], dest: Path) -> Path:
    """scene_timeline: [{"offset": float, "words": [{text,start,end}, ...]}]."""
    events: List[str] = []
    for scene in scene_timeline:
        offset = float(scene["offset"])
        for group in _group_words(scene.get("words") or []):
            start = offset + group[0]["start"]
            end = offset + group[-1]["end"] + 0.08
            text = " ".join(w["text"] for w in group)
            text = _escape(text.upper())
            events.append(
                f"Dialogue: 0,{_ts(start)},{_ts(end)},Caption,,0,0,0,,"
                f"{{\\fad(60,40)}}{text}"
            )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(ASS_HEADER + "\n".join(events) + "\n", encoding="utf-8")
    return dest


def _group_words(words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    groups: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    for word in words:
        if current:
            too_many = len(current) >= MAX_WORDS_PER_CAPTION
            too_long = word["end"] - current[0]["start"] > MAX_CAPTION_SECONDS
            # A pause of 0.5s+ reads as a sentence break — cut the caption there.
            gap = word["start"] - current[-1]["end"] > 0.5
            if too_many or too_long or gap:
                groups.append(current)
                current = []
        current.append(word)
    if current:
        groups.append(current)
    return groups


def _ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def _escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")
