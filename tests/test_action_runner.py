# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for the action runner (UI execution)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from smart_automator.models import (
    ActionSequence,
    ActionStatus,
    ActionStep,
    ActionType,
    ExecutionStrategy,
    Selector,
    SelectorStrategy,
)
from smart_automator.ui_executor.action_runner import ActionRunner


class TestActionRunner:
    """Tests for ActionRunner using mock Playwright page."""

    @pytest.mark.asyncio
    async def test_execute_navigate(self, mock_page: AsyncMock) -> None:
        runner = ActionRunner(page=mock_page)
        sequence = ActionSequence(
            name="test",
            platform="test",
            steps=[
                ActionStep(
                    action=ActionType.NAVIGATE,
                    url="https://example.com",
                ),
            ],
        )
        result = await runner.execute(sequence)
        assert result.successful_steps == 1
        assert result.success is True
        mock_page.goto.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_click(self, mock_page: AsyncMock) -> None:
        runner = ActionRunner(page=mock_page)
        sequence = ActionSequence(
            name="test",
            platform="test",
            steps=[
                ActionStep(
                    action=ActionType.CLICK,
                    selector=Selector(primary='[aria-label="Submit"]'),
                ),
            ],
        )
        result = await runner.execute(sequence)
        assert result.successful_steps == 1

    @pytest.mark.asyncio
    async def test_execute_type(self, mock_page: AsyncMock) -> None:
        runner = ActionRunner(page=mock_page)
        sequence = ActionSequence(
            name="test",
            platform="test",
            steps=[
                ActionStep(
                    action=ActionType.TYPE,
                    selector=Selector(primary='[role="textbox"]'),
                    value="Hello World",
                ),
            ],
        )
        result = await runner.execute(sequence)
        assert result.successful_steps == 1

    @pytest.mark.asyncio
    async def test_execute_with_wait(self, mock_page: AsyncMock) -> None:
        runner = ActionRunner(page=mock_page)
        sequence = ActionSequence(
            name="test",
            platform="test",
            steps=[
                ActionStep(
                    action=ActionType.CLICK,
                    selector=Selector(primary="text=Button"),
                    wait_ms=500,
                ),
            ],
        )
        result = await runner.execute(sequence)
        assert result.successful_steps == 1
        mock_page.wait_for_timeout.assert_awaited()

    @pytest.mark.asyncio
    async def test_execute_failure(self, mock_page: AsyncMock) -> None:
        # Make locator raise an error
        locator = MagicMock()
        locator.count = AsyncMock(return_value=0)
        locator.first = locator
        mock_page.locator = MagicMock(return_value=locator)

        runner = ActionRunner(page=mock_page)
        sequence = ActionSequence(
            name="test",
            platform="test",
            steps=[
                ActionStep(
                    action=ActionType.CLICK,
                    selector=Selector(primary="text=Nonexistent"),
                ),
            ],
        )
        result = await runner.execute(sequence)
        assert result.failed_steps == 1
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_multi_step(self, mock_page: AsyncMock) -> None:
        runner = ActionRunner(page=mock_page)
        sequence = ActionSequence(
            name="test",
            platform="test",
            steps=[
                ActionStep(action=ActionType.NAVIGATE, url="https://example.com"),
                ActionStep(
                    action=ActionType.CLICK,
                    selector=Selector(primary='[aria-label="Login"]'),
                ),
                ActionStep(
                    action=ActionType.TYPE,
                    selector=Selector(primary='[name="email"]'),
                    value="test@example.com",
                ),
            ],
        )
        result = await runner.execute(sequence)
        assert result.total_steps == 3
        assert result.successful_steps == 3
        assert result.total_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_no_page_error(self) -> None:
        runner = ActionRunner()
        sequence = ActionSequence(name="test", platform="test", steps=[])
        with pytest.raises(RuntimeError, match="No page"):
            await runner.execute(
                ActionSequence(
                    name="test",
                    platform="test",
                    steps=[ActionStep(action=ActionType.NAVIGATE, url="https://x.com")],
                )
            )

    @pytest.mark.asyncio
    async def test_scroll_action(self, mock_page: AsyncMock) -> None:
        runner = ActionRunner(page=mock_page)
        sequence = ActionSequence(
            name="test",
            platform="test",
            steps=[
                ActionStep(action=ActionType.SCROLL, value="500"),
            ],
        )
        result = await runner.execute(sequence)
        assert result.successful_steps == 1
        mock_page.evaluate.assert_awaited()
