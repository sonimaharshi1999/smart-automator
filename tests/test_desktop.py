# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for desktop executor module."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from smart_automator.desktop.executor import (
    DesktopAction,
    DesktopActionType,
    DesktopExecutor,
    DesktopResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_pyautogui() -> MagicMock:
    """Create a comprehensive pyautogui mock."""
    pag = MagicMock()
    pag.FAILSAFE = True
    pag.PAUSE = 0.05
    pos = MagicMock()
    pos.x = 500
    pos.y = 300
    pag.position.return_value = pos
    size = MagicMock()
    size.width = 1920
    size.height = 1080
    pag.size.return_value = size
    return pag


# ===========================================================================
# Enum & Dataclass Tests
# ===========================================================================

class TestDesktopActionType:
    """Tests for DesktopActionType enum."""

    def test_all_action_types(self) -> None:
        expected = {
            "click", "double_click", "right_click", "type_text",
            "hotkey", "move_to", "scroll", "drag", "open_app",
            "switch_window", "wait",
        }
        actual = {a.value for a in DesktopActionType}
        assert actual == expected

    def test_string_enum(self) -> None:
        assert DesktopActionType.CLICK == "click"
        assert isinstance(DesktopActionType.CLICK, str)


class TestDesktopAction:
    """Tests for DesktopAction dataclass."""

    def test_minimal_action(self) -> None:
        a = DesktopAction(action_type=DesktopActionType.CLICK)
        assert a.action_type == DesktopActionType.CLICK
        assert a.x is None
        assert a.y is None
        assert a.text is None
        assert a.humanize is True

    def test_full_action(self) -> None:
        a = DesktopAction(
            action_type=DesktopActionType.DRAG,
            x=10, y=20, end_x=100, end_y=200,
            humanize=False, description="drag action",
        )
        assert a.end_x == 100
        assert a.end_y == 200
        assert a.humanize is False


class TestDesktopResult:
    """Tests for DesktopResult dataclass."""

    def test_success_result(self) -> None:
        r = DesktopResult(action=DesktopActionType.CLICK, success=True, duration_ms=15.5)
        assert r.success is True
        assert r.error is None

    def test_failure_result(self) -> None:
        r = DesktopResult(
            action=DesktopActionType.CLICK, success=False,
            error="element not found",
        )
        assert r.success is False
        assert r.error == "element not found"


# ===========================================================================
# DesktopExecutor Tests
# ===========================================================================

