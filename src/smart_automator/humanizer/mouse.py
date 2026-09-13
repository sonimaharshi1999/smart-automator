# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Bezier curve mouse movements for natural pointer trajectories.

Real humans don't move the mouse in straight lines. They follow
curved paths with acceleration/deceleration patterns. This module
generates realistic mouse movements using cubic Bezier curves.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass
class Point:
    """A 2D point."""
    x: float
    y: float


class HumanMouse:
    """Generate human-like mouse movement paths using Bezier curves.

    Creates curved trajectories with:
    - Natural acceleration and deceleration
    - Slight overshoot near targets
    - Random micro-jitter along the path
    """

    def __init__(
        self,
        steps: int = 20,
        jitter_px: float = 2.0,
        overshoot_probability: float = 0.15,
    ) -> None:
        self._steps = max(5, steps)
        self._jitter = jitter_px
        self._overshoot_prob = overshoot_probability

    def generate_path(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
    ) -> list[tuple[float, float]]:
        """Generate a human-like mouse path from start to end.

        Uses cubic Bezier curves with random control points
        offset from the straight-line path.
        """
        start = Point(start_x, start_y)
        end = Point(end_x, end_y)

        # Calculate distance for control point offset
        dx = end.x - start.x
        dy = end.y - start.y
        distance = math.sqrt(dx * dx + dy * dy)
        offset = distance * 0.3

        # Random control points for the Bezier curve
        cp1 = Point(
            start.x + dx * 0.25 + random.gauss(0, offset * 0.3),
            start.y + dy * 0.25 + random.gauss(0, offset * 0.3),
        )
        cp2 = Point(
            start.x + dx * 0.75 + random.gauss(0, offset * 0.3),
            start.y + dy * 0.75 + random.gauss(0, offset * 0.3),
        )

        # Generate points along the Bezier curve
        path: list[tuple[float, float]] = []
        for i in range(self._steps + 1):
            t = i / self._steps
            point = self._cubic_bezier(start, cp1, cp2, end, t)

            # Add micro-jitter (less at start and end)
            edge_factor = 4 * t * (1 - t)  # Peaks at t=0.5
            jx = random.gauss(0, self._jitter * edge_factor)
            jy = random.gauss(0, self._jitter * edge_factor)

            path.append((point.x + jx, point.y + jy))

        # Simulate occasional overshoot
        if random.random() < self._overshoot_prob and len(path) > 2:
            overshoot = Point(
                end.x + random.gauss(0, 3),
                end.y + random.gauss(0, 3),
            )
            path[-2] = (overshoot.x, overshoot.y)

        # Ensure exact endpoint
        path[-1] = (end.x, end.y)
        return path

    @staticmethod
    def _cubic_bezier(
        p0: Point, p1: Point, p2: Point, p3: Point, t: float
    ) -> Point:
        """Calculate point on cubic Bezier curve at parameter t."""
        u = 1 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        x = uuu * p0.x + 3 * uu * t * p1.x + 3 * u * tt * p2.x + ttt * p3.x
        y = uuu * p0.y + 3 * uu * t * p1.y + 3 * u * tt * p2.y + ttt * p3.y

        return Point(x, y)

    def generate_timing(self, path_length: int) -> list[int]:
        """Generate per-step timing in milliseconds.

        Uses ease-in-out curve: slow at start/end, fast in middle.
        """
        timings: list[int] = []
        for i in range(path_length):
            t = i / max(path_length - 1, 1)
            # Ease-in-out: slow start, fast middle, slow end
            speed_factor = 1 - 4 * (t - 0.5) ** 2 + 0.2
            base_ms = int(15 / max(speed_factor, 0.1))
            timings.append(max(5, base_ms + random.randint(-3, 3)))
        return timings
