# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Generic REST/GraphQL API client with retry and rate limiting."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from smart_automator.models import RateLimit


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate_limit: RateLimit) -> None:
        self._rpm = rate_limit.requests_per_minute
        self._burst = rate_limit.burst_limit
        self._cooldown = rate_limit.cooldown_seconds
        self._tokens = float(self._burst)
        self._last_refill = time.monotonic()

    def acquire(self) -> float:
        """Acquire a token, returning wait time in seconds (0 if available)."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._burst,
            self._tokens + elapsed * (self._rpm / 60.0),
        )
        self._last_refill = now

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return 0.0
        return (1.0 - self._tokens) / (self._rpm / 60.0)


class APIClient:
    """Generic async HTTP client with retry logic and rate limiting.

    Supports REST and GraphQL endpoints with configurable
    authentication and rate limiting.
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        rate_limit: RateLimit | None = None,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._rate_limiter = RateLimiter(rate_limit or RateLimit())
        self._max_retries = max_retries
        self._timeout = timeout_seconds

    def _build_client(self) -> httpx.AsyncClient:
        """Create a configured httpx async client."""
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=self._timeout,
        )

    async def request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry and rate limiting."""
        wait = self._rate_limiter.acquire()
        if wait > 0:
            await asyncio.sleep(wait)

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with self._build_client() as client:
                    response = await client.request(
                        method=method,
                        url=path,
                        json=json,
                        params=params,
                        data=data,
                    )
                    response.raise_for_status()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    ):
                        return response.json()
                    return {"status": response.status_code, "text": response.text}
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    await asyncio.sleep(self._rate_limiter._cooldown)
                    continue
                if e.response.status_code >= 500:
                    last_error = e
                    await asyncio.sleep(2**attempt)
                    continue
                raise
            except httpx.RequestError as e:
                last_error = e
                await asyncio.sleep(2**attempt)
                continue

        raise last_error or RuntimeError("Request failed after retries")

    async def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """HTTP GET request."""
        return await self.request("GET", path, params=params)

    async def post(
        self, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """HTTP POST request."""
        return await self.request("POST", path, json=json)

    async def put(
        self, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """HTTP PUT request."""
        return await self.request("PUT", path, json=json)

    async def patch(
        self, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """HTTP PATCH request."""
        return await self.request("PATCH", path, json=json)

    async def delete(self, path: str) -> dict[str, Any]:
        """HTTP DELETE request."""
        return await self.request("DELETE", path)

    async def graphql(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        return await self.post("/graphql", json=payload)
