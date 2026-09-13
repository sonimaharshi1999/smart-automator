# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""AI-powered selector generation from live page state.

This is the core innovation: instead of maintaining Page Object Model files,
the selector engine generates resilient selectors dynamically by analyzing
the current page DOM. Priority order:
  aria-label > visible text > role > data-testid > CSS class > xpath
"""

from __future__ import annotations

from typing import Any

from smart_automator.models import Selector, SelectorStrategy


# JavaScript to extract element info from the page
ELEMENT_EXTRACTION_JS = """
(description) => {
    const results = [];
    const all = document.querySelectorAll(
        'button, a, input, textarea, select, [role], [aria-label], [data-testid]'
    );
    for (const el of all) {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;
        results.push({
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || '').trim().substring(0, 100),
            ariaLabel: el.getAttribute('aria-label') || '',
            role: el.getAttribute('role') || '',
            testId: el.getAttribute('data-testid') || '',
            type: el.getAttribute('type') || '',
            name: el.getAttribute('name') || '',
            placeholder: el.getAttribute('placeholder') || '',
            className: el.className || '',
            id: el.id || '',
            href: el.getAttribute('href') || '',
            rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height }
        });
    }
    return results;
}
"""


class SelectorEngine:
    """Generates resilient selectors from live page analysis.

    No POM needed. The engine examines the current page state
    and builds selectors using the most stable attributes available.
    """

    # Selector generation priority
    PRIORITIES: list[SelectorStrategy] = [
        SelectorStrategy.ARIA_LABEL,
        SelectorStrategy.VISIBLE_TEXT,
        SelectorStrategy.ROLE,
        SelectorStrategy.DATA_TESTID,
        SelectorStrategy.CSS_CLASS,
        SelectorStrategy.XPATH,
    ]

    def __init__(self, page: Any = None) -> None:
        self._page = page

    def set_page(self, page: Any) -> None:
        """Set the Playwright page to analyze."""
        self._page = page

    async def find_element(self, description: str) -> Selector:
        """Find the best selector for an element described in natural language.

        Extracts all interactive elements from the page and matches
        against the description using text similarity.
        """
        if not self._page:
            raise RuntimeError("No page set for selector engine")

        elements = await self._page.evaluate(ELEMENT_EXTRACTION_JS, description)
        return self._best_match(description, elements)

    def _best_match(
        self, description: str, elements: list[dict[str, Any]]
    ) -> Selector:
        """Find the best matching element and generate selectors."""
        description_lower = description.lower()
        scored: list[tuple[float, dict[str, Any]]] = []

        for el in elements:
            score = self._score_element(description_lower, el)
            if score > 0:
                scored.append((score, el))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            # Fallback: generate a broad text-based selector
            return Selector(
                primary=f"text={description}",
                strategy=SelectorStrategy.VISIBLE_TEXT,
                fallbacks=[f"//*[contains(text(), '{description}')]"],
                description=description,
            )

        best = scored[0][1]
        return self._generate_selector(best, description)

    def _score_element(
        self, description: str, element: dict[str, Any]
    ) -> float:
        """Score how well an element matches a description."""
        score = 0.0
        desc_words = set(description.split())

        # Aria label match (highest value)
        aria = element.get("ariaLabel", "").lower()
        if aria and self._text_overlap(description, aria) > 0.5:
            score += 10.0

        # Visible text match
        text = element.get("text", "").lower()
        if text:
            overlap = self._text_overlap(description, text)
            score += overlap * 7.0

        # Role match
        role = element.get("role", "").lower()
        if role and role in description:
            score += 3.0

        # Placeholder match (for inputs)
        placeholder = element.get("placeholder", "").lower()
        if placeholder and self._text_overlap(description, placeholder) > 0.3:
            score += 5.0

        # Tag type hints
        tag = element.get("tag", "")
        if "button" in description and tag == "button":
            score += 2.0
        if "link" in description and tag == "a":
            score += 2.0
        if "input" in description and tag == "input":
            score += 2.0

        return score

    @staticmethod
    def _text_overlap(a: str, b: str) -> float:
        """Calculate word overlap ratio between two strings."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        return len(intersection) / max(len(words_a), len(words_b))

    def _generate_selector(
        self, element: dict[str, Any], description: str
    ) -> Selector:
        """Generate a prioritized selector with fallbacks."""
        selectors: list[tuple[SelectorStrategy, str]] = []

        # Priority 1: aria-label
        aria = element.get("ariaLabel", "")
        if aria:
            selectors.append(
                (SelectorStrategy.ARIA_LABEL, f'[aria-label="{aria}"]')
            )

        # Priority 2: visible text
        text = element.get("text", "").strip()
        if text and len(text) < 50:
            selectors.append(
                (SelectorStrategy.VISIBLE_TEXT, f"text={text}")
            )

        # Priority 3: role
        role = element.get("role", "")
        tag = element.get("tag", "")
        if role:
            if text:
                selectors.append(
                    (SelectorStrategy.ROLE, f'role={role}[name="{text[:30]}"]')
                )
            else:
                selectors.append(
                    (SelectorStrategy.ROLE, f"role={role}")
                )

        # Priority 4: data-testid
        test_id = element.get("testId", "")
        if test_id:
            selectors.append(
                (SelectorStrategy.DATA_TESTID, f'[data-testid="{test_id}"]')
            )

        # Priority 5: CSS class + tag
        class_name = element.get("className", "")
        if class_name and isinstance(class_name, str):
            first_class = class_name.split()[0] if class_name.split() else ""
            if first_class:
                selectors.append(
                    (SelectorStrategy.CSS_CLASS, f"{tag}.{first_class}")
                )

        # Priority 6: XPath fallback
        el_id = element.get("id", "")
        if el_id:
            selectors.append(
                (SelectorStrategy.XPATH, f'//*[@id="{el_id}"]')
            )

        if not selectors:
            return Selector(
                primary=f"text={description}",
                strategy=SelectorStrategy.VISIBLE_TEXT,
                description=description,
            )

        primary_strategy, primary_sel = selectors[0]
        fallbacks = [s[1] for s in selectors[1:]]

        return Selector(
            primary=primary_sel,
            strategy=primary_strategy,
            fallbacks=fallbacks,
            description=description,
        )

    @staticmethod
    def build_label_xpath(label: str, tag: str = "*") -> str:
        """Build a label-based XPath selector.

        This is the 2026 pattern: use user-facing labels that
        almost never change, instead of brittle CSS selectors.
        """
        return (
            f"//{tag}["
            f"@aria-label='{label}' or "
            f"contains(text(), '{label}') or "
            f"@placeholder='{label}' or "
            f"@title='{label}'"
            f"]"
        )
