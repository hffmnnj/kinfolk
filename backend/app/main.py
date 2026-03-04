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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Privacy-first family smart display API",
    lifespan=lifespan,
)

# CORS middleware — allow Flutter app origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production via settings
    allow_credentials=True,
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
