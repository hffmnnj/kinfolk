"""Calendar events API router with unified sync endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.calendar_event import CalendarEvent
from app.models.event import Event
from app.schemas.common import APIResponse
from app.schemas.event import EventCreate, EventResponse

router = APIRouter()


def _get_sync_service(request: Request):
    """Retrieve CalendarSyncService from app state, or None."""
    return getattr(request.app.state, "calendar_sync", None)


# --- Unified event list (all sources) ---


@router.get("", response_model=APIResponse)
async def unified_event_list(
    request: Request,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
):
    """Return unified events from all synced sources.

    Query params:
        start: ISO datetime — filter events starting from this time
        end: ISO datetime — filter events ending before this time
    """
    sync_service = _get_sync_service(request)
    if sync_service is None:
        return APIResponse(
            data=[],
            timestamp=datetime.now(timezone.utc),
        )

    events = sync_service.get_unified_events(start=start, end=end)
    data = [
        {
            "id": e.id,
            "title": e.title,
            "start_time": e.start_time.isoformat(),
            "end_time": e.end_time.isoformat(),
            "location": e.location,
            "description": e.description,
            "attendees": e.attendees,
            "source": e.source,
            "external_id": e.external_id,
        }
        for e in events
    ]
    return APIResponse(data=data, timestamp=datetime.now(timezone.utc))


# --- Sync status and manual trigger ---


@router.get("/sync/status", response_model=APIResponse)
async def sync_status(request: Request):
    """Return per-source sync state (last_sync_at, last_error, event_count)."""
    sync_service = _get_sync_service(request)
    if sync_service is None:
        return APIResponse(
            data={"error": "Sync service not initialized"},
            timestamp=datetime.now(timezone.utc),
        )

    return APIResponse(
        data=sync_service.get_sync_status(),
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/sync", response_model=APIResponse)
async def trigger_sync(request: Request):
    """Manually trigger a full sync from all calendar sources."""
    sync_service = _get_sync_service(request)
    if sync_service is None:
        raise HTTPException(
            status_code=503,
            detail="Sync service not initialized",
        )

    results = await sync_service.sync_now()
    return APIResponse(data=results, timestamp=datetime.now(timezone.utc))


# --- Local event CRUD (existing endpoints preserved) ---


@router.get("/events", response_model=APIResponse)
async def list_events(db: Session = Depends(get_db)):
    """List all local calendar events."""
    events = db.query(Event).all()
    return APIResponse(
        data=[EventResponse.model_validate(e) for e in events],
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/events", response_model=APIResponse, status_code=201)
async def create_event(
    event: EventCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new calendar event locally and push to external sources."""
    db_event = Event(**event.model_dump(), id=str(uuid.uuid4()))
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    # Push to external sources immediately
    sync_service = _get_sync_service(request)
    if sync_service is not None:
        domain_event = CalendarEvent(
            id=db_event.id,
            title=db_event.title,
            start_time=db_event.start_time,
            end_time=db_event.end_time,
            location=db_event.location,
            description=db_event.description,
            attendees=db_event.attendees or [],
            source="local",
            external_id=db_event.external_id,
        )
        await sync_service.push_event(domain_event)

    return APIResponse(
        data=EventResponse.model_validate(db_event),
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/events/{event_id}", response_model=APIResponse)
async def get_event(event_id: str, db: Session = Depends(get_db)):
    """Get an event by ID."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return APIResponse(
        data=EventResponse.model_validate(event),
        timestamp=datetime.now(timezone.utc),
    )
