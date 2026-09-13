# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for configuration loading."""

from pathlib import Path

import pytest

from smart_automator.config import (
    AppConfig,
    BrowserConfig,
    HumanizerConfig,
    LLMConfig,
    load_config,
    load_platform_config,
)


class TestConfig:
    """Tests for configuration system."""

    def test_default_config(self) -> None:
        config = AppConfig()
        assert config.browser.headless is True
        assert config.humanizer.enabled is True
        assert config.llm.provider == "claude_cli"
        assert config.log_level == "INFO"

    def test_browser_config(self) -> None:
        config = BrowserConfig(
            headless=False,
            slow_mo=100,
            viewport_width=1920,
        )
        assert config.headless is False
        assert config.slow_mo == 100
        assert config.viewport_width == 1920

    def test_humanizer_config(self) -> None:
        config = HumanizerConfig(
            typo_probability=0.05,
            mouse_bezier_steps=30,
        )
        assert config.typo_probability == 0.05
        assert config.mouse_bezier_steps == 30

    def test_load_config_from_yaml(self, tmp_path: Path) -> None:
        yaml_content = """
browser:
  headless: false
  slow_mo: 50
humanizer:
  enabled: false
llm:
  provider: api
  model: claude-sonnet-4-20250514
log_level: DEBUG
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content)

        config = load_config(config_file)
        assert config.browser.headless is False
        assert config.browser.slow_mo == 50
        assert config.humanizer.enabled is False
        assert config.llm.provider == "api"
        assert config.log_level == "DEBUG"

    def test_load_config_missing_file(self) -> None:
        config = load_config(Path("nonexistent.yaml"))
        # Should return defaults
        assert config.browser.headless is True

    def test_load_platform_config(self, tmp_path: Path) -> None:
        yaml_content = """
name: test
base_url: https://test.com
has_api: true
"""
        (tmp_path / "test.yaml").write_text(yaml_content)
        platform = load_platform_config("test", tmp_path)
        assert platform["name"] == "test"
        assert platform["has_api"] is True

    def test_load_platform_config_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_platform_config("nonexistent", tmp_path)
