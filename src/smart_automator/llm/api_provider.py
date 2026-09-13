# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""API-based LLM provider: user configures their own API key.

Alternative to Claude CLI when users want to use the Anthropic API
directly or any compatible API endpoint.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from smart_automator.llm.base import LLMProvider


class APIProvider(LLMProvider):
    """LLM provider using HTTP API calls.

    Supports Anthropic Messages API format. Users provide their own
    API key via environment variable or direct configuration.
    """

    DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._model = model or self.DEFAULT_MODEL
        self._timeout = timeout_seconds

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        image_path: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Generate response using the Messages API."""
        if not self.is_available():
            raise RuntimeError(
                "API key not configured. Set ANTHROPIC_API_KEY or pass api_key."
            )

        messages: list[dict[str, Any]] = []
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        if image_path:
            content.insert(0, self._build_image_block(image_path))

        messages.append({"role": "user", "content": content})

        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Extract text from response
        text_blocks = [
            block["text"]
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_blocks)

    @staticmethod
    def _build_image_block(image_path: str) -> dict[str, Any]:
        """Build an image content block for the API."""
        import base64

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Determine media type
        ext = image_path.lower().rsplit(".", 1)[-1]
        media_types = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        media_type = media_types.get(ext, "image/png")

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_data,
            },
        }

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self._api_key)

    @property
    def name(self) -> str:
        return f"API ({self._model})"
