"""VoiceHistory Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class VoiceHistoryCreate(BaseModel):
    """Schema for creating a voice history record."""

    command: Optional[str] = None
    intent: Optional[str] = None
    response: Optional[str] = None
    audio_url: Optional[str] = None


class VoiceHistoryResponse(BaseModel):
    """Schema for voice history responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str]
    command: Optional[str]
    intent: Optional[str]
    response: Optional[str]
    audio_url: Optional[str]
    timestamp: datetime
