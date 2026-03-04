"""Timer Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TimerCreate(BaseModel):
    """Schema for creating a timer."""

    name: str = "timer"
    duration_seconds: Optional[int] = None
    fire_at: Optional[datetime] = None


class TimerResponse(BaseModel):
    """Schema for timer responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    duration_seconds: Optional[int]
    started_at: datetime
    fire_at: datetime
    completed: bool
    cancelled: bool
    user_id: Optional[str]
    remaining_seconds: Optional[int] = None
