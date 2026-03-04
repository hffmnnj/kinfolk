"""Intent dispatch service with category-based handler registry."""

from __future__ import annotations

import inspect
from typing import Awaitable, Callable

from app.schemas.intent import Intent, IntentCategory
from app.services.nlu import _intent_category

Handler = Callable[[Intent], str | Awaitable[str]]


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
