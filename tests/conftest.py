# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Shared test fixtures and mock factories."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from smart_automator.config import AppConfig, BrowserConfig, HumanizerConfig
from smart_automator.llm.base import LLMProvider
from smart_automator.models import (
    ActionSequence,
    ActionStep,
    ActionType,
    ExecutionStrategy,
    GenerationMode,
    PlatformConfig,
    RateLimit,
    Selector,
    SelectorStrategy,
)
from smart_automator.strategy.platform_registry import PlatformRegistry


# --- Mock LLM Provider ---

class MockLLMProvider(LLMProvider):
    """Mock LLM that returns predictable responses."""

    def __init__(self, response: str = "mock response") -> None:
        self._response = response
        self._calls: list[dict[str, Any]] = []

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        image_path: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        self._calls.append({
            "prompt": prompt,
            "system_prompt": system_prompt,
            "image_path": image_path,
        })
        return self._response

    def is_available(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return "Mock LLM"


# --- Fixtures ---

@pytest.fixture
def app_config() -> AppConfig:
    """Default application config for tests."""
    return AppConfig(
        browser=BrowserConfig(headless=True, timeout_ms=5000),
        humanizer=HumanizerConfig(enabled=False),
    )


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    """Mock LLM provider with default response."""
    return MockLLMProvider()


@pytest.fixture
def mock_llm_with_steps() -> MockLLMProvider:
    """Mock LLM that returns valid action steps JSON."""
    import json
    steps = [
        {
            "action": "navigate",
            "url": "https://linkedin.com/feed",
            "description": "Go to LinkedIn feed",
        },
        {
            "action": "click",
            "selector": {
                "primary": '[aria-label="Start a post"]',
                "strategy": "aria-label",
                "description": "Post button",
            },
            "wait_ms": 1000,
            "description": "Click post button",
        },
        {
            "action": "type",
            "selector": {
                "primary": '[role="textbox"]',
                "strategy": "role",
                "description": "Post text area",
            },
            "value": "Hello World",
            "description": "Type post content",
        },
    ]
    return MockLLMProvider(response=json.dumps(steps))


@pytest.fixture
def platform_registry(tmp_path: Path) -> PlatformRegistry:
    """Platform registry with test configs."""
    registry = PlatformRegistry()

    registry.register(PlatformConfig(
        name="github",
        display_name="GitHub",
        base_url="https://github.com",
        has_api=True,
        api_base_url="https://api.github.com",
        preferred_strategy=ExecutionStrategy.API,
        rate_limit=RateLimit(requests_per_minute=30),
    ))

    registry.register(PlatformConfig(
        name="linkedin",
        display_name="LinkedIn",
        base_url="https://www.linkedin.com",
        has_api=False,
        preferred_strategy=ExecutionStrategy.UI,
    ))

    registry.register(PlatformConfig(
        name="instagram",
        display_name="Instagram",
        base_url="https://www.instagram.com",
        has_api=True,
        preferred_strategy=ExecutionStrategy.API,
    ))

    return registry


@pytest.fixture
def sample_ui_sequence() -> ActionSequence:
    """Sample UI action sequence for testing."""
    return ActionSequence(
        name="test_linkedin_post",
        description="Post to LinkedIn",
        platform="linkedin",
        steps=[
            ActionStep(
                action=ActionType.NAVIGATE,
                url="https://www.linkedin.com/feed",
                description="Go to feed",
            ),
            ActionStep(
                action=ActionType.CLICK,
                selector=Selector(
                    primary='[aria-label="Start a post"]',
                    strategy=SelectorStrategy.ARIA_LABEL,
                    description="Post button",
                ),
                wait_ms=1000,
                description="Click post button",
            ),
            ActionStep(
                action=ActionType.TYPE,
                selector=Selector(
                    primary='[role="textbox"]',
                    strategy=SelectorStrategy.ROLE,
                    description="Text editor",
                ),
                value="Hello World",
                description="Type content",
            ),
        ],
        strategy=ExecutionStrategy.UI,
    )


@pytest.fixture
def sample_api_sequence() -> ActionSequence:
    """Sample API action sequence for testing."""
    return ActionSequence(
        name="test_github_issue",
        description="Create GitHub issue",
        platform="github",
        steps=[
            ActionStep(
                action=ActionType.API_CALL,
                value="create_issue",
                metadata={"title": "Test Issue", "body": "Test body"},
                description="Create issue via API",
            ),
        ],
        strategy=ExecutionStrategy.API,
    )


@pytest.fixture
def mock_page() -> AsyncMock:
    """Mock Playwright page object."""
    page = AsyncMock()

    # Mock locator chain
    locator = AsyncMock()
    locator.count = AsyncMock(return_value=1)
    locator.first = locator
    locator.click = AsyncMock()
    locator.fill = AsyncMock()
    locator.select_option = AsyncMock()
    locator.text_content = AsyncMock(return_value="Test Content")
    locator.wait_for = AsyncMock()

    page.locator = MagicMock(return_value=locator)
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.evaluate = AsyncMock(return_value=[])
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    page.set_default_timeout = MagicMock()

    return page
