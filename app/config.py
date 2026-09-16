from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default=ROOT_DIR / "data")
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 180.0

    image_api_key: str = ""
    image_base_url: str = "https://api.openai.com/v1"
    image_model: str = "dall-e-3"
    image_timeout_seconds: float = 180.0

    # Everything below is optional and free of charge.
    tts_voice: str = ""  # override the per-style default edge-tts voice
    pexels_api_key: str = ""  # free key -> real stock footage per scene
    pixabay_api_key: str = ""  # free key -> stock footage fallback

    @property
    def projects_dir(self) -> Path:
        return self.data_dir / "projects"

    @property
    def resolved_image_key(self) -> str:
        return self.image_api_key.strip() or self.llm_api_key.strip()

    @property
    def llm_ready(self) -> bool:
        return bool(self.llm_api_key.strip()) or self._is_local(self.llm_base_url)

    @property
    def images_ready(self) -> bool:
        return bool(self.resolved_image_key) or self._is_local(self.image_base_url)

    @staticmethod
    def _is_local(url: str) -> bool:
        base = url.lower()
        return "localhost" in base or "127.0.0.1" in base

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
