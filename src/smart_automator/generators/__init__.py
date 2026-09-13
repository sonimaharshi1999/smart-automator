# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Three script generation modes: prompt, screenshot, recording."""

from smart_automator.generators.prompt_generator import PromptGenerator
from smart_automator.generators.recording_enhancer import RecordingEnhancer
from smart_automator.generators.screenshot_generator import ScreenshotGenerator

__all__ = ["PromptGenerator", "ScreenshotGenerator", "RecordingEnhancer"]
