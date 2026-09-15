# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Visual overlay with animated buddy cursor (like Clicky's pointer)."""

from __future__ import annotations

import math
import platform
import threading
import time
from dataclasses import dataclass
from typing import Any

from smart_automator.humanizer.mouse import HumanMouse


@dataclass
class PointerStyle:
    """Visual pointer appearance."""
    color: str = "#FF4444"
    buddy_color: str = "#00AAFF"
    ring_radius: int = 30
    ring_width: int = 3
    arrow_size: int = 24
    label_font_size: int = 14
    label_bg_color: str = "#222222"
    label_text_color: str = "#FFFFFF"
    animation_duration_ms: int = 300
    pulse_enabled: bool = True
    buddy_trail_length: int = 5
    buddy_glow: bool = True


class BuddyCursor:
    """Animated companion cursor that glides independently from the real mouse.

    Moves along Bezier paths to target coordinates while the AI speaks,
    creating the signature Clicky-like pointing experience.
    """

    def __init__(self, canvas: Any, style: PointerStyle) -> None:
        self._canvas = canvas
        self._style = style
        self._x = 0.0
        self._y = 0.0
        self._target_x = 0.0
        self._target_y = 0.0
        self._items: list[int] = []
        self._trail: list[tuple[float, float]] = []
        self._mouse = HumanMouse(steps=30, jitter_px=1.0, overshoot_probability=0.1)
        self._animating = False
        self._visible = False

    @property
    def position(self) -> tuple[float, float]:
        return (self._x, self._y)

    @property
    def is_animating(self) -> bool:
        return self._animating

    def show(self, x: float, y: float) -> None:
        """Show buddy cursor at position instantly."""
        self._x = x
        self._y = y
        self._visible = True
        self._draw()

    def hide(self) -> None:
        """Hide the buddy cursor."""
        self._visible = False
        self._clear()

    def move_to(
        self,
        target_x: float,
        target_y: float,
        on_arrive: Any = None,
    ) -> None:
        """Animate buddy cursor to target using Bezier path."""
        if not self._canvas:
            return

        self._target_x = target_x
        self._target_y = target_y
        self._visible = True

        path = self._mouse.generate_path(self._x, self._y, target_x, target_y)
        timings = self._mouse.generate_timing(len(path))
        self._animating = True
        self._animate_along_path(path, timings, 0, on_arrive)

    def _animate_along_path(
        self,
        path: list[tuple[float, float]],
        timings: list[int],
        idx: int,
        on_arrive: Any,
    ) -> None:
        """Step through the Bezier path one frame at a time."""
        if not self._canvas or idx >= len(path):
            self._animating = False
            if on_arrive:
                on_arrive()
            return

        px, py = path[idx]
        self._trail.append((self._x, self._y))
        if len(self._trail) > self._style.buddy_trail_length:
            self._trail.pop(0)

        self._x = px
        self._y = py
        self._draw()

        delay = max(5, timings[idx] if idx < len(timings) else 15)
        self._canvas.after(delay, lambda: self._animate_along_path(path, timings, idx + 1, on_arrive))

    def _draw(self) -> None:
        """Draw the buddy cursor sprite at current position."""
        if not self._canvas or not self._visible:
            return

        self._clear()
        x, y = self._x, self._y
        color = self._style.buddy_color
        size = self._style.arrow_size

        # Trail (fading dots behind cursor)
        for i, (tx, ty) in enumerate(self._trail):
            alpha_ratio = (i + 1) / (len(self._trail) + 1)
            r = max(2, int(4 * alpha_ratio))
            trail_dot = self._canvas.create_oval(
                tx - r, ty - r, tx + r, ty + r,
                fill=color, outline="",
            )
            self._items.append(trail_dot)

        # Glow circle behind cursor
        if self._style.buddy_glow:
            glow_r = size + 6
            glow = self._canvas.create_oval(
                x - glow_r, y - glow_r, x + glow_r, y + glow_r,
                outline=color, width=1,
            )
            self._items.append(glow)

        # Arrow pointer (triangle pointing down-left, like a cursor)
        tip_x, tip_y = x, y
        wing1_x = x + size * 0.7
        wing1_y = y - size * 0.9
        wing2_x = x + size * 0.15
        wing2_y = y - size * 0.55
        wing3_x = x + size * 0.9
        wing3_y = y - size * 0.55

        # Main arrow body
        arrow = self._canvas.create_polygon(
            tip_x, tip_y,
            wing1_x, wing1_y,
            wing2_x, wing2_y,
            fill=color, outline="white", width=2,
        )
        self._items.append(arrow)

        # Small dot at tip for precision
        dot = self._canvas.create_oval(
            x - 3, y - 3, x + 3, y + 3,
            fill="white", outline="",
        )
        self._items.append(dot)

    def _clear(self) -> None:
        """Remove all buddy cursor canvas items."""
        if self._canvas:
            for item in self._items:
                try:
                    self._canvas.delete(item)
                except Exception:
                    pass
        self._items.clear()


