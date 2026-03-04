"""Schemas package."""

from app.schemas.common import APIError, APIResponse
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.schemas.intent import Intent, IntentCategory, IntentSlot
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.schemas.voice_history import VoiceHistoryCreate, VoiceHistoryResponse
from app.schemas.weather import ForecastDay, WeatherData, WeatherResponse

__all__ = [
    "APIResponse",
    "APIError",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "EventCreate",
    "EventUpdate",
    "EventResponse",
    "ForecastDay",
    "Intent",
    "IntentCategory",
    "IntentSlot",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "VoiceHistoryCreate",
    "VoiceHistoryResponse",
    "WeatherData",
    "WeatherResponse",
]
