# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Continuous screen capture for real-time AI vision analysis."""

from __future__ import annotations

import io
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np


@dataclass
class CaptureConfig:
    """Screen capture configuration."""
    interval_s: float = 1.5
    monitor_index: int = 0
    region: tuple[int, int, int, int] | None = None
    scale_factor: float = 0.5
    output_format: str = "png"
    output_dir: Path = field(default_factory=lambda: Path("screenshots"))
    max_history: int = 10


class ScreenCapture:
    """Continuous screen capture with change detection.

    Captures the screen at regular intervals and detects significant
    visual changes to trigger AI analysis only when needed.
    """

    def __init__(self, config: CaptureConfig | None = None) -> None:
        self._config = config or CaptureConfig()
        self._running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_frame: np.ndarray | None = None
        self._history: list[bytes] = []
        self._config.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_running(self) -> bool:
        return self._running

    def capture_once(self) -> bytes:
        """Capture a single screenshot, return as PNG bytes."""
        try:
            import mss

            with mss.mss() as sct:
                monitors = sct.monitors
                mon_idx = min(self._config.monitor_index + 1, len(monitors) - 1)
                monitor = monitors[mon_idx]

                if self._config.region:
                    x, y, w, h = self._config.region
                    monitor = {"left": x, "top": y, "width": w, "height": h}

                screenshot = sct.grab(monitor)
                img = self._mss_to_pil(screenshot)

                if self._config.scale_factor != 1.0:
                    new_w = int(img.width * self._config.scale_factor)
                    new_h = int(img.height * self._config.scale_factor)
                    img = img.resize((new_w, new_h))

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()

        except ImportError:
            return self._capture_fallback()

    def _capture_fallback(self) -> bytes:
        """Fallback capture using PIL.ImageGrab (Windows/macOS only)."""
        from PIL import ImageGrab

        img = ImageGrab.grab()
        if self._config.scale_factor != 1.0:
            new_w = int(img.width * self._config.scale_factor)
            new_h = int(img.height * self._config.scale_factor)
            img = img.resize((new_w, new_h))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def _mss_to_pil(screenshot: Any) -> Any:
        """Convert mss screenshot to PIL Image."""
        from PIL import Image
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    def start_continuous(
        self,
        on_frame: Callable[[bytes], None] | None = None,
        on_change: Callable[[bytes], None] | None = None,
        change_threshold: float = 0.05,
    ) -> None:
        """Start continuous screen capture in a background thread.

        Args:
            on_frame: Called on every capture with PNG bytes.
            on_change: Called only when significant visual change detected.
            change_threshold: Percentage of pixels changed to trigger on_change (0.0-1.0).
        """
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop,
            args=(on_frame, on_change, change_threshold),
            daemon=True,
        )
        self._thread.start()

    def _capture_loop(
        self,
        on_frame: Callable[[bytes], None] | None,
        on_change: Callable[[bytes], None] | None,
        change_threshold: float,
    ) -> None:
        """Continuous capture loop running in background thread."""
        while not self._stop_event.is_set():
            try:
                frame_bytes = self.capture_once()

                self._history.append(frame_bytes)
                if len(self._history) > self._config.max_history:
                    self._history.pop(0)

                if on_frame:
                    on_frame(frame_bytes)

                if on_change:
                    current = self._bytes_to_array(frame_bytes)
                    if self._last_frame is not None and current is not None:
                        change_pct = self._compute_change(self._last_frame, current)
                        if change_pct > change_threshold:
                            on_change(frame_bytes)
                    elif current is not None:
                        on_change(frame_bytes)

                    if current is not None:
                        self._last_frame = current

            except Exception:
                pass

            self._stop_event.wait(self._config.interval_s)

        self._running = False

    @staticmethod
    def _bytes_to_array(png_bytes: bytes) -> np.ndarray | None:
        """Convert PNG bytes to numpy array for change detection."""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(png_bytes))
            return np.array(img)
        except Exception:
            return None

    @staticmethod
    def _compute_change(prev: np.ndarray, curr: np.ndarray) -> float:
        """Compute percentage of changed pixels between two frames."""
        if prev.shape != curr.shape:
            return 1.0
        diff = np.abs(prev.astype(np.int16) - curr.astype(np.int16))
        changed = (diff.mean(axis=-1) > 20).sum()
        total = prev.shape[0] * prev.shape[1]
        return changed / total if total > 0 else 0.0

    def stop(self) -> None:
        """Stop continuous capture."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._running = False

    def save_screenshot(self, png_bytes: bytes, filename: str = "screen.png") -> Path:
        """Save a screenshot to the output directory."""
        path = self._config.output_dir / filename
        path.write_bytes(png_bytes)
        return path

    def get_latest(self) -> bytes | None:
        """Get the most recent captured frame."""
        return self._history[-1] if self._history else None
