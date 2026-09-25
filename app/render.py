"""End-to-end render orchestrator.

Pipeline: narration (free TTS) -> visuals (free stock/AI/local) -> word-timed
captions -> per-scene edit + concat -> master with music duck + loudnorm ->
automated QC. Progress is written to render.json so the UI can poll it.
"""
from __future__ import annotations

import json
import logging
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import qc as qc_mod
from app.store import load_project, project_dir, save_project
from app.slate import mark_done_for_project
from app.subtitles import build_captions
from app.tts import synthesize_scene, voice_for_style
from app.video import TAIL_PAD, build_scene_clip, concat_scenes, finalize
from app.visuals import acquire_scene_visual, generate_thumbnail, pick_music, VisualError

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ACTIVE: Dict[str, threading.Thread] = {}

STAGES = ["narration", "visuals", "captions", "assembly", "master", "qc", "done"]

# Narration pace -> edge-tts rate. "faster" is a gentle lift that stays natural;
# "fastest" is punchier for high-energy explainers.
PACE_RATES = {"normal": "+0%", "faster": "+15%", "fastest": "+28%"}


class RenderBusy(RuntimeError):
    pass


def start_render(project_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    project = load_project(project_id)
    if not project:
        raise ValueError("Project not found")
    with _LOCK:
        thread = _ACTIVE.get(project_id)
        if thread and thread.is_alive():
            raise RenderBusy("A render is already running for this project")
        status = _write_status(
            project_id,
            stage="narration",
            progress=0.0,
            message="Starting render…",
            state="running",
        )
        worker = threading.Thread(
            target=_run_safe, args=(project_id, options or {}), daemon=True
        )
        _ACTIVE[project_id] = worker
        worker.start()
    return status


def render_status(project_id: str) -> Dict[str, Any]:
    path = project_dir(project_id) / "render.json"
    if not path.exists():
        return {"state": "idle"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"state": "idle"}


def _run_safe(project_id: str, options: Dict[str, Any]) -> None:
    try:
        _run(project_id, options)
    except Exception as exc:  # noqa: BLE001 - report every failure to the UI
        logger.error("Render failed for %s:\n%s", project_id, traceback.format_exc())
        _write_status(
            project_id,
            stage="error",
            progress=0.0,
            message=str(exc),
            state="error",
        )


def _run(project_id: str, options: Dict[str, Any]) -> None:
    project = load_project(project_id)
    assert project is not None
    folder = project_dir(project_id)
    scenes: List[Dict[str, Any]] = project.get("scenes") or []
    if not scenes:
        raise ValueError("Project has no scenes")

    voice = str(options.get("voice") or "").strip() or voice_for_style(project.get("style", ""))
    use_captions = options.get("captions", True)
    use_music = options.get("music", True)
    prefer_stock = bool(options.get("stock_video", True))
    image_engine = str(options.get("image_engine") or "auto")
    if image_engine not in {"auto", "paid", "free"}:
        image_engine = "auto"
    if image_engine == "paid":
        prefer_stock = False  # user explicitly wants generated stills everywhere
    limit = int(options.get("scene_limit") or 0)
    if limit > 0:
        scenes = scenes[:limit]
    pace = str(options.get("pace") or "normal").lower()
    rate = PACE_RATES.get(pace, "+0%")

    total = len(scenes)
    audio_dir = folder / "audio"
    clips_dir = folder / "video" / "scenes"

    # ---- Stage 1: narration --------------------------------------------------
    timeline: List[Dict[str, Any]] = []
    offset = 0.0
    for i, scene in enumerate(scenes):
        _write_status(
            project_id, "narration", i / total,
            f"Voiceover {i + 1}/{total}: “{scene['narration'][:48]}…”",
        )
        audio = audio_dir / f"scene-{scene['id']:02d}.mp3"
        result = synthesize_scene(scene["narration"], audio, voice=voice, rate=rate)
        timeline.append(
            {
                "scene_id": scene["id"],
                "audio": str(audio),
                "duration": result["duration"],
                "offset": offset,
                "words": result["words"],
            }
        )
        offset += result["duration"] + TAIL_PAD
    total_duration = offset
    (audio_dir / "timings.json").write_text(
        json.dumps(timeline, indent=2), encoding="utf-8"
    )

    # ---- Stage 2: visuals ----------------------------------------------------
    visuals: List[Dict[str, str]] = []
    for i, scene in enumerate(scenes):
        _write_status(
            project_id, "visuals", i / total,
            f"Visual {i + 1}/{total}: {scene.get('visual_type', 'scene')}",
        )
        visual = acquire_scene_visual(
            scene, folder, prefer_stock_video=prefer_stock, image_engine=image_engine
        )
        visuals.append(visual)
        if visual["kind"] == "image":
            scene["image_path"] = f"/api/projects/{project_id}/files/{Path(visual['path']).name}"

    if project.get("thumbnail_prompt") and not project.get("thumbnail_path"):
        try:
            generate_thumbnail(
                project["thumbnail_prompt"],
                folder / "images" / "thumbnail.png",
                image_engine=image_engine,
            )
            project["thumbnail_path"] = f"/api/projects/{project_id}/files/thumbnail.png"
        except VisualError as exc:
            logger.warning("Thumbnail generation skipped: %s", exc)

    # ---- Stage 3: captions ---------------------------------------------------
    captions_path: Optional[Path] = None
    if use_captions:
        _write_status(project_id, "captions", 0.5, "Building word-timed captions")
        captions_path = build_captions(timeline, folder / "captions.ass")

    # ---- Stage 4: per-scene edit + concat -------------------------------------
    clip_paths: List[Path] = []
    for i, (scene, entry, visual) in enumerate(zip(scenes, timeline, visuals)):
        _write_status(
            project_id, "assembly", i / total,
            f"Cutting scene {i + 1}/{total} ({'footage' if visual['kind'] == 'video' else 'ken burns'})",
        )
        clip = clips_dir / f"scene-{scene['id']:02d}.mp4"
        build_scene_clip(visual, Path(entry["audio"]), entry["duration"], i, clip)
        clip_paths.append(clip)
    _write_status(project_id, "assembly", 0.95, "Joining scene cuts")
    base = concat_scenes(clip_paths, folder / "video" / "base.mp4")

    # ---- Stage 5: master -----------------------------------------------------
    music = pick_music(folder) if use_music else None
    _write_status(
        project_id, "master", 0.2,
        "Mastering: captions burn-in, music duck, loudness normalize"
        + ("" if music else " (no music file found — voice only)"),
    )
    final = finalize(
        base,
        folder / "final.mp4",
        total_duration,
        captions=captions_path,
        music=music,
    )

    # ---- Stage 6: QC ---------------------------------------------------------
    _write_status(project_id, "qc", 0.3, "Analyzing final quality (loudness, black frames, sync)")
    report = qc_mod.analyze(final, total_duration, total)
    review = qc_mod.llm_review(report, project)
    if review:
        report["llm_review"] = review
    (folder / "qc.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    project["video_path"] = f"/api/projects/{project_id}/video"
    project["video_duration"] = report.get("duration")
    project["qc"] = report
    project["rendered_at"] = datetime.now(timezone.utc).isoformat()
    save_project(project)
    mark_done_for_project(project_id)

    _write_status(
        project_id, "done", 1.0,
        f"Render complete — QC {report['verdict'].upper()} · {report['summary']}",
        state="done",
    )


def _write_status(
    project_id: str,
    stage: str,
    progress: float,
    message: str,
    state: str = "running",
) -> Dict[str, Any]:
    stage_index = STAGES.index(stage) if stage in STAGES else 0
    overall = (
        1.0 if state == "done"
        else min(0.99, (stage_index + max(0.0, min(progress, 1.0))) / (len(STAGES) - 1))
    )
    status = {
        "state": state,
        "stage": stage,
        "stage_progress": round(progress, 3),
        "overall": round(overall, 3),
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path = project_dir(project_id) / "render.json"
    path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status
