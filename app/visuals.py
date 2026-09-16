"""Free, copyright-safe visuals for every scene.

Priority per scene:
1. An image the user already generated (paid API) — reuse, never re-bill.
2. Free stock video (Pexels / Pixabay, free API keys, CC0-style licenses).
3. Free AI image generation via Pollinations (no key, no cost).
4. Offline cinematic title card rendered locally with Pillow (always works).
"""
from __future__ import annotations

import hashlib
import logging
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.config import get_settings

logger = logging.getLogger(__name__)

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
IMAGE_W, IMAGE_H = 1600, 900


class VisualError(RuntimeError):
    pass


def acquire_scene_visual(
    scene: Dict[str, Any],
    project_dir: Path,
    prefer_stock_video: bool = True,
    retries: int = 3,
) -> Dict[str, str]:
    """Return {"kind": "video"|"image", "path": str(local path)}."""
    images_dir = project_dir / "images"
    clips_dir = project_dir / "clips"
    images_dir.mkdir(parents=True, exist_ok=True)

    existing = scene.get("image_path")
    if existing:
        local = images_dir / Path(str(existing)).name
        if local.exists():
            return {"kind": "image", "path": str(local)}

    scene_id = int(scene["id"])
    settings = get_settings()

    if prefer_stock_video and (settings.pexels_api_key or settings.pixabay_api_key):
        clips_dir.mkdir(parents=True, exist_ok=True)
        clip = clips_dir / f"scene-{scene_id:02d}.mp4"
        if clip.exists():
            return {"kind": "video", "path": str(clip)}
        query = stock_query(scene)
        try:
            if settings.pexels_api_key and _pexels_video(query, clip, settings.pexels_api_key):
                return {"kind": "video", "path": str(clip)}
            if settings.pixabay_api_key and _pixabay_video(query, clip, settings.pixabay_api_key):
                return {"kind": "video", "path": str(clip)}
        except httpx.HTTPError as exc:
            logger.warning("Stock video lookup failed for scene %s: %s", scene_id, exc)

    image = images_dir / f"scene-{scene_id:02d}.png"
    if image.exists():
        return {"kind": "image", "path": str(image)}
    prompt = str(scene.get("image_prompt") or scene.get("narration") or "")
    for attempt in range(retries):
        try:
            generate_free_image(prompt, image, seed=scene_id * 101 + attempt)
            return {"kind": "image", "path": str(image)}
        except VisualError as exc:
            logger.warning(
                "Pollinations attempt %s failed for scene %s: %s", attempt + 1, scene_id, exc
            )
            time.sleep(2.0 * (attempt + 1))

    title_card(
        scene.get("on_screen_text") or _short_text(scene.get("narration", "")),
        image,
        seed=scene_id,
    )
    return {"kind": "image", "path": str(image)}


def generate_free_image(prompt: str, dest: Path, seed: int = 0) -> Path:
    """Pollinations.ai — free AI image generation, no key required.

    We request extra height and crop the bottom strip off, because the free
    tier can stamp a small watermark in the bottom-right corner.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Steer flux away from rendering a literal framed canvas on a wall.
    steered = (
        f"Full-bleed cinematic film frame: {prompt[:1200]} — edge-to-edge image, "
        "no frame, no border, no canvas edge, no wall, no matting"
    )
    url = POLLINATIONS_URL.format(prompt=quote(steered))
    params = {
        "width": IMAGE_W,
        "height": IMAGE_H + 100,  # extra headroom; final size is enforced below
        "nologo": "true",
        "seed": seed,
        "model": "flux",
    }
    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            content = response.content
    except httpx.HTTPError as exc:
        raise VisualError(f"Free image service failed: {exc}") from exc
    if len(content) < 5000:
        raise VisualError("Free image service returned an empty image")
    import io

    try:
        img = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001 - any decode failure means bad payload
        raise VisualError(f"Free image service returned invalid data: {exc}") from exc
    img = _strip_borders(img)
    # The free tier stamps a small watermark near the bottom-right regardless of
    # nologo, so always drop the bottom strip of whatever was returned.
    img = img.crop((0, 0, img.width, int(img.height * 0.92)))
    img = img.resize((IMAGE_W, IMAGE_H), Image.LANCZOS)
    img.save(dest)
    return dest


def _strip_borders(img: Image.Image, max_frac: float = 0.14) -> Image.Image:
    """Remove uniform bands (wall/frame/matting artifacts) from left/right/top.

    A band counts as border when its pixel values barely vary — real scene
    content (sea, sky, stone) always carries texture at 1600px wide.
    """
    import statistics

    gray = img.convert("L")
    w, h = gray.size
    px = gray.load()
    step = max(1, h // 80)

    def col_uniform(x: int) -> bool:
        vals = [px[x, y] for y in range(0, h, step)]
        return statistics.pstdev(vals) < 10.0

    def row_uniform(y: int) -> bool:
        vals = [px[x, y] for x in range(0, w, max(1, w // 80))]
        return statistics.pstdev(vals) < 10.0

    left = 0
    while left < int(w * max_frac) and col_uniform(left):
        left += 1
    right = w
    while right > w - int(w * max_frac) and col_uniform(right - 1):
        right -= 1
    top = 0
    while top < int(h * max_frac) and row_uniform(top):
        top += 1
    if left or top or right < w:
        # A few extra pixels hide the soft edge between band and content.
        pad = 6
        left = min(left + pad, w // 4) if left else 0
        top = min(top + pad, h // 4) if top else 0
        right = max(right - pad, w * 3 // 4) if right < w else w
        img = img.crop((left, top, right, h))
    return img


def generate_thumbnail(prompt: str, dest: Path) -> Path:
    seed = int(hashlib.sha1(prompt.encode()).hexdigest()[:6], 16)
    return generate_free_image(prompt, dest, seed=seed)


def stock_query(scene: Dict[str, Any]) -> str:
    """Compact search keywords from the scene's visual prompt."""
    keywords = scene.get("stock_keywords")
    if keywords:
        return str(keywords)
    prompt = str(scene.get("image_prompt") or scene.get("narration") or "")
    prompt = prompt.split("—")[0].split(" - ")[0]
    words = re.findall(r"[a-zA-Z]{3,}", prompt.lower())
    stop = {
        "cinematic", "painted", "illustration", "widescreen", "ultra", "detailed",
        "oil", "painting", "realism", "dramatic", "chiaroscuro", "warm", "amber",
        "torchlight", "against", "deep", "teal", "black", "shadows", "volumetric",
        "dust", "sea", "mist", "film", "still", "composition", "shallow", "depth",
        "field", "text", "letters", "watermark", "logo", "modern", "objects",
        "the", "and", "with", "over", "into", "from", "his", "her", "their",
    }
    picked = [w for w in words if w not in stop][:5]
    return " ".join(picked) or "cinematic landscape"


