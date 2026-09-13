# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""LLM provider abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    The framework works without an LLM for basic operations.
    LLM is needed for: prompt generation, recording enhancement,
    screenshot analysis (enhanced mode), and self-healing.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        image_path: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system instructions
            image_path: Optional image for vision analysis
            max_tokens: Maximum response tokens

        Returns:
            The LLM's text response
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM provider is available and configured."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display."""
        ...
