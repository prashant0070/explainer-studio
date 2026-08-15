from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ImageError(RuntimeError):
    pass


class ImageClient:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return self._settings.images_ready

    def generate(self, prompt: str, dest: Path) -> Path:
        if not self.enabled:
            raise ImageError("Set IMAGE_API_KEY or LLM_API_KEY to generate images")
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = self._settings.image_base_url.rstrip("/") + "/images/generations"
        headers = {"Content-Type": "application/json"}
        key = self._settings.resolved_image_key
        if key:
            headers["Authorization"] = f"Bearer {key}"
        model = self._settings.image_model
        payload = {
            "model": model,
            "prompt": prompt[:3900],
            "n": 1,
            "size": "1536x1024" if model.startswith("gpt-image") else "1792x1024",
        }
        if model.startswith("dall-e"):
            payload["response_format"] = "b64_json"
            payload["quality"] = "standard"
        try:
            with httpx.Client(timeout=self._settings.image_timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Image request failed: %s", exc)
            raise ImageError(f"Image request failed: {exc}") from exc

        item = (data.get("data") or [None])[0]
        if not item:
            raise ImageError("Image API returned no data")
        if item.get("b64_json"):
            dest.write_bytes(base64.b64decode(item["b64_json"]))
            return dest
        image_url = item.get("url")
        if not image_url:
            raise ImageError("Image API returned neither b64 nor url")
        _assert_http_url(image_url)
        try:
            with httpx.Client(timeout=self._settings.image_timeout_seconds) as client:
                download = client.get(image_url)
                download.raise_for_status()
                dest.write_bytes(download.content)
        except httpx.HTTPError as exc:
            raise ImageError(f"Failed to download generated image: {exc}") from exc
        return dest


def _assert_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ImageError("Image API returned an invalid URL")
