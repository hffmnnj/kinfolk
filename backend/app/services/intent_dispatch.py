"""Intent dispatch service with category-based handler registry."""

from __future__ import annotations

import inspect
from typing import Awaitable, Callable

from app.schemas.intent import Intent, IntentCategory
from app.services.nlu import _intent_category

Handler = Callable[[Intent], str | Awaitable[str]]


def setup_handlers(
    dispatch: "IntentDispatch",
    *,
    calendar_sync=None,
    db_factory=None,
    weather_service=None,
    music_service=None,
    ha_service=None,
    timer_service=None,
) -> None:
    """Register real intent handlers, replacing built-in stubs.

    Called from the application lifespan after all services are
    constructed.  Each handler is only registered when its backing
    service is available.
    """
    if calendar_sync is not None:
        from app.services.intent_handlers.calendar_handler import (
            CalendarIntentHandler,
        )

        calendar_handler = CalendarIntentHandler(
            calendar_sync_service=calendar_sync,
        )
        dispatch.register_handler(
            IntentCategory.CALENDAR,
            calendar_handler.handle,
        )

    if db_factory is not None:
        from app.services.intent_handlers.task_handler import (
            TaskIntentHandler,
        )

        task_handler = TaskIntentHandler(db_factory=db_factory)
        dispatch.register_handler(
            IntentCategory.TASKS,
            task_handler.handle,
        )

    if weather_service is not None:
        from app.services.intent_handlers.weather_handler import (
            WeatherIntentHandler,
        )

        weather_handler = WeatherIntentHandler(
            weather_service=weather_service,
        )
        dispatch.register_handler(
            IntentCategory.WEATHER,
            weather_handler.handle,
        )

    if music_service is not None:
        from app.services.intent_handlers.music_handler import (
            MusicIntentHandler,
        )

        music_handler = MusicIntentHandler(music_service=music_service)
        dispatch.register_handler(
            IntentCategory.MUSIC,
            music_handler.handle,
        )

    if ha_service is not None:
        from app.services.intent_handlers.smarthome_handler import (
            SmartHomeIntentHandler,
        )

        smarthome_handler = SmartHomeIntentHandler(ha_service=ha_service)
        dispatch.register_handler(
            IntentCategory.SMARTHOME,
            smarthome_handler.handle,
        )

    if timer_service is not None:
        from app.services.intent_handlers.timer_handler import (
            TimerIntentHandler,
        )

        timer_handler = TimerIntentHandler(timer_service=timer_service)
        dispatch.register_handler(
            IntentCategory.TIMERS,
            timer_handler.handle,
        )

    # System handler (photo frame, stop, etc.) — always available
    from app.services.intent_handlers.system_handler import (
        SystemIntentHandler,
    )

    system_handler = SystemIntentHandler()
    dispatch.register_handler(
        IntentCategory.SYSTEM,
        system_handler.handle,
    )


class IntentDispatch:
    """Route parsed intents to category handlers."""

    def __init__(self) -> None:
        self._handlers: dict[IntentCategory, Handler] = {}
        self._register_builtin_handlers()

    def register_handler(
        self,
        category: IntentCategory,
        handler: Handler,
    ) -> None:
        """Register or replace an intent handler for a category."""
        self._handlers[category] = handler

    async def dispatch(self, intent: Intent) -> str:
        """Dispatch a parsed intent to the best available category handler."""
        category = _intent_category(intent.name)
        handler = self._handlers.get(category)
        if handler is None:
            handler = self._handlers[IntentCategory.UNKNOWN]

        response = handler(intent)
        if inspect.isawaitable(response):
            return await response
        return response

    def _register_builtin_handlers(self) -> None:
        self.register_handler(IntentCategory.CALENDAR, self._stub_calendar)
        self.register_handler(IntentCategory.TASKS, self._stub_tasks)
        self.register_handler(IntentCategory.WEATHER, self._stub_weather)
        self.register_handler(IntentCategory.TIMERS, self._stub_timers)
        self.register_handler(IntentCategory.MUSIC, self._stub_music)
        self.register_handler(IntentCategory.SMARTHOME, self._stub_smarthome)
        self.register_handler(IntentCategory.SYSTEM, self._stub_system)
        self.register_handler(IntentCategory.UNKNOWN, self._fallback_unknown)

    @staticmethod
    async def _stub_calendar(intent: Intent) -> str:
        del intent
        return "I'll handle calendar soon."

    @staticmethod
    async def _stub_tasks(intent: Intent) -> str:
        del intent
        return "I'll handle tasks soon."

    @staticmethod
    async def _stub_weather(intent: Intent) -> str:
        del intent
        return "I'll handle weather soon."

    @staticmethod
    async def _stub_timers(intent: Intent) -> str:
        del intent
        return "I'll handle timers soon."

    @staticmethod
    async def _stub_music(intent: Intent) -> str:
        del intent
        return "I'll handle music soon."

    @staticmethod
    async def _stub_smarthome(intent: Intent) -> str:
        del intent
        return "I'll handle smarthome soon."

    @staticmethod
    async def _stub_system(intent: Intent) -> str:
        del intent
        return "I'll handle system soon."

    @staticmethod
    async def _fallback_unknown(intent: Intent) -> str:
        del intent
        return "I didn't understand that. Please try again."
