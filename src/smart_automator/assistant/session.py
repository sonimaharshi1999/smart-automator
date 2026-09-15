# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Interactive voice+vision session orchestrator.

Ties together: screen capture, voice I/O, visual overlay, desktop executor,
and the AI brain into a single interactive loop.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from smart_automator.assistant.brain import AssistantBrain, AssistantMode, AssistantResponse
from smart_automator.desktop.executor import DesktopExecutor, DesktopAction, DesktopActionType
from smart_automator.vision.screen_capture import ScreenCapture, CaptureConfig
from smart_automator.vision.overlay import VisualOverlay
from smart_automator.voice.listener import VoiceListener, ListenerConfig
from smart_automator.voice.speaker import VoiceSpeaker, TTSBackend
from smart_automator.voice.transcriber import AudioTranscriber, TranscriberBackend
from smart_automator.llm.base import LLMProvider


class SessionState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ACTING = "acting"
    CONFIRMING = "confirming"


@dataclass
class SessionConfig:
    """Configuration for an interactive session."""
    mode: AssistantMode = AssistantMode.ASK
    tts_backend: TTSBackend = TTSBackend.PYTTSX3
    transcriber_backend: TranscriberBackend = TranscriberBackend.WHISPER_LOCAL
    whisper_model: str = "base"
    capture_interval_s: float = 2.0
    overlay_enabled: bool = True
    voice_enabled: bool = True
    auto_screenshot: bool = True
    screenshots_dir: Path = field(default_factory=lambda: Path("screenshots"))


