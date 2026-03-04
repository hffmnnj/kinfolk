"""Voice-driven weather intent handler.

Routes weather intents (get_weather, get_forecast) to the weather
service and returns TTS-friendly response strings.
"""

from __future__ import annotations

import logging

from app.schemas.intent import Intent
from app.services.weather import WeatherService

LOGGER = logging.getLogger(__name__)

# Intent names from sentences.ini / NLU
_GET_WEATHER = "get_weather"
_GET_FORECAST = "get_forecast"


class WeatherIntentHandler:
    """Handle weather-related voice intents."""

    def __init__(self, weather_service: WeatherService) -> None:
        self._weather = weather_service

    async def handle(self, intent: Intent) -> str:
        """Route to current weather or forecast based on intent name."""
        if intent.name == _GET_FORECAST:
            return await self._handle_forecast()
        # Default: current weather for get_weather and any other
        return await self._handle_current()

    async def _handle_current(self) -> str:
        """Return a TTS-friendly current weather string."""
        try:
            data = await self._weather.get_current_weather()
        except Exception:
            LOGGER.exception("Weather intent: failed to fetch current")
            return "Sorry, I couldn't get the weather right now."

        temp = round(data.temperature)
        return (
            f"It's currently {temp} degrees and "
            f"{data.condition.lower()} in {data.city}."
        )

    async def _handle_forecast(self) -> str:
        """Return a TTS-friendly forecast summary."""
        try:
            days = await self._weather.get_forecast()
        except Exception:
            LOGGER.exception("Weather intent: failed to fetch forecast")
            return "Sorry, I couldn't get the forecast right now."

        if not days:
            return "I don't have forecast data available right now."

        lines = []
        for day in days[:3]:
            high = round(day.high)
            low = round(day.low)
            lines.append(
                f"{day.date}: high of {high}, low of {low}, {day.condition.lower()}."
            )

        return "Here's the forecast. " + " ".join(lines)
