"""Event model — calendar event."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    attendees = Column(JSON, nullable=True, default=list)
    recurrence = Column(String, nullable=True)  # RRULE format
    reminders = Column(JSON, nullable=True, default=list)
    color = Column(String, nullable=True, default="#D4A574")
    source = Column(String, nullable=True, default="local")
    external_id = Column(String, nullable=True)

    user = relationship("User", back_populates="events")
