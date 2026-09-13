# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for generation modes: prompt, screenshot, recording."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smart_automator.generators.prompt_generator import PromptGenerator
from smart_automator.generators.recording_enhancer import RecordingEnhancer
from smart_automator.generators.screenshot_generator import ScreenshotGenerator
from smart_automator.models import ActionType, GenerationMode

# Import from conftest
from tests.conftest import MockLLMProvider


class TestPromptGenerator:
    """Tests for prompt-based generation."""

    def test_generate_from_instruction(self, mock_llm_with_steps: MockLLMProvider) -> None:
        generator = PromptGenerator(mock_llm_with_steps)
        sequence = generator.generate(
            "Post 'Hello World' on LinkedIn",
            platform="linkedin",
        )
        assert sequence.name == "prompt_linkedin"
        assert sequence.generation_mode == GenerationMode.PROMPT
        assert len(sequence.steps) == 3

    def test_generated_steps_types(self, mock_llm_with_steps: MockLLMProvider) -> None:
        generator = PromptGenerator(mock_llm_with_steps)
        sequence = generator.generate("Post something", platform="linkedin")
        actions = [s.action for s in sequence.steps]
        assert ActionType.NAVIGATE in actions
        assert ActionType.CLICK in actions
        assert ActionType.TYPE in actions

    def test_invalid_llm_response(self, mock_llm: MockLLMProvider) -> None:
        mock_llm._response = "This is not JSON"
        generator = PromptGenerator(mock_llm)
        with pytest.raises(ValueError, match="invalid JSON"):
            generator.generate("Do something")

    def test_context_passed_to_llm(self, mock_llm_with_steps: MockLLMProvider) -> None:
        generator = PromptGenerator(mock_llm_with_steps)
        generator.generate(
            "Post something",
            platform="linkedin",
            context={"base_url": "https://linkedin.com", "logged_in": True},
        )
        call = mock_llm_with_steps._calls[0]
        assert "linkedin.com" in call["prompt"]
        assert "logged in" in call["prompt"]

    def test_parse_response_with_code_fences(self) -> None:
        steps_json = json.dumps([
            {"action": "navigate", "url": "https://example.com"},
        ])
        response = f"```json\n{steps_json}\n```"
        steps = PromptGenerator._parse_response(response)
        assert len(steps) == 1
        assert steps[0].action == ActionType.NAVIGATE


class TestScreenshotGenerator:
    """Tests for screenshot-based generation."""

    def test_generate_click_action(self, tmp_path: Path) -> None:
        # Create a tiny test image
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="blue")
        img_path = tmp_path / "test.png"
        img.save(img_path)

        generator = ScreenshotGenerator()
        sequence = generator.generate(
            str(img_path),
            "Click the Submit button",
            platform="generic",
        )
        assert sequence.generation_mode == GenerationMode.SCREENSHOT
        assert len(sequence.steps) >= 1
        assert sequence.steps[0].action == ActionType.CLICK

    def test_infer_action_type(self) -> None:
        assert ScreenshotGenerator._infer_action("click the button") == ActionType.CLICK
        assert ScreenshotGenerator._infer_action("type hello") == ActionType.TYPE
        assert ScreenshotGenerator._infer_action("scroll down") == ActionType.SCROLL
        assert ScreenshotGenerator._infer_action("go to page") == ActionType.NAVIGATE
        assert ScreenshotGenerator._infer_action("wait for load") == ActionType.WAIT
        assert ScreenshotGenerator._infer_action("do something") == ActionType.CLICK

    def test_extract_value(self) -> None:
        assert ScreenshotGenerator._extract_value("type 'hello'") == "hello"
        assert ScreenshotGenerator._extract_value('enter "world"') == "world"
        assert ScreenshotGenerator._extract_value("click button") is None


class TestRecordingEnhancer:
    """Tests for recording enhancement."""

    SAMPLE_RECORDING = """
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://linkedin.com/login")
        await page.locator(".login-email:nth-child(1)").fill("user@example.com")
        await page.locator(".login-password").fill("password123")
        await page.locator("button.btn-primary:nth-child(2)").click()
"""

    def test_enhance_selectors_only(self, mock_llm: MockLLMProvider) -> None:
        enhancer = RecordingEnhancer(mock_llm)
        result = enhancer.enhance_selectors_only(self.SAMPLE_RECORDING)
        # Should have added wait after goto
        assert "wait_for_load_state" in result

    def test_extract_actions(self) -> None:
        actions = RecordingEnhancer.extract_actions(self.SAMPLE_RECORDING)
        assert len(actions) >= 1
        # Should find the goto action
        navigates = [a for a in actions if a["action"] == "navigate"]
        assert len(navigates) == 1
        assert "linkedin.com" in navigates[0]["target"]

    def test_enhance_with_llm(self, mock_llm: MockLLMProvider) -> None:
        mock_llm._response = "# Enhanced script\nimport asyncio\n# Improved version"
        enhancer = RecordingEnhancer(mock_llm)
        result = enhancer.enhance(
            self.SAMPLE_RECORDING,
            platform="linkedin",
            add_humanizer=True,
        )
        assert "Enhanced script" in result or "asyncio" in result
        # Verify LLM was called
        assert len(mock_llm._calls) == 1
        assert "linkedin" in mock_llm._calls[0]["prompt"]
