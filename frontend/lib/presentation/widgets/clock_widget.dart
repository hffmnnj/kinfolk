import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../themes/kinfolk_colors.dart';

/// Provider that emits the current DateTime every second.
final clockProvider = StreamProvider<DateTime>((ref) {
  return Stream.periodic(
    const Duration(seconds: 1),
    (_) => DateTime.now(),
  ).distinct((a, b) => a.second == b.second);
});

/// Large animated clock widget displaying current time and date.
/// Updates every second via Riverpod StreamProvider.
/// Designed for the Kinfolk dashboard (prominent display).
class ClockWidget extends ConsumerWidget {
  const ClockWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final clockAsync = ref.watch(clockProvider);

    return clockAsync.when(
      data: (now) => _ClockDisplay(now: now),
      loading: () => _ClockDisplay(now: DateTime.now()),
      error: (_, __) => _ClockDisplay(now: DateTime.now()),
    );
  }
}

class _ClockDisplay extends StatelessWidget {
  final DateTime now;

  const _ClockDisplay({required this.now});

  @override
  Widget build(BuildContext context) {
    final timeStr = DateFormat('HH:mm').format(now);
    final secondsStr = DateFormat('ss').format(now);
    final dateStr = DateFormat('EEEE, MMMM d, y').format(now);

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Time: Large display font
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              timeStr,
              style: Theme.of(context).textTheme.displayLarge?.copyWith(
                color: KinfolkColors.softCream,
                fontWeight: FontWeight.w600,
                fontSize: 72, // Extra large for dashboard
                letterSpacing: -1,
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: 8.0, left: 4.0),
              child: Text(
                ':$secondsStr',
                style: Theme.of(context).textTheme.displayMedium?.copyWith(
                  color: KinfolkColors.warmClay.withAlpha(204), // 80% opacity
                  fontWeight: FontWeight.w400,
                  fontSize: 36,
                ),
              ),
            ),
          ],
        ),

        const SizedBox(height: 8),

        // Date: Warm Clay accent
        Text(
          dateStr,
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: KinfolkColors.warmClay,
            fontWeight: FontWeight.w500,
            fontSize: 18,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}
