"""Speech-to-text service abstraction with pluggable backends."""

from __future__ import annotations

from typing import Protocol


class STTError(Exception):
    """Base STT service error."""


class STTTranscriptionError(STTError):
    """Raised when transcription fails."""


class STTModelNotFoundError(STTTranscriptionError):
    """Raised when the local STT model is unavailable."""


class STTBackend(Protocol):
    """Speech-to-text backend contract."""

    async def transcribe(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
    ) -> str:
        """Transcribe 16kHz mono PCM audio bytes to text."""


class STTService:
    """Delegates transcription to configured STT backend."""

    def __init__(
        self,
        settings,
        backend: STTBackend | None = None,
    ) -> None:
        self._settings = settings
        self._sample_rate = getattr(settings, "audio_sample_rate", 16000)
        self._backend = backend or self._create_backend(settings)

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe bytes using configured backend."""
        return await self._backend.transcribe(
            audio_bytes=audio_bytes,
            sample_rate=self._sample_rate,
        )

    def _create_backend(self, settings) -> STTBackend:
        mode = str(getattr(settings, "stt_mode", "local")).strip().lower()

        if mode == "cloud":
            from app.services.stt_whisper import WhisperSTT

            return WhisperSTT(settings=settings)

        if mode == "local":
            from app.services.stt_vosk import VoskSTT

            return VoskSTT(settings=settings)

        raise ValueError(
            f"Invalid STT mode. Expected 'cloud' or 'local', got: {mode!r}"
        )
