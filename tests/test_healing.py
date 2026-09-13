# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for self-healing retry logic."""

import pytest

from smart_automator.healing.fallback import FallbackStrategy
from smart_automator.healing.retry import SelfHealingRetry
from smart_automator.models import (
    ActionStatus,
    ActionStep,
    ActionType,
    Selector,
    SelectorStrategy,
)


class TestSelfHealingRetry:
    """Tests for the self-healing retry system."""

    def test_broaden_text_selector(self) -> None:
        healer = SelfHealingRetry(max_retries=3)
        original = Selector(
            primary="text=Submit Form Now",
            strategy=SelectorStrategy.VISIBLE_TEXT,
            description="Submit button",
        )
        broadened = healer._broaden_selector(original)
        assert broadened.primary != original.primary
        assert "Submit" in broadened.primary

    def test_broaden_aria_selector(self) -> None:
        healer = SelfHealingRetry(max_retries=3)
        original = Selector(
            primary='[aria-label="Close dialog"]',
            strategy=SelectorStrategy.ARIA_LABEL,
            description="Close button",
        )
        broadened = healer._broaden_selector(original)
        # Broadened selector should be a contains() XPath
        assert "contains" in broadened.primary

    def test_healing_log(self) -> None:
        healer = SelfHealingRetry()
        assert healer.healing_log == []


class TestFallbackStrategy:
    """Tests for fallback strategies."""

    def test_broaden_text_long(self) -> None:
        original = Selector(
            primary="text=Submit Your Application Form Now",
            strategy=SelectorStrategy.VISIBLE_TEXT,
            description="Submit button",
        )
        broadened = FallbackStrategy.broaden_text_selector(original)
        assert "/i" in broadened.primary  # Case-insensitive

    def test_broaden_text_short(self) -> None:
        original = Selector(
            primary="text=Submit",
            strategy=SelectorStrategy.VISIBLE_TEXT,
            description="Submit",
        )
        broadened = FallbackStrategy.broaden_text_selector(original)
        assert "/i" in broadened.primary

    def test_role_based_fallback_button(self) -> None:
        selector = FallbackStrategy.role_based_fallback("Submit button")
        assert selector.strategy == SelectorStrategy.ROLE
        assert "button" in selector.primary

    def test_role_based_fallback_input(self) -> None:
        selector = FallbackStrategy.role_based_fallback("text field for email")
        assert "textbox" in selector.primary

    def test_role_based_fallback_link(self) -> None:
        selector = FallbackStrategy.role_based_fallback("link to home page")
        assert "link" in selector.primary

    def test_role_based_fallback_unknown(self) -> None:
        selector = FallbackStrategy.role_based_fallback("unknown element type")
        assert "button" in selector.primary  # Default fallback

    def test_position_based_selector(self) -> None:
        selector = FallbackStrategy.position_based_selector(100, 200)
        assert "100" in selector.primary
        assert "200" in selector.primary
