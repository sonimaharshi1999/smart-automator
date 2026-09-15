# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for streaming response parser and buddy cursor."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from smart_automator.assistant.streaming import (
    StreamEvent,
    StreamEventType,
    parse_response_stream,
    strip_tags,
    POINT_PATTERN,
    ACTION_PATTERN,
)
from smart_automator.vision.overlay import BuddyCursor, PointerStyle, VisualOverlay


class TestPointPattern:
    """Tests for the POINT tag regex."""

    def test_basic_point_with_label(self) -> None:
        m = POINT_PATTERN.search("[POINT:100,200:Settings gear]")
        assert m is not None
        assert m.group(1) == "100"
        assert m.group(2) == "200"
        assert m.group(3) == "Settings gear"

    def test_point_without_label(self) -> None:
        m = POINT_PATTERN.search("[POINT:50,75]")
        assert m is not None
        assert m.group(1) == "50"
        assert m.group(2) == "75"
        assert m.group(3) is None

    def test_point_in_sentence(self) -> None:
        text = "Click here [POINT:300,400:Button] to proceed"
        m = POINT_PATTERN.search(text)
        assert m is not None
        assert m.group(1) == "300"

    def test_no_match(self) -> None:
        assert POINT_PATTERN.search("no tags here") is None

    def test_multiple_points(self) -> None:
        text = "[POINT:10,20:A] then [POINT:30,40:B]"
        matches = list(POINT_PATTERN.finditer(text))
        assert len(matches) == 2


class TestActionPattern:
    """Tests for the ACTION tag regex."""

    def test_action_with_params(self) -> None:
        m = ACTION_PATTERN.search("[ACTION:click:login button]")
        assert m is not None
        assert m.group(1) == "click"
        assert m.group(2) == "login button"

    def test_action_without_params(self) -> None:
        m = ACTION_PATTERN.search("[ACTION:scroll]")
        assert m is not None
        assert m.group(1) == "scroll"
        assert m.group(2) is None


class TestParseResponseStream:
    """Tests for parse_response_stream."""

    def test_plain_speech_no_tags(self) -> None:
        events = parse_response_stream("Just some text here")
        types = [e.event_type for e in events]
        assert StreamEventType.SPEECH in types
        assert StreamEventType.END in types
        assert events[0].text == "Just some text here"

    def test_single_point_tag(self) -> None:
        events = parse_response_stream(
            "Click the button [POINT:500,300:Submit] to save"
        )
        types = [e.event_type for e in events]
        assert types == [
            StreamEventType.SPEECH,
            StreamEventType.POINT,
            StreamEventType.SPEECH,
            StreamEventType.END,
        ]
        assert events[0].text == "Click the button"
        assert events[1].x == 500
        assert events[1].y == 300
        assert events[1].label == "Submit"
        assert events[2].text == "to save"

    def test_multiple_point_tags(self) -> None:
        text = "First [POINT:10,20:A] then [POINT:30,40:B] done"
        events = parse_response_stream(text)
        point_events = [e for e in events if e.event_type == StreamEventType.POINT]
        assert len(point_events) == 2
        assert point_events[0].x == 10
        assert point_events[1].x == 30

    def test_point_at_start(self) -> None:
        events = parse_response_stream("[POINT:100,200:Start] do this")
        assert events[0].event_type == StreamEventType.POINT
        assert events[1].event_type == StreamEventType.SPEECH

    def test_point_at_end(self) -> None:
        events = parse_response_stream("Look here [POINT:100,200:End]")
        speech_events = [e for e in events if e.event_type == StreamEventType.SPEECH]
        assert speech_events[0].text == "Look here"

    def test_action_tag(self) -> None:
        events = parse_response_stream("I'll [ACTION:click:submit form] now")
        action_events = [e for e in events if e.event_type == StreamEventType.ACTION]
        assert len(action_events) == 1
        assert action_events[0].action_data["type"] == "click"

    def test_empty_text(self) -> None:
        events = parse_response_stream("")
        assert events == [StreamEvent(event_type=StreamEventType.END)]

    def test_mixed_point_and_action(self) -> None:
        text = "See [POINT:50,60:btn] and [ACTION:click:it] done"
        events = parse_response_stream(text)
        types = [e.event_type for e in events if e.event_type != StreamEventType.END]
        assert StreamEventType.POINT in types
        assert StreamEventType.ACTION in types
        assert StreamEventType.SPEECH in types

    def test_always_ends_with_end_event(self) -> None:
        for text in ["hello", "[POINT:1,2:x]", "", "a [POINT:1,2:b] c"]:
            events = parse_response_stream(text)
            assert events[-1].event_type == StreamEventType.END


class TestStripTags:
    """Tests for strip_tags."""

    def test_strip_point_tags(self) -> None:
        result = strip_tags("Click [POINT:100,200:here] to save")
        assert result == "Click to save"

    def test_strip_action_tags(self) -> None:
        result = strip_tags("I'll [ACTION:click:button] now")
        assert result == "I'll now"

    def test_strip_multiple(self) -> None:
        result = strip_tags("[POINT:1,2:a] text [POINT:3,4:b] more [ACTION:scroll]")
        assert result == "text more"

    def test_no_tags_unchanged(self) -> None:
        assert strip_tags("no tags here") == "no tags here"

    def test_collapses_whitespace(self) -> None:
        result = strip_tags("a  [POINT:1,2:x]  b")
        assert "  " not in result


class TestBuddyCursor:
    """Tests for the animated buddy cursor."""

    def test_initial_state(self) -> None:
        canvas = MagicMock()
        buddy = BuddyCursor(canvas, PointerStyle())
        assert buddy.position == (0.0, 0.0)
        assert buddy.is_animating is False

    def test_show(self) -> None:
        canvas = MagicMock()
        buddy = BuddyCursor(canvas, PointerStyle())
        buddy.show(100.0, 200.0)
        assert buddy.position == (100.0, 200.0)
        assert buddy._visible is True

    def test_hide(self) -> None:
        canvas = MagicMock()
        buddy = BuddyCursor(canvas, PointerStyle())
        buddy.show(50.0, 50.0)
        buddy.hide()
        assert buddy._visible is False

    def test_move_to_sets_animating(self) -> None:
        canvas = MagicMock()
        canvas.after = MagicMock()
        buddy = BuddyCursor(canvas, PointerStyle())
        buddy.show(0.0, 0.0)
        buddy.move_to(100.0, 200.0)
        assert buddy._animating is True

    def test_clear_removes_items(self) -> None:
        canvas = MagicMock()
        canvas.create_oval.return_value = 1
        canvas.create_polygon.return_value = 2
        buddy = BuddyCursor(canvas, PointerStyle())
        buddy._items = [1, 2, 3]
        buddy._clear()
        assert len(buddy._items) == 0
        assert canvas.delete.call_count == 3


class TestVisualOverlayBuddy:
    """Tests for VisualOverlay buddy cursor integration."""

    def test_overlay_has_no_buddy_before_start(self) -> None:
        overlay = VisualOverlay()
        assert overlay.buddy is None

    def test_point_at_queues_buddy_action(self) -> None:
        overlay = VisualOverlay()
        overlay._running = True
        overlay.point_at(100, 200, "test", 3.0)
        assert len(overlay._pending_actions) == 1

    def test_stop_clears_buddy(self) -> None:
        overlay = VisualOverlay()
        overlay._buddy = MagicMock()
        overlay._running = True
        overlay.stop()
        assert overlay._buddy is None
