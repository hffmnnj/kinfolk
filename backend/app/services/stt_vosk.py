"""Local offline STT backend using Vosk."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

from app.services.stt import STTModelNotFoundError, STTTranscriptionError


class VoskSTT:
    """Speech-to-text implementation backed by local Vosk model."""

    def __init__(
        self,
        settings,
        model_factory: Callable[[str], Any] | None = None,
        recognizer_factory: Callable[[Any, int], Any] | None = None,
        set_log_level: Callable[[int], None] | None = None,
    ) -> None:
        self._model_path = getattr(
            settings,
            "vosk_model_path",
            "./models/vosk-model-en-us",
        )
        self._model_factory = model_factory
        self._recognizer_factory = recognizer_factory
        self._set_log_level = set_log_level
        self._model: Any | None = None

    async def transcribe(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
    ) -> str:
        """Transcribe PCM audio bytes using local Vosk model."""
        if not audio_bytes:
            raise STTTranscriptionError("Audio payload is empty.")

        model = self._get_model()
        recognizer = self._get_recognizer(model=model, sample_rate=sample_rate)

        parts: list[str] = []
        for index in range(0, len(audio_bytes), 4096):
            chunk = audio_bytes[index:index + 4096]
            if recognizer.AcceptWaveform(chunk):
                text = self._extract_text(recognizer.Result())
                if text:
                    parts.append(text)

        final_text = self._extract_text(recognizer.FinalResult())
        if final_text:
            parts.append(final_text)

        transcript = " ".join(parts).strip()
        if not transcript:
            raise STTTranscriptionError("Vosk returned an empty transcript.")

        return transcript

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model

        if not os.path.isdir(self._model_path):
            raise STTModelNotFoundError(
                "Vosk model path not found: "
                f"{self._model_path}. Download a model and set "
                "VOSK_MODEL_PATH to its directory."
            )

        model_factory = self._model_factory
        if model_factory is None:
            try:
                import vosk
            except Exception as exc:
                raise STTTranscriptionError(
                    "vosk package is not installed. Install dependencies "
                    "to use local STT mode."
                ) from exc

            model_factory = vosk.Model
            self._recognizer_factory = (
                self._recognizer_factory or vosk.KaldiRecognizer
            )
            if self._set_log_level is None:
                self._set_log_level = vosk.SetLogLevel

        if self._set_log_level is not None:
            self._set_log_level(-1)

        try:
            self._model = model_factory(self._model_path)
        except Exception as exc:
            raise STTModelNotFoundError(
                f"Failed to load Vosk model from {self._model_path}: {exc}"
            ) from exc

        return self._model

    def _get_recognizer(self, model: Any, sample_rate: int) -> Any:
        recognizer_factory = self._recognizer_factory
        if recognizer_factory is None:
            try:
                import vosk
            except Exception as exc:
                raise STTTranscriptionError(
                    "vosk package is not installed. Install dependencies "
                    "to use local STT mode."
                ) from exc
            recognizer_factory = vosk.KaldiRecognizer

        return recognizer_factory(model, sample_rate)

    @staticmethod
    def _extract_text(raw_result: str) -> str:
        try:
            payload = json.loads(raw_result or "{}")
        except json.JSONDecodeError:
            return ""

        text = payload.get("text", "")
        if not isinstance(text, str):
            return ""

        return text.strip()
