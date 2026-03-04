"""Home Assistant WebSocket service for real-time state updates.

Maintains a single persistent WebSocket connection to Home Assistant,
subscribes to state_changed events, and relays updates to connected
Flutter clients via a FastAPI WebSocket endpoint.

When HA is not configured (ha_url or ha_token missing), the service
operates as a no-op — no connections are attempted and no errors raised.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    InvalidURI,
    WebSocketException,
)

from app.config import settings

LOGGER = logging.getLogger(__name__)

# Reconnect parameters
_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 60.0
_BACKOFF_FACTOR = 2.0


class HomeAssistantWSService:
    """Manages a single HA WebSocket connection and fans out state
    updates to subscribed Flutter clients."""

    def __init__(self, settings_obj=settings) -> None:
        self._ha_url = (settings_obj.ha_url or "").rstrip("/")
        self._ha_token = settings_obj.ha_token or ""

        # In-memory cache: entity_id -> full state dict
        self._state_cache: dict[str, dict[str, Any]] = {}

        # Connected Flutter WebSocket clients
        self._subscribers: set[asyncio.Queue[str]] = set()

        # Internal bookkeeping
        self._ws: Any | None = None
        self._listen_task: asyncio.Task[None] | None = None
        self._msg_id = 0
        self._running = False

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _is_configured(self) -> bool:
        return bool(self._ha_url and self._ha_token)

    def _ws_url(self) -> str:
        """Derive the WebSocket URL from the configured HA HTTP URL."""
        url = self._ha_url
        if url.startswith("https"):
            url = "wss" + url[5:]
        elif url.startswith("http"):
            url = "ws" + url[4:]
        return f"{url}/api/websocket"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background listener task (no-op if HA not configured)."""
        if not self._is_configured():
            LOGGER.info("HA not configured — WebSocket service disabled")
            return

        self._running = True
        self._listen_task = asyncio.create_task(self._run_forever())
        LOGGER.info("Home Assistant WebSocket service started")

    async def stop(self) -> None:
        """Gracefully shut down the HA WebSocket connection."""
        self._running = False

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None

        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        LOGGER.info("Home Assistant WebSocket service stopped")

    # ------------------------------------------------------------------
    # Core connection loop with exponential backoff
    # ------------------------------------------------------------------

    async def _run_forever(self) -> None:
        """Connect, authenticate, subscribe, and listen — reconnecting
        on failure with exponential backoff."""
        backoff = _INITIAL_BACKOFF

        while self._running:
            try:
                await self._connect_and_listen()
                # If _connect_and_listen returns cleanly, reset backoff
                backoff = _INITIAL_BACKOFF
            except asyncio.CancelledError:
                return
            except Exception:  # noqa: BLE001
                LOGGER.warning(
                    "HA WebSocket disconnected — reconnecting in %.0fs",
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * _BACKOFF_FACTOR, _MAX_BACKOFF)

    async def _connect_and_listen(self) -> None:
        ws_url = self._ws_url()
        LOGGER.debug("Connecting to HA WebSocket: %s", ws_url)

        try:
            async with websockets.connect(ws_url) as ws:
                self._ws = ws
                await self._authenticate(ws)
                await self._subscribe_events(ws)
                await self._listen(ws)
        except (
            ConnectionClosed,
            InvalidURI,
            WebSocketException,
            OSError,
        ) as exc:
            LOGGER.warning("HA WebSocket error: %s", exc)
            raise
        finally:
            self._ws = None

    # ------------------------------------------------------------------
    # HA WebSocket protocol
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    async def _authenticate(self, ws: Any) -> None:
        """Complete the HA WebSocket auth handshake."""
        # HA sends {"type": "auth_required"} on connect
        raw = await ws.recv()
        msg = json.loads(raw)

        if msg.get("type") != "auth_required":
            LOGGER.warning(
                "Unexpected HA greeting: %s",
                msg.get("type"),
            )

        # Send auth token
        auth_payload = json.dumps(
            {
                "type": "auth",
                "access_token": self._ha_token,
            }
        )
        await ws.send(auth_payload)

        raw = await ws.recv()
        msg = json.loads(raw)

        if msg.get("type") != "auth_ok":
            err = msg.get("message", "unknown")
            raise ConnectionError(f"HA auth failed: {err}")

        LOGGER.info("Authenticated with Home Assistant")

    async def _subscribe_events(self, ws: Any) -> None:
        """Subscribe to state_changed events."""
        sub_id = self._next_id()
        await ws.send(
            json.dumps(
                {
                    "id": sub_id,
                    "type": "subscribe_events",
                    "event_type": "state_changed",
                }
            )
        )

        raw = await ws.recv()
        msg = json.loads(raw)

        if not msg.get("success"):
            LOGGER.warning("Failed to subscribe to state_changed: %s", msg)
        else:
            LOGGER.info("Subscribed to HA state_changed events")

        # Also fetch all current states to seed the cache
        await self._fetch_all_states(ws)

    async def _fetch_all_states(self, ws: Any) -> None:
        """Fetch all current entity states to populate the cache."""
        req_id = self._next_id()
        msg_payload = json.dumps(
            {"id": req_id, "type": "get_states"},
        )
        await ws.send(msg_payload)

        raw = await ws.recv()
        msg = json.loads(raw)

        if msg.get("success") and isinstance(msg.get("result"), list):
            for entity in msg["result"]:
                entity_id = entity.get("entity_id", "")
                if entity_id:
                    self._state_cache[entity_id] = entity
            LOGGER.info(
                "Cached %d entity states from HA",
                len(self._state_cache),
            )

    async def _listen(self, ws: Any) -> None:
        """Listen for state_changed events and update cache + subscribers."""
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue

            if msg.get("type") != "event":
                continue

            event = msg.get("event", {})
            if event.get("event_type") != "state_changed":
                continue

            data = event.get("data", {})
            new_state = data.get("new_state")
            if not new_state:
                continue

            entity_id = new_state.get("entity_id", "")
            if not entity_id:
                continue

            # Update cache
            self._state_cache[entity_id] = new_state

            # Fan out to Flutter subscribers
            if "." in entity_id:
                domain = entity_id.split(".", 1)[0]
            else:
                domain = "unknown"
            payload = json.dumps(
                {
                    "type": "state_changed",
                    "entity_id": entity_id,
                    "state": new_state.get("state", "unknown"),
                    "attributes": new_state.get("attributes", {}),
                    "domain": domain,
                }
            )
            await self._broadcast(payload)

    # ------------------------------------------------------------------
    # Subscriber management (Flutter clients)
    # ------------------------------------------------------------------

    def subscribe(self) -> asyncio.Queue[str]:
        """Register a new Flutter client and return its message queue."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        """Remove a Flutter client subscription."""
        self._subscribers.discard(queue)

    async def _broadcast(self, payload: str) -> None:
        """Send a message to all connected Flutter clients."""
        dead: list[asyncio.Queue[str]] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(queue)

        for q in dead:
            self._subscribers.discard(q)

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def get_entity_state(self, entity_id: str) -> dict[str, Any]:
        """Return cached state for an entity, or empty dict if unknown."""
        return self._state_cache.get(entity_id, {})

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """Return the full entity state cache."""
        return dict(self._state_cache)

    def is_connected(self) -> bool:
        """True when the HA WebSocket connection is active."""
        return self._ws is not None and self._running

    def get_snapshot(self) -> list[dict[str, Any]]:
        """Return a list of all cached entities in a Flutter-friendly
        format for initial state hydration."""
        result: list[dict[str, Any]] = []
        for entity_id, state in self._state_cache.items():
            if "." in entity_id:
                domain = entity_id.split(".", 1)[0]
            else:
                domain = "unknown"
            result.append(
                {
                    "entity_id": entity_id,
                    "state": state.get("state", "unknown"),
                    "attributes": state.get("attributes", {}),
                    "domain": domain,
                }
            )
        return result
