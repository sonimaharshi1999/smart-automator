# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for humanizer modules."""

from smart_automator.humanizer.delays import ActionComplexity, HumanDelay
from smart_automator.humanizer.mouse import HumanMouse
from smart_automator.humanizer.scroll import HumanScroll
from smart_automator.humanizer.typing import HumanTyping, KeyEvent


class TestHumanDelay:
    """Tests for Gaussian delay generator."""

    def test_delay_within_range(self) -> None:
        delay = HumanDelay(speed_factor=1.0)
        for _ in range(100):
            ms = delay.get_delay_ms(ActionComplexity.SIMPLE)
            assert 50 <= ms <= 1000  # Wide range for Gaussian

    def test_complex_delays_longer(self) -> None:
        delay = HumanDelay(speed_factor=1.0)
        simple_total = sum(
            delay.get_delay_ms(ActionComplexity.SIMPLE) for _ in range(50)
        )
        complex_total = sum(
            delay.get_delay_ms(ActionComplexity.COMPLEX) for _ in range(50)
        )
        assert complex_total > simple_total

    def test_speed_factor(self) -> None:
        slow = HumanDelay(speed_factor=2.0)
        fast = HumanDelay(speed_factor=0.5)
        slow_total = sum(
            slow.get_delay_ms(ActionComplexity.MODERATE) for _ in range(50)
        )
        fast_total = sum(
            fast.get_delay_ms(ActionComplexity.MODERATE) for _ in range(50)
        )
        assert slow_total > fast_total

    def test_micro_pause(self) -> None:
        for _ in range(50):
            pause = HumanDelay.micro_pause()
            assert isinstance(pause, int)

    def test_reading_pause(self) -> None:
        short = HumanDelay.reading_pause(10)
        long = HumanDelay.reading_pause(500)
        assert long > short

    def test_delay_seconds(self) -> None:
        delay = HumanDelay()
        seconds = delay.get_delay_seconds(ActionComplexity.SIMPLE)
        assert isinstance(seconds, float)
        assert seconds > 0


class TestHumanMouse:
    """Tests for Bezier curve mouse movements."""

    def test_path_generation(self) -> None:
        mouse = HumanMouse(steps=15)
        path = mouse.generate_path(0, 0, 500, 300)
        assert len(path) == 16  # steps + 1
        # First point near start
        assert abs(path[0][0]) < 10
        assert abs(path[0][1]) < 10
        # Last point at target
        assert path[-1] == (500, 300)

    def test_path_is_curved(self) -> None:
        mouse = HumanMouse(steps=20, jitter_px=0)
        path = mouse.generate_path(0, 0, 100, 0)
        # At least one point should deviate from the x-axis
        y_values = [p[1] for p in path[1:-1]]
        non_zero_y = [y for y in y_values if abs(y) > 0.1]
        assert len(non_zero_y) > 0  # Path should curve

    def test_timing_generation(self) -> None:
        mouse = HumanMouse()
        path = mouse.generate_path(0, 0, 200, 200)
        timings = mouse.generate_timing(len(path))
        assert len(timings) == len(path)
        assert all(t >= 5 for t in timings)


class TestHumanTyping:
    """Tests for realistic typing simulation."""

    def test_typing_sequence_length(self) -> None:
        typer = HumanTyping(typo_probability=0)
        actions = typer.generate_typing_sequence("hello")
        # Without typos, should have at least 5 key presses
        key_presses = [a for a in actions if a.event == KeyEvent.PRESS]
        assert len(key_presses) == 5

    def test_typing_includes_pauses(self) -> None:
        typer = HumanTyping(typo_probability=0)
        actions = typer.generate_typing_sequence("hello world. more text")
        pauses = [a for a in actions if a.event == KeyEvent.PAUSE]
        assert len(pauses) > 0  # Should pause at spaces and punctuation

    def test_typo_simulation(self) -> None:
        typer = HumanTyping(typo_probability=1.0)  # Always make typos
        actions = typer.generate_typing_sequence("abcde")
        backspaces = [a for a in actions if a.event == KeyEvent.BACKSPACE]
        assert len(backspaces) > 0  # Should have corrections

    def test_duration_estimate(self) -> None:
        typer = HumanTyping(base_cpm=300)
        short = typer.calculate_duration_ms("hi")
        long = typer.calculate_duration_ms("this is a much longer string to type out")
        assert long > short


class TestHumanScroll:
    """Tests for natural scroll patterns."""

    def test_scroll_sequence(self) -> None:
        scroller = HumanScroll(base_step_px=100)
        steps = scroller.generate_scroll_sequence(500, "down")
        total = sum(s.pixels for s in steps if s.direction == "down")
        reverse = sum(s.pixels for s in steps if s.direction == "up")
        assert total - reverse >= 400  # Approximate target

    def test_scroll_direction(self) -> None:
        scroller = HumanScroll()
        steps = scroller.generate_scroll_sequence(200, "up")
        main_steps = [s for s in steps if s.direction == "up"]
        assert len(main_steps) > 0

    def test_scroll_to_element(self) -> None:
        scroller = HumanScroll()
        steps = scroller.scroll_to_element(0, 1000)
        assert all(s.direction == "down" for s in steps if s.pixels > 30)

    def test_smooth_scroll_js(self) -> None:
        js = HumanScroll.smooth_scroll_js(300, 500)
        assert "300" in js
        assert "smooth" in js
