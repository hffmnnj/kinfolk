"""Tests for wake word service and voice WebSocket endpoints."""

import asyncio
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import voice
from app.services.wake_word import WakeWordService


class _FakeStream:
    def __init__(self, callback=None, **kwargs):
        self.callback = callback or kwargs.get("callback")
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


class _FakeWebSocketClient:
    def __init__(self):
        self.messages = []

    async def send_json(self, payload):
        self.messages.append(payload)


@pytest.mark.asyncio
async def test_wake_word_service_instantiation_and_lifecycle():
    """Service starts and stops cleanly with injected dependencies."""

    class _FakeDetector:
        def predict(self, pcm):
            del pcm
            return {}

    stream_ref = {}

    def _stream_factory(callback):
        stream_ref["stream"] = _FakeStream(callback)
        return stream_ref["stream"]

    service = WakeWordService(
        sensitivity=0.5,
        engine="openwakeword",
        sample_rate=16000,
        channels=1,
        detector_factory=lambda: _FakeDetector(),
        audio_stream_factory=_stream_factory,
    )

    await service.start()
    status = service.get_status()

    assert status["wake_word"]["active"] is True
    assert status["listening"] is True
    assert stream_ref["stream"].started is True

    await service.stop()

    status_after = service.get_status()
    assert status_after["wake_word"]["active"] is False
    assert status_after["listening"] is False
    assert stream_ref["stream"].stopped is True
    assert stream_ref["stream"].closed is True


@pytest.mark.asyncio
async def test_wake_word_event_broadcast_with_mocked_dependencies(monkeypatch):
    """Wake word detection broadcasts an event to connected clients."""

    class _FakeModel:
        def predict(self, pcm):
            del pcm
            return {"kinfolk": 0.99}

    class _FakeSoundDeviceModule:
        InputStream = _FakeStream

    openwakeword_module = types.ModuleType("openwakeword")
    openwakeword_model_module = types.ModuleType("openwakeword.model")
    openwakeword_model_module.Model = _FakeModel

    monkeypatch.setitem(sys.modules, "openwakeword", openwakeword_module)
    monkeypatch.setitem(sys.modules, "openwakeword.model", openwakeword_model_module)
    monkeypatch.setitem(sys.modules, "sounddevice", _FakeSoundDeviceModule())

    service = WakeWordService(
        sensitivity=0.5,
        engine="openwakeword",
        sample_rate=16000,
        channels=1,
    )
    client = _FakeWebSocketClient()

    await service.start()
    await service.register_client(client)

    service._audio_callback(
        [[0.0] for _ in range(160)],
        160,
        None,
        None,
    )

    await asyncio.sleep(0.05)
    await service.stop()

    assert len(client.messages) == 1
    assert client.messages[0]["type"] == "wake_word"
    assert client.messages[0]["keyword"] == "kinfolk"
    assert client.messages[0]["confidence"] == 0.99


class _RouterWakeWordService:
    def __init__(self):
        self.registered = 0
        self.unregistered = 0

    def get_status(self):
        return {
            "wake_word": {"active": True, "engine": "openwakeword"},
            "listening": True,
            "audio": {"sample_rate": 16000, "channels": 1},
            "clients": 0,
            "last_detection": None,
        }

    async def register_client(self, websocket):
        self.registered += 1
        await websocket.send_json(
            {
                "type": "wake_word",
                "keyword": "kinfolk",
                "confidence": 0.99,
            }
        )

    async def unregister_client(self, websocket):
        del websocket
        self.unregistered += 1


def test_voice_websocket_connection_and_message_receipt():
    """Voice WS endpoint sends status and wake word events."""
    mock_service = _RouterWakeWordService()
    test_app = FastAPI()
    test_app.state.wake_word_service = mock_service
    test_app.include_router(voice.router, prefix="/api/v1/voice")

    with TestClient(test_app) as client:
        with client.websocket_connect("/api/v1/voice/ws") as websocket:
            status_msg = websocket.receive_json()
            wake_msg = websocket.receive_json()
            websocket.close()

    assert status_msg["type"] == "voice_status"
    assert wake_msg["type"] == "wake_word"
    assert wake_msg["keyword"] == "kinfolk"
    assert mock_service.registered == 1


@pytest.mark.asyncio
async def test_wake_word_service_graceful_shutdown():
    """Service shutdown stops stream resources without errors."""

    class _SilentDetector:
        def predict(self, pcm):
            del pcm
            return {}

    stream_ref = {}

    def _stream_factory(callback):
        stream_ref["stream"] = _FakeStream(callback)
        return stream_ref["stream"]

    service = WakeWordService(
        sensitivity=0.5,
        engine="openwakeword",
        sample_rate=16000,
        channels=1,
        detector_factory=lambda: _SilentDetector(),
        audio_stream_factory=_stream_factory,
    )

    await service.start()
    await service.stop()

    assert stream_ref["stream"].stopped is True
    assert stream_ref["stream"].closed is True
    assert service.get_status()["listening"] is False
