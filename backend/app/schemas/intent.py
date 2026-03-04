"""Intent schema definitions for voice NLU."""

from enum import Enum

from pydantic import BaseModel, Field


class IntentSlot(BaseModel):
    """Single extracted slot from an utterance."""

    name: str
    value: str


class Intent(BaseModel):
    """Recognized intent payload."""

    name: str
    slots: list[IntentSlot] = Field(default_factory=list)
    confidence: float = 1.0
    raw_text: str = ""


class IntentCategory(str, Enum):
    """Top-level intent category used by dispatcher routing."""

    CALENDAR = "calendar"
    TASKS = "tasks"
    WEATHER = "weather"
    TIMERS = "timers"
    MUSIC = "music"
    SMARTHOME = "smarthome"
    SYSTEM = "system"
    UNKNOWN = "unknown"
