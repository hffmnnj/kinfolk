"""Weather API router — current conditions and 5-day forecast."""

from fastapi import APIRouter, Request

from app.schemas.weather import ForecastDay, WeatherData

router = APIRouter()


@router.get("/current", response_model=WeatherData)
async def get_current_weather(request: Request) -> WeatherData:
    """Return current weather conditions from OpenWeatherMap."""
    weather_service = request.app.state.weather_service
    return await weather_service.get_current_weather()


@router.get("/forecast", response_model=list[ForecastDay])
async def get_forecast(request: Request) -> list[ForecastDay]:
    """Return 5-day weather forecast from OpenWeatherMap."""
    weather_service = request.app.state.weather_service
    return await weather_service.get_forecast()
