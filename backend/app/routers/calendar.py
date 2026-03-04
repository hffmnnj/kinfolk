"""Calendar events API router."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import Event
from app.schemas.common import APIResponse
from app.schemas.event import EventCreate, EventResponse

router = APIRouter()


@router.get("/events", response_model=APIResponse)
async def list_events(db: Session = Depends(get_db)):
    """List all calendar events."""
    events = db.query(Event).all()
    return APIResponse(
        data=[EventResponse.model_validate(e) for e in events],
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/events", response_model=APIResponse, status_code=201)
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    """Create a new calendar event."""
    db_event = Event(**event.model_dump(), id=str(uuid.uuid4()))
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
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
