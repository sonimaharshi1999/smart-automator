# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""GitHub API executor: create issues, comments, PRs via REST API."""

from __future__ import annotations

import os
from typing import Any

from smart_automator.api_executor.base import APIClient
from smart_automator.models import RateLimit


class GitHubAPIExecutor:
    """Execute GitHub actions via the REST API.

    Requires GITHUB_TOKEN environment variable.
    """

    API_BASE = "https://api.github.com"

    def __init__(
        self,
        token: str | None = None,
        rate_limit: RateLimit | None = None,
    ) -> None:
        self._token = token or os.getenv("GITHUB_TOKEN", "")
        self._client = APIClient(
            base_url=self.API_BASE,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            rate_limit=rate_limit or RateLimit(requests_per_minute=30),
        )

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new GitHub issue."""
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        return await self._client.post(
            f"/repos/{owner}/{repo}/issues", json=payload
        )

    async def add_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> dict[str, Any]:
        """Add a comment to an issue or PR."""
        return await self._client.post(
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
    ) -> dict[str, Any]:
        """List repository issues."""
        return await self._client.get(
            f"/repos/{owner}/{repo}/issues",
            params={"state": state, "per_page": per_page},
        )

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> dict[str, Any]:
        """Create a pull request."""
        return await self._client.post(
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": title,
                "head": head,
                "base": base,
                "body": body,
            },
        )

    async def get_repo_info(
        self, owner: str, repo: str
    ) -> dict[str, Any]:
        """Get repository information."""
        return await self._client.get(f"/repos/{owner}/{repo}")
