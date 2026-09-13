# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Screenshot-based generation: screenshot + instruction to selectors.

Mode 2: User provides a screenshot and says "Click the blue 'Submit' button"
-> Analyzer finds the element -> generates selector -> builds action.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smart_automator.models import (
    ActionSequence,
    ActionStep,
    ActionType,
    ElementInfo,
    GenerationMode,
    Selector,
    SelectorStrategy,
)
from smart_automator.ui_executor.screenshot_analyzer import ScreenshotAnalyzer


class ScreenshotGenerator:
    """Generate action sequences from screenshots + instructions.

    Does NOT require an LLM for basic operation. Uses the
    ScreenshotAnalyzer's heuristic detection. LLM enhances accuracy.
    """

    def __init__(
        self,
        analyzer: ScreenshotAnalyzer | None = None,
    ) -> None:
        self._analyzer = analyzer or ScreenshotAnalyzer()

    def generate(
        self,
        screenshot_path: str | Path,
        instruction: str,
        platform: str = "generic",
    ) -> ActionSequence:
        """Generate action sequence from screenshot analysis.

        Args:
            screenshot_path: Path to the screenshot image
            instruction: What to do (e.g., "Click the Submit button")
            platform: Target platform name

        Returns:
            ActionSequence with generated selectors
        """
        analysis = self._analyzer.analyze_screenshot(
            screenshot_path, instruction
        )

        steps = self._build_steps(instruction, analysis.elements)

        return ActionSequence(
            name=f"screenshot_{platform}",
            description=instruction,
            platform=platform,
            steps=steps,
            generation_mode=GenerationMode.SCREENSHOT,
        )

    def _build_steps(
        self,
        instruction: str,
        elements: list[ElementInfo],
    ) -> list[ActionStep]:
        """Build action steps from detected elements."""
        instruction_lower = instruction.lower()

        # Parse the instruction for action keywords
        action = self._infer_action(instruction_lower)

        # Find the best matching element
        best_element = self._find_best_element(instruction_lower, elements)

        if best_element:
            selector = self._element_to_selector(best_element)
        else:
            # Fallback: use instruction text as selector
            selector = Selector(
                primary=f"text={instruction}",
                strategy=SelectorStrategy.VISIBLE_TEXT,
                description=instruction,
            )

        # Extract value for type actions
        value = self._extract_value(instruction)

        steps = [
            ActionStep(
                action=action,
                selector=selector,
                value=value if action == ActionType.TYPE else None,
                description=instruction,
                wait_ms=500,
            )
        ]

        return steps

    @staticmethod
    def _infer_action(instruction: str) -> ActionType:
        """Infer the action type from instruction text."""
        action_keywords = {
            ActionType.CLICK: ["click", "press", "tap", "hit", "select", "choose"],
            ActionType.TYPE: ["type", "enter", "input", "write", "fill"],
            ActionType.SCROLL: ["scroll", "swipe"],
            ActionType.NAVIGATE: ["go to", "navigate", "open", "visit"],
            ActionType.WAIT: ["wait", "pause"],
        }

        for action, keywords in action_keywords.items():
            if any(kw in instruction for kw in keywords):
                return action

        return ActionType.CLICK  # Default

    @staticmethod
    def _find_best_element(
        instruction: str, elements: list[ElementInfo]
    ) -> ElementInfo | None:
        """Find the element that best matches the instruction."""
        if not elements:
            return None

        scored: list[tuple[float, ElementInfo]] = []
        for el in elements:
            score = el.confidence
            if el.text and el.text.lower() in instruction:
                score += 0.5
            if el.element_type in instruction:
                score += 0.3
            scored.append((score, el))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None

    @staticmethod
    def _element_to_selector(element: ElementInfo) -> Selector:
        """Convert an ElementInfo to a Selector."""
        if element.suggested_selector:
            return Selector(
                primary=element.suggested_selector,
                strategy=SelectorStrategy.XPATH,
                description=element.text,
            )

        if element.text:
            return Selector(
                primary=f"text={element.text}",
                strategy=SelectorStrategy.VISIBLE_TEXT,
                fallbacks=[
                    f"//*[contains(text(), '{element.text}')]",
                ],
                description=element.text,
            )

        return Selector(
            primary=f"{element.element_type}",
            strategy=SelectorStrategy.ROLE,
            description=element.element_type,
        )

    @staticmethod
    def _extract_value(instruction: str) -> str | None:
        """Extract a quoted value from instruction text."""
        import re

        match = re.search(r"['\"](.+?)['\"]", instruction)
        return match.group(1) if match else None
