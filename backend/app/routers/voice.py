"""Voice assistant API router."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.voice_history import VoiceHistory
from app.schemas.common import APIResponse
from app.schemas.voice_history import VoiceHistoryCreate, VoiceHistoryResponse

router = APIRouter()


@router.get("/history", response_model=APIResponse)
async def list_voice_history(db: Session = Depends(get_db)):
    """List voice command history (most recent first, max 100)."""
    history = (
        db.query(VoiceHistory).order_by(VoiceHistory.timestamp.desc()).limit(100).all()
    )
    return APIResponse(
        data=[VoiceHistoryResponse.model_validate(h) for h in history],
        timestamp=datetime.now(timezone.utc),
    )


@router.post("/command", response_model=APIResponse, status_code=201)
async def process_voice_command(
    command: VoiceHistoryCreate, db: Session = Depends(get_db)
):
    """Process a voice command (placeholder)."""
    db_entry = VoiceHistory(**command.model_dump(), id=str(uuid.uuid4()))
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return APIResponse(
        data=VoiceHistoryResponse.model_validate(db_entry),
        timestamp=datetime.now(timezone.utc),
    )
