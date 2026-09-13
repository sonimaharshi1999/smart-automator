# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Humanizer: makes automation indistinguishable from human interaction."""

from smart_automator.humanizer.delays import HumanDelay
from smart_automator.humanizer.mouse import HumanMouse
from smart_automator.humanizer.scroll import HumanScroll
from smart_automator.humanizer.typing import HumanTyping

__all__ = ["HumanDelay", "HumanMouse", "HumanScroll", "HumanTyping"]
