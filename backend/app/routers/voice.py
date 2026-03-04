"""Voice assistant API router."""

import uuid
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.voice_history import VoiceHistory
from app.schemas.common import APIResponse
from app.schemas.intent import Intent
from app.schemas.voice_history import VoiceHistoryCreate, VoiceHistoryResponse
from app.services.nlu import NLUService

router = APIRouter()


class IntentRequest(BaseModel):
    text: str


def _get_wake_word_service(request: Request):
    return getattr(request.app.state, "wake_word_service", None)


def _get_nlu_service(request: Request):
    service = getattr(request.app.state, "nlu_service", None)
    if service is None:
        return NLUService(settings=settings)
    return service


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
    command: VoiceHistoryCreate,
    db: Session = Depends(get_db),
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


@router.get("/status", response_model=APIResponse)
async def voice_status(request: Request):
    """Get current wake word and voice pipeline status."""
    wake_word_service = _get_wake_word_service(request)

    if wake_word_service is None:
        data = {
            "wake_word": {
                "active": False,
                "engine": "unavailable",
                "sensitivity": None,
                "wake_words": ["hey kin", "kinfolk"],
            },
            "listening": False,
            "audio": {"sample_rate": None, "channels": None},
            "clients": 0,
            "last_detection": None,
        }
    else:
        data = wake_word_service.get_status()

    return APIResponse(data=data, timestamp=datetime.now(timezone.utc))


@router.post("/intent", response_model=APIResponse)
async def parse_intent(payload: IntentRequest, request: Request):
    """Parse freeform text into a structured intent."""
    nlu_service = _get_nlu_service(request)
    intent = nlu_service.parse(payload.text)
    return APIResponse(
        data=Intent.model_validate(intent).model_dump(),
        timestamp=datetime.now(timezone.utc),
    )


@router.websocket("/ws")
async def voice_events_websocket(websocket: WebSocket):
    """Stream real-time wake word events to connected clients."""
    await websocket.accept()

    wake_word_service = getattr(websocket.app.state, "wake_word_service", None)
    if wake_word_service is None:
        await websocket.send_json(
            {
                "type": "voice_status",
                "data": {
                    "wake_word": {"active": False, "engine": "unavailable"},
                    "listening": False,
                },
            }
        )
        await websocket.close(code=1013)
        return

    await websocket.send_json(
        {
            "type": "voice_status",
            "data": wake_word_service.get_status(),
        }
    )

    await wake_word_service.register_client(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await wake_word_service.unregister_client(websocket)
