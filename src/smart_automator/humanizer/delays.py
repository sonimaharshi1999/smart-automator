# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Human-like delay patterns using Gaussian distribution.

Not just random.uniform() -- real humans have natural pauses
that follow a bell curve, with longer pauses after complex actions.
"""

from __future__ import annotations

import random
from enum import Enum


class ActionComplexity(str, Enum):
    """How complex an action is, affecting delay distribution."""
    SIMPLE = "simple"      # Click a button
    MODERATE = "moderate"  # Fill a form field
    COMPLEX = "complex"    # Read content, make a decision
    IDLE = "idle"          # Natural pause between task sections


# Delay parameters: (mean_ms, stddev_ms, min_ms, max_ms)
DELAY_PROFILES: dict[ActionComplexity, tuple[int, int, int, int]] = {
    ActionComplexity.SIMPLE: (300, 100, 100, 600),
    ActionComplexity.MODERATE: (700, 200, 300, 1500),
    ActionComplexity.COMPLEX: (1500, 500, 500, 4000),
    ActionComplexity.IDLE: (3000, 1000, 1000, 8000),
}


class HumanDelay:
    """Generate human-like delays using Gaussian distribution.

    Delays follow a bell curve centered on typical human reaction times.
    More complex actions have longer, more variable delays.
    """

    def __init__(
        self,
        speed_factor: float = 1.0,
        min_override: int | None = None,
        max_override: int | None = None,
    ) -> None:
        """Initialize with optional speed adjustment.

        Args:
            speed_factor: Multiplier for all delays (0.5 = faster, 2.0 = slower)
            min_override: Override minimum delay in ms
            max_override: Override maximum delay in ms
        """
        self._speed = max(0.1, speed_factor)
        self._min_override = min_override
        self._max_override = max_override

    def get_delay_ms(
        self,
        complexity: ActionComplexity = ActionComplexity.SIMPLE,
    ) -> int:
        """Generate a human-like delay in milliseconds."""
        mean, stddev, min_ms, max_ms = DELAY_PROFILES[complexity]

        # Apply speed factor
        mean = int(mean * self._speed)
        stddev = int(stddev * self._speed)
        min_ms = self._min_override or int(min_ms * self._speed)
        max_ms = self._max_override or int(max_ms * self._speed)

        # Gaussian distribution clamped to range
        delay = int(random.gauss(mean, stddev))
        return max(min_ms, min(max_ms, delay))

    def get_delay_seconds(
        self,
        complexity: ActionComplexity = ActionComplexity.SIMPLE,
    ) -> float:
        """Generate a human-like delay in seconds."""
        return self.get_delay_ms(complexity) / 1000.0

    @staticmethod
    def micro_pause() -> int:
        """Very short pause (50-150ms), like between keystrokes."""
        return int(random.gauss(80, 25))

    @staticmethod
    def reading_pause(word_count: int) -> int:
        """Pause proportional to content length (reading time).

        Average reading speed: ~250 words per minute.
        """
        wpm = random.gauss(250, 50)
        minutes = word_count / max(wpm, 100)
        return int(minutes * 60 * 1000)
