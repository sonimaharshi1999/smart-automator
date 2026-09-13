# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""API executor: REST/GraphQL client for platforms with APIs."""

from smart_automator.api_executor.base import APIClient
from smart_automator.api_executor.github_api import GitHubAPIExecutor
from smart_automator.api_executor.mock_instagram_api import MockInstagramAPIExecutor

__all__ = ["APIClient", "GitHubAPIExecutor", "MockInstagramAPIExecutor"]
