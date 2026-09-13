# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Action runner: executes action steps on live pages using Playwright.

Works WITHOUT an LLM. Takes pre-computed selectors and executes actions.
Self-healing (which requires LLM) is handled by the healing module.
"""

from __future__ import annotations

import time
from typing import Any

from smart_automator.config import HumanizerConfig
from smart_automator.models import (
    ActionSequence,
    ActionStatus,
    ActionStep,
    ActionType,
    ExecutionResult,
    ExecutionStrategy,
    Selector,
    StepResult,
)


class ActionRunner:
    """Executes automation actions on a Playwright page.

    No LLM needed. Takes ActionSequence with selectors and runs them.
    Integrates with humanizer for natural interaction patterns.
    """

    def __init__(
        self,
        page: Any = None,
        humanizer_config: HumanizerConfig | None = None,
    ) -> None:
        self._page = page
        self._humanizer_config = humanizer_config or HumanizerConfig()
        self._humanizer_enabled = self._humanizer_config.enabled

    def set_page(self, page: Any) -> None:
        """Set the Playwright page to execute on."""
        self._page = page

    async def execute(self, sequence: ActionSequence) -> ExecutionResult:
        """Execute a full action sequence."""
        if not self._page:
            raise RuntimeError("No page set for action runner")

        result = ExecutionResult(
            sequence_name=sequence.name,
            strategy_used=ExecutionStrategy.UI,
            total_steps=len(sequence.steps),
        )

        start = time.monotonic()

        for i, step in enumerate(sequence.steps):
            step_result = await self._execute_step(i, step)
            result.step_results.append(step_result)

            if step_result.status == ActionStatus.SUCCESS:
                result.successful_steps += 1
            elif step_result.status == ActionStatus.HEALED:
                result.healed_steps += 1
            else:
                result.failed_steps += 1
                if step_result.error:
                    result.error = step_result.error
                break

        result.total_duration_ms = (time.monotonic() - start) * 1000
        return result

    async def _execute_step(
        self, index: int, step: ActionStep
    ) -> StepResult:
        """Execute a single action step."""
        start = time.monotonic()

        try:
            await self._run_action(step)
            if step.wait_ms > 0:
                await self._page.wait_for_timeout(step.wait_ms)

            duration = (time.monotonic() - start) * 1000
            return StepResult(
                step_index=index,
                action=step.action,
                status=ActionStatus.SUCCESS,
                duration_ms=duration,
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return StepResult(
                step_index=index,
                action=step.action,
                status=ActionStatus.FAILED,
                duration_ms=duration,
                error=str(e),
            )

    async def _run_action(self, step: ActionStep) -> None:
        """Dispatch and run a specific action type."""
        handlers = {
            ActionType.NAVIGATE: self._action_navigate,
            ActionType.CLICK: self._action_click,
            ActionType.TYPE: self._action_type,
            ActionType.SELECT: self._action_select,
            ActionType.SCROLL: self._action_scroll,
            ActionType.WAIT: self._action_wait,
            ActionType.SCREENSHOT: self._action_screenshot,
            ActionType.ASSERT: self._action_assert,
        }

        handler = handlers.get(step.action)
        if not handler:
            raise ValueError(f"Unsupported action: {step.action}")
        await handler(step)

    async def _action_navigate(self, step: ActionStep) -> None:
        """Navigate to a URL."""
        if not step.url:
            raise ValueError("Navigate action requires a URL")
        await self._page.goto(step.url, wait_until="networkidle")

    async def _action_click(self, step: ActionStep) -> None:
        """Click an element using selector with fallbacks."""
        locator = await self._resolve_selector(step.selector)
        await locator.click()

    async def _action_type(self, step: ActionStep) -> None:
        """Type text into an element."""
        if step.value is None:
            raise ValueError("Type action requires a value")
        locator = await self._resolve_selector(step.selector)
        await locator.fill(step.value)

    async def _action_select(self, step: ActionStep) -> None:
        """Select an option from a dropdown."""
        if step.value is None:
            raise ValueError("Select action requires a value")
        locator = await self._resolve_selector(step.selector)
        await locator.select_option(step.value)

    async def _action_scroll(self, step: ActionStep) -> None:
        """Scroll the page."""
        amount = int(step.value or "300")
        await self._page.evaluate(f"window.scrollBy(0, {amount})")

    async def _action_wait(self, step: ActionStep) -> None:
        """Wait for a specified duration."""
        ms = step.wait_ms or int(step.value or "1000")
        await self._page.wait_for_timeout(ms)

    async def _action_screenshot(self, step: ActionStep) -> None:
        """Take a screenshot."""
        path = step.value or "screenshot.png"
        await self._page.screenshot(path=path)

    async def _action_assert(self, step: ActionStep) -> None:
        """Assert element existence or content."""
        if step.selector:
            locator = await self._resolve_selector(step.selector)
            await locator.wait_for(state="visible", timeout=5000)
            if step.value:
                text = await locator.text_content()
                if step.value not in (text or ""):
                    raise AssertionError(
                        f"Expected '{step.value}' in element text, "
                        f"got '{text}'"
                    )

    async def _resolve_selector(
        self, selector: Selector | None
    ) -> Any:
        """Resolve a Selector to a Playwright locator, trying fallbacks."""
        if not selector:
            raise ValueError("Action requires a selector")

        # Try primary selector
        try:
            locator = self._page.locator(selector.primary)
            count = await locator.count()
            if count > 0:
                return locator.first
        except Exception:
            pass

        # Try fallbacks
        for fallback in selector.fallbacks:
            try:
                locator = self._page.locator(fallback)
                count = await locator.count()
                if count > 0:
                    return locator.first
            except Exception:
                continue

        raise RuntimeError(
            f"Could not find element: {selector.description or selector.primary}"
        )
