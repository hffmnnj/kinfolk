"""Wake word detection service using openWakeWord."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import WebSocket

LOGGER = logging.getLogger(__name__)


def _normalize_label(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


class WakeWordService:
    """Local wake word detection and WebSocket event broadcast."""

    def __init__(
        self,
        sensitivity: float,
        engine: str,
        sample_rate: int,
        channels: int,
        wake_words: tuple[str, ...] = ("hey kin", "kinfolk"),
        detector_factory: Callable[[], Any] | None = None,
        audio_stream_factory: (
            Callable[[Callable[..., Any]], Any] | None
        ) = None,
    ) -> None:
        self._sensitivity = sensitivity
        self._engine = engine
        self._sample_rate = sample_rate
        self._channels = channels
        self._wake_words = wake_words
        self._wake_word_tokens = tuple(
            _normalize_label(word) for word in wake_words
        )

        self._detector_factory = detector_factory or self._build_detector
        self._audio_stream_factory = (
            audio_stream_factory or self._build_audio_stream
        )

        self._detector: Any | None = None
        self._audio_stream: Any | None = None
        self._audio_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=32)
        self._process_task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        self._running = False
        self._enabled = True
        self._last_detection: datetime | None = None
        self._last_detection_monotonic = 0.0

        self._clients: set[WebSocket] = set()
        self._client_lock = asyncio.Lock()

    async def start(self) -> None:
        """Start wake word detector as a background task."""
        if self._running:
            return

        self._loop = asyncio.get_running_loop()
        self._detector = self._detector_factory()
        if self._detector is None:
            self._enabled = False
            return

        self._audio_stream = self._audio_stream_factory(self._audio_callback)
        if self._audio_stream is None:
            self._enabled = False
            return

        self._audio_stream.start()
        self._running = True
        self._enabled = True
        self._process_task = asyncio.create_task(
            self._process_audio(),
            name="wake-word",
        )

    async def stop(self) -> None:
        """Stop wake word detector and cleanup resources."""
        self._running = False

        if self._process_task is not None:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
            self._process_task = None

        if self._audio_stream is not None:
            try:
                self._audio_stream.stop()
            except Exception:
                LOGGER.exception("Failed to stop audio stream")
            try:
                self._audio_stream.close()
            except Exception:
                LOGGER.exception("Failed to close audio stream")
            self._audio_stream = None

        while not self._audio_queue.empty():
            self._audio_queue.get_nowait()

    async def register_client(self, websocket: WebSocket) -> None:
        """Register a WebSocket client for wake word events."""
        async with self._client_lock:
            self._clients.add(websocket)

    async def unregister_client(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket client."""
        async with self._client_lock:
            self._clients.discard(websocket)

    def get_status(self) -> dict[str, Any]:
        """Return current voice pipeline status."""
        return {
            "wake_word": {
                "active": self._running and self._enabled,
                "engine": self._engine,
                "sensitivity": self._sensitivity,
                "wake_words": list(self._wake_words),
            },
            "listening": self._running and self._enabled,
            "audio": {
                "sample_rate": self._sample_rate,
                "channels": self._channels,
            },
            "clients": len(self._clients),
            "last_detection": (
                self._last_detection.isoformat()
                if self._last_detection
                else None
            ),
        }

    async def notify_detection(self, wake_word: str, score: float) -> None:
        """Broadcast wake word detection to connected clients."""
        self._last_detection = datetime.now(timezone.utc)
        payload = {
            "event": "wake_word_detected",
            "wake_word": wake_word,
            "score": score,
            "timestamp": self._last_detection.isoformat(),
        }
        await self._broadcast(payload)

    def _build_detector(self) -> Any | None:
        """Create openWakeWord detector instance."""
        if self._engine != "openwakeword":
            LOGGER.warning("Unsupported wake word engine: %s", self._engine)
            return None

        try:
            from openwakeword.model import Model
        except Exception as exc:
            LOGGER.warning(
                "openwakeword unavailable, wake word disabled: %s",
                exc,
            )
            return None

        try:
            return Model()
        except Exception as exc:
            LOGGER.warning(
                "Failed to initialize openwakeword model: %s",
                exc,
            )
            return None

    def _build_audio_stream(self, callback: Callable[..., Any]) -> Any | None:
        """Create sounddevice input stream."""
        try:
            import sounddevice as sd
        except Exception as exc:
            LOGGER.warning(
                "sounddevice unavailable, wake word disabled: %s",
                exc,
            )
            return None

        try:
            return sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                callback=callback,
            )
        except Exception as exc:
            LOGGER.warning(
                "Failed to initialize microphone input stream: %s",
                exc,
            )
            return None

    def _audio_callback(
        self,
        indata: Any,
        frames: int,
        time_info: Any,
        status: Any,
    ) -> None:
        """Receive microphone chunks and enqueue for async processing."""
        del frames, time_info

        if not self._running or self._loop is None:
            return

        if status:
            LOGGER.debug("Audio status warning: %s", status)

        chunk = indata.copy() if hasattr(indata, "copy") else indata

        def _enqueue() -> None:
            if self._audio_queue.full():
                return
            self._audio_queue.put_nowait(chunk)

        self._loop.call_soon_threadsafe(_enqueue)

    async def _process_audio(self) -> None:
        """Consume audio and run local wake word detection."""
        while self._running:
            chunk = await self._audio_queue.get()
            pcm = self._to_pcm16(chunk)
            detections = self._predict_scores(pcm)
            match = self._pick_wake_word(detections)
            if match is None:
                continue

            wake_word, score = match
            now_monotonic = asyncio.get_running_loop().time()
            if now_monotonic - self._last_detection_monotonic < 1.5:
                continue

            self._last_detection_monotonic = now_monotonic
            await self.notify_detection(wake_word=wake_word, score=score)

    def _to_pcm16(self, indata: Any) -> Any:
        try:
            import numpy as np
        except Exception:
            return indata

        array = np.asarray(indata)
        if array.ndim == 2:
            mono = array[:, 0]
        else:
            mono = array

        clipped = np.clip(mono, -1.0, 1.0)
        return (clipped * 32767).astype(np.int16)

    def _predict_scores(self, pcm: Any) -> dict[str, float]:
        if self._detector is None:
            return {}

        try:
            raw = self._detector.predict(pcm)
        except Exception:
            LOGGER.exception("Wake word detection failed for audio chunk")
            return {}

        if isinstance(raw, dict):
            return {str(key): float(value) for key, value in raw.items()}

        return {}

    def _pick_wake_word(
        self,
        scores: dict[str, float],
    ) -> tuple[str, float] | None:
        best_label = ""
        best_score = 0.0

        for label, score in scores.items():
            if score < self._sensitivity:
                continue

            normalized = _normalize_label(label)
            if not any(
                token in normalized for token in self._wake_word_tokens
            ):
                continue

            if score > best_score:
                best_score = score
                best_label = label

        if not best_label:
            return None

        return best_label, best_score

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        async with self._client_lock:
            clients = list(self._clients)

        dead_clients: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                dead_clients.append(client)

        if dead_clients:
            async with self._client_lock:
                for dead in dead_clients:
                    self._clients.discard(dead)
