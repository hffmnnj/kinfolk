"""Authentication router for third-party OAuth providers."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.schemas.common import APIResponse
from app.services.calendar_google import (
    GoogleCalendarAuthError,
    GoogleCalendarConfigError,
    GoogleCalendarService,
)

router = APIRouter()


@router.get("/google", response_model=APIResponse)
async def get_google_auth_url():
    """Return Google OAuth URL for one-time account linking."""
    service = GoogleCalendarService()
    try:
        auth_url = service.get_auth_url()
    except GoogleCalendarConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return APIResponse(
        data={"provider": "google", "auth_url": auth_url},
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/google/callback", response_model=APIResponse)
async def handle_google_oauth_callback(
    code: str = Query(..., min_length=1),
    state: str | None = Query(default=None),
):
    """Handle OAuth callback and persist tokens for future sync."""
    service = GoogleCalendarService()
    try:
        service.handle_callback(code=code, state=state)
    except GoogleCalendarConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GoogleCalendarAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return APIResponse(
        data={"provider": "google", "connected": True},
        timestamp=datetime.now(timezone.utc),
    )
