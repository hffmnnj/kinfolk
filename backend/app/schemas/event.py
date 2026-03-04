"""Event (calendar) Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    """Schema for creating an event."""

    title: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    description: Optional[str] = None
    attendees: Optional[list[str]] = None
    recurrence: Optional[str] = None
    reminders: Optional[list[dict[str, Any]]] = None
    color: Optional[str] = "#D4A574"
    source: str = "local"


class EventUpdate(BaseModel):
    """Schema for updating an event."""

    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class EventResponse(BaseModel):
    """Schema for event responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str]
    title: str
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    description: Optional[str]
    attendees: Optional[list[str]]
    recurrence: Optional[str]
    color: Optional[str]
    source: Optional[str]
