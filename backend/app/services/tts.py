"""Text-to-Speech service — config-driven backend selection.

Delegates to NanoTTS (offline) or gTTS (network) based on
``settings.tts_engine``.  Both ``speak()`` and ``synthesize()`` are
async so they integrate cleanly with the FastAPI event loop.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


class TTSService:
    """Unified TTS facade with pluggable backends.

    Parameters
    ----------
    settings:
        Application settings object (must expose ``tts_engine``,
        ``tts_speed``, and ``tts_volume``).
    backend_override:
        Optional backend instance injected for testing.
    playback_fn:
        Optional callable for audio playback — injected for testing.
    """

    def __init__(
        self,
        settings: Any,
        backend_override: Any | None = None,
        playback_fn: Any | None = None,
    ) -> None:
        self._engine = getattr(settings, "tts_engine", "nanotts")
        self._speed = getattr(settings, "tts_speed", 1.0)
        self._volume = getattr(settings, "tts_volume", 0.8)
        self._playback_fn = playback_fn or self._default_playback
        self._backend = backend_override or self._build_backend()

    def _build_backend(self) -> Any:
        """Lazily construct the configured TTS backend."""
        if self._engine == "gtts":
            from app.services.tts_gtts import GTTSBackend

            return GTTSBackend(lang="en", slow=False)

        # Default: nanotts
        from app.services.tts_nanotts import NanoTTSBackend

        return NanoTTSBackend(
            lang="en-US",
            speed=self._speed,
            volume=self._volume,
        )

    @property
    def engine(self) -> str:
        """Return the active engine name."""
        return self._engine

    @property
    def available(self) -> bool:
        """Return *True* when the active backend is usable."""
        return getattr(self._backend, "available", False)

    async def synthesize(self, text: str) -> bytes:
        """Convert *text* to WAV audio bytes without playing."""
        if not text or not text.strip():
            return b""
        return await self._backend.synthesize(text)

    async def speak(self, text: str) -> None:
        """Synthesise *text* and play through system audio."""
        audio = await self.synthesize(text)
        if not audio:
            LOGGER.debug("No audio produced for text: %r", text)
            return
        await self._playback_fn(audio)

    @staticmethod
    async def _default_playback(audio_data: bytes) -> None:
        """Play WAV bytes via ``aplay`` subprocess.

        Falls back to ``sounddevice`` when ``aplay`` is unavailable.
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)
            tmp.write(audio_data)

        try:
            proc = subprocess.run(
                ["aplay", "-q", str(wav_path)],
                capture_output=True,
                timeout=30,
                check=False,
            )
            if proc.returncode == 0:
                return

            LOGGER.debug(
                "aplay failed (rc=%d), trying sounddevice",
                proc.returncode,
            )
        except FileNotFoundError:
            LOGGER.debug("aplay not found, trying sounddevice")

        try:
            import sounddevice as sd
            import numpy as np
            import wave as wave_mod

            with wave_mod.open(str(wav_path), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                sample_width = wf.getsampwidth()
                channels = wf.getnchannels()
                rate = wf.getframerate()

            dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
            dtype = dtype_map.get(sample_width, np.int16)
            audio_array = np.frombuffer(frames, dtype=dtype)
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)

            sd.play(audio_array, samplerate=rate)
            sd.wait()
        except Exception as exc:
            LOGGER.warning("Audio playback failed: %s", exc)
        finally:
            wav_path.unlink(missing_ok=True)
