"""System intent handler for photo frame and other system-level voice commands.

Routes ``system`` intents such as "show photo frame" and "stop" to
appropriate actions and returns TTS-friendly response strings.
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.intent import Intent

LOGGER = logging.getLogger(__name__)

# Intent names from sentences.ini / NLU
_SHOW_PHOTO_FRAME = "show_photo_frame"
_STOP = "stop"


class SystemIntentHandler:
    """Handle system-level voice intents."""

    def __init__(self, wake_word_service: Any | None = None) -> None:
        self._wake_word_service = wake_word_service

    async def handle(self, intent: Intent) -> str:
        """Route to the correct system action based on intent name."""
        if intent.name == _SHOW_PHOTO_FRAME:
            return await self._handle_show_photo_frame(intent)
        if intent.name == _STOP:
            return await self._handle_stop(intent)

        return "I'm not sure how to handle that system request."

    async def _handle_show_photo_frame(self, intent: Intent) -> str:
        """Signal the frontend to launch photo frame mode."""
        del intent  # Unused — no slots needed
        LOGGER.info("System intent: launching photo frame")
        if self._wake_word_service is not None:
            try:
                await self._wake_word_service.notify_system_action(
                    "show_photo_frame",
                )
            except Exception:
                LOGGER.exception("Failed to broadcast show_photo_frame action")
        return "Launching photo frame."

    async def _handle_stop(self, intent: Intent) -> str:
        """Signal the frontend to return to the dashboard."""
        del intent
        LOGGER.info("System intent: returning to dashboard")
        if self._wake_word_service is not None:
            try:
                await self._wake_word_service.notify_system_action("stop")
            except Exception:
                LOGGER.exception("Failed to broadcast stop action")
        return "Returning to dashboard."
