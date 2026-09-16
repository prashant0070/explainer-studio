from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.demo import DEMO_PROJECT
from app.generator import GeneratorError, generate_pack
from app.images import ImageClient, ImageError
from app.llm import LlmError
from app.prompts import DURATION_TARGETS, StyleName
from app.render import RenderBusy, render_status, start_render
from app.research import ResearchError, notes_from_research, research_topic, suggest_topics
from app.store import export_zip, image_path, list_projects, load_project, project_dir, save_project
from app.tts import VOICE_MENU
from app.visuals import VisualError, generate_free_image

WEB_DIR = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(title="Explainer Studio")


class GenerateRequest(BaseModel):
    topic: str = Field(min_length=2)
    style: StyleName = "odyssey"
    duration: str = "12"
    angle: str = ""
    notes: str = ""
    research: bool = True


class IdeasRequest(BaseModel):
    niche: str = Field(min_length=3)
    count: int = 6


class ImageRequest(BaseModel):
    scene_ids: Optional[List[int]] = None
    include_thumbnail: bool = True
    limit: int = 8


class RenderRequest(BaseModel):
    voice: str = ""
    captions: bool = True
    music: bool = True
    stock_video: bool = True
    scene_limit: int = 0


@app.get("/api/health")
def health() -> Dict[str, Any]:
    settings = get_settings()
    return {
        "llm_ready": settings.llm_ready,
        "images_ready": settings.images_ready,
        "stock_ready": bool(settings.pexels_api_key or settings.pixabay_api_key),
        "model": settings.llm_model,
        "image_model": settings.image_model,
        "durations": DURATION_TARGETS,
        "voices": VOICE_MENU,
    }


@app.get("/api/projects")
def projects() -> Dict[str, Any]:
    return {"projects": list_projects()}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> Dict[str, Any]:
    if project_id == DEMO_PROJECT["id"]:
        existing = load_project(project_id)
        return existing or save_project(dict(DEMO_PROJECT))
    project = load_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@app.post("/api/research/ideas")
def research_ideas(req: IdeasRequest) -> Dict[str, Any]:
    try:
        ideas = suggest_topics(req.niche, max(1, min(req.count, 12)))
    except (ResearchError, LlmError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ideas": ideas}


@app.post("/api/generate")
def generate(req: GenerateRequest) -> Dict[str, Any]:
    if req.duration not in DURATION_TARGETS:
        raise HTTPException(400, "Duration must be 8, 12, or 15")
    notes = req.notes
    research: Optional[Dict[str, Any]] = None
    if req.research:
        try:
            research = research_topic(req.topic)
            brief = notes_from_research(research)
            notes = f"{notes.strip()}\n\n{brief}".strip() if notes.strip() else brief
        except (ResearchError, LlmError):
            research = None  # research is best-effort; script can proceed without
    try:
        pack = generate_pack(req.topic, req.style, req.duration, req.angle, notes)
    except (GeneratorError, LlmError) as exc:
        raise HTTPException(400, str(exc)) from exc
    if research:
        pack["research"] = research
    return save_project(pack)


@app.post("/api/projects/{project_id}/images")
def generate_images(project_id: str, req: ImageRequest) -> Dict[str, Any]:
    project = load_project(project_id)
    if not project:
        if project_id == DEMO_PROJECT["id"]:
            project = save_project(dict(DEMO_PROJECT))
        else:
            raise HTTPException(404, "Project not found")

    client = ImageClient()
    use_paid = client.enabled

    def make(prompt: str, dest: Path, seed: int) -> None:
        if use_paid:
            client.generate(prompt, dest)
        else:
            generate_free_image(prompt, dest, seed=seed)

    scenes = project.get("scenes") or []
    wanted = set(req.scene_ids or [])
    generated = 0
    errors: List[str] = []

    if req.include_thumbnail and project.get("thumbnail_prompt") and not project.get("thumbnail_path"):
        dest = image_path(project_id, "thumbnail.png")
        try:
            make(project["thumbnail_prompt"], dest, seed=7)
            project["thumbnail_path"] = f"/api/projects/{project_id}/files/thumbnail.png"
            generated += 1
        except (ImageError, VisualError) as exc:
            errors.append(f"thumbnail: {exc}")

    remaining = max(0, req.limit - generated)
    for scene in scenes:
        if remaining <= 0:
            break
        if wanted and scene["id"] not in wanted:
            continue
        if scene.get("image_path"):
            continue
        dest = image_path(project_id, f"scene-{scene['id']:02d}.png")
        try:
            make(scene["image_prompt"], dest, seed=scene["id"] * 101)
            scene["image_path"] = f"/api/projects/{project_id}/files/scene-{scene['id']:02d}.png"
            generated += 1
            remaining -= 1
        except (ImageError, VisualError) as exc:
            errors.append(f"scene {scene['id']}: {exc}")
            break

    save_project(project)
    return {"project": project, "generated": generated, "errors": errors, "free_mode": not use_paid}


@app.post("/api/projects/{project_id}/render")
def render_project(project_id: str, req: RenderRequest) -> Dict[str, Any]:
    if not load_project(project_id):
        if project_id == DEMO_PROJECT["id"]:
            save_project(dict(DEMO_PROJECT))
        else:
            raise HTTPException(404, "Project not found")
    try:
        return start_render(project_id, req.model_dump())
    except RenderBusy as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/projects/{project_id}/render/status")
def get_render_status(project_id: str) -> Dict[str, Any]:
    return render_status(project_id)


@app.get("/api/projects/{project_id}/video")
def project_video(project_id: str) -> FileResponse:
    path = project_dir(project_id) / "final.mp4"
    if not path.exists():
        raise HTTPException(404, "No rendered video yet")
    return FileResponse(path, media_type="video/mp4", filename=f"{project_id}.mp4")


@app.get("/api/projects/{project_id}/files/{name}")
def project_file(project_id: str, name: str) -> FileResponse:
    path = image_path(project_id, name)
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path)


@app.get("/api/projects/{project_id}/export")
def export_project(project_id: str) -> FileResponse:
    project = load_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    zip_path = export_zip(project)
    filename = f"{project_id}-explainer.zip"
    return FileResponse(zip_path, filename=filename, media_type="application/zip")


if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
