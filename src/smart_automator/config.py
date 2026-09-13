# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Platform registry and global configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class BrowserConfig:
    """Browser automation settings."""

    headless: bool = True
    slow_mo: int = 0
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str | None = None
    timeout_ms: int = 30000
    screenshot_on_failure: bool = True


@dataclass
class HumanizerConfig:
    """Humanizer behavior settings."""

    enabled: bool = True
    min_delay_ms: int = 100
    max_delay_ms: int = 2000
    typing_speed_cpm: int = 250
    typo_probability: float = 0.03
    mouse_bezier_steps: int = 20
    scroll_step_px: int = 100


@dataclass
class LLMConfig:
    """LLM provider settings."""

    provider: str = "claude_cli"
    model: str = "claude-sonnet-4-20250514"
    api_key: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 2


@dataclass
class SchedulerConfig:
    """Task scheduling settings."""

    max_concurrent: int = 3
    retry_on_failure: bool = True
    retry_delay_seconds: int = 60


@dataclass
class AppConfig:
    """Root application configuration."""

    browser: BrowserConfig = field(default_factory=BrowserConfig)
    humanizer: HumanizerConfig = field(default_factory=HumanizerConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    platforms_dir: Path = field(default_factory=lambda: Path("platforms"))
    workflows_dir: Path = field(default_factory=lambda: Path("workflows"))
    screenshots_dir: Path = field(default_factory=lambda: Path("screenshots"))
    log_level: str = "INFO"


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load configuration from YAML file or return defaults."""
    if config_path and config_path.exists():
        with open(config_path, "r") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return AppConfig(
            browser=BrowserConfig(**data.get("browser", {})),
            humanizer=HumanizerConfig(**data.get("humanizer", {})),
            llm=LLMConfig(**data.get("llm", {})),
            scheduler=SchedulerConfig(**data.get("scheduler", {})),
            platforms_dir=Path(data.get("platforms_dir", "platforms")),
            workflows_dir=Path(data.get("workflows_dir", "workflows")),
            log_level=data.get("log_level", "INFO"),
        )
    return AppConfig()


def load_platform_config(platform_name: str, platforms_dir: Path) -> dict[str, Any]:
    """Load a platform configuration YAML."""
    config_path = platforms_dir / f"{platform_name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Platform config not found: {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f) or {}


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(os.getenv("SMART_AUTOMATOR_ROOT", Path.cwd()))
