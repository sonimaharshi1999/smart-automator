# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Platform registry: loads and manages platform configurations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from smart_automator.models import (
    AuthConfig,
    ExecutionStrategy,
    PlatformConfig,
    RateLimit,
)


class PlatformRegistry:
    """Registry of known platforms and their capabilities.

    Loads platform configs from YAML files and provides lookup
    for strategy selection.
    """

    def __init__(self, platforms_dir: Path | None = None) -> None:
        self._platforms: dict[str, PlatformConfig] = {}
        if platforms_dir and platforms_dir.exists():
            self._load_all(platforms_dir)

    def _load_all(self, platforms_dir: Path) -> None:
        """Load all platform YAML configs from a directory."""
        for yaml_file in platforms_dir.glob("*.yaml"):
            if yaml_file.stem == "custom_template":
                continue
            try:
                config = self._parse_yaml(yaml_file)
                self._platforms[config.name] = config
            except Exception:
                continue

    def _parse_yaml(self, path: Path) -> PlatformConfig:
        """Parse a platform YAML file into a PlatformConfig."""
        with open(path, "r") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        rate_limit_data = data.get("rate_limit", {})
        rate_limit = RateLimit(**rate_limit_data) if rate_limit_data else RateLimit()

        auth_data = data.get("auth")
        auth = AuthConfig(**auth_data) if auth_data else None

        strategy_str = data.get("preferred_strategy", "ui")
        strategy = ExecutionStrategy(strategy_str)

        return PlatformConfig(
            name=data.get("name", path.stem),
            display_name=data.get("display_name", data.get("name", path.stem)),
            base_url=data.get("base_url", ""),
            has_api=data.get("has_api", False),
            api_base_url=data.get("api_base_url"),
            api_version=data.get("api_version"),
            preferred_strategy=strategy,
            rate_limit=rate_limit,
            auth=auth,
            selectors_hint=data.get("selectors_hint", {}),
            notes=data.get("notes", ""),
        )

    def register(self, config: PlatformConfig) -> None:
        """Register a platform configuration."""
        self._platforms[config.name] = config

    def get(self, name: str) -> PlatformConfig | None:
        """Get a platform config by name."""
        return self._platforms.get(name)

    def has_api(self, name: str) -> bool:
        """Check if a platform has API support."""
        platform = self._platforms.get(name)
        return platform.has_api if platform else False

    def get_strategy(self, name: str) -> ExecutionStrategy:
        """Get the preferred execution strategy for a platform."""
        platform = self._platforms.get(name)
        if not platform:
            return ExecutionStrategy.UI
        return platform.preferred_strategy

    def list_platforms(self) -> list[str]:
        """List all registered platform names."""
        return list(self._platforms.keys())

    def get_all(self) -> dict[str, PlatformConfig]:
        """Get all platform configurations."""
        return dict(self._platforms)
