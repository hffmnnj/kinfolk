"""
Kinfolk API — Main Application Entry Point.

Privacy-first family smart display backend.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import Event, Task, Timer, User, VoiceHistory  # noqa: F401
from app.routers import (
    auth,
    calendar,
    music,
    smarthome,
    tasks,
    timers,
    users,
    voice,
    weather,
)
from app.services.calendar_caldav import CalDAVCalendarService
from app.services.calendar_google import GoogleCalendarService
from app.services.calendar_sync import CalendarSyncService
from app.services.home_assistant import HomeAssistantService
from app.services.home_assistant_ws import HomeAssistantWSService
from app.services.intent_dispatch import IntentDispatch, setup_handlers
from app.services.music import MopidyMusicService
from app.services.nlu import NLUService
from app.services.stt import STTService
from app.services.tts import TTSService
from app.services.timers import TimerService
from app.services.voice_pipeline import VoicePipeline
from app.services.wake_word import WakeWordService
from app.services.weather import WeatherService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup and initialize services."""
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

    # Weather service
    weather_service = WeatherService()
    app.state.weather_service = weather_service

    # Calendar sync — wire up available sources
    google_service = GoogleCalendarService(settings=settings)
    caldav_service = CalDAVCalendarService(app_settings=settings)
    calendar_sync = CalendarSyncService(
        google_service=google_service,
        caldav_service=caldav_service,
        db_factory=SessionLocal,
        settings=settings,
    )
    music_service = MopidyMusicService(mopidy_url=settings.mopidy_url)
    ha_service = HomeAssistantService(settings_obj=settings)
    ha_ws_service = HomeAssistantWSService(settings_obj=settings)

    # Timer service — persists to DB, fires TTS alerts on expiry
    timer_service = TimerService(
        db_factory=SessionLocal,
        tts_service=tts_service,
    )

    # Wire real intent handlers now that backing services exist
    setup_handlers(
        intent_dispatch_service,
        calendar_sync=calendar_sync,
        db_factory=SessionLocal,
        weather_service=weather_service,
        music_service=music_service,
        ha_service=ha_service,
        timer_service=timer_service,
    )

    app.state.wake_word_service = wake_word_service
    app.state.stt_service = stt_service
    app.state.tts_service = tts_service
    app.state.nlu_service = nlu_service
    app.state.intent_dispatch_service = intent_dispatch_service
    app.state.voice_pipeline = voice_pipeline
    app.state.calendar_sync = calendar_sync
    app.state.music_service = music_service
    app.state.ha_service = ha_service
    app.state.ha_ws_service = ha_ws_service
    app.state.timer_service = timer_service

    await wake_word_service.start()
    await calendar_sync.start()
    await timer_service.start()
    await ha_ws_service.start()

    try:
        yield
    finally:
        await ha_ws_service.stop()
        await timer_service.stop()
        await calendar_sync.stop()
        await wake_word_service.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Privacy-first family smart display API",
    lifespan=lifespan,
)

# CORS middleware — use settings-driven origins
# (never wildcard with credentials)
_cors_origins = ["*"] if settings.cors_allow_all else settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # credentials + wildcard is forbidden
    allow_credentials=not settings.cors_allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# API v1 routers
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(
    calendar.router,
    prefix="/api/v1/calendar",
    tags=["calendar"],
)
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])
app.include_router(
    smarthome.router,
    prefix="/api/v1/smarthome",
    tags=["smarthome"],
)
app.include_router(weather.router, prefix="/api/v1/weather", tags=["weather"])
app.include_router(music.router, prefix="/api/v1/music", tags=["music"])
app.include_router(timers.router, prefix="/api/v1/timers", tags=["timers"])
