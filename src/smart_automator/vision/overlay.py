# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Visual overlay for pointing at screen elements (like Clicky's pointer)."""

from __future__ import annotations

import platform
import threading
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class PointerStyle:
    """Visual pointer appearance."""
    color: str = "#FF4444"
    ring_radius: int = 30
    ring_width: int = 3
    arrow_size: int = 20
    label_font_size: int = 14
    label_bg_color: str = "#222222"
    label_text_color: str = "#FFFFFF"
    animation_duration_ms: int = 300
    pulse_enabled: bool = True


class VisualOverlay:
    """Transparent fullscreen overlay that points at UI elements.

    Creates an always-on-top transparent window using tkinter.
    Renders animated pointers, labels, and highlight rings on
    target screen coordinates.
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

    @property
    def is_active(self) -> bool:
        return self._running

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
        """Point at a screen coordinate with an animated ring and optional label."""
        with self._lock:
            self._pending_actions.append((self._draw_pointer, x, y, label, duration_s))

    def _draw_pointer(self, x: int, y: int, label: str, duration_s: float) -> None:
        """Draw a pointer ring and label at coordinates."""
        if not self._canvas:
            return

        self._clear()
        r = self._style.ring_radius

        ring = self._canvas.create_oval(
            x - r, y - r, x + r, y + r,
            outline=self._style.color,
            width=self._style.ring_width,
        )
        self._items.append(ring)

        crosshair_v = self._canvas.create_line(
            x, y - r // 2, x, y + r // 2,
            fill=self._style.color, width=2,
        )
        crosshair_h = self._canvas.create_line(
            x - r // 2, y, x + r // 2, y,
            fill=self._style.color, width=2,
        )
        self._items.extend([crosshair_v, crosshair_h])

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
            self._root.after(int(duration_s * 1000), self._clear)

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

        self._clear()
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
            self._root.after(int(duration_s * 1000), self._clear)

    def _clear(self) -> None:
        """Clear all overlay items."""
        if self._canvas:
            for item in self._items:
                try:
                    self._canvas.delete(item)
                except Exception:
                    pass
        self._items.clear()

    def stop(self) -> None:
        """Close the overlay window."""
        self._running = False
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
        self._root = None
        self._canvas = None
