"""Cloud STT backend using OpenAI Whisper API."""

from __future__ import annotations

from typing import Any, Callable

from app.services.stt import STTTranscriptionError


class WhisperSTT:
    """Speech-to-text implementation backed by Whisper API."""

    def __init__(
        self,
        settings,
        client_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self._api_key = getattr(settings, "openai_api_key", None)
        self._client_factory = client_factory or self._default_client_factory
        self._client: Any | None = None

    async def transcribe(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
    ) -> str:
        """Transcribe WAV bytes with Whisper."""
        del sample_rate

        if not audio_bytes:
            raise STTTranscriptionError("Audio payload is empty.")

        if not self._api_key:
            raise STTTranscriptionError(
                "OpenAI API key is missing. "
                "Set OPENAI_API_KEY for cloud STT mode."
            )

        try:
            client = self._get_client()
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.wav", audio_bytes, "audio/wav"),
            )
        except STTTranscriptionError:
            raise
        except Exception as exc:
            raise STTTranscriptionError(
                "Whisper transcription request failed."
            ) from exc

        text = getattr(response, "text", "")
        if not isinstance(text, str) or not text.strip():
            raise STTTranscriptionError(
                "Whisper returned an empty transcript."
            )

        return text.strip()

    def _get_client(self) -> Any:
        if self._client is None:
            if not self._api_key:
                raise STTTranscriptionError(
                    "OpenAI API key is not configured."
                )
            self._client = self._client_factory(self._api_key)
        return self._client

    @staticmethod
    def _default_client_factory(api_key: str) -> Any:
        try:
            from openai import AsyncOpenAI
        except Exception as exc:
            raise STTTranscriptionError(
                "openai package is not installed. Install dependencies "
                "to use cloud STT mode."
            ) from exc

        return AsyncOpenAI(api_key=api_key)
