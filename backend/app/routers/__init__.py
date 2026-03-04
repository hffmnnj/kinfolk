"""Routers package."""

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

__all__ = [
    "users",
    "auth",
    "calendar",
    "tasks",
    "timers",
    "voice",
    "smarthome",
    "weather",
    "music",
]
