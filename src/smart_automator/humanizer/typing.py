# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Realistic typing simulation with variable speed and typo correction.

Real humans type with variable speed, make occasional typos, and
correct them. This module simulates all of that for natural interaction.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum


class KeyEvent(str, Enum):
    """Types of keyboard events."""
    PRESS = "press"
    BACKSPACE = "backspace"
    PAUSE = "pause"


@dataclass
class TypeAction:
    """A single typing action."""
    event: KeyEvent
    char: str = ""
    delay_ms: int = 0


# Keys near each other on QWERTY layout (for realistic typos)
QWERTY_NEIGHBORS: dict[str, str] = {
    "a": "sqwz", "b": "vngh", "c": "xdfv", "d": "sfcer",
    "e": "wrd", "f": "dgcvr", "g": "fhbvt", "h": "gjbny",
    "i": "uojk", "j": "hknmu", "k": "jlmi", "l": "kop",
    "m": "njk", "n": "bhjm", "o": "iplk", "p": "ol",
    "q": "wa", "r": "edft", "s": "adwxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc",
    "y": "tghu", "z": "xsa",
}


class HumanTyping:
    """Simulate human-like typing with variable speed and typos.

    Features:
    - Variable inter-key delay based on character pairs
    - Occasional typos with immediate correction
    - Pauses at word boundaries and punctuation
    - Faster typing for common words, slower for unusual ones
    """

    def __init__(
        self,
        base_cpm: int = 250,
        typo_probability: float = 0.03,
        correction_delay_ms: int = 200,
    ) -> None:
        """Initialize typing simulator.

        Args:
            base_cpm: Base characters per minute (typing speed)
            typo_probability: Chance of making a typo per character
            correction_delay_ms: Delay before correcting a typo
        """
        self._base_delay_ms = int(60_000 / max(base_cpm, 50))
        self._typo_prob = max(0.0, min(0.2, typo_probability))
        self._correction_delay = correction_delay_ms

    def generate_typing_sequence(self, text: str) -> list[TypeAction]:
        """Generate a complete typing sequence with natural variation.

        Returns a list of TypeActions including key presses, typo
        corrections (backspace + correct char), and natural pauses.
        """
        actions: list[TypeAction] = []
        prev_char = ""

        for i, char in enumerate(text):
            # Natural pause at word boundaries
            if char == " " and prev_char != " ":
                pause = random.gauss(self._base_delay_ms * 1.5, 30)
                actions.append(
                    TypeAction(
                        event=KeyEvent.PAUSE,
                        delay_ms=max(20, int(pause)),
                    )
                )

            # Longer pause after punctuation
            if prev_char in ".!?;:":
                pause = random.gauss(self._base_delay_ms * 3, 80)
                actions.append(
                    TypeAction(
                        event=KeyEvent.PAUSE,
                        delay_ms=max(50, int(pause)),
                    )
                )

            # Maybe make a typo
            if (
                self._typo_prob > 0
                and random.random() < self._typo_prob
                and char.lower() in QWERTY_NEIGHBORS
            ):
                typo_actions = self._generate_typo(char)
                actions.extend(typo_actions)
            else:
                delay = self._char_delay(char, prev_char)
                actions.append(
                    TypeAction(event=KeyEvent.PRESS, char=char, delay_ms=delay)
                )

            prev_char = char

        return actions

    def _generate_typo(self, correct_char: str) -> list[TypeAction]:
        """Generate a typo and its correction sequence."""
        neighbors = QWERTY_NEIGHBORS.get(correct_char.lower(), "")
        if not neighbors:
            delay = self._char_delay(correct_char, "")
            return [TypeAction(event=KeyEvent.PRESS, char=correct_char, delay_ms=delay)]

        wrong_char = random.choice(neighbors)
        if correct_char.isupper():
            wrong_char = wrong_char.upper()

        return [
            # Type wrong character
            TypeAction(
                event=KeyEvent.PRESS,
                char=wrong_char,
                delay_ms=self._char_delay(wrong_char, ""),
            ),
            # Pause (realizing the mistake)
            TypeAction(
                event=KeyEvent.PAUSE,
                delay_ms=self._correction_delay + random.randint(-50, 100),
            ),
            # Backspace
            TypeAction(event=KeyEvent.BACKSPACE, delay_ms=random.randint(30, 80)),
            # Type correct character
            TypeAction(
                event=KeyEvent.PRESS,
                char=correct_char,
                delay_ms=self._char_delay(correct_char, ""),
            ),
        ]

    def _char_delay(self, char: str, prev_char: str) -> int:
        """Calculate delay for a specific character.

        Factors: base speed, character complexity, digraph frequency.
        """
        base = self._base_delay_ms

        # Uppercase requires shift (slower)
        if char.isupper():
            base = int(base * 1.3)

        # Numbers and symbols are slower
        if char.isdigit():
            base = int(base * 1.2)
        elif not char.isalnum() and char != " ":
            base = int(base * 1.4)

        # Common digraphs are faster (muscle memory)
        digraph = (prev_char + char).lower()
        fast_digraphs = {"th", "he", "in", "er", "an", "re", "on", "at", "en", "nd"}
        if digraph in fast_digraphs:
            base = int(base * 0.7)

        # Add natural variation
        variation = random.gauss(0, base * 0.2)
        return max(20, int(base + variation))

    def calculate_duration_ms(self, text: str) -> int:
        """Estimate total typing duration for a text string."""
        actions = self.generate_typing_sequence(text)
        return sum(a.delay_ms for a in actions)
