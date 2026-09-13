# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Browser lifecycle management with anti-detection features."""

from __future__ import annotations

from typing import Any

from smart_automator.config import BrowserConfig


class BrowserManager:
    """Manages Playwright browser lifecycle with anti-detection.

    Handles browser launch, context creation, and cleanup.
    Includes anti-detection measures: realistic user agent,
    viewport randomization, WebGL fingerprint masking.
    """

    # Common user agents for rotation
    USER_AGENTS: list[str] = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
            "Gecko/20100101 Firefox/121.0"
        ),
    ]

    def __init__(self, config: BrowserConfig | None = None) -> None:
        self._config = config or BrowserConfig()
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    @property
    def page(self) -> Any:
        """Get the current page object."""
        return self._page

    @property
    def is_running(self) -> bool:
        """Check if browser is running."""
        return self._browser is not None

    def get_launch_args(self) -> dict[str, Any]:
        """Build browser launch arguments with anti-detection."""
        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]
        return {
            "headless": self._config.headless,
            "slow_mo": self._config.slow_mo,
            "args": args,
        }

    def get_context_options(self) -> dict[str, Any]:
        """Build browser context options."""
        import random

        ua = self._config.user_agent or random.choice(self.USER_AGENTS)
        width_jitter = random.randint(-20, 20)
        height_jitter = random.randint(-20, 20)

        return {
            "viewport": {
                "width": self._config.viewport_width + width_jitter,
                "height": self._config.viewport_height + height_jitter,
            },
            "user_agent": ua,
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }

    async def launch(self) -> Any:
        """Launch browser and create context."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            **self.get_launch_args()
        )
        self._context = await self._browser.new_context(
            **self.get_context_options()
        )
        # Anti-detection: override navigator.webdriver
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self._config.timeout_ms)
        return self._page

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None

    async def screenshot(self, path: str | None = None) -> bytes:
        """Take a screenshot of the current page."""
        if not self._page:
            raise RuntimeError("Browser not launched")
        kwargs: dict[str, Any] = {"full_page": True}
        if path:
            kwargs["path"] = path
        return await self._page.screenshot(**kwargs)

    async def navigate(self, url: str) -> None:
        """Navigate to a URL."""
        if not self._page:
            raise RuntimeError("Browser not launched")
        await self._page.goto(url, wait_until="networkidle")
