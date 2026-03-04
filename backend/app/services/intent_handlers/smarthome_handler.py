"""Smart home voice intent handler backed by Home Assistant."""

from __future__ import annotations

import re
from typing import Any

from app.schemas.intent import Intent
from app.services.home_assistant import HomeAssistantService

_TURN_ON = {"turn_on", "turn_device"}
_TURN_OFF = {"turn_off"}
_SET_VALUE = {"set_value", "set_device"}
_ACTIVATE_SCENE = {"activate_scene"}


def _get_slot(intent: Intent, name: str) -> str:
    for slot in intent.slots:
        if slot.name == name and slot.value:
            return slot.value.strip()
    return ""


def _normalize(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for token in _normalize(text).split(" "):
        if not token:
            continue
        if token.endswith("s") and len(token) > 3:
            token = token[:-1]
        tokens.append(token)
    return tokens


class SmartHomeIntentHandler:
    """Route smarthome intents to Home Assistant service calls."""

    def __init__(self, ha_service: HomeAssistantService) -> None:
        self._ha = ha_service

    async def handle(self, intent: Intent) -> str:
        if intent.name in _TURN_ON:
            return await self._handle_turn(intent, turn_on=True)
        if intent.name in _TURN_OFF:
            return await self._handle_turn(intent, turn_on=False)
        if intent.name in _SET_VALUE:
            return await self._handle_set_value(intent)
        if intent.name in _ACTIVATE_SCENE:
            return await self._handle_activate_scene(intent)
        return "I couldn't map that smart home request yet."

    async def _handle_turn(self, intent: Intent, turn_on: bool) -> str:
        if intent.name == "turn_device":
            text = (intent.raw_text or "").lower()
            if "turn off" in text or "switch off" in text:
                turn_on = False
            elif "turn on" in text or "switch on" in text:
                turn_on = True

        device_name = _get_slot(intent, "device")
        if not device_name:
            return "Which device should I control?"

        entity_id = await self._resolve_device_entity(device_name)
        if not entity_id:
            return f"I couldn't find a device named {device_name}."

        if turn_on:
            ok = await self._ha.turn_on(entity_id)
        else:
            ok = await self._ha.turn_off(entity_id)

        if not ok:
            return "I couldn't reach Home Assistant right now."

        action = "on" if turn_on else "off"
        return f"Okay, I turned {device_name} {action}."

    async def _handle_set_value(self, intent: Intent) -> str:
        device_name = _get_slot(intent, "device")
        value = _get_slot(intent, "value")

        if not device_name or not value:
            return "Tell me which device and value to set."

        entity_id = await self._resolve_device_entity(device_name)
        if not entity_id:
            return f"I couldn't find a device named {device_name}."

        domain = entity_id.split(".", 1)[0]
        ok = await self._ha.call_service(
            domain,
            "set_value",
            entity_id,
            value=value,
        )
        if not ok:
            return "I couldn't apply that setting right now."

        return f"Set {device_name} to {value}."

    async def _handle_activate_scene(self, intent: Intent) -> str:
        scene_name = _get_slot(intent, "scene")
        if not scene_name:
            return "Which scene should I activate?"

        scene_entity = await self._resolve_scene_entity(scene_name)
        if not scene_entity:
            return f"I couldn't find a scene named {scene_name}."

        ok = await self._ha.activate_scene(scene_entity)
        if not ok:
            return "I couldn't activate that scene right now."

        return f"Activated the {scene_name} scene."

    async def _resolve_device_entity(self, requested_name: str) -> str | None:
        devices = await self._ha.get_entities()
        return self._best_entity_match(
            requested_name,
            [
                {
                    "id": device.entity_id,
                    "name": device.name,
                    "search": f"{device.entity_id} {device.name}",
                }
                for device in devices
            ],
        )

    async def _resolve_scene_entity(self, requested_name: str) -> str | None:
        scenes = await self._ha.get_scenes()
        return self._best_entity_match(
            requested_name,
            [
                {
                    "id": str(scene.get("entity_id", "")),
                    "name": str(scene.get("name", "")),
                    "search": (
                        f"{scene.get('entity_id', '')} "
                        f"{scene.get('name', '')}"
                    ),
                }
                for scene in scenes
            ],
        )

    @staticmethod
    def _best_entity_match(
        requested_name: str,
        candidates: list[dict[str, Any]],
    ) -> str | None:
        requested_tokens = _tokenize(requested_name)
        if not requested_tokens:
            return None

        best_id: str | None = None
        best_score = 0

        for candidate in candidates:
            text = _normalize(str(candidate.get("search", "")))
            if not text:
                continue

            score = 0
            for token in requested_tokens:
                if token in text:
                    score += 1

            if score > best_score:
                best_score = score
                best_id = str(candidate.get("id", ""))

        return best_id if best_score > 0 else None
