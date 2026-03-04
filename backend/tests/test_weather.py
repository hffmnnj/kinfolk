"""Tests for weather service, router, and intent handler."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.schemas.intent import Intent
from app.schemas.weather import ForecastDay, WeatherData
from app.services.weather import WeatherService

# ── Sample OWM API responses ────────────────────────────────────

_CURRENT_RESPONSE = {
    "main": {
        "temp": 68.5,
        "feels_like": 66.0,
        "humidity": 55,
    },
    "weather": [
        {
            "description": "clear sky",
            "icon": "01d",
        }
    ],
    "wind": {"speed": 8.2},
    "name": "San Francisco",
}

_FORECAST_RESPONSE = {
    "list": [
        {
            "dt_txt": "2026-03-05 09:00:00",
            "main": {"temp": 60.0, "humidity": 50},
            "weather": [{"description": "clouds", "icon": "03d"}],
        },
        {
            "dt_txt": "2026-03-05 12:00:00",
            "main": {"temp": 65.0, "humidity": 45},
            "weather": [{"description": "partly cloudy", "icon": "02d"}],
        },
        {
            "dt_txt": "2026-03-05 18:00:00",
            "main": {"temp": 62.0, "humidity": 55},
            "weather": [{"description": "clouds", "icon": "03d"}],
        },
        {
            "dt_txt": "2026-03-06 12:00:00",
            "main": {"temp": 70.0, "humidity": 40},
            "weather": [{"description": "sunny", "icon": "01d"}],
        },
    ],
}


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://example.com"),
    )


# ── WeatherService tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_weather_success():
    """Current weather is parsed correctly from OWM response."""
    service = WeatherService(
        api_key="test-key",
        city="San Francisco",
        units="imperial",
    )

    with patch("app.services.weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=_mock_response(_CURRENT_RESPONSE),
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await service.get_current_weather()

    assert isinstance(result, WeatherData)
    assert result.temperature == 68.5
    assert result.feels_like == 66.0
    assert result.condition == "Clear Sky"
    assert result.humidity == 55
    assert result.wind_speed == 8.2
    assert result.city == "San Francisco"


@pytest.mark.asyncio
async def test_get_forecast_success():
    """Forecast is aggregated by day from 3-hour entries."""
    service = WeatherService(
        api_key="test-key",
        city="San Francisco",
        units="imperial",
    )

    with patch("app.services.weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=_mock_response(_FORECAST_RESPONSE),
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await service.get_forecast()

    assert isinstance(result, list)
    assert len(result) == 2  # Two distinct dates in sample data

    day1 = result[0]
    assert isinstance(day1, ForecastDay)
    assert day1.date == "2026-03-05"
    assert day1.high == 65.0
    assert day1.low == 60.0
    # Midday condition should be used
    assert day1.condition == "Partly Cloudy"


@pytest.mark.asyncio
async def test_caching_avoids_second_api_call():
    """Second call within TTL returns cached data without API hit."""
    service = WeatherService(
        api_key="test-key",
        city="San Francisco",
        units="imperial",
    )

    with patch("app.services.weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=_mock_response(_CURRENT_RESPONSE),
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # First call — hits API
        result1 = await service.get_current_weather()
        assert mock_client.get.call_count == 1

        # Second call — should use cache
        result2 = await service.get_current_weather()
        assert mock_client.get.call_count == 1  # No additional call

    assert result1.temperature == result2.temperature


@pytest.mark.asyncio
async def test_cache_expires_after_ttl():
    """Cache expires and triggers a new API call after TTL."""
    service = WeatherService(
        api_key="test-key",
        city="San Francisco",
        units="imperial",
    )

    with patch("app.services.weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=_mock_response(_CURRENT_RESPONSE),
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        # First call
        await service.get_current_weather()
        assert mock_client.get.call_count == 1

        # Expire the cache by backdating the timestamp
        service._current_cache_time = time.monotonic() - 700

        # Second call — cache expired, should hit API again
        await service.get_current_weather()
        assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_graceful_fallback_no_api_key():
    """Returns placeholder data when no API key is configured."""
    service = WeatherService(
        api_key="",
        city="San Francisco",
        units="imperial",
    )

    result = await service.get_current_weather()

    assert isinstance(result, WeatherData)
    assert result.temperature == 72.0
    assert result.condition == "Sunny"
    assert result.city == "San Francisco"


@pytest.mark.asyncio
async def test_graceful_fallback_api_error():
    """Returns placeholder data when API call fails."""
    service = WeatherService(
        api_key="test-key",
        city="San Francisco",
        units="imperial",
    )

    with patch("app.services.weather.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused"),
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await service.get_current_weather()

    assert isinstance(result, WeatherData)
    assert result.temperature == 72.0
    assert result.condition == "Sunny"


@pytest.mark.asyncio
async def test_forecast_fallback_no_api_key():
    """Returns empty forecast when no API key is configured."""
    service = WeatherService(
        api_key="",
        city="San Francisco",
        units="imperial",
    )

    result = await service.get_forecast()
    assert result == []


# ── Intent handler tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_weather_intent_handler_current():
    """Weather intent handler returns spoken current weather."""
    from app.services.intent_handlers.weather_handler import (
        WeatherIntentHandler,
    )

    mock_service = AsyncMock(spec=WeatherService)
    mock_service.get_current_weather = AsyncMock(
        return_value=WeatherData(
            temperature=72.0,
            feels_like=70.0,
            condition="Sunny",
            humidity=45,
            wind_speed=5.0,
            city="San Francisco",
            timestamp=datetime.now(timezone.utc),
        ),
    )

    handler = WeatherIntentHandler(weather_service=mock_service)
    intent = Intent(name="get_weather", raw_text="what's the weather")

    result = await handler.handle(intent)

    assert "72" in result
    assert "sunny" in result.lower()
    assert "San Francisco" in result


@pytest.mark.asyncio
async def test_weather_intent_handler_forecast():
    """Weather intent handler returns spoken forecast."""
    from app.services.intent_handlers.weather_handler import (
        WeatherIntentHandler,
    )

    mock_service = AsyncMock(spec=WeatherService)
    mock_service.get_forecast = AsyncMock(
        return_value=[
            ForecastDay(
                date="2026-03-05",
                high=70.0,
                low=55.0,
                condition="Partly Cloudy",
                humidity=50,
            ),
            ForecastDay(
                date="2026-03-06",
                high=75.0,
                low=60.0,
                condition="Sunny",
                humidity=40,
            ),
        ],
    )

    handler = WeatherIntentHandler(weather_service=mock_service)
    intent = Intent(name="get_forecast", raw_text="what's the forecast")

    result = await handler.handle(intent)

    assert "forecast" in result.lower()
    assert "70" in result
    assert "55" in result


@pytest.mark.asyncio
async def test_weather_intent_handler_error_fallback():
    """Weather intent handler returns graceful error message."""
    from app.services.intent_handlers.weather_handler import (
        WeatherIntentHandler,
    )

    mock_service = AsyncMock(spec=WeatherService)
    mock_service.get_current_weather = AsyncMock(
        side_effect=Exception("API down"),
    )

    handler = WeatherIntentHandler(weather_service=mock_service)
    intent = Intent(name="get_weather", raw_text="what's the weather")

    result = await handler.handle(intent)

    assert "sorry" in result.lower()
