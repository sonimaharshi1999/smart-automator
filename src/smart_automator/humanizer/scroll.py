# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Natural scroll patterns for human-like page navigation.

Real humans scroll in variable increments with pauses for reading.
This module generates scroll sequences that mimic natural behavior.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class ScrollStep:
    """A single scroll action."""
    pixels: int
    delay_ms: int
    direction: str = "down"  # "down" or "up"


class HumanScroll:
    """Generate human-like scroll patterns.

    Features:
    - Variable scroll distances (not uniform increments)
    - Reading pauses proportional to visible content
    - Occasional small reverse scrolls (overshoot correction)
    - Speed variation based on content density
    """

    def __init__(
        self,
        base_step_px: int = 100,
        reading_speed_factor: float = 1.0,
    ) -> None:
        self._base_step = base_step_px
        self._reading_speed = reading_speed_factor

    def generate_scroll_sequence(
        self,
        total_distance: int,
        direction: str = "down",
    ) -> list[ScrollStep]:
        """Generate a human-like scroll sequence.

        Args:
            total_distance: Total pixels to scroll
            direction: 'down' or 'up'
        """
        steps: list[ScrollStep] = []
        remaining = abs(total_distance)
        step_count = 0

        while remaining > 0:
            # Variable scroll amount (Gaussian around base step)
            amount = int(random.gauss(self._base_step, self._base_step * 0.3))
            amount = max(30, min(remaining, amount))

            # Reading pause: longer every few scrolls
            if step_count % 3 == 0 and step_count > 0:
                # Longer pause (reading)
                delay = int(random.gauss(800, 200) * self._reading_speed)
            else:
                # Quick scroll pause
                delay = int(random.gauss(200, 50))

            steps.append(ScrollStep(
                pixels=amount,
                delay_ms=max(50, delay),
                direction=direction,
            ))

            remaining -= amount
            step_count += 1

            # Occasional micro-reverse (overshoot correction)
            if random.random() < 0.08 and step_count > 1:
                reverse = random.randint(20, 60)
                reverse_dir = "up" if direction == "down" else "down"
                steps.append(ScrollStep(
                    pixels=reverse,
                    delay_ms=random.randint(100, 300),
                    direction=reverse_dir,
                ))

        return steps

    def scroll_to_element(
        self,
        current_y: int,
        target_y: int,
    ) -> list[ScrollStep]:
        """Generate scroll sequence to bring an element into view."""
        distance = target_y - current_y
        direction = "down" if distance > 0 else "up"
        return self.generate_scroll_sequence(abs(distance), direction)

    @staticmethod
    def smooth_scroll_js(pixels: int, duration_ms: int = 500) -> str:
        """Generate JavaScript for smooth scroll animation."""
        return (
            f"window.scrollBy({{ top: {pixels}, behavior: 'smooth' }}); "
            f"await new Promise(r => setTimeout(r, {duration_ms}));"
        )
