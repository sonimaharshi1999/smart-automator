# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for assistant modules: brain, session."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch, call

import pytest

from smart_automator.assistant.brain import (
    AssistantBrain,
    AssistantMode,
    AssistantResponse,
    ConversationTurn,
)
from smart_automator.assistant.session import (
    InteractiveSession,
    SessionConfig,
    SessionState,
)
from smart_automator.llm.base import LLMProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class StubLLM(LLMProvider):
    """Stub LLM that returns configurable JSON responses."""

    def __init__(self, response: str = '{"speech": "OK"}') -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def generate(
        self, prompt: str, system_prompt: str | None = None,
        image_path: str | None = None, max_tokens: int = 4096,
    ) -> str:
        self.calls.append({"prompt": prompt, "image_path": image_path})
        return self._response

    def is_available(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return "StubLLM"


def _make_llm_response(
    speech: str = "Hello",
    actions: list[dict[str, Any]] | None = None,
    pointers: list[dict[str, Any]] | None = None,
    needs_confirmation: bool = False,
    follow_up: str = "",
) -> str:
    """Build a valid JSON LLM response."""
    return json.dumps({
        "speech": speech,
        "actions": actions or [],
        "pointers": pointers or [],
        "needs_confirmation": needs_confirmation,
        "follow_up": follow_up,
    })


# ===========================================================================
# Enum & Dataclass Tests
# ===========================================================================

class TestAssistantMode:
    """Tests for AssistantMode enum."""

    def test_enum_values(self) -> None:
        assert AssistantMode.GUIDE.value == "guide"
        assert AssistantMode.DO.value == "do"
        assert AssistantMode.ASK.value == "ask"

    def test_string_enum(self) -> None:
        assert AssistantMode.GUIDE == "guide"


class TestConversationTurn:
    """Tests for ConversationTurn dataclass."""

    def test_defaults(self) -> None:
        turn = ConversationTurn(role="user", content="hello")
        assert turn.role == "user"
        assert turn.content == "hello"
        assert turn.screenshot_context is False
        assert turn.actions_taken == []
        assert turn.timestamp > 0

    def test_with_actions(self) -> None:
        actions = [{"type": "click", "x": 10, "y": 20}]
        turn = ConversationTurn(role="assistant", content="done", actions_taken=actions)
        assert len(turn.actions_taken) == 1


class TestAssistantResponse:
    """Tests for AssistantResponse dataclass."""

    def test_defaults(self) -> None:
        r = AssistantResponse(speech_text="Hello")
        assert r.speech_text == "Hello"
        assert r.actions == []
        assert r.pointers == []
        assert r.mode_used == AssistantMode.GUIDE
        assert r.needs_confirmation is False
        assert r.follow_up == ""


class TestSessionState:
    """Tests for SessionState enum."""

    def test_all_states(self) -> None:
        expected = {"idle", "listening", "thinking", "speaking", "acting", "confirming"}
        actual = {s.value for s in SessionState}
        assert actual == expected


class TestSessionConfig:
    """Tests for SessionConfig defaults."""

    def test_defaults(self) -> None:
        cfg = SessionConfig()
        assert cfg.mode == AssistantMode.ASK
        assert cfg.overlay_enabled is True
        assert cfg.voice_enabled is True
        assert cfg.auto_screenshot is True


# ===========================================================================
# AssistantBrain Tests
# ===========================================================================

class TestAssistantBrain:
    """Tests for AssistantBrain (LLM mocked with StubLLM)."""

    def test_default_construction(self) -> None:
        llm = StubLLM()
        brain = AssistantBrain(llm)
        assert brain.mode == AssistantMode.ASK
        assert brain.history == []

    def test_custom_mode(self) -> None:
        brain = AssistantBrain(StubLLM(), mode=AssistantMode.DO)
        assert brain.mode == AssistantMode.DO

    def test_mode_setter(self) -> None:
        brain = AssistantBrain(StubLLM())
        brain.mode = AssistantMode.GUIDE
        assert brain.mode == AssistantMode.GUIDE

    def test_process_returns_response(self) -> None:
        llm = StubLLM(_make_llm_response(speech="I see your screen"))
        brain = AssistantBrain(llm, mode=AssistantMode.ASK)
        resp = brain.process("open settings")
        assert isinstance(resp, AssistantResponse)
        assert resp.speech_text == "I see your screen"

    def test_process_adds_to_history(self) -> None:
        llm = StubLLM(_make_llm_response())
        brain = AssistantBrain(llm)
        brain.process("test input")
        assert len(brain.history) == 2  # user + assistant
        assert brain.history[0].role == "user"
        assert brain.history[1].role == "assistant"

    def test_process_with_screenshot(self) -> None:
        llm = StubLLM(_make_llm_response())
        brain = AssistantBrain(llm)
        brain.process("what is on screen", screenshot_path="/tmp/screen.png")
        assert llm.calls[0]["image_path"] == "/tmp/screen.png"
        assert brain.history[0].screenshot_context is True

    def test_process_guide_mode_strips_actions(self) -> None:
        resp_json = _make_llm_response(
            speech="Click here",
            actions=[{"type": "click", "x": 10, "y": 20}],
            pointers=[{"x": 10, "y": 20, "label": "Settings"}],
        )
        brain = AssistantBrain(StubLLM(resp_json), mode=AssistantMode.GUIDE)
        resp = brain.process("where is settings")
        assert resp.actions == []  # GUIDE mode strips actions
        assert len(resp.pointers) == 1

    def test_process_do_mode_keeps_actions(self) -> None:
        resp_json = _make_llm_response(
            speech="Clicking now",
            actions=[{"type": "click", "x": 100, "y": 200}],
        )
        brain = AssistantBrain(StubLLM(resp_json), mode=AssistantMode.DO)
        resp = brain.process("click the button")
        assert len(resp.actions) == 1
        assert resp.mode_used == AssistantMode.DO

    def test_process_ask_mode_sets_confirmation(self) -> None:
        resp_json = _make_llm_response(
            speech="Should I click?",
            actions=[{"type": "click", "x": 50, "y": 60}],
            needs_confirmation=True,
        )
        brain = AssistantBrain(StubLLM(resp_json), mode=AssistantMode.ASK)
        resp = brain.process("click the button")
        assert resp.needs_confirmation is True

    def test_process_mode_override_do(self) -> None:
        brain = AssistantBrain(StubLLM(_make_llm_response()), mode=AssistantMode.ASK)
        resp = brain.process("just do it")
        assert resp.mode_used == AssistantMode.DO

    def test_process_mode_override_guide(self) -> None:
        brain = AssistantBrain(StubLLM(_make_llm_response()), mode=AssistantMode.DO)
        resp = brain.process("show me where the settings are")
        assert resp.mode_used == AssistantMode.GUIDE

    def test_process_mode_override_ask(self) -> None:
        brain = AssistantBrain(StubLLM(_make_llm_response()), mode=AssistantMode.DO)
        resp = brain.process("what would you do here")
        assert resp.mode_used == AssistantMode.ASK

    def test_process_llm_error_returns_fallback(self) -> None:
        llm = StubLLM()
        llm.generate = MagicMock(side_effect=RuntimeError("API timeout"))
        brain = AssistantBrain(llm, mode=AssistantMode.ASK)
        resp = brain.process("help me")
        assert "issue" in resp.speech_text.lower() or "try again" in resp.speech_text.lower()

    def test_process_invalid_json_falls_back(self) -> None:
        brain = AssistantBrain(StubLLM("This is not JSON at all"), mode=AssistantMode.ASK)
        resp = brain.process("do something")
        assert resp.speech_text == "This is not JSON at all"

    def test_confirm_action_returns_last_actions(self) -> None:
        resp_json = _make_llm_response(
            speech="Should I click?",
            actions=[{"type": "click", "x": 10, "y": 20}],
            needs_confirmation=True,
        )
        brain = AssistantBrain(StubLLM(resp_json), mode=AssistantMode.ASK)
        brain.process("click that button")

        confirmed = brain.confirm_action()
        assert confirmed is not None
        assert len(confirmed.actions) == 1
        assert confirmed.mode_used == AssistantMode.DO

    def test_confirm_action_no_history_returns_none(self) -> None:
        brain = AssistantBrain(StubLLM())
        assert brain.confirm_action() is None

    def test_reject_action(self) -> None:
        brain = AssistantBrain(StubLLM())
        resp = brain.reject_action()
        assert "won't perform" in resp.speech_text.lower() or "understood" in resp.speech_text.lower()

    def test_clear_history(self) -> None:
        brain = AssistantBrain(StubLLM(_make_llm_response()))
        brain.process("first")
        brain.process("second")
        assert len(brain.history) == 4
        brain.clear_history()
        assert brain.history == []

    def test_get_summary_empty(self) -> None:
        brain = AssistantBrain(StubLLM())
        assert brain.get_summary() == "No conversation yet."

    def test_get_summary_with_history(self) -> None:
        brain = AssistantBrain(StubLLM(_make_llm_response()))
        brain.process("test input")
        summary = brain.get_summary()
        assert "1 exchanges" in summary

    def test_history_trimming(self) -> None:
        brain = AssistantBrain(StubLLM(_make_llm_response()), max_history=5)
        for i in range(20):
            brain.process(f"message {i}")
        # History should be trimmed to max_history
        assert len(brain.history) <= 10  # max_history * 2 then trimmed to max_history


# ===========================================================================
# InteractiveSession Tests
# ===========================================================================

class TestInteractiveSession:
    """Tests for InteractiveSession (all hardware mocked)."""

    def _make_session(self, llm: LLMProvider | None = None, config: SessionConfig | None = None) -> InteractiveSession:
        """Build a session with all hardware components mocked."""
        cfg = config or SessionConfig(
            overlay_enabled=False,
            voice_enabled=False,
            auto_screenshot=False,
        )
        session = InteractiveSession.__new__(InteractiveSession)
        session._config = cfg
        session._state = SessionState.IDLE
        session._running = False
        session._brain = AssistantBrain(llm or StubLLM(_make_llm_response()))
        session._desktop = MagicMock()
        session._capture = MagicMock()
        session._overlay = MagicMock() if cfg.overlay_enabled else None
        session._listener = MagicMock() if cfg.voice_enabled else None
        session._speaker = MagicMock()
        session._transcriber = MagicMock()
        session._on_state_change = None
        session._on_response = None
        return session

    def test_default_state(self) -> None:
        session = self._make_session()
        assert session.state == SessionState.IDLE

    def test_mode_property(self) -> None:
        session = self._make_session()
        assert session.mode == AssistantMode.ASK

    def test_mode_setter(self) -> None:
        session = self._make_session()
        session.mode = AssistantMode.DO
        assert session.mode == AssistantMode.DO

    def test_start(self) -> None:
        session = self._make_session()
        state_changes: list[SessionState] = []
        session.start(on_state_change=lambda s: state_changes.append(s))
        assert session._running is True
        assert SessionState.IDLE in state_changes

    def test_start_with_auto_screenshot(self) -> None:
        cfg = SessionConfig(overlay_enabled=False, voice_enabled=False, auto_screenshot=True)
        session = self._make_session(config=cfg)
        session.start()
        session._capture.start_continuous.assert_called_once()

    def test_stop(self) -> None:
        session = self._make_session()
        session._running = True
        session.stop()
        assert session._running is False
        assert session.state == SessionState.IDLE
        session._capture.stop.assert_called_once()
        session._speaker.stop.assert_called_once()

    def test_stop_with_overlay(self) -> None:
        cfg = SessionConfig(overlay_enabled=True, voice_enabled=False, auto_screenshot=False)
        session = self._make_session(config=cfg)
        session._running = True
        session.stop()
        session._overlay.stop.assert_called_once()

    def test_stop_with_listener(self) -> None:
        cfg = SessionConfig(overlay_enabled=False, voice_enabled=True, auto_screenshot=False)
        session = self._make_session(config=cfg)
        session._running = True
        session.stop()
        session._listener.stop.assert_called_once()

    def test_process_text_returns_response(self) -> None:
        llm = StubLLM(_make_llm_response(speech="Done"))
        session = self._make_session(llm=llm)
        session._running = True
        resp = session.process_text("open settings")
        assert isinstance(resp, AssistantResponse)
        assert resp.speech_text == "Done"
        assert session.state == SessionState.IDLE

    def test_process_text_with_screenshot_context(self) -> None:
        llm = StubLLM(_make_llm_response())
        cfg = SessionConfig(overlay_enabled=False, voice_enabled=False, auto_screenshot=True)
        session = self._make_session(llm=llm, config=cfg)
        session._running = True
        session._capture.get_latest.return_value = b"png-bytes"
        session._capture.save_screenshot.return_value = Path("/tmp/context.png")

        session.process_text("what do you see")
        session._capture.save_screenshot.assert_called_once()

    def test_process_text_fires_on_response_callback(self) -> None:
        session = self._make_session()
        session._running = True
        responses: list[AssistantResponse] = []
        session._on_response = lambda r: responses.append(r)
        session.process_text("test")
        assert len(responses) == 1

    def test_process_voice_no_listener_returns_none(self) -> None:
        session = self._make_session()
        session._running = True
        session._listener = None
        assert session.process_voice() is None

    def test_process_voice_not_running_returns_none(self) -> None:
        cfg = SessionConfig(overlay_enabled=False, voice_enabled=True, auto_screenshot=False)
        session = self._make_session(config=cfg)
        session._running = False
        assert session.process_voice() is None

    def test_process_voice_empty_audio_returns_none(self) -> None:
        cfg = SessionConfig(overlay_enabled=False, voice_enabled=True, auto_screenshot=False)
        session = self._make_session(config=cfg)
        session._running = True
        session._listener.record_until_silence.return_value = b""
        assert session.process_voice() is None
        assert session.state == SessionState.IDLE

    def test_process_voice_empty_transcription_returns_none(self) -> None:
        cfg = SessionConfig(overlay_enabled=False, voice_enabled=True, auto_screenshot=False)
        session = self._make_session(config=cfg)
        session._running = True
        session._listener.record_until_silence.return_value = b"audio-data"
        session._transcriber.transcribe.return_value = "   "
        assert session.process_voice() is None

    def test_process_voice_full_cycle(self) -> None:
        llm = StubLLM(_make_llm_response(speech="Got it"))
        cfg = SessionConfig(overlay_enabled=False, voice_enabled=True, auto_screenshot=False)
        session = self._make_session(llm=llm, config=cfg)
        session._running = True
        session._listener.record_until_silence.return_value = b"audio-data"
        session._transcriber.transcribe.return_value = "open settings"

        resp = session.process_voice()
        assert resp is not None
        assert resp.speech_text == "Got it"

    def test_confirm_delegates_to_brain(self) -> None:
        resp_json = _make_llm_response(
            speech="Should I?",
            actions=[{"type": "click", "x": 10, "y": 20}],
            needs_confirmation=True,
        )
        session = self._make_session(llm=StubLLM(resp_json))
        session._running = True
        session.process_text("click button")

        confirmed = session.confirm()
        assert confirmed is not None
        assert confirmed.mode_used == AssistantMode.DO

    def test_reject_speaks_rejection(self) -> None:
        session = self._make_session()
        resp = session.reject()
        assert "won't" in resp.speech_text.lower() or "understood" in resp.speech_text.lower()

    def test_handle_response_with_pointers(self) -> None:
        cfg = SessionConfig(overlay_enabled=True, voice_enabled=False, auto_screenshot=False)
        session = self._make_session(config=cfg)
        response = AssistantResponse(
            speech_text="Look here",
            pointers=[{"x": 100, "y": 200, "label": "Button"}],
            mode_used=AssistantMode.GUIDE,
        )
        session._handle_response(response)
        session._overlay.point_at.assert_called_once_with(100, 200, label="Button", duration_s=2.0)

    def test_handle_response_confirmation_sets_state(self) -> None:
        session = self._make_session()
        response = AssistantResponse(
            speech_text="Should I proceed?",
            actions=[{"type": "click", "x": 10, "y": 20}],
            needs_confirmation=True,
            mode_used=AssistantMode.ASK,
        )
        session._handle_response(response)
        assert session.state == SessionState.CONFIRMING

    def test_handle_response_do_mode_executes(self) -> None:
        session = self._make_session()
        session._desktop.execute.return_value = MagicMock(success=True)
        response = AssistantResponse(
            speech_text="Clicking now",
            actions=[{"type": "click", "x": 100, "y": 200, "description": "test"}],
            mode_used=AssistantMode.DO,
        )
        session._handle_response(response)
        session._desktop.execute.assert_called_once()

    def test_handle_response_failed_action_speaks_error(self) -> None:
        cfg = SessionConfig(overlay_enabled=False, voice_enabled=True, auto_screenshot=False)
        session = self._make_session(config=cfg)
        session._desktop.execute.return_value = MagicMock(success=False, error="fail")
        response = AssistantResponse(
            speech_text="Doing it",
            actions=[{"type": "click", "x": 10, "y": 20, "description": "test"}],
            mode_used=AssistantMode.DO,
        )
        session._handle_response(response)
        # Speaker should be called for failure message
        assert session._speaker.speak.call_count >= 1

    def test_state_change_callback(self) -> None:
        session = self._make_session()
        changes: list[SessionState] = []
        session._on_state_change = lambda s: changes.append(s)
        session._set_state(SessionState.THINKING)
        assert changes == [SessionState.THINKING]
