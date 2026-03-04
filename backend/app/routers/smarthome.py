"""Smart home integration API router backed by Home Assistant."""

import asyncio
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)

from app.config import settings
from app.schemas.common import APIResponse
from app.schemas.smarthome import DeviceCommand
from app.services.home_assistant import HomeAssistantService
from app.services.home_assistant_ws import HomeAssistantWSService

router = APIRouter()


@router.get("/devices", response_model=APIResponse)
async def list_devices(request: Request):
    """List smart home entities from Home Assistant (or cache)."""
    ha_service = _get_ha_service(request)
    devices = await ha_service.get_entities()
    connected = await ha_service.is_connected()

    return APIResponse(
        data={
            "devices": [device.model_dump() for device in devices],
            "connected": connected,
        },
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/devices/{entity_id}/command", response_model=APIResponse)
async def command_device(
    entity_id: str,
    payload: DeviceCommand,
    request: Request,
):
    """Run a command against a Home Assistant entity."""
    ha_service = _get_ha_service(request)

    if payload.command == "turn_on":
        ok = await ha_service.turn_on(entity_id, **payload.params)
    elif payload.command == "turn_off":
        ok = await ha_service.turn_off(entity_id)
    elif payload.command == "set_value":
        domain = entity_id.split(".", 1)[0]
        if "." not in entity_id:
            domain = "homeassistant"
        ok = await ha_service.call_service(
            domain,
            "set_value",
            entity_id,
            **payload.params,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported device command",
        )

    if not ok:
        raise HTTPException(
            status_code=503,
            detail="Home Assistant unavailable or command failed",
        )

    return APIResponse(
        data={
            "entity_id": entity_id,
            "command": payload.command,
            "success": ok,
        },
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/scenes", response_model=APIResponse)
async def list_scenes(request: Request):
    """List Home Assistant scenes."""
    ha_service = _get_ha_service(request)
    scenes = await ha_service.get_scenes()

    return APIResponse(
        data={
            "scenes": scenes,
        },
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/scenes/{scene_id}/activate", response_model=APIResponse)
async def activate_scene(scene_id: str, request: Request):
    """Activate a Home Assistant scene."""
    ha_service = _get_ha_service(request)
    ok = await ha_service.activate_scene(scene_id)

    if not ok:
        raise HTTPException(
            status_code=503,
            detail="Home Assistant unavailable or scene activation failed",
        )

    return APIResponse(
        data={"scene_id": scene_id, "success": ok},
        timestamp=datetime.now(timezone.utc),
    )


@router.websocket("/ws")
async def smarthome_ws(websocket: WebSocket):
    """Stream real-time HA state changes to Flutter clients.

    On connect the client receives a ``snapshot`` message containing
    all cached entity states, followed by individual ``state_changed``
    messages as they arrive from Home Assistant.
    """
    ha_ws: HomeAssistantWSService | None = getattr(
        websocket.app.state, "ha_ws_service", None
    )

    await websocket.accept()

    # If the HA WebSocket service is not available, inform the client
    # and keep the connection open (Flutter shows offline indicator).
    if ha_ws is None:
        await websocket.send_json({"type": "status", "connected": False})
        # Hold connection open so Flutter doesn't spin-reconnect
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            return

    # Send initial snapshot so Flutter can hydrate immediately
    snapshot = ha_ws.get_snapshot()
    await websocket.send_json(
        {
            "type": "snapshot",
            "connected": ha_ws.is_connected(),
            "entities": snapshot,
        }
    )

    # Subscribe to the HA state fan-out queue
    queue = ha_ws.subscribe()
    try:
        while True:
            # Wait for the next state_changed message from HA
            payload = await queue.get()
            await websocket.send_text(payload)
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        pass
    finally:
        ha_ws.unsubscribe(queue)


def _get_ha_service(request: Request) -> HomeAssistantService:
    service = getattr(request.app.state, "ha_service", None)
    if service is None:
        return HomeAssistantService(settings_obj=settings)
    return service
