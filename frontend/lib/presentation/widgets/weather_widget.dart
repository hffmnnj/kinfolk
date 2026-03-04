import 'package:flutter/material.dart';
import '../../domain/entities/weather.dart';
import '../themes/kinfolk_colors.dart';

/// Weather display widget for the Kinfolk dashboard.
/// Accepts a WeatherData entity — ready for OpenWeatherMap integration.
/// Currently displays placeholder data.
class WeatherWidget extends StatelessWidget {
  final WeatherData weather;

  const WeatherWidget({super.key, required this.weather});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: KinfolkColors.darkCard,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
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
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: KinfolkColors.sageGray,
                    ),
                  ),
                ],
              ),
            ),

            // Location and feels-like
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.location_on,
                  color: KinfolkColors.warmClay,
                  size: 16,
                ),
                const SizedBox(height: 2),
                Text(
                  weather.location,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: KinfolkColors.sageGray,
                  ),
                ),
                if (weather.feelsLike != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Feels ${weather.feelsLike!.round()}°',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: KinfolkColors.sageGray,
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
