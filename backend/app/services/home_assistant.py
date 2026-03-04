"""Home Assistant REST API service with offline fallback cache."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.schemas.smarthome import SmartDevice

LOGGER = logging.getLogger(__name__)


class HomeAssistantService:
    """Async Home Assistant client for device and scene operations."""

    def __init__(self, settings_obj=settings) -> None:
        self._ha_url = (settings_obj.ha_url or "").rstrip("/")
        self._ha_token = settings_obj.ha_token
        self._entity_cache: dict[str, SmartDevice] = {}
        self._scenes_cache: list[dict[str, Any]] = []

    def _is_configured(self) -> bool:
        return bool(self._ha_url and self._ha_token)

    def _headers(self) -> dict[str, str]:
        if not self._ha_token:
            return {"Content-Type": "application/json"}
        return {
            "Authorization": f"Bearer {self._ha_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _entity_to_device(payload: dict[str, Any]) -> SmartDevice:
        entity_id = str(payload.get("entity_id", ""))
        domain = entity_id.split(".", 1)[0] if "." in entity_id else "unknown"
        attributes = payload.get("attributes", {}) or {}

        display_name = (
            attributes.get("friendly_name")
            or entity_id.replace("_", " ").replace(".", " ").strip()
        )

        return SmartDevice(
            entity_id=entity_id,
            name=str(display_name),
            state=str(payload.get("state", "unknown")),
            domain=domain,
            attributes=attributes,
        )

    async def _get_json(self, path: str) -> Any:
        url = f"{self._ha_url}{path}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def _post_json(self, path: str, payload: dict[str, Any]) -> bool:
        url = f"{self._ha_url}{path}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
        return True

    async def is_connected(self) -> bool:
        """Check if Home Assistant is reachable and authenticated."""
        if not self._is_configured():
            return False

        try:
            await self._get_json("/api/")
            return True
        except (httpx.HTTPError, ValueError):
            return False

    async def get_entities(self) -> list[SmartDevice]:
        """Fetch all entities, returning cache when offline."""
        if not self._is_configured():
            return list(self._entity_cache.values())

        try:
            entities = await self._get_json("/api/states")
            devices: list[SmartDevice] = []
            for entity in entities:
                device = self._entity_to_device(entity)
                if not device.entity_id:
                    continue
                self._entity_cache[device.entity_id] = device
                devices.append(device)
            return devices
        except (httpx.HTTPError, ValueError):
            LOGGER.warning("Home Assistant unreachable; using cached entities")
            return list(self._entity_cache.values())

    async def get_entity_state(self, entity_id: str) -> SmartDevice:
        """Fetch one entity state, falling back to cache when offline."""
        fallback_domain = entity_id.split(".", 1)[0]
        if "." not in entity_id:
            fallback_domain = "unknown"

        if not self._is_configured():
            cached = self._entity_cache.get(entity_id)
            if cached is not None:
                return cached
            return SmartDevice(
                entity_id=entity_id,
                name=entity_id,
                state="unavailable",
                domain=fallback_domain,
                attributes={},
            )

        try:
            payload = await self._get_json(f"/api/states/{entity_id}")
            device = self._entity_to_device(payload)
            self._entity_cache[device.entity_id] = device
            return device
        except (httpx.HTTPError, ValueError):
            cached = self._entity_cache.get(entity_id)
            if cached is not None:
                return cached
            return SmartDevice(
                entity_id=entity_id,
                name=entity_id,
                state="unavailable",
                domain=fallback_domain,
                attributes={},
            )

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
        **kwargs: Any,
    ) -> bool:
        """Call a Home Assistant service endpoint."""
        if not self._is_configured():
            return False

        payload = {"entity_id": entity_id, **kwargs}
        try:
            return await self._post_json(
                f"/api/services/{domain}/{service}",
                payload,
            )
        except (httpx.HTTPError, ValueError):
            LOGGER.warning(
                "Home Assistant service call failed: %s.%s %s",
                domain,
                service,
                entity_id,
            )
            return False

    async def turn_on(self, entity_id: str, **kwargs: Any) -> bool:
        """Turn a device on via its entity domain."""
        domain = entity_id.split(".", 1)[0]
        if "." not in entity_id:
            domain = "homeassistant"
        ok = await self.call_service(domain, "turn_on", entity_id, **kwargs)
        if ok and entity_id in self._entity_cache:
            cached = self._entity_cache[entity_id]
            self._entity_cache[entity_id] = cached.model_copy(
                update={"state": "on"},
            )
        return ok

    async def turn_off(self, entity_id: str) -> bool:
        """Turn a device off via its entity domain."""
        domain = entity_id.split(".", 1)[0]
        if "." not in entity_id:
            domain = "homeassistant"
        ok = await self.call_service(domain, "turn_off", entity_id)
        if ok and entity_id in self._entity_cache:
            cached = self._entity_cache[entity_id]
            self._entity_cache[entity_id] = cached.model_copy(
                update={"state": "off"},
            )
        return ok

    async def activate_scene(self, scene_id: str) -> bool:
        """Activate a Home Assistant scene by scene entity id."""
        if not scene_id.startswith("scene."):
            scene_id = f"scene.{scene_id}"
        return await self.call_service("scene", "turn_on", scene_id)

    async def get_scenes(self) -> list[dict[str, Any]]:
        """List Home Assistant scenes, using cache when offline."""
        entities = await self.get_entities()
        scenes = [
            {
                "entity_id": device.entity_id,
                "name": device.name,
                "state": device.state,
            }
            for device in entities
            if device.domain == "scene"
        ]

        if scenes:
            self._scenes_cache = scenes
            return scenes

        return self._scenes_cache
