# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Mock Instagram Graph API executor: demonstrates the pattern."""

from __future__ import annotations

import os
from typing import Any

from smart_automator.api_executor.base import APIClient
from smart_automator.models import RateLimit


class MockInstagramAPIExecutor:
    """Mock Instagram Graph API executor.

    Demonstrates how to add a new platform API executor.
    In production, this would use the real Instagram Graph API.
    """

    API_BASE = "https://graph.instagram.com"

    def __init__(
        self,
        access_token: str | None = None,
        rate_limit: RateLimit | None = None,
    ) -> None:
        self._token = access_token or os.getenv("INSTAGRAM_TOKEN", "")
        self._client = APIClient(
            base_url=self.API_BASE,
            headers={"Authorization": f"Bearer {self._token}"},
            rate_limit=rate_limit or RateLimit(requests_per_minute=200),
        )

    async def get_user_profile(self, user_id: str = "me") -> dict[str, Any]:
        """Get user profile information."""
        return await self._client.get(
            f"/{user_id}",
            params={"fields": "id,username,account_type,media_count"},
        )

    async def get_media(
        self,
        user_id: str = "me",
        limit: int = 25,
    ) -> dict[str, Any]:
        """Get user's media posts."""
        return await self._client.get(
            f"/{user_id}/media",
            params={
                "fields": "id,caption,media_type,timestamp,permalink",
                "limit": limit,
            },
        )

    async def create_media_container(
        self,
        image_url: str,
        caption: str = "",
    ) -> dict[str, Any]:
        """Create a media container for publishing."""
        return await self._client.post(
            "/me/media",
            json={
                "image_url": image_url,
                "caption": caption,
            },
        )

    async def publish_media(
        self, creation_id: str
    ) -> dict[str, Any]:
        """Publish a media container."""
        return await self._client.post(
            "/me/media_publish",
            json={"creation_id": creation_id},
        )
