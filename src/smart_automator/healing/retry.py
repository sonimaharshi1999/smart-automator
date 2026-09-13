# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Self-healing retry: on selector failure, AI finds new selectors.

Flow: selector fails -> take screenshot -> AI analyzes what changed
-> generates new selector -> retry with new selector.
"""

from __future__ import annotations

import time
from typing import Any

from smart_automator.models import (
    ActionStatus,
    ActionStep,
    Selector,
    SelectorStrategy,
    StepResult,
)


class SelfHealingRetry:
    """Retry failed actions by healing broken selectors.

    When a selector fails:
    1. Take a screenshot of the current page state
    2. Use the selector engine to find the element again
    3. Retry with the new selector
    4. Log the healing for future reference
    """

    def __init__(
        self,
        max_retries: int = 3,
        selector_engine: Any = None,
        llm_provider: Any = None,
    ) -> None:
        self._max_retries = max_retries
        self._selector_engine = selector_engine
        self._llm = llm_provider
        self._healing_log: list[dict[str, str]] = []

    async def retry_with_healing(
        self,
        page: Any,
        step: ActionStep,
        original_error: str,
    ) -> StepResult:
        """Attempt to heal a failed action and retry.

        Args:
            page: Playwright page object
            step: The failed action step
            original_error: The original error message

        Returns:
            StepResult with healed status if successful
        """
        for attempt in range(self._max_retries):
            try:
                new_selector = await self._heal_selector(
                    page, step, original_error
                )
                if not new_selector:
                    continue

                # Create a new step with the healed selector
                healed_step = step.model_copy()
                healed_step.selector = new_selector

                # Try the action with the new selector
                start = time.monotonic()
                await self._execute_with_selector(page, healed_step)
                duration = (time.monotonic() - start) * 1000

                # Log the healing
                self._healing_log.append({
                    "original": step.selector.primary if step.selector else "",
                    "healed": new_selector.primary,
                    "attempt": str(attempt + 1),
                })

                return StepResult(
                    step_index=0,
                    action=step.action,
                    status=ActionStatus.HEALED,
                    duration_ms=duration,
                    healed_selector=new_selector.primary,
                )

            except Exception:
                continue

        return StepResult(
            step_index=0,
            action=step.action,
            status=ActionStatus.FAILED,
            error=f"Healing failed after {self._max_retries} attempts: {original_error}",
        )

    async def _heal_selector(
        self,
        page: Any,
        step: ActionStep,
        error: str,
    ) -> Selector | None:
        """Generate a new selector by analyzing the current page."""
        if not step.selector:
            return None

        description = step.selector.description or step.description

        # Strategy 1: Use selector engine if available
        if self._selector_engine:
            try:
                self._selector_engine.set_page(page)
                return await self._selector_engine.find_element(description)
            except Exception:
                pass

        # Strategy 2: Try broader selector patterns
        return self._broaden_selector(step.selector)

    @staticmethod
    def _broaden_selector(original: Selector) -> Selector:
        """Broaden a selector to be less specific.

        Tries progressively less specific patterns:
        exact text -> contains text -> role -> tag
        """
        primary = original.primary

        fallbacks: list[str] = []

        # If it's an exact text match, try contains
        if primary.startswith("text="):
            text = primary[5:]
            fallbacks.append(f"text=/{text}/i")
            fallbacks.append(f"//*[contains(text(), '{text}')]")

        # If it's an aria-label, try partial match
        if "aria-label=" in primary:
            import re
            match = re.search(r'aria-label="([^"]+)"', primary)
            if match:
                label = match.group(1)
                fallbacks.append(f"//*[contains(@aria-label, '{label}')]")

        if not fallbacks:
            return original

        return Selector(
            primary=fallbacks[0],
            strategy=SelectorStrategy.XPATH,
            fallbacks=fallbacks[1:] + original.fallbacks,
            description=original.description,
        )

    @staticmethod
    async def _execute_with_selector(page: Any, step: ActionStep) -> None:
        """Execute an action with a given selector on a page."""
        if not step.selector:
            raise ValueError("Step has no selector")

        locator = page.locator(step.selector.primary)
        await locator.wait_for(state="visible", timeout=5000)

        from smart_automator.models import ActionType

        if step.action == ActionType.CLICK:
            await locator.click()
        elif step.action == ActionType.TYPE:
            await locator.fill(step.value or "")
        elif step.action == ActionType.SELECT:
            await locator.select_option(step.value or "")

    @property
    def healing_log(self) -> list[dict[str, str]]:
        """Get the log of all healing operations."""
        return list(self._healing_log)
