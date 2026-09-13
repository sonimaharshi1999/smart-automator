# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Recording enhancer: hardens raw Playwright codegen output.

Mode 3: User runs `playwright codegen`, gets raw script
-> AI replaces fragile selectors with label-based ones
-> Adds humanizer delays
-> Adds error handling and retry logic
"""

from __future__ import annotations

import re
from typing import Any

from smart_automator.llm.base import LLMProvider

ENHANCE_SYSTEM_PROMPT = """You are a Playwright script optimizer. Given a raw Playwright
codegen recording, enhance it with:

1. REPLACE fragile selectors:
   - Replace CSS selectors with aria-label or text-based selectors
   - Replace nth-child selectors with role-based selectors
   - Prefer: page.get_by_role(), page.get_by_text(), page.get_by_label()

2. ADD error handling:
   - Wrap actions in try/except with meaningful error messages
   - Add retry logic for flaky selectors
   - Add wait_for_load_state() after navigation

3. ADD humanizer patterns:
   - Add random delays between actions (100-500ms)
   - Use page.wait_for_timeout() with variable durations

4. IMPROVE structure:
   - Add descriptive comments for each logical step
   - Group related actions into functions
   - Add type hints

Return the enhanced Python script only. No markdown fences."""


class RecordingEnhancer:
    """Enhance raw Playwright recordings with AI.

    Takes raw output from `playwright codegen` and produces
    a hardened, resilient automation script with:
    - Label-based selectors instead of CSS/nth-child
    - Humanizer delays
    - Error handling and retry logic
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def enhance(
        self,
        raw_script: str,
        platform: str = "generic",
        add_humanizer: bool = True,
        add_error_handling: bool = True,
    ) -> str:
        """Enhance a raw Playwright recording script.

        Args:
            raw_script: Raw output from playwright codegen
            platform: Target platform for context
            add_humanizer: Whether to add human-like delays
            add_error_handling: Whether to add try/except blocks

        Returns:
            Enhanced Python script as a string
        """
        prompt = self._build_prompt(
            raw_script, platform, add_humanizer, add_error_handling
        )
        enhanced = self._llm.generate(
            prompt, system_prompt=ENHANCE_SYSTEM_PROMPT
        )

        # Clean up response
        enhanced = self._clean_response(enhanced)
        return enhanced

    def enhance_selectors_only(self, raw_script: str) -> str:
        """Replace fragile selectors without full LLM enhancement.

        Uses regex-based heuristics to upgrade common selector patterns.
        Works WITHOUT an LLM.
        """
        script = raw_script

        # Replace CSS nth-child with more stable patterns
        script = re.sub(
            r'page\.locator\("([^"]*):nth-child\(\d+\)"\)',
            lambda m: self._suggest_replacement(m.group(1)),
            script,
        )

        # Replace bare class selectors
        script = re.sub(
            r'page\.locator\("\.([a-zA-Z0-9_-]+)"\)',
            lambda m: f'page.locator("[class*=\'{m.group(1)}\']")',
            script,
        )

        # Add wait after navigation
        script = re.sub(
            r'(page\.goto\([^)]+\))',
            r'\1\n    await page.wait_for_load_state("networkidle")',
            script,
        )

        return script

    @staticmethod
    def _build_prompt(
        raw_script: str,
        platform: str,
        add_humanizer: bool,
        add_error_handling: bool,
    ) -> str:
        """Build the enhancement prompt."""
        parts = [
            f"Enhance this raw Playwright recording for {platform}:",
            "",
            raw_script,
            "",
            "Requirements:",
        ]

        parts.append("- Replace all fragile selectors with label-based ones")
        if add_humanizer:
            parts.append("- Add human-like random delays between actions")
        if add_error_handling:
            parts.append("- Add try/except error handling with retry")

        return "\n".join(parts)

    @staticmethod
    def _clean_response(response: str) -> str:
        """Clean LLM response to extract pure Python code."""
        text = response.strip()

        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]

        return text.strip()

    @staticmethod
    def _suggest_replacement(selector: str) -> str:
        """Suggest a more stable selector replacement."""
        # If it looks like a button, use role
        if "btn" in selector or "button" in selector:
            return 'page.get_by_role("button")'
        # If it looks like a link, use role
        if "link" in selector or "nav" in selector:
            return 'page.get_by_role("link")'
        # If it looks like input, use role
        if "input" in selector or "field" in selector:
            return 'page.get_by_role("textbox")'
        # Default: keep but add a comment
        return f'page.locator("{selector}")  # TODO: replace with stable selector'

    @staticmethod
    def extract_actions(raw_script: str) -> list[dict[str, str]]:
        """Extract action descriptions from a raw recording.

        Parses the script to identify what actions were recorded.
        """
        actions: list[dict[str, str]] = []

        goto_pattern = re.compile(r'page\.goto\("([^"]+)"\)')
        click_pattern = re.compile(r'page\.(?:locator|get_by_\w+)\(([^)]+)\)\.click\(\)')
        fill_pattern = re.compile(
            r'page\.(?:locator|get_by_\w+)\(([^)]+)\)\.fill\("([^"]+)"\)'
        )

        for line in raw_script.split("\n"):
            line = line.strip()

            match = goto_pattern.search(line)
            if match:
                actions.append({"action": "navigate", "target": match.group(1)})
                continue

            match = click_pattern.search(line)
            if match:
                actions.append({"action": "click", "target": match.group(1)})
                continue

            match = fill_pattern.search(line)
            if match:
                actions.append({
                    "action": "type",
                    "target": match.group(1),
                    "value": match.group(2),
                })

        return actions
