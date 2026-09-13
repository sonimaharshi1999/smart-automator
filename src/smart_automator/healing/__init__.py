# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Self-healing: retry with AI-generated alternative selectors."""

from smart_automator.healing.fallback import FallbackStrategy
from smart_automator.healing.retry import SelfHealingRetry

__all__ = ["SelfHealingRetry", "FallbackStrategy"]
