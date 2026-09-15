# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Desktop-level action executor using pyautogui for OS-native mouse/keyboard control."""

from __future__ import annotations

import platform
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from smart_automator.humanizer.mouse import HumanMouse
from smart_automator.humanizer.delays import HumanDelay
from smart_automator.humanizer.typing import HumanTyping


class DesktopActionType(str, Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    MOVE_TO = "move_to"
    SCROLL = "scroll"
    DRAG = "drag"
    OPEN_APP = "open_app"
    SWITCH_WINDOW = "switch_window"
    WAIT = "wait"


@dataclass
class DesktopAction:
    """A desktop-level action to perform."""
    action_type: DesktopActionType
    x: int | None = None
    y: int | None = None
    text: str | None = None
    keys: list[str] | None = None
    end_x: int | None = None
    end_y: int | None = None
    scroll_amount: int | None = None
    app_name: str | None = None
    duration_s: float = 0.0
    humanize: bool = True
    description: str = ""


@dataclass
class DesktopResult:
    """Result of a desktop action execution."""
    action: DesktopActionType
    success: bool
    duration_ms: float = 0.0
    error: str | None = None
    screenshot_after: bytes | None = None


class DesktopExecutor:
    """Execute desktop-level actions (clicks, typing, hotkeys, app launches).

    Uses pyautogui for cross-platform mouse/keyboard control.
    Integrates humanizer for natural movement patterns.
    """

    def __init__(
        self,
        humanize: bool = True,
        failsafe: bool = True,
        mouse_steps: int = 20,
    ) -> None:
        self._humanize = humanize
        self._mouse = HumanMouse(steps=mouse_steps) if humanize else None
        self._delay = HumanDelay() if humanize else None
        self._typer = HumanTyping() if humanize else None
        self._failsafe = failsafe
        self._pyautogui: Any = None
        self._init_pyautogui()

    def _init_pyautogui(self) -> None:
        """Initialize pyautogui with safety settings."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = self._failsafe
            pyautogui.PAUSE = 0.05
            self._pyautogui = pyautogui
        except ImportError:
            self._pyautogui = None

    def is_available(self) -> bool:
        """Check if pyautogui is available."""
        return self._pyautogui is not None

    def execute(self, action: DesktopAction) -> DesktopResult:
        """Execute a single desktop action."""
        if not self._pyautogui:
            return DesktopResult(
                action=action.action_type, success=False,
                error="pyautogui not installed",
            )

        start = time.perf_counter()

        try:
            if action.action_type == DesktopActionType.CLICK:
                self._do_click(action.x or 0, action.y or 0, action.humanize)
            elif action.action_type == DesktopActionType.DOUBLE_CLICK:
                self._do_double_click(action.x or 0, action.y or 0, action.humanize)
            elif action.action_type == DesktopActionType.RIGHT_CLICK:
                self._do_right_click(action.x or 0, action.y or 0, action.humanize)
            elif action.action_type == DesktopActionType.TYPE_TEXT:
                self._do_type(action.text or "", action.humanize)
            elif action.action_type == DesktopActionType.HOTKEY:
                self._do_hotkey(action.keys or [])
            elif action.action_type == DesktopActionType.MOVE_TO:
                self._do_move(action.x or 0, action.y or 0, action.humanize)
            elif action.action_type == DesktopActionType.SCROLL:
                self._do_scroll(action.scroll_amount or 0, action.x, action.y)
            elif action.action_type == DesktopActionType.DRAG:
                self._do_drag(
                    action.x or 0, action.y or 0,
                    action.end_x or 0, action.end_y or 0,
                )
            elif action.action_type == DesktopActionType.OPEN_APP:
                self._do_open_app(action.app_name or "")
            elif action.action_type == DesktopActionType.SWITCH_WINDOW:
                self._do_switch_window(action.text or "")
            elif action.action_type == DesktopActionType.WAIT:
                time.sleep(action.duration_s)

            elapsed = (time.perf_counter() - start) * 1000
            return DesktopResult(
                action=action.action_type, success=True, duration_ms=elapsed,
            )

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return DesktopResult(
                action=action.action_type, success=False,
                duration_ms=elapsed, error=str(e),
            )

    def execute_sequence(self, actions: list[DesktopAction]) -> list[DesktopResult]:
        """Execute a sequence of desktop actions."""
        results: list[DesktopResult] = []
        for action in actions:
            result = self.execute(action)
            results.append(result)
            if not result.success:
                break
            if self._humanize and self._delay:
                time.sleep(self._delay.get_delay_seconds())
        return results

    def _do_click(self, x: int, y: int, humanize: bool) -> None:
        """Move to position and click."""
        self._do_move(x, y, humanize)
        self._pyautogui.click()

    def _do_double_click(self, x: int, y: int, humanize: bool) -> None:
        self._do_move(x, y, humanize)
        self._pyautogui.doubleClick()

    def _do_right_click(self, x: int, y: int, humanize: bool) -> None:
        self._do_move(x, y, humanize)
        self._pyautogui.rightClick()

    def _do_move(self, x: int, y: int, humanize: bool) -> None:
        """Move mouse to position, optionally with Bezier path."""
        if humanize and self._mouse:
            current = self._pyautogui.position()
            path = self._mouse.generate_path(
                current.x, current.y, float(x), float(y),
            )
            timings = self._mouse.generate_timing(len(path))
            for (px, py), ms in zip(path, timings):
                self._pyautogui.moveTo(int(px), int(py))
                time.sleep(ms / 1000)
        else:
            self._pyautogui.moveTo(x, y)

    def _do_type(self, text: str, humanize: bool) -> None:
        """Type text with optional humanized delays."""
        if humanize and self._typer:
            from smart_automator.humanizer.typing import KeyEvent
            actions = self._typer.generate_typing_sequence(text)
            for action in actions:
                if action.event == KeyEvent.PRESS:
                    self._pyautogui.write(action.char, interval=0)
                elif action.event == KeyEvent.BACKSPACE:
                    self._pyautogui.press("backspace")
                time.sleep(action.delay_ms / 1000)
        else:
            self._pyautogui.write(text, interval=0.02)

    def _do_hotkey(self, keys: list[str]) -> None:
        """Press a key combination."""
        self._pyautogui.hotkey(*keys)

    def _do_scroll(self, amount: int, x: int | None, y: int | None) -> None:
        """Scroll at position."""
        if x is not None and y is not None:
            self._pyautogui.moveTo(x, y)
        self._pyautogui.scroll(amount)

    def _do_drag(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Drag from one position to another."""
        self._pyautogui.moveTo(x1, y1)
        self._pyautogui.drag(x2 - x1, y2 - y1, duration=0.5)

    def _do_open_app(self, app_name: str) -> None:
        """Open an application by name."""
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["start", "", app_name], shell=True)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", app_name])
        elif system == "Linux":
            subprocess.Popen([app_name])
        time.sleep(1.0)

    def _do_switch_window(self, title: str) -> None:
        """Switch to a window by title (best-effort)."""
        system = platform.system()
        if system == "Windows":
            try:
                import pygetwindow as gw
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    windows[0].activate()
            except ImportError:
                self._pyautogui.hotkey("alt", "tab")
        elif system == "Darwin":
            subprocess.run(
                ["osascript", "-e", f'tell application "{title}" to activate'],
                timeout=5,
            )
        else:
            self._pyautogui.hotkey("alt", "tab")

    def get_cursor_position(self) -> tuple[int, int]:
        """Get current cursor position."""
        if self._pyautogui:
            pos = self._pyautogui.position()
            return (pos.x, pos.y)
        return (0, 0)

    def get_screen_size(self) -> tuple[int, int]:
        """Get screen resolution."""
        if self._pyautogui:
            size = self._pyautogui.size()
            return (size.width, size.height)
        return (1920, 1080)
