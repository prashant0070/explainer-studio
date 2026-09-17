from __future__ import annotations

from typing import Any, Dict, List

from app.llm import LlmClient
from app.prompts import (
    DURATION_TARGETS,
    StyleName,
    normalize_image_prompt,
    system_prompt,
    user_prompt,
)

REQUIRED_SCENE_KEYS = ("narration", "image_prompt")


class GeneratorError(RuntimeError):
    pass


def generate_pack(
    topic: str,
    style: StyleName,
    duration_key: str,
    angle: str,
    notes: str,
    llm: LlmClient | None = None,
) -> Dict[str, Any]:
    if duration_key not in DURATION_TARGETS:
        raise GeneratorError("Duration must be 8, 12, or 15")
    if not topic.strip():
        raise GeneratorError("Topic is required")

    client = llm or LlmClient()
    data = client.chat_json(
        system_prompt(style),
        user_prompt(topic, style, duration_key, angle, notes),
        temperature=0.75,
    )
    return normalize_pack(data, topic, style, duration_key)


def normalize_pack(
    data: Dict[str, Any],
    topic: str,
    style: StyleName,
    duration_key: str,
) -> Dict[str, Any]:
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 6:
        raise GeneratorError("Model returned too few scenes")

    cleaned: List[Dict[str, Any]] = []
    for index, raw in enumerate(scenes, start=1):
        if not isinstance(raw, dict):
            continue
        narration = str(raw.get("narration") or "").strip()
        image_prompt = normalize_image_prompt(str(raw.get("image_prompt") or "").strip(), style)
        if not narration or not image_prompt:
            continue
        duration = _as_int(raw.get("duration_seconds"), 12)
        duration = min(22, max(6, duration))
        cleaned.append(
            {
                "id": index,
                "section": str(raw.get("section") or "story").strip() or "story",
                "visual_type": str(raw.get("visual_type") or "establishing").strip(),
                "narration": narration,
                "on_screen_text": str(raw.get("on_screen_text") or "").strip(),
                "duration_seconds": duration,
                "image_prompt": image_prompt,
                "image_path": None,
            }
        )

    if len(cleaned) < 6:
        raise GeneratorError("Not enough usable scenes after cleanup")

    for index, scene in enumerate(cleaned, start=1):
        scene["id"] = index

    titles = [str(t).strip() for t in (data.get("titles") or []) if str(t).strip()]
    if not titles:
        titles = [topic.strip()]

    narration_parts = [scene["narration"] for scene in cleaned]
    full_narration = str(data.get("full_narration") or "").strip() or "\n\n".join(narration_parts)
    word_count = len(full_narration.split())
    runtime = sum(scene["duration_seconds"] for scene in cleaned)

    chapters = data.get("chapters") if isinstance(data.get("chapters"), list) else []
    tags = [str(t).strip() for t in (data.get("tags") or []) if str(t).strip()]

    return {
        "topic": topic.strip(),
        "style": style,
        "duration_key": duration_key,
        "titles": titles[:5],
        "thumbnail_text": str(data.get("thumbnail_text") or titles[0]).strip(),
        "thumbnail_prompt": normalize_image_prompt(str(data.get("thumbnail_prompt") or "").strip(), style),
        "thumbnail_path": None,
        "hook": str(data.get("hook") or cleaned[0]["narration"]).strip(),
        "driving_question": str(data.get("driving_question") or "").strip(),
        "thesis": str(data.get("thesis") or "").strip(),
        "runtime_seconds": runtime,
        "word_count": word_count,
        "youtube_description": str(data.get("youtube_description") or "").strip(),
        "tags": tags[:20],
        "chapters": _clean_chapters(chapters),
        "full_narration": full_narration,
        "scenes": cleaned,
    }


def _clean_chapters(chapters: List[Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for item in chapters:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        time = str(item.get("time") or "").strip()
        if title and time:
            out.append({"time": time, "title": title})
    return out


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
