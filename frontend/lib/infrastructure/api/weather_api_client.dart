import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../domain/entities/weather.dart';

/// Client for the backend weather API endpoints.
///
/// Fetches current weather and forecast data from the FastAPI backend
/// which proxies OpenWeatherMap.
class WeatherApiClient {
  final String baseUrl;

  const WeatherApiClient({this.baseUrl = 'http://localhost:8080'});

  /// Fetch current weather conditions.
  Future<WeatherData> getCurrentWeather() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/weather/current'),
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return WeatherData.fromJson(json);
      }

      debugPrint(
        'WeatherApiClient: current weather failed: ${response.statusCode}',
      );
      return WeatherData.placeholder;
    } catch (e) {
      debugPrint('WeatherApiClient: current weather error: $e');
      return WeatherData.placeholder;
    }
  }

  /// Fetch 5-day forecast.
  Future<List<ForecastDay>> getForecast() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/weather/forecast'),
      );

      if (response.statusCode == 200) {
        final jsonList = jsonDecode(response.body) as List<dynamic>;
        return jsonList
            .map((item) => ForecastDay.fromJson(item as Map<String, dynamic>))
            .toList();
      }

      debugPrint('WeatherApiClient: forecast failed: ${response.statusCode}');
      return [];
    } catch (e) {
      debugPrint('WeatherApiClient: forecast error: $e');
      return [];
    }
  }
}
