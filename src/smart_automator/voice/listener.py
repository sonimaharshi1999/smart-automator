# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Push-to-talk voice listener using sounddevice for audio capture."""

from __future__ import annotations

import io
import queue
import threading
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np


@dataclass
class ListenerConfig:
    """Voice listener configuration."""
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    chunk_duration_s: float = 0.1
    silence_threshold: float = 500.0
    silence_duration_s: float = 1.5
    max_recording_s: float = 30.0
    output_dir: Path = field(default_factory=lambda: Path("recordings"))


class VoiceListener:
    """Push-to-talk voice capture with silence detection.

    Supports two modes:
    1. Push-to-talk: record while hotkey held
    2. Auto-detect: start on voice, stop after silence threshold
    """

    def __init__(self, config: ListenerConfig | None = None) -> None:
        self._config = config or ListenerConfig()
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._is_recording = False
        self._stop_event = threading.Event()
        self._config.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def record_until_silence(self, on_chunk: Callable[[np.ndarray], None] | None = None) -> bytes:
        """Record audio until silence is detected. Returns WAV bytes."""
        import sounddevice as sd

        self._is_recording = True
        self._stop_event.clear()
        frames: list[np.ndarray] = []
        silence_chunks = 0
        chunk_samples = int(self._config.sample_rate * self._config.chunk_duration_s)
        max_chunks = int(self._config.max_recording_s / self._config.chunk_duration_s)
        silence_limit = int(self._config.silence_duration_s / self._config.chunk_duration_s)

        def callback(indata: np.ndarray, frame_count: int, time_info: dict, status: int) -> None:
            self._audio_queue.put(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                dtype=self._config.dtype,
                blocksize=chunk_samples,
                callback=callback,
            ):
                while not self._stop_event.is_set() and len(frames) < max_chunks:
                    try:
                        chunk = self._audio_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    frames.append(chunk)
                    if on_chunk:
                        on_chunk(chunk)

                    amplitude = np.abs(chunk.astype(np.float32)).mean()
                    if amplitude < self._config.silence_threshold:
                        silence_chunks += 1
                        if silence_chunks >= silence_limit and len(frames) > silence_limit:
                            break
                    else:
                        silence_chunks = 0
        finally:
            self._is_recording = False

        if not frames:
            return b""

        audio_data = np.concatenate(frames)
        return self._to_wav_bytes(audio_data)

    def record_for_duration(self, duration_s: float) -> bytes:
        """Record audio for a fixed duration. Returns WAV bytes."""
        import sounddevice as sd

        self._is_recording = True
        samples = int(self._config.sample_rate * duration_s)

        try:
            audio = sd.rec(
                samples,
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                dtype=self._config.dtype,
            )
            sd.wait()
        finally:
            self._is_recording = False

        return self._to_wav_bytes(audio)

    def stop(self) -> None:
        """Stop ongoing recording."""
        self._stop_event.set()

    def _to_wav_bytes(self, audio: np.ndarray) -> bytes:
        """Convert numpy audio array to WAV bytes."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self._config.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self._config.sample_rate)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()

    def save_recording(self, wav_bytes: bytes, filename: str = "recording.wav") -> Path:
        """Save WAV bytes to file."""
        path = self._config.output_dir / filename
        path.write_bytes(wav_bytes)
        return path
