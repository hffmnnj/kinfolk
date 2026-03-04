"""Music playback API router backed by Mopidy."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.schemas.common import APIResponse
from app.services.music import MopidyMusicService

router = APIRouter()


class SetVolumeRequest(BaseModel):
    """Request body for explicit volume setting."""

    level: int = Field(ge=0, le=100)


def _get_music_service(request: Request) -> MopidyMusicService:
    service = getattr(request.app.state, "music_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Music service not initialized",
        )
    return service


@router.get("/status", response_model=APIResponse)
async def get_music_status(request: Request):
    """Return current playback state and track details."""
    service = _get_music_service(request)
    state = await service.get_playback_state()
    return APIResponse(
        data=state.model_dump(),
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/play", response_model=APIResponse)
async def play_music(request: Request):
    service = _get_music_service(request)
    await service.play()
    state = await service.get_playback_state()
    return APIResponse(
        data=state.model_dump(),
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/pause", response_model=APIResponse)
async def pause_music(request: Request):
    service = _get_music_service(request)
    await service.pause()
    state = await service.get_playback_state()
    return APIResponse(
        data=state.model_dump(),
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/next", response_model=APIResponse)
async def next_track(request: Request):
    service = _get_music_service(request)
    await service.next_track()
    state = await service.get_playback_state()
    return APIResponse(
        data=state.model_dump(),
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/previous", response_model=APIResponse)
async def previous_track(request: Request):
    service = _get_music_service(request)
    await service.previous_track()
    state = await service.get_playback_state()
    return APIResponse(
        data=state.model_dump(),
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/volume", response_model=APIResponse)
async def set_volume(payload: SetVolumeRequest, request: Request):
    service = _get_music_service(request)
    await service.set_volume(payload.level)
    state = await service.get_playback_state()
    return APIResponse(
        data=state.model_dump(),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/search", response_model=APIResponse)
async def search_music(request: Request, q: str = Query(min_length=1)):
    service = _get_music_service(request)
    tracks = await service.search(q)
    return APIResponse(
        data=[track.model_dump() for track in tracks],
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/browse", response_model=APIResponse)
async def browse_music(request: Request, path: str = ""):
    service = _get_music_service(request)
    entries = await service.browse(path=path)
    return APIResponse(
        data=[entry.model_dump() for entry in entries],
        timestamp=datetime.now(timezone.utc),
    )
