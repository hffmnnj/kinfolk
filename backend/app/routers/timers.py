"""Timers API router."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.schemas.common import APIResponse
from app.schemas.timer import TimerCreate, TimerResponse
from app.services.timers import TimerService

router = APIRouter()


def _get_timer_service(request: Request) -> TimerService:
    """Retrieve the TimerService from application state."""
    service = getattr(request.app.state, "timer_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Timer service not available",
        )
    return service


def _enrich_response(timer, service: TimerService) -> TimerResponse:
    """Build a TimerResponse with computed remaining_seconds."""
    remaining = service.remaining_seconds(timer)
    resp = TimerResponse.model_validate(timer)
    resp.remaining_seconds = remaining
    return resp


@router.get("/", response_model=APIResponse)
async def list_timers(request: Request):
    """List active timers with remaining seconds."""
    service = _get_timer_service(request)
    timers = service.get_timers()
    data = [_enrich_response(t, service) for t in timers]
    return APIResponse(
        data=data,
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/", response_model=APIResponse, status_code=201)
async def create_timer(body: TimerCreate, request: Request):
    """Create a new timer or alarm."""
    service = _get_timer_service(request)

    if body.fire_at is not None:
        timer = service.set_alarm(
            name=body.name,
            fire_at=body.fire_at,
        )
    elif body.duration_seconds is not None and body.duration_seconds > 0:
        timer = service.set_timer(
            name=body.name,
            duration_seconds=body.duration_seconds,
        )
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either duration_seconds or fire_at",
        )

    return APIResponse(
        data=_enrich_response(timer, service),
        timestamp=datetime.now(timezone.utc),
    )


@router.delete("/{timer_id}", response_model=APIResponse)
async def cancel_timer(timer_id: str, request: Request):
    """Cancel a timer by ID."""
    service = _get_timer_service(request)
    cancelled = service.cancel_timer(timer_id)
    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail="Timer not found or already completed",
        )
    return APIResponse(
        data={"cancelled": True},
        timestamp=datetime.now(timezone.utc),
    )
