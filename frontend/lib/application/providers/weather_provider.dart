import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/weather.dart';
import '../../infrastructure/api/weather_api_client.dart';

/// Combined weather state holding current conditions and forecast.
class WeatherState {
  final WeatherData current;
  final List<ForecastDay> forecast;
  final bool isLoading;
  final String? error;

  const WeatherState({
    required this.current,
    this.forecast = const [],
    this.isLoading = false,
    this.error,
  });

  WeatherState copyWith({
    WeatherData? current,
    List<ForecastDay>? forecast,
    bool? isLoading,
    String? error,
  }) {
    return WeatherState(
      current: current ?? this.current,
      forecast: forecast ?? this.forecast,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

/// Notifier that fetches weather data and auto-refreshes every 10 minutes.
class WeatherNotifier extends StateNotifier<WeatherState> {
  final WeatherApiClient _client;
  Timer? _refreshTimer;

  WeatherNotifier({WeatherApiClient? client})
    : _client = client ?? const WeatherApiClient(),
      super(
        const WeatherState(current: WeatherData.placeholder, isLoading: true),
      ) {
    _fetchAll();
    _refreshTimer = Timer.periodic(
      const Duration(minutes: 10),
      (_) => _fetchAll(),
    );
  }

  Future<void> _fetchAll() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final results = await Future.wait([
        _client.getCurrentWeather(),
        _client.getForecast(),
      ]);

      final current = results[0] as WeatherData;
      final forecast = results[1] as List<ForecastDay>;

      state = WeatherState(
        current: current,
        forecast: forecast,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  /// Force a manual refresh.
  Future<void> refresh() => _fetchAll();

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}

/// Global weather state provider — auto-refreshes every 10 minutes.
final weatherProvider = StateNotifierProvider<WeatherNotifier, WeatherState>((
  ref,
) {
  return WeatherNotifier();
});
