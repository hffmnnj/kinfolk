"""Timer model — named timers and alarms."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Timer(Base):
    __tablename__ = "timers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=False, default=_utcnow)
    fire_at = Column(DateTime, nullable=False)
    completed = Column(Boolean, default=False)
    cancelled = Column(Boolean, default=False)
    user_id = Column(String, nullable=True)
