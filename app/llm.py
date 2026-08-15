from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class LlmError(RuntimeError):
    pass


class LlmClient:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return self._settings.llm_ready

    def chat_json(self, system: str, user: str, temperature: float = 0.7) -> Dict[str, Any]:
        raw = self.chat(system, user, temperature=temperature)
        parsed = parse_json_object(raw)
        if parsed is None:
            raise LlmError("Model did not return valid JSON")
        return parsed

    def chat(self, system: str, user: str, temperature: float = 0.7, max_tokens: int = 8000) -> str:
        if not self.enabled:
            raise LlmError("Set LLM_API_KEY in .env, or point LLM_BASE_URL at a local model")
        url = self._settings.llm_base_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self._settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self._settings.llm_api_key}"
        payload = {
            "model": self._settings.llm_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            with httpx.Client(timeout=self._settings.llm_timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("LLM request failed: %s", exc)
            raise LlmError(f"LLM request failed: {exc}") from exc
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError("LLM returned an unexpected payload") from exc


def parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return None
    match = _FENCE.search(text)
    if match:
        text = match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None
