# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Prompt-based generation: natural language to action steps.

Mode 1: User types "Post 'Hello World' on LinkedIn"
-> LLM generates action steps -> executor runs them.
"""

from __future__ import annotations

import json
from typing import Any

from smart_automator.llm.base import LLMProvider
from smart_automator.models import (
    ActionSequence,
    ActionStep,
    ActionType,
    GenerationMode,
    Selector,
    SelectorStrategy,
)

SYSTEM_PROMPT = """You are an automation script generator. Given a natural language
instruction, generate a JSON array of action steps for browser automation.

Each step must have:
- "action": one of navigate, click, type, select, scroll, wait, screenshot, assert, login
- "selector": object with "primary" (selector string), "strategy" (aria-label, visible-text,
  role, data-testid), "description" (what the element is)
- "value": text to type, URL to navigate to, or assertion value
- "url": URL for navigate actions
- "wait_ms": milliseconds to wait after action
- "description": human-readable step description

SELECTOR PRIORITY: Always prefer aria-label > visible text > role > data-testid > CSS class.
Use label-based selectors that won't break when the UI changes.

Return ONLY valid JSON array. No markdown, no explanation."""


class PromptGenerator:
    """Generate action sequences from natural language prompts.

    Requires an LLM provider. Takes a human instruction like
    "Post 'Hello World' on LinkedIn" and generates an executable
    action sequence.
    """

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def generate(
        self,
        instruction: str,
        platform: str = "generic",
        context: dict[str, Any] | None = None,
    ) -> ActionSequence:
        """Generate an action sequence from a natural language instruction.

        Args:
            instruction: Natural language description of what to automate
            platform: Target platform name
            context: Optional context (e.g., platform config, login state)

        Returns:
            ActionSequence ready for execution
        """
        prompt = self._build_prompt(instruction, platform, context)
        response = self._llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        steps = self._parse_response(response)

        return ActionSequence(
            name=f"prompt_{platform}",
            description=instruction,
            platform=platform,
            steps=steps,
            generation_mode=GenerationMode.PROMPT,
        )

    def _build_prompt(
        self,
        instruction: str,
        platform: str,
        context: dict[str, Any] | None,
    ) -> str:
        """Build the generation prompt."""
        parts = [f"Generate automation steps for: {instruction}"]
        parts.append(f"Target platform: {platform}")

        if context:
            if context.get("base_url"):
                parts.append(f"Base URL: {context['base_url']}")
            if context.get("logged_in"):
                parts.append("User is already logged in.")
            if context.get("selectors_hint"):
                parts.append(
                    f"Known selectors: {json.dumps(context['selectors_hint'])}"
                )

        return "\n".join(parts)

    @staticmethod
    def _parse_response(response: str) -> list[ActionStep]:
        """Parse LLM response into ActionStep list."""
        # Strip markdown code fences if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            raw_steps: list[dict[str, Any]] = json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"LLM returned invalid JSON: {text[:200]}")

        steps: list[ActionStep] = []
        for raw in raw_steps:
            action_str = raw.get("action", "").lower()
            try:
                action = ActionType(action_str)
            except ValueError:
                continue

            selector = None
            if raw.get("selector"):
                sel = raw["selector"]
                strategy_str = sel.get("strategy", "visible-text")
                try:
                    strategy = SelectorStrategy(strategy_str)
                except ValueError:
                    strategy = SelectorStrategy.VISIBLE_TEXT

                selector = Selector(
                    primary=sel.get("primary", ""),
                    strategy=strategy,
                    fallbacks=sel.get("fallbacks", []),
                    description=sel.get("description", ""),
                )

            steps.append(ActionStep(
                action=action,
                selector=selector,
                value=raw.get("value"),
                url=raw.get("url"),
                wait_ms=raw.get("wait_ms", 0),
                description=raw.get("description", ""),
            ))

        return steps
