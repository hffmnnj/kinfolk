"""Calendar domain entity shared across calendar providers."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    """Provider-agnostic calendar event."""

    id: Optional[str] = None
    title: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    description: Optional[str] = None
    attendees: list[str] = Field(default_factory=list)
    source: str = "local"
    external_id: Optional[str] = None
