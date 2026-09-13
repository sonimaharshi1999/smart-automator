# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for strategy selection and platform registry."""

from pathlib import Path

import pytest

from smart_automator.models import (
    ActionSequence,
    ActionStep,
    ActionType,
    ExecutionStrategy,
    PlatformConfig,
    RateLimit,
    Selector,
    SelectorStrategy,
)
from smart_automator.strategy.platform_registry import PlatformRegistry
from smart_automator.strategy.selector import StrategySelector


class TestPlatformRegistry:
    """Tests for PlatformRegistry."""

    def test_register_and_get(self, platform_registry: PlatformRegistry) -> None:
        github = platform_registry.get("github")
        assert github is not None
        assert github.name == "github"
        assert github.has_api is True

    def test_get_nonexistent(self, platform_registry: PlatformRegistry) -> None:
        result = platform_registry.get("nonexistent")
        assert result is None

    def test_has_api(self, platform_registry: PlatformRegistry) -> None:
        assert platform_registry.has_api("github") is True
        assert platform_registry.has_api("linkedin") is False
        assert platform_registry.has_api("unknown") is False

    def test_get_strategy(self, platform_registry: PlatformRegistry) -> None:
        assert platform_registry.get_strategy("github") == ExecutionStrategy.API
        assert platform_registry.get_strategy("linkedin") == ExecutionStrategy.UI
        assert platform_registry.get_strategy("unknown") == ExecutionStrategy.UI

    def test_list_platforms(self, platform_registry: PlatformRegistry) -> None:
        platforms = platform_registry.list_platforms()
        assert "github" in platforms
        assert "linkedin" in platforms
        assert "instagram" in platforms

    def test_load_from_yaml(self, tmp_path: Path) -> None:
        yaml_content = """
name: test_platform
display_name: Test Platform
base_url: https://test.com
has_api: true
api_base_url: https://api.test.com
preferred_strategy: api
rate_limit:
  requests_per_minute: 60
auth:
  method: token
  token_env_var: TEST_TOKEN
"""
        yaml_file = tmp_path / "test_platform.yaml"
        yaml_file.write_text(yaml_content)

        registry = PlatformRegistry(tmp_path)
        platform = registry.get("test_platform")
        assert platform is not None
        assert platform.has_api is True
        assert platform.rate_limit.requests_per_minute == 60


class TestStrategySelector:
    """Tests for StrategySelector."""

    def test_api_sequence_github(self, platform_registry: PlatformRegistry) -> None:
        selector = StrategySelector(platform_registry)
        sequence = ActionSequence(
            name="test",
            platform="github",
            steps=[
                ActionStep(action=ActionType.API_CALL, value="create_issue"),
            ],
        )
        assert selector.select(sequence) == ExecutionStrategy.API

    def test_ui_sequence_linkedin(self, platform_registry: PlatformRegistry) -> None:
        selector = StrategySelector(platform_registry)
        sequence = ActionSequence(
            name="test",
            platform="linkedin",
            steps=[
                ActionStep(action=ActionType.CLICK, selector=Selector(primary="text=Post")),
                ActionStep(action=ActionType.TYPE, selector=Selector(primary="[role=textbox]"), value="Hi"),
            ],
        )
        assert selector.select(sequence) == ExecutionStrategy.UI

    def test_hybrid_sequence(self, platform_registry: PlatformRegistry) -> None:
        selector = StrategySelector(platform_registry)
        # GitHub has API, but CLICK is UI-only
        sequence = ActionSequence(
            name="test",
            platform="github",
            steps=[
                ActionStep(action=ActionType.API_CALL, value="create_issue"),
                ActionStep(action=ActionType.CLICK, selector=Selector(primary="text=View")),
                ActionStep(action=ActionType.SCREENSHOT),
            ],
        )
        assert selector.select(sequence) == ExecutionStrategy.HYBRID

    def test_empty_sequence(self, platform_registry: PlatformRegistry) -> None:
        selector = StrategySelector(platform_registry)
        sequence = ActionSequence(name="test", platform="github", steps=[])
        assert selector.select(sequence) == ExecutionStrategy.UI

    def test_explain(self, platform_registry: PlatformRegistry) -> None:
        selector = StrategySelector(platform_registry)
        sequence = ActionSequence(
            name="test",
            platform="github",
            steps=[
                ActionStep(action=ActionType.API_CALL, value="create_issue"),
                ActionStep(action=ActionType.SCREENSHOT),
            ],
        )
        explanations = selector.explain(sequence)
        assert len(explanations) == 2
        assert explanations[0]["strategy"] == "api"
        assert explanations[1]["strategy"] == "ui"
