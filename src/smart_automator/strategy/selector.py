# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Strategy selector: decides API vs UI execution per action."""

from __future__ import annotations

from smart_automator.models import (
    ActionSequence,
    ActionStep,
    ActionType,
    ExecutionStrategy,
)
from smart_automator.strategy.platform_registry import PlatformRegistry


# Actions that can only be done via UI
UI_ONLY_ACTIONS: set[ActionType] = {
    ActionType.CLICK,
    ActionType.SCROLL,
    ActionType.SCREENSHOT,
    ActionType.UPLOAD,
}

# Actions that map cleanly to API calls
API_FRIENDLY_ACTIONS: set[ActionType] = {
    ActionType.API_CALL,
    ActionType.ASSERT,
}


class StrategySelector:
    """Selects execution strategy (API vs UI) based on platform
    capabilities and action requirements.

    Decision logic:
    1. If platform has no API -> always UI
    2. If action is UI-only (click, scroll, screenshot) -> UI
    3. If action is API-friendly and platform has API -> API
    4. If platform prefers API and action supports it -> API
    5. Default -> UI
    """

    def __init__(self, registry: PlatformRegistry) -> None:
        self._registry = registry

    def select(self, sequence: ActionSequence) -> ExecutionStrategy:
        """Select strategy for an entire action sequence.

        Returns HYBRID if some steps need UI and others can use API.
        """
        if not sequence.steps:
            return ExecutionStrategy.UI

        strategies = [
            self._select_for_step(step, sequence.platform)
            for step in sequence.steps
        ]

        unique = set(strategies)
        if len(unique) == 1:
            return unique.pop()
        return ExecutionStrategy.HYBRID

    def _select_for_step(
        self, step: ActionStep, platform: str
    ) -> ExecutionStrategy:
        """Select strategy for a single action step."""
        has_api = self._registry.has_api(platform)
        preferred = self._registry.get_strategy(platform)

        # UI-only actions always go to UI
        if step.action in UI_ONLY_ACTIONS:
            return ExecutionStrategy.UI

        # Explicit API calls go to API if available
        if step.action == ActionType.API_CALL and has_api:
            return ExecutionStrategy.API

        # If platform has API and prefers it, use API for compatible actions
        if has_api and preferred == ExecutionStrategy.API:
            if step.action not in UI_ONLY_ACTIONS:
                return ExecutionStrategy.API

        # Login can go either way - prefer API if available
        if step.action == ActionType.LOGIN and has_api:
            return ExecutionStrategy.API

        return ExecutionStrategy.UI

    def explain(self, sequence: ActionSequence) -> list[dict[str, str]]:
        """Explain strategy decisions for each step in a sequence."""
        explanations = []
        for i, step in enumerate(sequence.steps):
            strategy = self._select_for_step(step, sequence.platform)
            has_api = self._registry.has_api(sequence.platform)

            if step.action in UI_ONLY_ACTIONS:
                reason = f"{step.action.value} requires browser interaction"
            elif strategy == ExecutionStrategy.API:
                reason = f"Platform '{sequence.platform}' has API support"
            else:
                reason = (
                    f"Platform '{sequence.platform}' "
                    f"{'has no API' if not has_api else 'prefers UI'}"
                )

            explanations.append({
                "step": i,
                "action": step.action.value,
                "strategy": strategy.value,
                "reason": reason,
            })
        return explanations