class InteractiveSession:
    """Full voice+vision interactive session.

    Orchestrates the complete loop:
    1. Capture screen continuously
    2. Listen for voice input (push-to-talk or auto-detect)
    3. Transcribe speech to text
    4. Send text + screenshot to AI brain
    5. Execute response (speak + point + act)
    6. Repeat
    """

    def __init__(
        self,
        llm: LLMProvider,
        config: SessionConfig | None = None,
    ) -> None:
        self._config = config or SessionConfig()
        self._state = SessionState.IDLE
        self._running = False

        self._brain = AssistantBrain(llm, mode=self._config.mode)
        self._desktop = DesktopExecutor(humanize=True)
        self._capture = ScreenCapture(CaptureConfig(
            interval_s=self._config.capture_interval_s,
            output_dir=self._config.screenshots_dir,
        ))
        self._overlay = VisualOverlay() if self._config.overlay_enabled else None
        self._listener = VoiceListener() if self._config.voice_enabled else None
        self._speaker = VoiceSpeaker(backend=self._config.tts_backend)
        self._transcriber = AudioTranscriber(
            backend=self._config.transcriber_backend,
            model_size=self._config.whisper_model,
        )
        self._on_state_change: Callable[[SessionState], None] | None = None
        self._on_response: Callable[[AssistantResponse], None] | None = None

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def mode(self) -> AssistantMode:
        return self._brain.mode

    @mode.setter
    def mode(self, value: AssistantMode) -> None:
        self._brain.mode = value

    def start(
        self,
        on_state_change: Callable[[SessionState], None] | None = None,
        on_response: Callable[[AssistantResponse], None] | None = None,
    ) -> None:
        """Start the interactive session."""
        self._on_state_change = on_state_change
        self._on_response = on_response
        self._running = True

        if self._config.auto_screenshot:
            self._capture.start_continuous()

        if self._overlay:
            self._overlay.start()

        self._set_state(SessionState.IDLE)

    def stop(self) -> None:
        """Stop the interactive session and clean up."""
        self._running = False
        self._capture.stop()
        if self._overlay:
            self._overlay.stop()
        if self._listener:
            self._listener.stop()
        if self._speaker:
            self._speaker.stop()
        self._set_state(SessionState.IDLE)

    def process_voice(self) -> AssistantResponse | None:
        """Run one voice interaction cycle: listen -> transcribe -> process -> respond."""
        if not self._listener or not self._running:
            return None

        self._set_state(SessionState.LISTENING)
        audio_bytes = self._listener.record_until_silence()

        if not audio_bytes:
            self._set_state(SessionState.IDLE)
            return None

        self._set_state(SessionState.THINKING)
        text = self._transcriber.transcribe(audio_bytes)

        if not text.strip():
            self._set_state(SessionState.IDLE)
            return None

        return self.process_text(text)

    def process_text(self, text: str) -> AssistantResponse:
        """Process a text command (from voice transcription or direct input)."""
        self._set_state(SessionState.THINKING)

        screenshot_path = None
        if self._config.auto_screenshot:
            frame = self._capture.get_latest()
            if frame:
                screenshot_path = str(
                    self._capture.save_screenshot(frame, "context.png")
                )

        response = self._brain.process(text, screenshot_path)

        if self._on_response:
            self._on_response(response)

        self._handle_response(response)

        self._set_state(SessionState.IDLE)
        return response

    def confirm(self) -> AssistantResponse | None:
        """Confirm a pending ASK-mode action."""
        confirmed = self._brain.confirm_action()
        if confirmed:
            self._handle_response(confirmed)
        return confirmed

    def reject(self) -> AssistantResponse:
        """Reject a pending action."""
        response = self._brain.reject_action()
        self._speak(response.speech_text)
        return response

    def _handle_response(self, response: AssistantResponse) -> None:
        """Execute the full response: interleave speech with pointer movement.

        Parses inline [POINT:x,y:label] tags from the speech text so the buddy
        cursor moves mid-sentence (like Clicky), instead of waiting for the
        full response before pointing.
        """
        from smart_automator.assistant.streaming import (
            parse_response_stream, StreamEventType, strip_tags,
        )

        # JSON-level pointers (backward compat): move buddy before speaking
        if response.pointers and self._overlay:
            for ptr in response.pointers:
                self._overlay.point_at(
                    ptr.get("x", 0),
                    ptr.get("y", 0),
                    label=ptr.get("label", ""),
                    duration_s=2.0,
                )

        # Parse inline POINT tags from speech for mid-speech buddy movement
        events = parse_response_stream(response.speech_text)
        has_inline_points = any(e.event_type == StreamEventType.POINT for e in events)

        if has_inline_points:
            self._speak_with_points(events)
        else:
            self._speak(response.speech_text)

        if response.needs_confirmation:
            self._set_state(SessionState.CONFIRMING)
            return

        if response.actions and response.mode_used == AssistantMode.DO:
            self._set_state(SessionState.ACTING)
            self._execute_actions(response.actions)

    def _speak_with_points(self, events: list) -> None:
        """Interleave speech segments with buddy cursor movement.

        For each speech chunk, speak it. For each POINT tag, move the
        buddy cursor. This creates the Clicky-like experience where
        the cursor points at elements while the AI talks.
        """
        from smart_automator.assistant.streaming import StreamEventType

        if not self._config.voice_enabled and not self._overlay:
            return

        self._set_state(SessionState.SPEAKING)

        for event in events:
            if event.event_type == StreamEventType.SPEECH and event.text:
                if self._config.voice_enabled:
                    self._speaker.speak(event.text, blocking=True)
            elif event.event_type == StreamEventType.POINT and self._overlay:
                self._overlay.point_at(event.x, event.y, label=event.label, duration_s=2.5)
                time.sleep(0.4)
            elif event.event_type == StreamEventType.END:
                break

    def _speak(self, text: str) -> None:
        """Speak text if voice is enabled. Strips any remaining POINT tags."""
        if not text or not self._config.voice_enabled:
            return
        from smart_automator.assistant.streaming import strip_tags
        self._set_state(SessionState.SPEAKING)
        self._speaker.speak(strip_tags(text), blocking=True)

    def _execute_actions(self, actions: list[dict[str, Any]]) -> None:
        """Convert brain actions to DesktopActions and execute."""
        for action_dict in actions:
            action_type = action_dict.get("type", "wait")

            try:
                desktop_type = DesktopActionType(action_type)
            except ValueError:
                continue

            desktop_action = DesktopAction(
                action_type=desktop_type,
                x=action_dict.get("x"),
                y=action_dict.get("y"),
                text=action_dict.get("text"),
                keys=action_dict.get("keys"),
                app_name=action_dict.get("app_name"),
                description=action_dict.get("description", ""),
            )

            if self._overlay and desktop_action.x and desktop_action.y:
                self._overlay.point_at(
                    desktop_action.x, desktop_action.y,
                    label=desktop_action.description,
                    duration_s=1.0,
                )
                time.sleep(0.5)

            result = self._desktop.execute(desktop_action)
            if not result.success:
                self._speak(f"Action failed: {result.error}")
                break

            time.sleep(0.3)

    def _set_state(self, state: SessionState) -> None:
        """Update session state and notify callback."""
        self._state = state
        if self._on_state_change:
            self._on_state_change(state)

    def run_interactive_loop(self) -> None:
        """Run a blocking interactive voice loop until stopped."""
        self.start()
        try:
            while self._running:
                try:
                    self.process_voice()
                except KeyboardInterrupt:
                    break
                except Exception:
                    time.sleep(0.5)
        finally:
            self.stop()
