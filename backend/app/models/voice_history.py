"""VoiceHistory model — voice command history."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class VoiceHistory(Base):
    __tablename__ = "voice_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    command = Column(Text, nullable=True)
    intent = Column(String, nullable=True)
    response = Column(Text, nullable=True)
    audio_url = Column(String, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="voice_history")
