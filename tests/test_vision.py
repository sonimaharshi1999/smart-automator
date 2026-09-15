# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for vision modules: screen_capture, overlay."""

from __future__ import annotations

import io
import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest

from smart_automator.vision.screen_capture import CaptureConfig, ScreenCapture
from smart_automator.vision.overlay import PointerStyle, VisualOverlay


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_png_bytes(width: int = 10, height: int = 10) -> bytes:
    """Create minimal valid PNG bytes via PIL for testing."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ===========================================================================
# CaptureConfig Tests
# ===========================================================================

class TestCaptureConfig:
    """Tests for CaptureConfig defaults and overrides."""

    def test_default_config(self) -> None:
        cfg = CaptureConfig()
        assert cfg.interval_s == 1.5
        assert cfg.monitor_index == 0
        assert cfg.region is None
        assert cfg.scale_factor == 0.5
        assert cfg.output_format == "png"
        assert cfg.max_history == 10

    def test_custom_config(self) -> None:
        cfg = CaptureConfig(
            interval_s=0.5,
            monitor_index=1,
            region=(0, 0, 800, 600),
            scale_factor=1.0,
        )
        assert cfg.interval_s == 0.5
        assert cfg.monitor_index == 1
        assert cfg.region == (0, 0, 800, 600)
        assert cfg.scale_factor == 1.0


# ===========================================================================
# ScreenCapture Tests
# ===========================================================================

class TestScreenCapture:
    """Tests for ScreenCapture (all screen access mocked)."""

    def test_default_construction(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path / "caps")
        cap = ScreenCapture(config=cfg)
        assert cap.is_running is False
        assert (tmp_path / "caps").exists()

    def test_construction_without_config(self) -> None:
        with patch.object(Path, "mkdir"):
            cap = ScreenCapture()
        assert cap.is_running is False

    def test_is_running_property(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path)
        cap = ScreenCapture(config=cfg)
        assert cap.is_running is False
        cap._running = True
        assert cap.is_running is True

    def test_capture_once_with_mss(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path, scale_factor=1.0)
        cap = ScreenCapture(config=cfg)

        from PIL import Image
        pil_img = Image.new("RGB", (100, 100))

        mock_mss = MagicMock()
        mock_sct = MagicMock()
        mock_sct.monitors = [
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        ]
        fake_screenshot = MagicMock()
        fake_screenshot.size = (100, 100)
        fake_screenshot.bgra = b"\x00" * (100 * 100 * 4)
        mock_sct.grab.return_value = fake_screenshot
        mock_mss.mss.return_value.__enter__ = MagicMock(return_value=mock_sct)
        mock_mss.mss.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict("sys.modules", {"mss": mock_mss}), \
             patch.object(ScreenCapture, "_mss_to_pil", return_value=pil_img):
            result = cap.capture_once()

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_capture_once_fallback(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path, scale_factor=1.0)
        cap = ScreenCapture(config=cfg)

        from PIL import Image
        fake_img = Image.new("RGB", (100, 100))

        with patch.dict("sys.modules", {"mss": None}), \
             patch("PIL.ImageGrab.grab", return_value=fake_img):
            result = cap._capture_fallback()

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_save_screenshot(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path)
        cap = ScreenCapture(config=cfg)
        png = _make_png_bytes()
        path = cap.save_screenshot(png, "test_shot.png")
        assert path.exists()
        assert path.name == "test_shot.png"
        assert path.read_bytes() == png

    def test_get_latest_empty_history(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path)
        cap = ScreenCapture(config=cfg)
        assert cap.get_latest() is None

    def test_get_latest_returns_last(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path)
        cap = ScreenCapture(config=cfg)
        cap._history = [b"frame1", b"frame2", b"frame3"]
        assert cap.get_latest() == b"frame3"

    def test_start_continuous_sets_running(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path)
        cap = ScreenCapture(config=cfg)

        with patch.object(cap, "_capture_loop"):
            cap.start_continuous()
            time.sleep(0.1)
            assert cap._running is True
            cap.stop()

    def test_start_continuous_idempotent(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path)
        cap = ScreenCapture(config=cfg)
        cap._running = True  # Already running
        cap.start_continuous()  # Should return early
        assert cap._thread is None  # No new thread created

    def test_stop(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path)
        cap = ScreenCapture(config=cfg)
        cap._running = True
        cap._stop_event.clear()
        mock_thread = MagicMock()
        cap._thread = mock_thread
        cap.stop()
        assert cap._running is False
        assert cap._stop_event.is_set()
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_compute_change_identical_frames(self) -> None:
        frame = np.full((10, 10, 3), 128, dtype=np.uint8)
        assert ScreenCapture._compute_change(frame, frame) == 0.0

    def test_compute_change_totally_different(self) -> None:
        black = np.zeros((10, 10, 3), dtype=np.uint8)
        white = np.full((10, 10, 3), 255, dtype=np.uint8)
        change = ScreenCapture._compute_change(black, white)
        assert change == 1.0

    def test_compute_change_different_shapes(self) -> None:
        a = np.zeros((10, 10, 3), dtype=np.uint8)
        b = np.zeros((20, 20, 3), dtype=np.uint8)
        assert ScreenCapture._compute_change(a, b) == 1.0

    def test_history_max_cap(self, tmp_path: Path) -> None:
        cfg = CaptureConfig(output_dir=tmp_path, max_history=3)
        cap = ScreenCapture(config=cfg)
        cap._history = [b"f1", b"f2", b"f3"]
        # Simulate adding one more in _capture_loop logic
        cap._history.append(b"f4")
        if len(cap._history) > cfg.max_history:
            cap._history.pop(0)
        assert len(cap._history) == 3
        assert cap._history[0] == b"f2"


# ===========================================================================
# PointerStyle Tests
# ===========================================================================

class TestPointerStyle:
    """Tests for PointerStyle defaults."""

    def test_default_style(self) -> None:
        s = PointerStyle()
        assert s.color == "#FF4444"
        assert s.ring_radius == 30
        assert s.ring_width == 3
        assert s.label_font_size == 14
        assert s.pulse_enabled is True

    def test_custom_style(self) -> None:
        s = PointerStyle(color="#00FF00", ring_radius=50, pulse_enabled=False)
        assert s.color == "#00FF00"
        assert s.ring_radius == 50
        assert s.pulse_enabled is False


# ===========================================================================
# VisualOverlay Tests
# ===========================================================================

class TestVisualOverlay:
    """Tests for VisualOverlay (tkinter fully mocked)."""

    def test_default_construction(self) -> None:
        overlay = VisualOverlay()
        assert overlay.is_active is False
        assert overlay._style.color == "#FF4444"

    def test_custom_style_construction(self) -> None:
        style = PointerStyle(color="#0000FF", ring_radius=40)
        overlay = VisualOverlay(style=style)
        assert overlay._style.color == "#0000FF"
        assert overlay._style.ring_radius == 40

    def test_is_active_property(self) -> None:
        overlay = VisualOverlay()
        assert overlay.is_active is False
        overlay._running = True
        assert overlay.is_active is True

    def test_start_sets_running(self) -> None:
        overlay = VisualOverlay()
        with patch.object(overlay, "_create_window"):
            overlay.start()
            time.sleep(0.05)
            assert overlay._running is True
            overlay._running = False  # cleanup

    def test_start_idempotent(self) -> None:
        overlay = VisualOverlay()
        overlay._running = True
        overlay.start()  # Should return early
        assert overlay._thread is None  # No new thread created

    def test_stop_clears_state(self) -> None:
        overlay = VisualOverlay()
        overlay._running = True
        mock_root = MagicMock()
        overlay._root = mock_root
        overlay._canvas = MagicMock()

        overlay.stop()

        assert overlay._running is False
        assert overlay._root is None
        assert overlay._canvas is None
        mock_root.destroy.assert_called_once()

    def test_stop_handles_destroy_error(self) -> None:
        overlay = VisualOverlay()
        overlay._running = True
        mock_root = MagicMock()
        mock_root.destroy.side_effect = RuntimeError("tk error")
        overlay._root = mock_root

        overlay.stop()  # Should not raise
        assert overlay._running is False

    def test_point_at_queues_action(self) -> None:
        overlay = VisualOverlay()
        overlay.point_at(100, 200, label="Click here", duration_s=2.0)
        assert len(overlay._pending_actions) == 1
        action = overlay._pending_actions[0]
        assert action[1] == 100  # x
        assert action[2] == 200  # y
        assert action[3] == "Click here"

    def test_highlight_region_queues_action(self) -> None:
        overlay = VisualOverlay()
        overlay.highlight_region(10, 20, 300, 400, label="Region", duration_s=5.0)
        assert len(overlay._pending_actions) == 1
        action = overlay._pending_actions[0]
        assert action[1] == 10  # x
        assert action[2] == 20  # y
        assert action[3] == 300  # w
        assert action[4] == 400  # h

    def test_clear_removes_items(self) -> None:
        overlay = VisualOverlay()
        mock_canvas = MagicMock()
        overlay._canvas = mock_canvas
        overlay._items = [1, 2, 3]
        overlay._clear()
        assert overlay._items == []
        assert mock_canvas.delete.call_count == 3

    def test_clear_handles_canvas_error(self) -> None:
        overlay = VisualOverlay()
        mock_canvas = MagicMock()
        mock_canvas.delete.side_effect = RuntimeError("tk error")
        overlay._canvas = mock_canvas
        overlay._items = [1]
        overlay._clear()  # Should not raise
        assert overlay._items == []

    def test_draw_pointer_no_canvas_is_noop(self) -> None:
        overlay = VisualOverlay()
        overlay._canvas = None
        overlay._draw_pointer(100, 200, "test", 1.0)  # Should not raise

    def test_draw_highlight_no_canvas_is_noop(self) -> None:
        overlay = VisualOverlay()
        overlay._canvas = None
        overlay._draw_highlight(0, 0, 100, 100, "test", 1.0)  # Should not raise
