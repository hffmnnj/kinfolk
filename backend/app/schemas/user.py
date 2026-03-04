"""User Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    """Schema for creating a user."""

    name: str
    email: Optional[str] = None
    role: str = "adult"
    preferences: Optional[dict[str, Any]] = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    preferences: Optional[dict[str, Any]] = None


class UserResponse(BaseModel):
    """Schema for user responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: Optional[str]
    role: str
    profile_photo: Optional[str]
    preferences: Optional[dict[str, Any]]
    created_at: datetime
    last_active: datetime
