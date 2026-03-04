"""Common API response schemas."""

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    status: str = "success"
    data: Optional[T] = None
    timestamp: datetime = Field(default_factory=_utcnow)


class APIError(BaseModel):
    """Standard API error response."""

    status: str = "error"
    error: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=_utcnow)
