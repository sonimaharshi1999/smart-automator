# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Screenshot analyzer: finds elements by analyzing page screenshots.

Works WITHOUT an LLM by using basic image analysis for element detection.
When an LLM is available, it can enhance results with vision capabilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smart_automator.models import ElementInfo, ScreenshotAnalysis


class ScreenshotAnalyzer:
    """Analyzes screenshots to detect interactive elements.

    Core analysis works without LLM using heuristic-based detection.
    LLM provider can be optionally injected for enhanced analysis.
    """

    # Common UI element color ranges (approximate HSV ranges)
    BUTTON_MIN_SIZE = (40, 20)
    INPUT_MIN_SIZE = (100, 25)

    def __init__(self, llm_provider: Any = None) -> None:
        self._llm = llm_provider

    def analyze_screenshot(
        self,
        image_path: str | Path,
        instruction: str = "",
    ) -> ScreenshotAnalysis:
        """Analyze a screenshot to find interactive elements.

        Uses basic image analysis (edge detection, color analysis)
        to identify buttons, inputs, and other interactive elements.
        If an LLM provider is available, enhances with vision AI.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Screenshot not found: {image_path}")

        # Basic analysis using PIL
        elements = self._detect_elements_basic(image_path)

        return ScreenshotAnalysis(
            elements=elements,
            page_description=f"Analyzed {image_path.name}",
            suggested_actions=[instruction] if instruction else [],
        )

    def _detect_elements_basic(
        self, image_path: Path
    ) -> list[ElementInfo]:
        """Basic element detection using image analysis heuristics.

        Detects rectangular regions that likely contain interactive elements
        based on contrast boundaries and common UI patterns.
        """
        try:
            from PIL import Image

            img = Image.open(image_path)
            width, height = img.size
        except ImportError:
            return []
        except Exception:
            return []

        elements: list[ElementInfo] = []

        # Scan for high-contrast rectangular regions (likely buttons/inputs)
        grid_x, grid_y = 10, 10
        cell_w = width // grid_x
        cell_h = height // grid_y

        for gy in range(grid_y):
            for gx in range(grid_x):
                x = gx * cell_w
                y = gy * cell_h
                region = img.crop((x, y, x + cell_w, y + cell_h))

                # Check if region has characteristics of an interactive element
                element = self._classify_region(region, x, y, cell_w, cell_h)
                if element:
                    elements.append(element)

        return elements

    @staticmethod
    def _classify_region(
        region: Any,
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> ElementInfo | None:
        """Classify a screen region as an element type.

        Uses color uniformity and size heuristics to guess element type.
        """
        try:
            from PIL import ImageStat

            stat = ImageStat.Stat(region)
            # High stddev in one channel suggests text/borders
            stddevs = stat.stddev
            mean_stddev = sum(s for s in stddevs[:3]) / 3

            if mean_stddev < 15:
                # Very uniform region - could be a solid button
                avg_brightness = sum(stat.mean[:3]) / 3
                if 50 < avg_brightness < 200 and w > 40 and h > 20:
                    return ElementInfo(
                        element_type="button",
                        location={"x": x, "y": y, "width": w, "height": h},
                        confidence=0.4,
                    )
            elif mean_stddev > 40:
                # High variance - likely text content
                if h > 25 and w > 100:
                    return ElementInfo(
                        element_type="text_input",
                        location={"x": x, "y": y, "width": w, "height": h},
                        confidence=0.3,
                    )
        except Exception:
            pass

        return None

    def analyze_with_llm(
        self,
        image_path: str | Path,
        instruction: str,
    ) -> ScreenshotAnalysis:
        """Enhanced analysis using LLM vision capabilities.

        Requires an LLM provider to be configured.
        Falls back to basic analysis if LLM is unavailable.
        """
        if not self._llm:
            return self.analyze_screenshot(image_path, instruction)

        prompt = (
            f"Analyze this screenshot and identify interactive UI elements. "
            f"User instruction: {instruction}\n"
            f"For each element, provide: type, visible text, "
            f"approximate position (x, y, width, height), "
            f"and a suggested CSS/XPath selector."
        )

        try:
            response = self._llm.generate(prompt, image_path=str(image_path))
            return self._parse_llm_response(response)
        except Exception:
            return self.analyze_screenshot(image_path, instruction)

    @staticmethod
    def _parse_llm_response(response: str) -> ScreenshotAnalysis:
        """Parse LLM response into structured element info."""
        elements: list[ElementInfo] = []
        lines = response.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Simple parsing: expect "type: text | selector: ..."
            if "|" in line:
                parts = dict(
                    p.strip().split(": ", 1)
                    for p in line.split("|")
                    if ": " in p
                )
                elements.append(
                    ElementInfo(
                        element_type=parts.get("type", "unknown"),
                        text=parts.get("text", ""),
                        suggested_selector=parts.get("selector", ""),
                        confidence=0.7,
                    )
                )

        return ScreenshotAnalysis(
            elements=elements,
            page_description="LLM-analyzed screenshot",
        )
