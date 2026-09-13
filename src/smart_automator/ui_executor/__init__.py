# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""UI executor: Playwright-based browser automation with AI-powered selectors."""

from smart_automator.ui_executor.action_runner import ActionRunner
from smart_automator.ui_executor.browser import BrowserManager
from smart_automator.ui_executor.screenshot_analyzer import ScreenshotAnalyzer
from smart_automator.ui_executor.selector_engine import SelectorEngine

__all__ = [
    "ActionRunner",
    "BrowserManager",
    "ScreenshotAnalyzer",
    "SelectorEngine",
]
