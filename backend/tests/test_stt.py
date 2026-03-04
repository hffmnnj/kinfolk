"""Tests for dual-mode speech-to-text services."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.stt import (
    STTModelNotFoundError,
    STTService,
    STTTranscriptionError,
)
from app.services.stt_vosk import VoskSTT
from app.services.stt_whisper import WhisperSTT


class _BackendRecorder:
    def __init__(self, text: str):
        self.text = text
        self.calls: list[tuple[bytes, int]] = []

    async def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        self.calls.append((audio_bytes, sample_rate))
        return self.text


@pytest.mark.asyncio
async def test_stt_service_delegates_to_whisper_when_mode_cloud(monkeypatch):
    """Cloud mode selects Whisper backend and delegates transcription."""
    backend = _BackendRecorder(text="cloud text")

    monkeypatch.setattr(
        STTService,
        "_create_backend",
        lambda self, settings: backend,
    )

    settings = SimpleNamespace(stt_mode="cloud", audio_sample_rate=16000)
    service = STTService(settings=settings)

    result = await service.transcribe(b"audio")

    assert result == "cloud text"
    assert backend.calls == [(b"audio", 16000)]


@pytest.mark.asyncio
async def test_stt_service_delegates_to_vosk_when_mode_local(monkeypatch):
    """Local mode selects Vosk backend and delegates transcription."""
    backend = _BackendRecorder(text="local text")

    monkeypatch.setattr(
        STTService,
        "_create_backend",
        lambda self, settings: backend,
    )

    settings = SimpleNamespace(stt_mode="local", audio_sample_rate=22050)
    service = STTService(settings=settings)

    result = await service.transcribe(b"audio")

    assert result == "local text"
    assert backend.calls == [(b"audio", 22050)]


@pytest.mark.asyncio
async def test_whisper_transcribe_uses_openai_client_mock():
    """Whisper backend uses async OpenAI client contract."""

    class _FakeTranscriptions:
        async def create(self, *, model, file):
            assert model == "whisper-1"
            assert file[0] == "audio.wav"
            assert file[2] == "audio/wav"
            return SimpleNamespace(text="Hello world")

    class _FakeClient:
        def __init__(self):
            self.audio = SimpleNamespace(transcriptions=_FakeTranscriptions())

    whisper = WhisperSTT(
        settings=SimpleNamespace(openai_api_key="test-key"),
        client_factory=lambda api_key: _FakeClient(),
    )

    result = await whisper.transcribe(b"wav-bytes")

    assert result == "Hello world"


@pytest.mark.asyncio
async def test_whisper_transcribe_raises_on_api_error():
    """Whisper backend wraps API failures in STTTranscriptionError."""

    class _BrokenTranscriptions:
        async def create(self, *, model, file):
            del model, file
            raise RuntimeError("upstream failure")

    class _FakeClient:
        def __init__(self):
            self.audio = SimpleNamespace(transcriptions=_BrokenTranscriptions())

    whisper = WhisperSTT(
        settings=SimpleNamespace(openai_api_key="test-key"),
        client_factory=lambda api_key: _FakeClient(),
    )

    with pytest.raises(STTTranscriptionError):
        await whisper.transcribe(b"wav-bytes")


@pytest.mark.asyncio
async def test_vosk_transcribe_uses_model_and_recognizer_mocks(tmp_path):
    """Vosk backend streams chunks and returns composed transcript."""

    class _FakeRecognizer:
        def __init__(self, model, sample_rate):
            del model, sample_rate
            self.calls = 0

        def AcceptWaveform(self, chunk):
            self.calls += 1
            del chunk
            return self.calls == 1

        def Result(self):
            return '{"text": "hello"}'

        def FinalResult(self):
            return '{"text": "world"}'

    model_path = tmp_path / "vosk-model"
    model_path.mkdir()

    vosk_stt = VoskSTT(
        settings=SimpleNamespace(vosk_model_path=str(model_path)),
        model_factory=lambda path: object(),
        recognizer_factory=lambda model, sample_rate: _FakeRecognizer(
            model,
            sample_rate,
        ),
        set_log_level=lambda level: None,
    )

    result = await vosk_stt.transcribe(b"x" * 9000, sample_rate=16000)

    assert result == "hello world"


@pytest.mark.asyncio
async def test_vosk_missing_model_path_raises_clear_error(tmp_path):
    """Missing model directory raises STTModelNotFoundError."""
    missing = tmp_path / "missing-model"
    vosk_stt = VoskSTT(
        settings=SimpleNamespace(vosk_model_path=str(missing)),
    )

    with pytest.raises(STTModelNotFoundError, match="Vosk model path not found"):
        await vosk_stt.transcribe(b"audio", sample_rate=16000)
