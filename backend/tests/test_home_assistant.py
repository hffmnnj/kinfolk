"""Tests for Home Assistant service and smarthome intent handler."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from app.schemas.intent import Intent, IntentSlot
from app.schemas.smarthome import SmartDevice
from app.services.home_assistant import HomeAssistantService
from app.services.intent_handlers.smarthome_handler import SmartHomeIntentHandler


@dataclass
class _TestSettings:
    ha_url: str | None = "http://ha.local:8123"
    ha_token: str | None = "test-token"


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPError("request failed")


@pytest.mark.asyncio
async def test_get_entities_lists_devices(monkeypatch):
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def get(self, url, headers=None):
            del headers
            assert url.endswith("/api/states")
            return _FakeResponse(
                [
                    {
                        "entity_id": "light.living_room",
                        "state": "on",
                        "attributes": {"friendly_name": "Living Room Light"},
                    },
                    {
                        "entity_id": "switch.coffee_machine",
                        "state": "off",
                        "attributes": {"friendly_name": "Coffee Machine"},
                    },
                ]
            )

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    service = HomeAssistantService(settings_obj=_TestSettings())
    devices = await service.get_entities()

    assert len(devices) == 2
    assert devices[0].entity_id == "light.living_room"
    assert devices[0].name == "Living Room Light"


@pytest.mark.asyncio
async def test_turn_on_turn_off_and_scene_activation(monkeypatch):
    calls = []

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def post(self, url, headers=None, json=None):
            del headers
            calls.append((url, json))
            return _FakeResponse({"result": "ok"})

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    service = HomeAssistantService(settings_obj=_TestSettings())

    assert await service.turn_on("light.kitchen") is True
    assert await service.turn_off("switch.fan") is True
    assert await service.activate_scene("movie_mode") is True

    assert calls[0][0].endswith("/api/services/light/turn_on")
    assert calls[1][0].endswith("/api/services/switch/turn_off")
    assert calls[2][0].endswith("/api/services/scene/turn_on")
    assert calls[2][1]["entity_id"] == "scene.movie_mode"


@pytest.mark.asyncio
async def test_graceful_offline_mode_returns_cached_entities(monkeypatch):
    class _OnlineClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def get(self, url, headers=None):
            del headers
            assert url.endswith("/api/states")
            return _FakeResponse(
                [
                    {
                        "entity_id": "light.office",
                        "state": "on",
                        "attributes": {"friendly_name": "Office Light"},
                    }
                ]
            )

    monkeypatch.setattr(httpx, "AsyncClient", _OnlineClient)
    service = HomeAssistantService(settings_obj=_TestSettings())

    online = await service.get_entities()
    assert len(online) == 1
    assert online[0].entity_id == "light.office"

    class _OfflineClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        async def get(self, url, headers=None):
            del headers
            request = httpx.Request("GET", url)
            raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(httpx, "AsyncClient", _OfflineClient)

    offline = await service.get_entities()
    assert len(offline) == 1
    assert offline[0].entity_id == "light.office"


@pytest.mark.asyncio
async def test_smarthome_intent_handler_routes_intents():
    class _FakeHAService:
        def __init__(self) -> None:
            self.calls = []

        async def get_entities(self):
            return [
                SmartDevice(
                    entity_id="light.living_room_ceiling",
                    name="Living Room Ceiling",
                    state="off",
                    domain="light",
                    attributes={},
                ),
                SmartDevice(
                    entity_id="switch.coffee_machine",
                    name="Coffee Machine",
                    state="off",
                    domain="switch",
                    attributes={},
                ),
            ]

        async def get_scenes(self):
            return [
                {
                    "entity_id": "scene.movie_mode",
                    "name": "Movie Mode",
                    "state": "scening",
                }
            ]

        async def turn_on(self, entity_id: str, **kwargs):
            self.calls.append(("turn_on", entity_id, kwargs))
            return True

        async def turn_off(self, entity_id: str):
            self.calls.append(("turn_off", entity_id, {}))
            return True

        async def call_service(self, domain, service, entity_id, **kwargs):
            self.calls.append(("call_service", domain, service, entity_id, kwargs))
            return True

        async def activate_scene(self, scene_id: str):
            self.calls.append(("activate_scene", scene_id, {}))
            return True

    ha = _FakeHAService()
    handler = SmartHomeIntentHandler(ha_service=ha)

    response_on = await handler.handle(
        Intent(
            name="turn_device",
            raw_text="turn on living room lights",
            slots=[IntentSlot(name="device", value="living room lights")],
        )
    )
    assert "turned living room lights on" in response_on

    response_off = await handler.handle(
        Intent(
            name="turn_off",
            slots=[IntentSlot(name="device", value="coffee machine")],
        )
    )
    assert "turned coffee machine off" in response_off

    response_set = await handler.handle(
        Intent(
            name="set_device",
            slots=[
                IntentSlot(name="device", value="living room lights"),
                IntentSlot(name="value", value="50"),
            ],
        )
    )
    assert "Set living room lights to 50." == response_set

    response_scene = await handler.handle(
        Intent(
            name="activate_scene",
            slots=[IntentSlot(name="scene", value="movie mode")],
        )
    )
    assert "Activated the movie mode scene." == response_scene

    assert ha.calls[0][0] == "turn_on"
    assert ha.calls[0][1] == "light.living_room_ceiling"
    assert ha.calls[1][0] == "turn_off"
    assert ha.calls[1][1] == "switch.coffee_machine"
    assert ha.calls[2][0] == "call_service"
    assert ha.calls[2][1] == "light"
    assert ha.calls[2][2] == "set_value"
    assert ha.calls[3][0] == "activate_scene"
    assert ha.calls[3][1] == "scene.movie_mode"