class TestDesktopExecutor:
    """Tests for DesktopExecutor (pyautogui fully mocked)."""

    def test_construction_with_humanize(self) -> None:
        mock_pag = MagicMock()
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            executor = DesktopExecutor(humanize=True)
        assert executor._humanize is True
        assert executor._mouse is not None
        assert executor._delay is not None
        assert executor._typer is not None

    def test_construction_without_humanize(self) -> None:
        mock_pag = MagicMock()
        with patch.dict("sys.modules", {"pyautogui": mock_pag}):
            executor = DesktopExecutor(humanize=False)
        assert executor._mouse is None
        assert executor._delay is None
        assert executor._typer is None

    def test_is_available_true(self) -> None:
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = _make_mock_pyautogui()
        assert executor.is_available() is True

    def test_is_available_false(self) -> None:
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = None
        assert executor.is_available() is False

    def test_execute_without_pyautogui_fails(self) -> None:
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = None
        executor._humanize = False
        action = DesktopAction(action_type=DesktopActionType.CLICK, x=100, y=200)
        result = executor.execute(action)
        assert result.success is False
        assert "not installed" in (result.error or "")

    def test_execute_click(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._mouse = None
        executor._delay = None

        action = DesktopAction(action_type=DesktopActionType.CLICK, x=100, y=200, humanize=False)
        result = executor.execute(action)

        assert result.success is True
        assert result.action == DesktopActionType.CLICK
        pag.moveTo.assert_called_with(100, 200)
        pag.click.assert_called_once()

    def test_execute_double_click(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._mouse = None

        action = DesktopAction(action_type=DesktopActionType.DOUBLE_CLICK, x=50, y=60, humanize=False)
        result = executor.execute(action)

        assert result.success is True
        pag.doubleClick.assert_called_once()

    def test_execute_right_click(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._mouse = None

        action = DesktopAction(action_type=DesktopActionType.RIGHT_CLICK, x=10, y=20, humanize=False)
        result = executor.execute(action)

        assert result.success is True
        pag.rightClick.assert_called_once()

    def test_execute_type_text_no_humanize(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._typer = None

        action = DesktopAction(action_type=DesktopActionType.TYPE_TEXT, text="hello", humanize=False)
        result = executor.execute(action)

        assert result.success is True
        pag.write.assert_called_once_with("hello", interval=0.02)

    def test_execute_hotkey(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False

        action = DesktopAction(action_type=DesktopActionType.HOTKEY, keys=["ctrl", "c"])
        result = executor.execute(action)

        assert result.success is True
        pag.hotkey.assert_called_once_with("ctrl", "c")

    def test_execute_move_to(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._mouse = None

        action = DesktopAction(action_type=DesktopActionType.MOVE_TO, x=300, y=400, humanize=False)
        result = executor.execute(action)

        assert result.success is True
        pag.moveTo.assert_called_with(300, 400)

    def test_execute_scroll(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False

        action = DesktopAction(action_type=DesktopActionType.SCROLL, scroll_amount=5, x=100, y=200)
        result = executor.execute(action)

        assert result.success is True
        pag.moveTo.assert_called_with(100, 200)
        pag.scroll.assert_called_once_with(5)

    def test_execute_drag(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False

        action = DesktopAction(
            action_type=DesktopActionType.DRAG,
            x=10, y=20, end_x=110, end_y=120,
        )
        result = executor.execute(action)

        assert result.success is True
        pag.moveTo.assert_called_with(10, 20)
        pag.drag.assert_called_once_with(100, 100, duration=0.5)

    @patch("smart_automator.desktop.executor.subprocess.Popen")
    @patch("smart_automator.desktop.executor.platform.system", return_value="Windows")
    @patch("smart_automator.desktop.executor.time.sleep")
    def test_execute_open_app(
        self, mock_sleep: MagicMock, mock_platform: MagicMock, mock_popen: MagicMock,
    ) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False

        action = DesktopAction(action_type=DesktopActionType.OPEN_APP, app_name="notepad")
        result = executor.execute(action)

        assert result.success is True
        mock_popen.assert_called_once()

    @patch("smart_automator.desktop.executor.time.sleep")
    def test_execute_wait(self, mock_sleep: MagicMock) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False

        action = DesktopAction(action_type=DesktopActionType.WAIT, duration_s=1.5)
        result = executor.execute(action)

        assert result.success is True
        mock_sleep.assert_called_once_with(1.5)

    def test_execute_records_duration(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._mouse = None

        action = DesktopAction(action_type=DesktopActionType.CLICK, x=0, y=0, humanize=False)
        result = executor.execute(action)

        assert result.duration_ms >= 0

    def test_execute_handles_exception(self) -> None:
        pag = _make_mock_pyautogui()
        pag.click.side_effect = RuntimeError("display error")
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._mouse = None

        action = DesktopAction(action_type=DesktopActionType.CLICK, x=0, y=0, humanize=False)
        result = executor.execute(action)

        assert result.success is False
        assert "display error" in (result.error or "")

    def test_execute_sequence_all_succeed(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._mouse = None
        executor._delay = None
        executor._typer = None

        actions = [
            DesktopAction(action_type=DesktopActionType.CLICK, x=10, y=20, humanize=False),
            DesktopAction(action_type=DesktopActionType.CLICK, x=30, y=40, humanize=False),
        ]
        results = executor.execute_sequence(actions)

        assert len(results) == 2
        assert all(r.success for r in results)

    def test_execute_sequence_stops_on_failure(self) -> None:
        pag = _make_mock_pyautogui()
        pag.click.side_effect = [None, RuntimeError("fail")]
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._mouse = None
        executor._delay = None

        actions = [
            DesktopAction(action_type=DesktopActionType.CLICK, x=1, y=1, humanize=False),
            DesktopAction(action_type=DesktopActionType.CLICK, x=2, y=2, humanize=False),
            DesktopAction(action_type=DesktopActionType.CLICK, x=3, y=3, humanize=False),
        ]
        results = executor.execute_sequence(actions)

        assert len(results) == 2  # Stops after second failure
        assert results[0].success is True
        assert results[1].success is False

    def test_get_cursor_position(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag

        pos = executor.get_cursor_position()
        assert pos == (500, 300)

    def test_get_cursor_position_no_pyautogui(self) -> None:
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = None
        assert executor.get_cursor_position() == (0, 0)

    def test_get_screen_size(self) -> None:
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag

        size = executor.get_screen_size()
        assert size == (1920, 1080)

    def test_get_screen_size_no_pyautogui(self) -> None:
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = None
        assert executor.get_screen_size() == (1920, 1080)

    def test_execute_empty_text_type(self) -> None:
        """Typing empty text should still succeed."""
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False
        executor._typer = None

        action = DesktopAction(action_type=DesktopActionType.TYPE_TEXT, text="", humanize=False)
        result = executor.execute(action)
        assert result.success is True

    def test_execute_hotkey_empty_keys(self) -> None:
        """Hotkey with empty list should still attempt the call."""
        pag = _make_mock_pyautogui()
        executor = DesktopExecutor.__new__(DesktopExecutor)
        executor._pyautogui = pag
        executor._humanize = False

        action = DesktopAction(action_type=DesktopActionType.HOTKEY, keys=[])
        result = executor.execute(action)
        assert result.success is True
        pag.hotkey.assert_called_once_with()
