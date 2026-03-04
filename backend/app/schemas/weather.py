"""Weather API schemas."""

from datetime import datetime

from pydantic import BaseModel


class WeatherData(BaseModel):
    """Current weather conditions."""

    temperature: float
    feels_like: float
    condition: str
    humidity: int
    wind_speed: float
    city: str
    icon: str = ""
    timestamp: datetime


class ForecastDay(BaseModel):
    """Single day in a 5-day forecast."""

    date: str
    high: float
    low: float
    condition: str
    humidity: int
    icon: str = ""


class WeatherResponse(BaseModel):
    """Combined current + forecast response."""

    current: WeatherData
    forecast: list[ForecastDay] = []
