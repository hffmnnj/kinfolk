/// Weather data entity — domain layer.
/// Holds current weather conditions for the dashboard widget.
library;

/// Temperature unit preference.
enum TemperatureUnit { fahrenheit, celsius }

/// Immutable weather data value object.
class WeatherData {
  final double temperature;
  final TemperatureUnit unit;
  final String condition;
  final String location;
  final double? feelsLike;
  final double? humidity;
  final String? iconCode;

  const WeatherData({
    required this.temperature,
    required this.unit,
    required this.condition,
    required this.location,
    this.feelsLike,
    this.humidity,
    this.iconCode,
  });

  /// Returns temperature as integer string with unit symbol.
  String get temperatureDisplay {
    final symbol = unit == TemperatureUnit.fahrenheit ? '°F' : '°C';
    return '${temperature.round()}$symbol';
  }

  /// Returns condition emoji for visual representation.
  String get conditionEmoji {
    final lower = condition.toLowerCase();
    if (lower.contains('sun') || lower.contains('clear')) return '☀️';
    if (lower.contains('cloud')) return '☁️';
    if (lower.contains('rain')) return '🌧️';
    if (lower.contains('snow')) return '❄️';
    if (lower.contains('storm') || lower.contains('thunder')) return '⛈️';
    if (lower.contains('fog') || lower.contains('mist')) return '🌫️';
    if (lower.contains('wind')) return '💨';
    return '🌤️'; // Partly cloudy as default
  }
}