def _pexels_video(query: str, dest: Path, api_key: str) -> bool:
    with httpx.Client(timeout=60.0) as client:
        response = client.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            headers={"Authorization": api_key},
        )
        response.raise_for_status()
        videos = response.json().get("videos") or []
        for video in videos:
            files = sorted(
                (f for f in video.get("video_files", []) if f.get("width")),
                key=lambda f: abs(int(f.get("width") or 0) - 1920),
            )
            if files:
                return _download(files[0]["link"], dest)
    return False


def _pixabay_video(query: str, dest: Path, api_key: str) -> bool:
    with httpx.Client(timeout=60.0) as client:
        response = client.get(
            "https://pixabay.com/api/videos/",
            params={"key": api_key, "q": query[:100], "per_page": 5, "safesearch": "true"},
        )
        response.raise_for_status()
        hits = response.json().get("hits") or []
        for hit in hits:
            videos = hit.get("videos") or {}
            candidate = videos.get("large") or videos.get("medium") or videos.get("small")
            if candidate and candidate.get("url"):
                return _download(candidate["url"], dest)
    return False


def _download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=180.0, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with dest.open("wb") as handle:
                for chunk in response.iter_bytes(65536):
                    handle.write(chunk)
    return dest.exists() and dest.stat().st_size > 20000


# ---------------------------------------------------------------- title card


_PALETTES = [
    ((12, 20, 28), (32, 58, 66), (233, 196, 106)),
    ((16, 14, 26), (54, 39, 66), (231, 178, 104)),
    ((10, 22, 20), (28, 62, 56), (222, 184, 120)),
    ((20, 14, 12), (66, 40, 30), (236, 200, 130)),
]


def title_card(text: str, dest: Path, seed: int = 0) -> Path:
    """Offline cinematic gradient card — the render never blocks on a network."""
    rng = random.Random(seed)
    top, bottom, accent = _PALETTES[seed % len(_PALETTES)]
    img = Image.new("RGB", (IMAGE_W, IMAGE_H), top)
    draw = ImageDraw.Draw(img)
    for y in range(IMAGE_H):
        t = y / IMAGE_H
        draw.line(
            [(0, y), (IMAGE_W, y)],
            fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)),
        )
    # Soft vignette glow spots for depth.
    glow = Image.new("RGB", (IMAGE_W, IMAGE_H), (0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for _ in range(3):
        cx, cy = rng.randint(0, IMAGE_W), rng.randint(0, IMAGE_H)
        radius = rng.randint(200, 480)
        glow_draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=tuple(c // 5 for c in accent),
        )
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(160)), 0.5)

    draw = ImageDraw.Draw(img)
    message = _short_text(text) or "SCENE"
    font = _font(64)
    lines = _wrap(draw, message.upper(), font, IMAGE_W - 320)
    total = len(lines) * 84
    y = (IMAGE_H - total) // 2
    for line in lines:
        width = draw.textlength(line, font=font)
        x = (IMAGE_W - width) / 2
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=accent)
        y += 84
    bar_y = y + 24
    draw.rectangle(
        (IMAGE_W // 2 - 90, bar_y, IMAGE_W // 2 + 90, bar_y + 5), fill=accent
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return dest


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: Any, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    line = ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines[:4]


def _short_text(text: str, limit: int = 60) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"


def pick_music(project_dir: Path) -> Optional[Path]:
    """Music is optional: drop royalty-free tracks into data/music/ (project
    folder music.mp3 wins). Everything else in the pipeline stays keyless."""
    local = project_dir / "music.mp3"
    if local.exists():
        return local
    music_dir = get_settings().data_dir / "music"
    if music_dir.exists():
        tracks = sorted(
            p for p in music_dir.iterdir() if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".ogg"}
        )
        if tracks:
            return tracks[0]
    return None
