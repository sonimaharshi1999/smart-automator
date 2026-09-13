# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Fallback strategies when primary selectors and healing both fail."""

from __future__ import annotations

from typing import Any

from smart_automator.models import Selector, SelectorStrategy


class FallbackStrategy:
    """Provides fallback strategies when selectors break.

    Strategies (in order):
    1. Broader text-based selector
    2. Role-based selector
    3. Visual position matching
    4. Full page scan for interactive elements
    """

    @staticmethod
    def broaden_text_selector(selector: Selector) -> Selector:
        """Make a text selector less specific."""
        text = selector.primary
        if text.startswith("text="):
            text = text[5:]

        # Try partial match
        words = text.split()
        if len(words) > 2:
            # Use first two significant words
            short_text = " ".join(words[:2])
            return Selector(
                primary=f"text=/{short_text}/i",
                strategy=SelectorStrategy.VISIBLE_TEXT,
                fallbacks=[
                    f"//*[contains(text(), '{short_text}')]",
                    f"//*[contains(normalize-space(.), '{short_text}')]",
                ],
                description=f"Broadened: {selector.description}",
            )

        return Selector(
            primary=f"text=/{text}/i",
            strategy=SelectorStrategy.VISIBLE_TEXT,
            fallbacks=[f"//*[contains(text(), '{text}')]"],
            description=f"Case-insensitive: {selector.description}",
        )

    @staticmethod
    def role_based_fallback(
        element_description: str,
    ) -> Selector:
        """Generate a role-based selector from element description."""
        desc = element_description.lower()

        role_map = {
            "button": "button",
            "link": "link",
            "input": "textbox",
            "text field": "textbox",
            "text area": "textbox",
            "checkbox": "checkbox",
            "radio": "radio",
            "dropdown": "combobox",
            "select": "combobox",
            "tab": "tab",
            "menu": "menu",
            "dialog": "dialog",
            "heading": "heading",
        }

        for keyword, role in role_map.items():
            if keyword in desc:
                return Selector(
                    primary=f"role={role}",
                    strategy=SelectorStrategy.ROLE,
                    description=f"Role fallback for: {element_description}",
                )

        return Selector(
            primary="role=button",
            strategy=SelectorStrategy.ROLE,
            description=f"Generic role fallback for: {element_description}",
        )

    @staticmethod
    async def scan_interactive_elements(page: Any) -> list[dict[str, str]]:
        """Scan the page for all interactive elements.

        Returns a list of elements with their selectors and descriptions.
        Useful as a last resort when targeted selectors fail.
        """
        js_scan = """
        () => {
            const interactive = document.querySelectorAll(
                'button, a, input, textarea, select, [role="button"], ' +
                '[role="link"], [onclick], [tabindex]'
            );
            return Array.from(interactive).map(el => {
                const rect = el.getBoundingClientRect();
                return {
                    tag: el.tagName.toLowerCase(),
                    text: (el.textContent || '').trim().substring(0, 50),
                    ariaLabel: el.getAttribute('aria-label') || '',
                    role: el.getAttribute('role') || '',
                    visible: rect.width > 0 && rect.height > 0,
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                };
            }).filter(e => e.visible);
        }
        """
        try:
            return await page.evaluate(js_scan)
        except Exception:
            return []

    @staticmethod
    def position_based_selector(x: int, y: int) -> Selector:
        """Generate a position-based selector as absolute last resort.

        This is brittle and should only be used when all other
        strategies have failed.
        """
        js_selector = (
            f"document.elementFromPoint({x}, {y})"
        )
        return Selector(
            primary=f"js={js_selector}",
            strategy=SelectorStrategy.XPATH,
            description=f"Position-based fallback at ({x}, {y})",
        )
