import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../application/providers/weather_provider.dart';
import '../../domain/entities/weather.dart';
import '../themes/kinfolk_colors.dart';

/// Weather display widget for the Kinfolk dashboard.
/// Fetches live data from the WeatherProvider and shows current
/// conditions with a 5-day forecast strip.
class WeatherWidget extends ConsumerWidget {
  const WeatherWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final weatherState = ref.watch(weatherProvider);

    return Card(
      color: KinfolkColors.darkCard,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Current conditions row
            _CurrentWeatherRow(
              weather: weatherState.current,
              isLoading: weatherState.isLoading,
            ),

            // Forecast strip (only if we have forecast data)
            if (weatherState.forecast.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(height: 1, color: KinfolkColors.sageGray.withAlpha(51)),
              const SizedBox(height: 12),
              _ForecastStrip(forecast: weatherState.forecast),
            ],
          ],
        ),
      ),
    );
  }
}

/// Displays current temperature, condition, location, and feels-like.
class _CurrentWeatherRow extends StatelessWidget {
  final WeatherData weather;
  final bool isLoading;

  const _CurrentWeatherRow({required this.weather, required this.isLoading});

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const SizedBox(
        height: 48,
        child: Center(
          child: SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: KinfolkColors.warmClay,
            ),
          ),
        ),
      );
    }

    return Row(
      children: [
        // Weather icon / emoji
        Text(weather.conditionEmoji, style: const TextStyle(fontSize: 40)),

        const SizedBox(width: 16),

        // Temperature and condition
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                weather.temperatureDisplay,
                style: Theme.of(context).textTheme.displaySmall?.copyWith(
                  color: KinfolkColors.softCream,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                weather.condition,
                style: Theme.of(
                  context,
                ).textTheme.bodyLarge?.copyWith(color: KinfolkColors.sageGray),
              ),
            ],
          ),
        ),

        // Location and feels-like
        Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.location_on, color: KinfolkColors.warmClay, size: 16),
            const SizedBox(height: 2),
            Text(
              weather.location,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: KinfolkColors.sageGray),
            ),
            if (weather.feelsLike != null) ...[
              const SizedBox(height: 4),
              Text(
                'Feels ${weather.feelsLike!.round()}°',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: KinfolkColors.sageGray),
              ),
            ],
          ],
        ),
      ],
    );
  }
}

/// Horizontal strip showing up to 5 days of forecast.
class _ForecastStrip extends StatelessWidget {
  final List<ForecastDay> forecast;

  const _ForecastStrip({required this.forecast});

  @override
  Widget build(BuildContext context) {
    // Show at most 5 days
    final days = forecast.take(5).toList();

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: days.map((day) => _ForecastDayTile(day: day)).toList(),
    );
  }
}

/// Single forecast day tile.
class _ForecastDayTile extends StatelessWidget {
  final ForecastDay day;

  const _ForecastDayTile({required this.day});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          day.shortDay,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: KinfolkColors.sageGray,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
        Text(day.conditionEmoji, style: const TextStyle(fontSize: 20)),
        const SizedBox(height: 4),
        Text(
          '${day.high.round()}°',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: KinfolkColors.softCream,
            fontWeight: FontWeight.w500,
          ),
        ),
        Text(
          '${day.low.round()}°',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: KinfolkColors.sageGray),
        ),
      ],
    );
  }
}
