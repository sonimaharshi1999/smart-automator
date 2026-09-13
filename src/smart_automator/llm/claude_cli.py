# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Claude CLI provider: uses `claude -p` subprocess for LLM calls.

Default provider - no API key needed. Uses the locally installed
Claude CLI tool to generate responses.
"""

from __future__ import annotations

import shutil
import subprocess

from smart_automator.llm.base import LLMProvider


class ClaudeCLIProvider(LLMProvider):
    """LLM provider using Claude CLI subprocess calls.

    Calls `claude -p "prompt"` and captures stdout.
    No API key configuration needed.
    """

    def __init__(
        self,
        timeout_seconds: int = 60,
        model: str | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._model = model
        self._cli_path = shutil.which("claude")

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        image_path: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """Generate response using Claude CLI."""
        if not self.is_available():
            raise RuntimeError(
                "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
            )

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        cmd = ["claude", "-p", full_prompt]
        if self._model:
            cmd.extend(["--model", self._model])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                encoding="utf-8",
            )
            if result.returncode != 0:
                raise RuntimeError(f"Claude CLI error: {result.stderr}")
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Claude CLI timed out after {self._timeout}s"
            )
        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found in PATH")

    def is_available(self) -> bool:
        """Check if Claude CLI is installed."""
        return self._cli_path is not None

    @property
    def name(self) -> str:
        return "Claude CLI"
