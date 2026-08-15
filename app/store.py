from __future__ import annotations

import json
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import get_settings


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def project_dir(project_id: str) -> Path:
    path = get_settings().projects_dir / project_id
    path.mkdir(parents=True, exist_ok=True)
    (path / "images").mkdir(exist_ok=True)
    return path


def save_project(project: Dict[str, Any]) -> Dict[str, Any]:
    project_id = project.get("id") or new_id()
    project["id"] = project_id
    project["updated_at"] = datetime.now(timezone.utc).isoformat()
    if "created_at" not in project:
        project["created_at"] = project["updated_at"]
    dest = project_dir(project_id) / "project.json"
    dest.write_text(json.dumps(project, indent=2), encoding="utf-8")
    return project


def load_project(project_id: str) -> Optional[Dict[str, Any]]:
    path = get_settings().projects_dir / project_id / "project.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_projects() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    root = get_settings().projects_dir
    if not root.exists():
        return rows
    for folder in sorted(root.iterdir(), reverse=True):
        data_path = folder / "project.json"
        if not data_path.exists():
            continue
        data = json.loads(data_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "id": data.get("id", folder.name),
                "topic": data.get("topic", ""),
                "style": data.get("style", ""),
                "title": (data.get("titles") or [""])[0],
                "scene_count": len(data.get("scenes") or []),
                "updated_at": data.get("updated_at", ""),
            }
        )
    return rows


def image_path(project_id: str, name: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return project_dir(project_id) / "images" / safe


def export_zip(project: Dict[str, Any]) -> Path:
    project_id = project["id"]
    folder = project_dir(project_id)
    zip_path = folder / "export.zip"
    script = render_script_markdown(project)
    youtube = render_youtube_text(project)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("script.md", script)
        zf.writestr("youtube.txt", youtube)
        zf.writestr("project.json", json.dumps(project, indent=2))
        images = folder / "images"
        if images.exists():
            for file in images.iterdir():
                if file.is_file():
                    zf.write(file, f"images/{file.name}")
    return zip_path


def render_script_markdown(project: Dict[str, Any]) -> str:
    titles = project.get("titles") or [project.get("topic", "Untitled")]
    lines = [
        f"# {titles[0]}",
        "",
        f"**Style:** {project.get('style')}  ",
        f"**Runtime:** {project.get('runtime_seconds')}s · **Words:** {project.get('word_count')}  ",
        f"**Thumbnail text:** {project.get('thumbnail_text')}",
        "",
        "## Titles",
        "",
    ]
    for title in titles:
        lines.append(f"- {title}")
    lines += [
        "",
        "## Hook",
        "",
        project.get("hook", ""),
        "",
        f"**Driving question:** {project.get('driving_question', '')}",
        "",
        f"**Thesis:** {project.get('thesis', '')}",
        "",
        "## Full narration",
        "",
        project.get("full_narration", ""),
        "",
        "## Scenes",
        "",
    ]
    for scene in project.get("scenes") or []:
        lines += [
            f"### Scene {scene['id']} — {scene.get('section')} / {scene.get('visual_type')} ({scene.get('duration_seconds')}s)",
            "",
            scene.get("narration", ""),
            "",
            f"*Image prompt:* {scene.get('image_prompt', '')}",
            "",
        ]
        if scene.get("on_screen_text"):
            lines.append(f"*On-screen:* {scene['on_screen_text']}")
            lines.append("")
    return "\n".join(lines)


def render_youtube_text(project: Dict[str, Any]) -> str:
    titles = project.get("titles") or [""]
    lines = [
        titles[0],
        "",
        project.get("youtube_description", ""),
        "",
        "Chapters",
    ]
    for chapter in project.get("chapters") or []:
        lines.append(f"{chapter.get('time')} {chapter.get('title')}")
    tags = project.get("tags") or []
    if tags:
        lines += ["", "Tags", ", ".join(tags)]
    return "\n".join(lines)
