"""Persistent production queue — saved topics we work through one by one."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.intel import SCIENCE_TOPICS, TEN_TOPICS


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def slate_path() -> Path:
    return get_settings().data_dir / "slate.json"


def default_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for topic in SCIENCE_TOPICS:
        items.append(_item("science", topic))
    for topic in TEN_TOPICS:
        items.append(_item("myth", topic))
    return items


def _item(lane: str, topic: Dict[str, Any]) -> Dict[str, Any]:
    rank = int(topic.get("rank") or 0)
    ident = f"{lane[:3]}-{rank:02d}-{_slug(str(topic.get('title') or topic.get('topic') or 'topic'))}"
    return {
        "id": ident,
        "lane": lane,
        "rank": rank,
        "status": "queued",
        "topic": topic.get("topic", ""),
        "title": topic.get("title", ""),
        "hook": topic.get("hook", ""),
        "style": topic.get("style", "odyssey"),
        "demand": topic.get("demand", ""),
        "why": topic.get("why", ""),
        "gap": topic.get("gap", ""),
        "project_id": None,
        "notes": "",
    }


def load_slate() -> Dict[str, Any]:
    path = slate_path()
    if not path.exists():
        return save_slate({"items": default_items()})
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("items"):
        data["items"] = default_items()
        return save_slate(data)
    return data


def save_slate(data: Dict[str, Any]) -> Dict[str, Any]:
    get_settings().ensure_dirs()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    data.setdefault("name", "Explainer Studio production queue")
    slate_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def reset_slate() -> Dict[str, Any]:
    return save_slate({"items": default_items()})


def merge_topics(topics: List[Dict[str, Any]], lane: str) -> Dict[str, Any]:
    """Add intel topics to the queue without wiping existing status."""
    slate = load_slate()
    by_title = {item.get("title"): item for item in slate["items"]}
    by_topic = {item.get("topic"): item for item in slate["items"]}
    added = 0
    for topic in topics:
        existing = by_title.get(topic.get("title")) or by_topic.get(topic.get("topic"))
        if existing:
            for key in ("hook", "demand", "why", "gap", "style"):
                if topic.get(key):
                    existing[key] = topic[key]
            continue
        item = _item(lane or "science", topic)
        slate["items"].append(item)
        added += 1
    save_slate(slate)
    slate["merged"] = added
    return slate


def get_item(item_id: str) -> Optional[Dict[str, Any]]:
    for item in load_slate().get("items") or []:
        if item.get("id") == item_id:
            return item
    return None


def update_item(item_id: str, **fields: Any) -> Dict[str, Any]:
    slate = load_slate()
    found = False
    for item in slate["items"]:
        if item.get("id") == item_id:
            item.update({k: v for k, v in fields.items() if v is not None})
            found = True
            break
    if not found:
        raise KeyError(item_id)
    return save_slate(slate)


def mark_project(item_id: str, project_id: str, status: str = "in_progress") -> None:
    try:
        update_item(item_id, project_id=project_id, status=status)
    except KeyError:
        return


def mark_done_for_project(project_id: str) -> None:
    slate = load_slate()
    changed = False
    for item in slate["items"]:
        if item.get("project_id") == project_id and item.get("status") != "done":
            item["status"] = "done"
            changed = True
    if changed:
        save_slate(slate)
