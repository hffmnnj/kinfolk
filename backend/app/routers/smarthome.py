"""Smart home integration API router (placeholder)."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.common import APIResponse

router = APIRouter()


@router.get("/devices", response_model=APIResponse)
async def list_devices():
    """List smart home devices (placeholder — Home Assistant in Milestone 5)."""
    return APIResponse(
        data={
            "devices": [],
            "message": "Smart home integration coming in Milestone 5",
        },
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/scenes", response_model=APIResponse)
async def list_scenes():
    """List smart home scenes (placeholder)."""
    return APIResponse(
        data={
            "scenes": [],
            "message": "Smart home integration coming in Milestone 5",
        },
        timestamp=datetime.now(timezone.utc),
    )
