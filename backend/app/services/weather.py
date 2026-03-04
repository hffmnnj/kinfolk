"""Weather service using OpenWeatherMap API.

Fetches current conditions and 5-day forecast with in-memory
caching (10-minute TTL) to avoid excessive API calls.  Falls
back to placeholder data when the API key is missing or the
API is unreachable.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings
from app.schemas.weather import ForecastDay, WeatherData

LOGGER = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 600  # 10 minutes

_OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
_OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def _placeholder_current() -> WeatherData:
    """Return placeholder weather when API is unavailable."""
    return WeatherData(
        temperature=72.0,
        feels_like=70.0,
        condition="Sunny",
        humidity=45,
        wind_speed=5.0,
        city=settings.weather_city,
        icon="01d",
        timestamp=datetime.now(timezone.utc),
    )


def _placeholder_forecast() -> list[ForecastDay]:
    """Return placeholder forecast when API is unavailable."""
    return []


class WeatherService:
    """OpenWeatherMap client with in-memory caching."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        city: Optional[str] = None,
        units: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or settings.openweather_api_key
        self._city = city or settings.weather_city
        self._units = units or settings.weather_units

        # In-memory cache
        self._current_cache: Optional[WeatherData] = None
        self._current_cache_time: float = 0.0
        self._forecast_cache: Optional[list[ForecastDay]] = None
        self._forecast_cache_time: float = 0.0

    @property
    def _has_api_key(self) -> bool:
        return bool(self._api_key)

    def _is_cache_valid(self, cache_time: float) -> bool:
        return (time.monotonic() - cache_time) < _CACHE_TTL_SECONDS

    async def get_current_weather(self) -> WeatherData:
        """Fetch current weather, using cache when available."""
        if self._current_cache and self._is_cache_valid(
            self._current_cache_time,
        ):
            return self._current_cache

        if not self._has_api_key:
            LOGGER.warning(
                "No OpenWeatherMap API key configured; "
                "returning placeholder weather data"
            )
            return _placeholder_current()

        try:
            data = await self._fetch_current()
            self._current_cache = data
            self._current_cache_time = time.monotonic()
            return data
        except Exception:
            LOGGER.exception("Failed to fetch current weather from OWM")
            if self._current_cache is not None:
                return self._current_cache
            return _placeholder_current()

    async def get_forecast(self) -> list[ForecastDay]:
        """Fetch 5-day forecast, using cache when available."""
        if self._forecast_cache is not None and self._is_cache_valid(
            self._forecast_cache_time,
        ):
            return self._forecast_cache

        if not self._has_api_key:
            LOGGER.warning(
                "No OpenWeatherMap API key configured; returning empty forecast"
            )
            return _placeholder_forecast()

        try:
            data = await self._fetch_forecast()
            self._forecast_cache = data
            self._forecast_cache_time = time.monotonic()
            return data
        except Exception:
            LOGGER.exception("Failed to fetch forecast from OWM")
            if self._forecast_cache is not None:
                return self._forecast_cache
            return _placeholder_forecast()

    async def _fetch_current(self) -> WeatherData:
        """Call OWM current weather endpoint."""
        params = {
            "q": self._city,
            "appid": self._api_key,
            "units": self._units,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_OWM_CURRENT_URL, params=params)
            resp.raise_for_status()
            body = resp.json()

        main = body.get("main", {})
        weather_list = body.get("weather", [{}])
        weather_info = weather_list[0] if weather_list else {}
        wind = body.get("wind", {})

        return WeatherData(
            temperature=main.get("temp", 0.0),
            feels_like=main.get("feels_like", 0.0),
            condition=weather_info.get("description", "Unknown").title(),
            humidity=main.get("humidity", 0),
            wind_speed=wind.get("speed", 0.0),
            city=body.get("name", self._city),
            icon=weather_info.get("icon", ""),
            timestamp=datetime.now(timezone.utc),
        )

    async def _fetch_forecast(self) -> list[ForecastDay]:
        """Call OWM 5-day/3-hour forecast and aggregate to daily."""
        params = {
            "q": self._city,
            "appid": self._api_key,
            "units": self._units,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_OWM_FORECAST_URL, params=params)
            resp.raise_for_status()
            body = resp.json()

        # Group 3-hour entries by date
        daily: dict[str, dict] = {}
        for entry in body.get("list", []):
            dt_txt = entry.get("dt_txt", "")
            date_str = dt_txt.split(" ")[0] if dt_txt else ""
            if not date_str:
                continue

            main = entry.get("main", {})
            weather_list = entry.get("weather", [{}])
            weather_info = weather_list[0] if weather_list else {}
            temp = main.get("temp", 0.0)

            if date_str not in daily:
                daily[date_str] = {
                    "high": temp,
                    "low": temp,
                    "condition": weather_info.get("description", "Unknown").title(),
                    "humidity": main.get("humidity", 0),
                    "icon": weather_info.get("icon", ""),
                    "count": 1,
                    "humidity_sum": main.get("humidity", 0),
                }
            else:
                day = daily[date_str]
                day["high"] = max(day["high"], temp)
                day["low"] = min(day["low"], temp)
                day["count"] += 1
                day["humidity_sum"] += main.get("humidity", 0)
                # Use midday condition as representative
                hour = dt_txt.split(" ")[1] if " " in dt_txt else ""
                if hour.startswith("12"):
                    day["condition"] = weather_info.get(
                        "description", day["condition"]
                    ).title()
                    day["icon"] = weather_info.get("icon", day["icon"])

        # Convert to ForecastDay list (max 5 days)
        result: list[ForecastDay] = []
        for date_str in sorted(daily.keys())[:5]:
            day = daily[date_str]
            avg_humidity = day["humidity_sum"] // day["count"]
            result.append(
                ForecastDay(
                    date=date_str,
                    high=round(day["high"], 1),
                    low=round(day["low"], 1),
                    condition=day["condition"],
                    humidity=avg_humidity,
                    icon=day["icon"],
                )
            )

        return result
