"""
Kinfolk API — Main Application Entry Point.

Privacy-first family smart display backend.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.models import Event, Task, User, VoiceHistory  # noqa: F401
from app.routers import calendar, smarthome, tasks, users, voice
from app.services.intent_dispatch import IntentDispatch
from app.services.nlu import NLUService
from app.services.stt import STTService
from app.services.tts import TTSService
from app.services.voice_pipeline import VoicePipeline
from app.services.wake_word import WakeWordService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    if not app.dependency_overrides:
        Base.metadata.create_all(bind=engine)

    wake_word_service = WakeWordService(
        sensitivity=settings.wake_word_sensitivity,
        engine=settings.wake_word_engine,
        sample_rate=settings.audio_sample_rate,
        channels=settings.audio_channels,
    )
    stt_service = STTService(settings=settings)
    tts_service = TTSService(settings=settings)
    nlu_service = NLUService(settings=settings)
    intent_dispatch_service = IntentDispatch()
    voice_pipeline = VoicePipeline(
        wake_word_service=wake_word_service,
        stt_service=stt_service,
        nlu_service=nlu_service,
        dispatch_service=intent_dispatch_service,
        tts_service=tts_service,
    )

    app.state.wake_word_service = wake_word_service
    app.state.stt_service = stt_service
    app.state.tts_service = tts_service
    app.state.nlu_service = nlu_service
    app.state.intent_dispatch_service = intent_dispatch_service
    app.state.voice_pipeline = voice_pipeline
    await wake_word_service.start()

    try:
        yield
    finally:
        await wake_word_service.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Privacy-first family smart display API",
    lifespan=lifespan,
)

# CORS middleware — use settings-driven origins (never wildcard with credentials)
_cors_origins = ["*"] if settings.cors_allow_all else settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=not settings.cors_allow_all,  # credentials + wildcard is forbidden
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# API v1 routers
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(calendar.router, prefix="/api/v1/calendar", tags=["calendar"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])
app.include_router(smarthome.router, prefix="/api/v1/smarthome", tags=["smarthome"])
