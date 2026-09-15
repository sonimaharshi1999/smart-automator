# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Text-to-speech output using pyttsx3 (offline) or ElevenLabs (API)."""

from __future__ import annotations

import threading
from enum import Enum
from typing import Any


class TTSBackend(str, Enum):
    PYTTSX3 = "pyttsx3"
    ELEVENLABS = "elevenlabs"
    SYSTEM = "system"


class VoiceSpeaker:
    """Convert text to speech with configurable backends.

    Priority: pyttsx3 (free, offline) > system TTS > ElevenLabs (paid, high quality).
    """

    def __init__(
        self,
        backend: TTSBackend = TTSBackend.PYTTSX3,
        api_key: str | None = None,
        voice_id: str = "default",
        rate: int = 175,
        volume: float = 0.9,
    ) -> None:
        self._backend = backend
        self._api_key = api_key
        self._voice_id = voice_id
        self._rate = rate
        self._volume = volume
        self._engine: Any = None
        self._speaking = False
        self._lock = threading.Lock()

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def speak(self, text: str, blocking: bool = True) -> None:
        """Speak text aloud."""
        if not text.strip():
            return

        if blocking:
            self._do_speak(text)
        else:
            thread = threading.Thread(target=self._do_speak, args=(text,), daemon=True)
            thread.start()

    def _do_speak(self, text: str) -> None:
        """Internal speak implementation."""
        with self._lock:
            self._speaking = True
            try:
                if self._backend == TTSBackend.PYTTSX3:
                    self._speak_pyttsx3(text)
                elif self._backend == TTSBackend.ELEVENLABS:
                    self._speak_elevenlabs(text)
                elif self._backend == TTSBackend.SYSTEM:
                    self._speak_system(text)
            finally:
                self._speaking = False

    def _speak_pyttsx3(self, text: str) -> None:
        """Speak using pyttsx3 (offline, cross-platform)."""
        import pyttsx3

        if not self._engine:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self._rate)
            self._engine.setProperty("volume", self._volume)

            voices = self._engine.getProperty("voices")
            if self._voice_id != "default" and voices:
                for v in voices:
                    if self._voice_id in v.id.lower():
                        self._engine.setProperty("voice", v.id)
                        break

        self._engine.say(text)
        self._engine.runAndWait()

    def _speak_elevenlabs(self, text: str) -> None:
        """Speak using ElevenLabs API (high quality, paid)."""
        import httpx
        import tempfile

        if not self._api_key:
            raise ValueError("ElevenLabs API key required")

        voice = self._voice_id if self._voice_id != "default" else "21m00Tcm4TlvDq8ikWAM"

        response = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
            headers={"xi-api-key": self._api_key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_monolingual_v1"},
            timeout=15,
        )
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(response.content)
            f.flush()
            self._play_audio_file(f.name)

    def _speak_system(self, text: str) -> None:
        """Speak using OS-native TTS (Windows SAPI, macOS say)."""
        import platform
        import subprocess

        system = platform.system()
        if system == "Darwin":
            subprocess.run(["say", text], timeout=30)
        elif system == "Windows":
            ps_cmd = f'Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak("{text}")'
            subprocess.run(["powershell", "-Command", ps_cmd], timeout=30)
        elif system == "Linux":
            subprocess.run(["espeak", text], timeout=30)

    @staticmethod
    def _play_audio_file(path: str) -> None:
        """Play an audio file using available backend."""
        try:
            import playsound
            playsound.playsound(path)
            return
        except ImportError:
            pass

        import platform
        import subprocess
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["afplay", path], timeout=30)
        elif system == "Windows":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
        elif system == "Linux":
            subprocess.run(["aplay", path], timeout=30)

    def stop(self) -> None:
        """Stop ongoing speech."""
        if self._engine and self._backend == TTSBackend.PYTTSX3:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._speaking = False

    def is_available(self) -> bool:
        """Check if the configured TTS backend is available."""
        if self._backend == TTSBackend.PYTTSX3:
            try:
                import pyttsx3
                return True
            except ImportError:
                return False
        elif self._backend == TTSBackend.ELEVENLABS:
            return self._api_key is not None
        elif self._backend == TTSBackend.SYSTEM:
            return True
        return False
