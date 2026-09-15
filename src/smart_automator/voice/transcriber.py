# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Audio transcription using Whisper (local) or Deepgram (API)."""

from __future__ import annotations

import io
import json
import subprocess
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any


class TranscriberBackend(str, Enum):
    WHISPER_LOCAL = "whisper_local"
    WHISPER_API = "whisper_api"
    DEEPGRAM = "deepgram"


class AudioTranscriber:
    """Transcribe audio to text using configurable backends.

    Priority: whisper local (free) > deepgram (fast streaming) > whisper API.
    """

    def __init__(
        self,
        backend: TranscriberBackend = TranscriberBackend.WHISPER_LOCAL,
        model_size: str = "base",
        api_key: str | None = None,
        language: str = "en",
    ) -> None:
        self._backend = backend
        self._model_size = model_size
        self._api_key = api_key
        self._language = language
        self._whisper_model: Any = None

    def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text."""
        if self._backend == TranscriberBackend.WHISPER_LOCAL:
            return self._transcribe_whisper_local(audio_bytes)
        elif self._backend == TranscriberBackend.DEEPGRAM:
            return self._transcribe_deepgram(audio_bytes)
        elif self._backend == TranscriberBackend.WHISPER_API:
            return self._transcribe_whisper_api(audio_bytes)
        raise ValueError(f"Unknown backend: {self._backend}")

    def transcribe_file(self, audio_path: str | Path) -> str:
        """Transcribe an audio file to text."""
        audio_bytes = Path(audio_path).read_bytes()
        return self.transcribe(audio_bytes)

    def _transcribe_whisper_local(self, audio_bytes: bytes) -> str:
        """Transcribe using local Whisper model (faster-whisper or openai-whisper)."""
        try:
            return self._transcribe_faster_whisper(audio_bytes)
        except ImportError:
            pass

        try:
            return self._transcribe_openai_whisper(audio_bytes)
        except ImportError:
            pass

        return self._transcribe_whisper_cli(audio_bytes)

    def _transcribe_faster_whisper(self, audio_bytes: bytes) -> str:
        """Use faster-whisper (CTranslate2-based, very fast)."""
        from faster_whisper import WhisperModel

        if not self._whisper_model:
            self._whisper_model = WhisperModel(
                self._model_size, device="auto", compute_type="auto"
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            f.flush()
            segments, _ = self._whisper_model.transcribe(
                f.name, language=self._language
            )
            return " ".join(seg.text.strip() for seg in segments)

    def _transcribe_openai_whisper(self, audio_bytes: bytes) -> str:
        """Use openai-whisper Python package."""
        import whisper

        if not self._whisper_model:
            self._whisper_model = whisper.load_model(self._model_size)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            f.flush()
            result = self._whisper_model.transcribe(f.name, language=self._language)
            return result["text"].strip()

    def _transcribe_whisper_cli(self, audio_bytes: bytes) -> str:
        """Fallback: call whisper CLI if installed."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            f.flush()
            try:
                result = subprocess.run(
                    ["whisper", f.name, "--language", self._language, "--output_format", "txt"],
                    capture_output=True, text=True, timeout=60,
                )
                txt_path = Path(f.name).with_suffix(".txt")
                if txt_path.exists():
                    return txt_path.read_text(encoding="utf-8").strip()
                return result.stdout.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return "[transcription unavailable - install whisper or faster-whisper]"

    def _transcribe_deepgram(self, audio_bytes: bytes) -> str:
        """Transcribe using Deepgram API (fast, streaming-capable)."""
        import httpx

        if not self._api_key:
            raise ValueError("Deepgram API key required")

        response = httpx.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {self._api_key}",
                "Content-Type": "audio/wav",
            },
            content=audio_bytes,
            params={"language": self._language, "model": "nova-2", "smart_format": "true"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["results"]["channels"][0]["alternatives"][0]["transcript"]

    def _transcribe_whisper_api(self, audio_bytes: bytes) -> str:
        """Transcribe using OpenAI Whisper API."""
        import httpx

        if not self._api_key:
            raise ValueError("OpenAI API key required for Whisper API")

        files = {"file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")}
        response = httpx.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            files=files,
            data={"model": "whisper-1", "language": self._language},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["text"]

    def is_available(self) -> bool:
        """Check if the configured backend is available."""
        if self._backend == TranscriberBackend.WHISPER_LOCAL:
            try:
                import faster_whisper
                return True
            except ImportError:
                pass
            try:
                import whisper
                return True
            except ImportError:
                pass
            try:
                result = subprocess.run(["whisper", "--help"], capture_output=True, timeout=5)
                return result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
        elif self._backend in (TranscriberBackend.DEEPGRAM, TranscriberBackend.WHISPER_API):
            return self._api_key is not None
        return False