class VisualOverlay:
    """Transparent fullscreen overlay with animated buddy cursor.

    Creates an always-on-top transparent window using tkinter.
    Features:
    - Animated buddy cursor that glides via Bezier paths (like Clicky)
    - Pulsing target rings at destination
    - Floating labels next to targets
    - Region highlighting
    """

    def __init__(self, style: PointerStyle | None = None) -> None:
        self._style = style or PointerStyle()
        self._root: Any = None
        self._canvas: Any = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._items: list[int] = []
        self._pending_actions: list[tuple] = []
        self._lock = threading.Lock()
        self._buddy: BuddyCursor | None = None

    @property
    def is_active(self) -> bool:
        return self._running

    @property
    def buddy(self) -> BuddyCursor | None:
        return self._buddy

    def start(self) -> None:
        """Start the overlay window in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._create_window, daemon=True)
        self._thread.start()
        time.sleep(0.3)

    def _create_window(self) -> None:
        """Create the transparent tkinter overlay window."""
        try:
            import tkinter as tk

            self._root = tk.Tk()
            self._root.title("SmartAutomator Overlay")
            self._root.attributes("-topmost", True)
            self._root.overrideredirect(True)

            screen_w = self._root.winfo_screenwidth()
            screen_h = self._root.winfo_screenheight()
            self._root.geometry(f"{screen_w}x{screen_h}+0+0")

            system = platform.system()
            if system == "Windows":
                self._root.attributes("-transparentcolor", "black")
                self._root.config(bg="black")
            elif system == "Darwin":
                self._root.attributes("-transparent", True)
                self._root.config(bg="systemTransparent")
            else:
                self._root.attributes("-alpha", 0.8)
                self._root.config(bg="black")

            self._root.attributes("-alpha", 0.85)

            self._canvas = tk.Canvas(
                self._root,
                width=screen_w,
                height=screen_h,
                highlightthickness=0,
                bg="black" if system == "Windows" else "systemTransparent" if system == "Darwin" else "black",
            )
            self._canvas.pack()

            self._buddy = BuddyCursor(self._canvas, self._style)

            self._root.bind("<Escape>", lambda e: self.stop())

            self._poll_actions()
            self._root.mainloop()

        except Exception:
            self._running = False

    def _poll_actions(self) -> None:
        """Process pending drawing actions on the tkinter thread."""
        if not self._root or not self._running:
            return

        with self._lock:
            actions = list(self._pending_actions)
            self._pending_actions.clear()

        for action in actions:
            try:
                action[0](*action[1:])
            except Exception:
                pass

        if self._running and self._root:
            self._root.after(50, self._poll_actions)

    def point_at(self, x: int, y: int, label: str = "", duration_s: float = 3.0) -> None:
        """Animate buddy cursor to target, then draw ring and label."""
        with self._lock:
            self._pending_actions.append((self._buddy_point, x, y, label, duration_s))

    def _buddy_point(self, x: int, y: int, label: str, duration_s: float) -> None:
        """Move buddy cursor to target, draw ring on arrival."""
        if not self._canvas or not self._buddy:
            return

        if not self._buddy._visible:
            # First point — start from top-right corner
            screen_w = self._root.winfo_screenwidth() if self._root else 1920
            self._buddy.show(screen_w * 0.8, 100)

        def on_arrive() -> None:
            self._draw_target_ring(x, y, label, duration_s)

        self._buddy.move_to(float(x), float(y), on_arrive=on_arrive)

    def _draw_target_ring(self, x: int, y: int, label: str, duration_s: float) -> None:
        """Draw pulsing ring and label at the target location."""
        if not self._canvas:
            return

        self._clear_rings()
        r = self._style.ring_radius

        ring = self._canvas.create_oval(
            x - r, y - r, x + r, y + r,
            outline=self._style.color,
            width=self._style.ring_width,
        )
        self._items.append(ring)

        if label:
            label_x = x + r + 10
            label_y = y - 10

            bg = self._canvas.create_rectangle(
                label_x - 5, label_y - self._style.label_font_size,
                label_x + len(label) * 8 + 10, label_y + 8,
                fill=self._style.label_bg_color, outline="",
            )
            txt = self._canvas.create_text(
                label_x, label_y,
                text=label, anchor="sw",
                fill=self._style.label_text_color,
                font=("Consolas", self._style.label_font_size),
            )
            self._items.extend([bg, txt])

        if self._style.pulse_enabled:
            self._animate_pulse(x, y, r, 0)

        if duration_s > 0:
            self._root.after(int(duration_s * 1000), self._clear_rings)

    def _animate_pulse(self, x: int, y: int, base_r: int, step: int) -> None:
        """Animate a pulsing ring effect."""
        if not self._canvas or not self._running or step > 6:
            return

        expand = base_r + step * 5
        pulse = self._canvas.create_oval(
            x - expand, y - expand, x + expand, y + expand,
            outline=self._style.color, width=1,
        )
        self._items.append(pulse)
        self._root.after(80, lambda: self._fade_item(pulse))
        self._root.after(100, lambda: self._animate_pulse(x, y, base_r, step + 1))

    def _fade_item(self, item_id: int) -> None:
        """Remove a canvas item (simulates fade)."""
        if self._canvas:
            try:
                self._canvas.delete(item_id)
                if item_id in self._items:
                    self._items.remove(item_id)
            except Exception:
                pass

    def highlight_region(
        self, x: int, y: int, w: int, h: int,
        label: str = "", duration_s: float = 3.0,
    ) -> None:
        """Highlight a rectangular region on screen."""
        with self._lock:
            self._pending_actions.append(
                (self._draw_highlight, x, y, w, h, label, duration_s)
            )

    def _draw_highlight(
        self, x: int, y: int, w: int, h: int,
        label: str, duration_s: float,
    ) -> None:
        """Draw a highlight rectangle."""
        if not self._canvas:
            return

        self._clear_rings()
        rect = self._canvas.create_rectangle(
            x, y, x + w, y + h,
            outline=self._style.color, width=2, dash=(5, 3),
        )
        self._items.append(rect)

        if label:
            txt = self._canvas.create_text(
                x + w // 2, y - 5,
                text=label, anchor="s",
                fill=self._style.label_text_color,
                font=("Consolas", self._style.label_font_size),
            )
            self._items.append(txt)

        if duration_s > 0:
            self._root.after(int(duration_s * 1000), self._clear_rings)

    def _clear_rings(self) -> None:
        """Clear ring/highlight items (not the buddy cursor)."""
        if self._canvas:
            for item in self._items:
                try:
                    self._canvas.delete(item)
                except Exception:
                    pass
        self._items.clear()

    def _clear(self) -> None:
        """Clear all overlay items including buddy cursor."""
        self._clear_rings()
        if self._buddy:
            self._buddy.hide()

    def stop(self) -> None:
        """Close the overlay window."""
        self._running = False
        if self._buddy:
            self._buddy.hide()
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
        self._root = None
        self._canvas = None
        self._buddy = None
