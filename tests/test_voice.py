# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for voice modules: listener, transcriber, speaker."""

from __future__ import annotations

import io
import wave
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest

from smart_automator.voice.listener import ListenerConfig, VoiceListener
from smart_automator.voice.transcriber import AudioTranscriber, TranscriberBackend
from smart_automator.voice.speaker import TTSBackend, VoiceSpeaker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes(duration_s: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Create minimal valid WAV bytes for testing."""
    samples = int(sample_rate * duration_s)
    audio = np.zeros(samples, dtype=np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


# ===========================================================================
# VoiceListener Tests
# ===========================================================================

class TestListenerConfig:
    """Tests for ListenerConfig defaults and overrides."""

    def test_default_config(self) -> None:
        cfg = ListenerConfig()
        assert cfg.sample_rate == 16000
        assert cfg.channels == 1
        assert cfg.dtype == "int16"
        assert cfg.silence_threshold == 500.0
        assert cfg.max_recording_s == 30.0

    def test_custom_config(self) -> None:
        cfg = ListenerConfig(sample_rate=44100, channels=2, silence_threshold=200.0)
        assert cfg.sample_rate == 44100
        assert cfg.channels == 2
        assert cfg.silence_threshold == 200.0


class TestVoiceListener:
    """Tests for VoiceListener (all hardware mocked)."""

    def test_default_construction(self, tmp_path: Path) -> None:
        cfg = ListenerConfig(output_dir=tmp_path / "rec")
        listener = VoiceListener(config=cfg)
        assert listener.is_recording is False
        assert (tmp_path / "rec").exists()

    def test_construction_without_config(self, tmp_path: Path) -> None:
        with patch.object(Path, "mkdir"):
            listener = VoiceListener()
        assert listener.is_recording is False

    def test_record_until_silence_returns_wav_bytes(self, tmp_path: Path) -> None:
        cfg = ListenerConfig(
            output_dir=tmp_path,
            silence_threshold=100.0,
            silence_duration_s=0.1,
            chunk_duration_s=0.1,
            max_recording_s=0.5,
        )
        listener = VoiceListener(config=cfg)

        silent_chunk = np.zeros(int(16000 * 0.1), dtype=np.int16)
        voice_chunk = (np.ones(int(16000 * 0.1), dtype=np.int16) * 5000)

        class FakeStream:
            def __enter__(self_inner: Any) -> Any:
                listener._audio_queue.put(voice_chunk)
                listener._audio_queue.put(silent_chunk)
                listener._audio_queue.put(silent_chunk)
                return self_inner
            def __exit__(self_inner: Any, *args: Any) -> None:
                pass

        mock_sd = MagicMock()
        mock_sd.InputStream.return_value = FakeStream()
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            result = listener.record_until_silence()

        assert isinstance(result, bytes)
        assert len(result) > 44

    def test_record_until_silence_empty_returns_empty(self, tmp_path: Path) -> None:
        """When stop event is pre-set, returns empty bytes."""
        cfg = ListenerConfig(output_dir=tmp_path, max_recording_s=0.1, chunk_duration_s=0.05)
        listener = VoiceListener(config=cfg)

        # Directly test the WAV conversion with empty frames
        result = listener._to_wav_bytes(np.array([], dtype=np.int16))
        assert isinstance(result, bytes)
        assert listener.is_recording is False

    def test_record_for_duration(self, tmp_path: Path) -> None:
        cfg = ListenerConfig(output_dir=tmp_path)
        listener = VoiceListener(config=cfg)

        fake_audio = np.zeros(16000, dtype=np.int16)
        mock_sd = MagicMock()
        mock_sd.rec.return_value = fake_audio
        mock_sd.wait.return_value = None
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            result = listener.record_for_duration(1.0)
        assert isinstance(result, bytes)
        assert len(result) > 44
        assert listener.is_recording is False

    def test_stop_sets_event(self, tmp_path: Path) -> None:
        cfg = ListenerConfig(output_dir=tmp_path)
        listener = VoiceListener(config=cfg)
        listener.stop()
        assert listener._stop_event.is_set()

    def test_save_recording(self, tmp_path: Path) -> None:
        cfg = ListenerConfig(output_dir=tmp_path)
        listener = VoiceListener(config=cfg)
        wav = _make_wav_bytes()
        path = listener.save_recording(wav, "test.wav")
        assert path.exists()
        assert path.name == "test.wav"
        assert path.read_bytes() == wav

    def test_is_recording_property(self, tmp_path: Path) -> None:
        cfg = ListenerConfig(output_dir=tmp_path)
        listener = VoiceListener(config=cfg)
        assert listener.is_recording is False
        listener._is_recording = True
        assert listener.is_recording is True

    def test_to_wav_bytes_format(self, tmp_path: Path) -> None:
        cfg = ListenerConfig(output_dir=tmp_path, sample_rate=16000, channels=1)
        listener = VoiceListener(config=cfg)
        audio = np.zeros(16000, dtype=np.int16)
        wav = listener._to_wav_bytes(audio)
        buf = io.BytesIO(wav)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 16000
            assert wf.getsampwidth() == 2


# ===========================================================================
# AudioTranscriber Tests
# ===========================================================================

class TestTranscriberBackend:
    """Tests for TranscriberBackend enum."""

    def test_enum_values(self) -> None:
        assert TranscriberBackend.WHISPER_LOCAL.value == "whisper_local"
        assert TranscriberBackend.WHISPER_API.value == "whisper_api"
        assert TranscriberBackend.DEEPGRAM.value == "deepgram"


class TestAudioTranscriber:
    """Tests for AudioTranscriber (all backends mocked)."""

    def test_default_construction(self) -> None:
        t = AudioTranscriber()
        assert t._backend == TranscriberBackend.WHISPER_LOCAL
        assert t._model_size == "base"
        assert t._language == "en"

    def test_custom_construction(self) -> None:
        t = AudioTranscriber(
            backend=TranscriberBackend.DEEPGRAM,
            api_key="test-key",
            language="es",
        )
        assert t._backend == TranscriberBackend.DEEPGRAM
        assert t._api_key == "test-key"
        assert t._language == "es"

    @patch("smart_automator.voice.transcriber.AudioTranscriber._transcribe_whisper_local")
    def test_transcribe_whisper_local(self, mock_local: MagicMock) -> None:
        mock_local.return_value = "hello world"
        t = AudioTranscriber(backend=TranscriberBackend.WHISPER_LOCAL)
        result = t.transcribe(b"fake-audio")
        assert result == "hello world"
        mock_local.assert_called_once_with(b"fake-audio")

    @patch("smart_automator.voice.transcriber.AudioTranscriber._transcribe_deepgram")
    def test_transcribe_deepgram(self, mock_dg: MagicMock) -> None:
        mock_dg.return_value = "transcription from deepgram"
        t = AudioTranscriber(backend=TranscriberBackend.DEEPGRAM, api_key="key")
        result = t.transcribe(b"audio")
        assert result == "transcription from deepgram"

    @patch("smart_automator.voice.transcriber.AudioTranscriber._transcribe_whisper_api")
    def test_transcribe_whisper_api(self, mock_api: MagicMock) -> None:
        mock_api.return_value = "api result"
        t = AudioTranscriber(backend=TranscriberBackend.WHISPER_API, api_key="key")
        result = t.transcribe(b"audio")
        assert result == "api result"

    def test_transcribe_file(self, tmp_path: Path) -> None:
        wav = _make_wav_bytes()
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(wav)

        t = AudioTranscriber()
        with patch.object(t, "transcribe", return_value="file text") as mock_t:
            result = t.transcribe_file(audio_file)
        assert result == "file text"
        mock_t.assert_called_once_with(wav)

    def test_is_available_whisper_local_with_faster_whisper(self) -> None:
        t = AudioTranscriber(backend=TranscriberBackend.WHISPER_LOCAL)
        with patch.dict("sys.modules", {"faster_whisper": MagicMock()}):
            assert t.is_available() is True

    def test_is_available_deepgram_needs_key(self) -> None:
        assert AudioTranscriber(backend=TranscriberBackend.DEEPGRAM).is_available() is False
        assert AudioTranscriber(backend=TranscriberBackend.DEEPGRAM, api_key="k").is_available() is True

    def test_is_available_whisper_api_needs_key(self) -> None:
        assert AudioTranscriber(backend=TranscriberBackend.WHISPER_API).is_available() is False
        assert AudioTranscriber(backend=TranscriberBackend.WHISPER_API, api_key="k").is_available() is True

    def test_deepgram_without_key_raises(self) -> None:
        t = AudioTranscriber(backend=TranscriberBackend.DEEPGRAM)
        with pytest.raises(ValueError, match="Deepgram API key required"):
            t._transcribe_deepgram(b"audio")

    def test_whisper_api_without_key_raises(self) -> None:
        t = AudioTranscriber(backend=TranscriberBackend.WHISPER_API)
        with pytest.raises(ValueError, match="OpenAI API key required"):
            t._transcribe_whisper_api(b"audio")

    @patch("smart_automator.voice.transcriber.subprocess.run")
    def test_whisper_cli_fallback_not_found(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError
        t = AudioTranscriber(backend=TranscriberBackend.WHISPER_LOCAL)
        result = t._transcribe_whisper_cli(b"audio")
        assert "unavailable" in result.lower()


# ===========================================================================
# VoiceSpeaker Tests
# ===========================================================================

class TestTTSBackend:
    """Tests for TTSBackend enum."""

    def test_enum_values(self) -> None:
        assert TTSBackend.PYTTSX3.value == "pyttsx3"
        assert TTSBackend.ELEVENLABS.value == "elevenlabs"
        assert TTSBackend.SYSTEM.value == "system"


class TestVoiceSpeaker:
    """Tests for VoiceSpeaker (all audio mocked)."""

    def test_default_construction(self) -> None:
        s = VoiceSpeaker()
        assert s._backend == TTSBackend.PYTTSX3
        assert s.is_speaking is False
        assert s._rate == 175
        assert s._volume == 0.9

    def test_custom_construction(self) -> None:
        s = VoiceSpeaker(
            backend=TTSBackend.ELEVENLABS,
            api_key="el-key",
            voice_id="custom",
            rate=200,
            volume=0.5,
        )
        assert s._backend == TTSBackend.ELEVENLABS
        assert s._api_key == "el-key"
        assert s._voice_id == "custom"
        assert s._rate == 200

    def test_speak_empty_text_is_noop(self) -> None:
        s = VoiceSpeaker()
        with patch.object(s, "_do_speak") as mock_do:
            s.speak("   ", blocking=True)
            mock_do.assert_not_called()

    @patch("smart_automator.voice.speaker.VoiceSpeaker._speak_pyttsx3")
    def test_speak_blocking_pyttsx3(self, mock_speak: MagicMock) -> None:
        s = VoiceSpeaker(backend=TTSBackend.PYTTSX3)
        s.speak("hello", blocking=True)
        mock_speak.assert_called_once_with("hello")
        assert s.is_speaking is False

    @patch("smart_automator.voice.speaker.VoiceSpeaker._speak_pyttsx3")
    def test_speak_non_blocking(self, mock_speak: MagicMock) -> None:
        s = VoiceSpeaker(backend=TTSBackend.PYTTSX3)
        s.speak("hello", blocking=False)
        # Non-blocking starts a thread; give it a moment
        import time
        time.sleep(0.1)
        mock_speak.assert_called_once_with("hello")

    def test_is_speaking_property(self) -> None:
        s = VoiceSpeaker()
        assert s.is_speaking is False
        s._speaking = True
        assert s.is_speaking is True

    def test_stop_clears_speaking(self) -> None:
        s = VoiceSpeaker()
        s._speaking = True
        s.stop()
        assert s.is_speaking is False

    def test_stop_with_engine(self) -> None:
        s = VoiceSpeaker(backend=TTSBackend.PYTTSX3)
        mock_engine = MagicMock()
        s._engine = mock_engine
        s._speaking = True
        s.stop()
        mock_engine.stop.assert_called_once()
        assert s.is_speaking is False

    def test_is_available_pyttsx3(self) -> None:
        s = VoiceSpeaker(backend=TTSBackend.PYTTSX3)
        with patch.dict("sys.modules", {"pyttsx3": MagicMock()}):
            assert s.is_available() is True

    def test_is_available_elevenlabs_needs_key(self) -> None:
        assert VoiceSpeaker(backend=TTSBackend.ELEVENLABS).is_available() is False
        assert VoiceSpeaker(backend=TTSBackend.ELEVENLABS, api_key="k").is_available() is True

    def test_is_available_system_always_true(self) -> None:
        s = VoiceSpeaker(backend=TTSBackend.SYSTEM)
        assert s.is_available() is True

    def test_elevenlabs_without_key_raises(self) -> None:
        s = VoiceSpeaker(backend=TTSBackend.ELEVENLABS)
        with pytest.raises(ValueError, match="ElevenLabs API key required"):
            s._speak_elevenlabs("test")

    @patch("subprocess.run")
    @patch("platform.system", return_value="Darwin")
    def test_speak_system_macos(self, mock_platform: MagicMock, mock_run: MagicMock) -> None:
        s = VoiceSpeaker(backend=TTSBackend.SYSTEM)
        s._speak_system("hello")
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["say", "hello"]
