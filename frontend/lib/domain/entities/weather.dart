/// Weather data entities — domain layer.
/// Holds current weather conditions and forecast for the dashboard widget.
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
  final double? windSpeed;

  const WeatherData({
    required this.temperature,
    required this.unit,
    required this.condition,
    required this.location,
    this.feelsLike,
    this.humidity,
    this.iconCode,
    this.windSpeed,
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

  /// Create from backend JSON response.
  factory WeatherData.fromJson(Map<String, dynamic> json) {
    return WeatherData(
      temperature: (json['temperature'] as num).toDouble(),
      unit: TemperatureUnit.fahrenheit, // Backend uses imperial by default
      condition: json['condition'] as String? ?? 'Unknown',
      location: json['city'] as String? ?? '',
      feelsLike: (json['feels_like'] as num?)?.toDouble(),
      humidity: (json['humidity'] as num?)?.toDouble(),
      windSpeed: (json['wind_speed'] as num?)?.toDouble(),
      iconCode: json['icon'] as String?,
    );
  }

  /// Placeholder data for loading/error states.
  static const placeholder = WeatherData(
    temperature: 72,
    unit: TemperatureUnit.fahrenheit,
    condition: 'Sunny',
    location: 'Loading...',
    feelsLike: 70,
  );
}

/// Single day in a multi-day forecast.
class ForecastDay {
  final String date;
  final double high;
  final double low;
  final String condition;
  final int humidity;
  final String? icon;

  const ForecastDay({
    required this.date,
    required this.high,
    required this.low,
    required this.condition,
    required this.humidity,
    this.icon,
  });

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
    return '🌤️';
  }

  /// Short day label from date string (e.g. "Mon", "Tue").
  String get shortDay {
    try {
      final parts = date.split('-');
      if (parts.length == 3) {
        final dt = DateTime(
          int.parse(parts[0]),
          int.parse(parts[1]),
          int.parse(parts[2]),
        );
        const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
        return days[dt.weekday - 1];
      }
    } catch (_) {
      // Fall through to default
    }
    return date.length >= 5 ? date.substring(5) : date;
  }

  /// Create from backend JSON response.
  factory ForecastDay.fromJson(Map<String, dynamic> json) {
    return ForecastDay(
      date: json['date'] as String? ?? '',
      high: (json['high'] as num).toDouble(),
      low: (json['low'] as num).toDouble(),
      condition: json['condition'] as String? ?? 'Unknown',
      humidity: (json['humidity'] as num?)?.toInt() ?? 0,
      icon: json['icon'] as String?,
    );
  }
}
