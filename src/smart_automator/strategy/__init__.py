# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Strategy selection: picks API vs UI based on platform capabilities."""

from smart_automator.strategy.platform_registry import PlatformRegistry
from smart_automator.strategy.selector import StrategySelector

__all__ = ["PlatformRegistry", "StrategySelector"]
