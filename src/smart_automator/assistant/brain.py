# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Conversational AI brain that orchestrates guide/do/ask modes.

Analyzes screen context, interprets voice commands, decides whether to
guide the user (explain + point) or act (execute desktop actions),
and manages multi-turn conversation state.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from smart_automator.llm.base import LLMProvider


class AssistantMode(str, Enum):
    GUIDE = "guide"
    DO = "do"
    ASK = "ask"


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    screenshot_context: bool = False
    actions_taken: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AssistantResponse:
    """Structured response from the AI brain."""
    speech_text: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    pointers: list[dict[str, Any]] = field(default_factory=list)
    mode_used: AssistantMode = AssistantMode.GUIDE
    needs_confirmation: bool = False
    follow_up: str = ""


SYSTEM_PROMPT = """You are SmartAutomator Assistant, an AI that can see the user's screen and control their computer.

Current mode: {mode}
- GUIDE: Explain what to do and POINT at UI elements. Do NOT perform actions.
- DO: Perform the requested actions directly using desktop control.
- ASK: Explain what you plan to do, then wait for user confirmation before acting.

When responding, output a JSON object with these fields:
{{
    "speech": "What to say to the user (natural, conversational)",
    "actions": [
        {{
            "type": "click|double_click|right_click|type_text|hotkey|move_to|scroll|open_app|switch_window|wait",
            "x": 500,
            "y": 300,
            "text": "text to type if applicable",
            "keys": ["ctrl", "c"],
            "app_name": "chrome",
            "description": "Brief description of what this action does"
        }}
    ],
    "pointers": [
        {{
            "x": 500,
            "y": 300,
            "label": "Click here",
            "description": "The Settings icon"
        }}
    ],
    "needs_confirmation": false,
    "follow_up": "Optional follow-up question or next step suggestion"
}}

You can also embed pointer commands inline with speech using [POINT:x,y:label] tags.
Example: "Click the settings button [POINT:1205,45:Settings gear] in the top-right corner"
This makes the buddy cursor glide to the element WHILE you speak.

Rules:
- In GUIDE mode: populate pointers (or use inline [POINT] tags), leave actions empty
- In DO mode: populate actions, optionally add pointers for visual feedback
- In ASK mode: populate actions AND set needs_confirmation=true
- Always provide speech text explaining what you're doing/suggesting
- Use screen coordinates from the screenshot analysis
- Be concise and natural in speech
- If you can't determine the exact coordinates, ask the user for clarification
- Prefer inline [POINT:x,y:label] tags for a more natural conversational flow
"""


class AssistantBrain:
    """AI brain that interprets commands and generates structured responses.

    Manages conversation history, screen context, and mode switching
    to orchestrate the full guide/do/ask workflow.
    """

    def __init__(
        self,
        llm: LLMProvider,
        mode: AssistantMode = AssistantMode.ASK,
        max_history: int = 20,
    ) -> None:
        self._llm = llm
        self._mode = mode
        self._history: list[ConversationTurn] = []
        self._max_history = max_history

    @property
    def mode(self) -> AssistantMode:
        return self._mode

    @mode.setter
    def mode(self, value: AssistantMode) -> None:
        self._mode = value

    @property
    def history(self) -> list[ConversationTurn]:
        return list(self._history)

    def process(
        self,
        user_input: str,
        screenshot_path: str | None = None,
    ) -> AssistantResponse:
        """Process user input (text from voice transcription) and return structured response."""
        self._history.append(ConversationTurn(
            role="user",
            content=user_input,
            screenshot_context=screenshot_path is not None,
        ))

        mode_override = self._detect_mode_override(user_input)
        active_mode = mode_override or self._mode

        system = SYSTEM_PROMPT.format(mode=active_mode.value.upper())
        context = self._build_context(user_input)

        try:
            raw = self._llm.generate(
                prompt=context,
                system_prompt=system,
                image_path=screenshot_path,
                max_tokens=2048,
            )
            response = self._parse_response(raw, active_mode)
        except Exception as e:
            response = AssistantResponse(
                speech_text=f"I encountered an issue: {str(e)[:100]}. Could you try again?",
                mode_used=active_mode,
            )

        self._history.append(ConversationTurn(
            role="assistant",
            content=response.speech_text,
            actions_taken=response.actions,
        ))

        if len(self._history) > self._max_history * 2:
            self._history = self._history[-self._max_history:]

        return response

    def confirm_action(self) -> AssistantResponse | None:
        """Called when user confirms a pending ASK-mode action."""
        for turn in reversed(self._history):
            if turn.role == "assistant" and turn.actions_taken:
                return AssistantResponse(
                    speech_text="Proceeding with the action now.",
                    actions=turn.actions_taken,
                    mode_used=AssistantMode.DO,
                    needs_confirmation=False,
                )
        return None

    def reject_action(self) -> AssistantResponse:
        """Called when user rejects a pending action."""
        return AssistantResponse(
            speech_text="Understood, I won't perform that action. What would you like to do instead?",
            mode_used=self._mode,
        )

    def _detect_mode_override(self, text: str) -> AssistantMode | None:
        """Detect if user wants to temporarily switch modes."""
        lower = text.lower().strip()

        do_patterns = [
            r"\bdo it\b", r"\bjust do\b", r"\bgo ahead\b",
            r"\bperform\b", r"\bexecute\b", r"\brun it\b",
        ]
        guide_patterns = [
            r"\bshow me\b", r"\bwhere is\b", r"\bpoint to\b",
            r"\bhow do i\b", r"\bwhere should\b", r"\bguide me\b",
        ]
        ask_patterns = [
            r"\bwhat would you\b", r"\bshould i\b", r"\bcheck first\b",
        ]

        for p in do_patterns:
            if re.search(p, lower):
                return AssistantMode.DO
        for p in guide_patterns:
            if re.search(p, lower):
                return AssistantMode.GUIDE
        for p in ask_patterns:
            if re.search(p, lower):
                return AssistantMode.ASK

        return None

    def _build_context(self, current_input: str) -> str:
        """Build conversation context from history."""
        parts: list[str] = []

        recent = self._history[-6:]
        for turn in recent[:-1]:
            prefix = "User" if turn.role == "user" else "Assistant"
            parts.append(f"{prefix}: {turn.content}")

        parts.append(f"User: {current_input}")
        parts.append("Respond with the JSON object as specified in the system prompt.")

        return "\n".join(parts)

    def _parse_response(self, raw: str, mode: AssistantMode) -> AssistantResponse:
        """Parse LLM response into structured AssistantResponse."""
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            try:
                data = json.loads(json_match.group())
                actions = data.get("actions", [])
                if mode == AssistantMode.GUIDE:
                    actions = []

                return AssistantResponse(
                    speech_text=data.get("speech", raw[:200]),
                    actions=actions,
                    pointers=data.get("pointers", []),
                    mode_used=mode,
                    needs_confirmation=data.get("needs_confirmation", mode == AssistantMode.ASK),
                    follow_up=data.get("follow_up", ""),
                )
            except json.JSONDecodeError:
                pass

        return AssistantResponse(
            speech_text=raw[:300].strip(),
            mode_used=mode,
        )

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._history.clear()

    def get_summary(self) -> str:
        """Get a summary of the conversation so far."""
        if not self._history:
            return "No conversation yet."

        user_turns = sum(1 for t in self._history if t.role == "user")
        actions = sum(len(t.actions_taken) for t in self._history)
        return f"{user_turns} exchanges, {actions} actions performed"
