# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for AI-powered selector engine."""

from unittest.mock import AsyncMock

import pytest

from smart_automator.models import SelectorStrategy
from smart_automator.ui_executor.selector_engine import SelectorEngine


class TestSelectorEngine:
    """Tests for the selector engine's matching logic."""

    def test_best_match_aria_label(self) -> None:
        """aria-label match should score highest."""
        engine = SelectorEngine()
        elements = [
            {
                "tag": "button",
                "text": "Submit",
                "ariaLabel": "Submit form",
                "role": "button",
                "testId": "",
                "type": "",
                "name": "",
                "placeholder": "",
                "className": "btn-primary",
                "id": "submit-btn",
                "href": "",
                "rect": {"x": 0, "y": 0, "w": 100, "h": 40},
            },
        ]
        selector = engine._best_match("Submit form", elements)
        assert selector.strategy == SelectorStrategy.ARIA_LABEL
        assert "aria-label" in selector.primary

    def test_best_match_text(self) -> None:
        """Visible text match when no aria-label."""
        engine = SelectorEngine()
        elements = [
            {
                "tag": "button",
                "text": "Click Here",
                "ariaLabel": "",
                "role": "",
                "testId": "",
                "type": "",
                "name": "",
                "placeholder": "",
                "className": "",
                "id": "",
                "href": "",
                "rect": {"x": 0, "y": 0, "w": 100, "h": 40},
            },
        ]
        selector = engine._best_match("Click Here", elements)
        assert "Click Here" in selector.primary

    def test_best_match_no_match(self) -> None:
        """Should return text-based fallback when no match found."""
        engine = SelectorEngine()
        selector = engine._best_match("nonexistent element", [])
        assert "nonexistent element" in selector.primary
        assert selector.strategy == SelectorStrategy.VISIBLE_TEXT

    def test_text_overlap(self) -> None:
        """Test word overlap calculation."""
        assert SelectorEngine._text_overlap("submit form", "submit form") == 1.0
        assert SelectorEngine._text_overlap("submit", "submit form") == 0.5
        assert SelectorEngine._text_overlap("hello", "world") == 0.0
        assert SelectorEngine._text_overlap("", "") == 0.0

    def test_build_label_xpath(self) -> None:
        """Test label-based XPath generation."""
        xpath = SelectorEngine.build_label_xpath("Submit", "button")
        assert "//button[" in xpath
        assert "@aria-label='Submit'" in xpath
        assert "contains(text(), 'Submit')" in xpath
        assert "@placeholder='Submit'" in xpath

    def test_generate_selector_with_testid(self) -> None:
        """data-testid should be included as fallback."""
        engine = SelectorEngine()
        element = {
            "tag": "button",
            "text": "Submit",
            "ariaLabel": "Submit",
            "role": "button",
            "testId": "submit-btn",
            "type": "",
            "name": "",
            "placeholder": "",
            "className": "btn",
            "id": "",
            "href": "",
            "rect": {"x": 0, "y": 0, "w": 100, "h": 40},
        }
        selector = engine._generate_selector(element, "Submit")
        all_selectors = [selector.primary] + selector.fallbacks
        has_testid = any("data-testid" in s for s in all_selectors)
        assert has_testid

    def test_score_button_hint(self) -> None:
        """Button keyword in description should boost button elements."""
        engine = SelectorEngine()
        element = {
            "tag": "button",
            "text": "OK",
            "ariaLabel": "",
            "role": "",
            "testId": "",
            "className": "",
        }
        score = engine._score_element("ok button", element)
        assert score > 0

    @pytest.mark.asyncio
    async def test_find_element_no_page(self) -> None:
        """Should raise error if no page is set."""
        engine = SelectorEngine()
        with pytest.raises(RuntimeError, match="No page"):
            await engine.find_element("Submit")

    @pytest.mark.asyncio
    async def test_find_element_with_mock_page(self, mock_page: AsyncMock) -> None:
        """Should work with mock page returning elements."""
        mock_page.evaluate = AsyncMock(return_value=[
            {
                "tag": "button",
                "text": "Login",
                "ariaLabel": "Log in to your account",
                "role": "button",
                "testId": "login-btn",
                "type": "submit",
                "name": "",
                "placeholder": "",
                "className": "auth-button",
                "id": "login",
                "href": "",
                "rect": {"x": 200, "y": 300, "w": 120, "h": 40},
            },
        ])
        engine = SelectorEngine(page=mock_page)
        selector = await engine.find_element("Log in")
        assert selector is not None
        assert selector.primary != ""
