"""User model — represents a family member."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, JSON, String
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    role = Column(String, nullable=False, default="adult")
    profile_photo = Column(String, nullable=True)
    preferences = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=_utcnow)
    last_active = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Relationships
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    voice_history = relationship(
        "VoiceHistory", back_populates="user", cascade="all, delete-orphan"
    )
