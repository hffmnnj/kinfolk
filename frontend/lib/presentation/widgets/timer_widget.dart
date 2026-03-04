import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../application/providers/timer_provider.dart';
import '../../domain/entities/timer_entity.dart';
import '../themes/kinfolk_colors.dart';

/// Horizontally scrollable row of active timer countdown cards.
///
/// Shows nothing when no timers are active, keeping the dashboard
/// clean.  Each card displays the timer name, MM:SS countdown,
/// a circular progress indicator, and a cancel button.
class TimerWidget extends ConsumerWidget {
  const TimerWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final timers = ref.watch(timerProvider);

    if (timers.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8.0),
          child: Row(
            children: [
              Icon(Icons.timer, color: KinfolkColors.warmClay, size: 20),
              const SizedBox(width: 8),
              Text(
                'Timers',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: KinfolkColors.softCream,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
        SizedBox(
          height: 100,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: timers.length,
            separatorBuilder: (_, __) => const SizedBox(width: 12),
            itemBuilder: (context, index) {
              return _TimerCard(timer: timers[index]);
            },
          ),
        ),
      ],
    );
  }
}

class _TimerCard extends ConsumerWidget {
  final TimerEntity timer;

  const _TimerCard({required this.timer});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isExpired = timer.remainingSeconds <= 0;

    return Container(
      width: 160,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: KinfolkColors.darkCard,
        borderRadius: BorderRadius.circular(12),
        border:
            isExpired
                ? Border.all(
                  color: KinfolkColors.sunsetOrange.withAlpha(153),
                  width: 1.5,
                )
                : null,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: name + cancel button
          Row(
            children: [
              Expanded(
                child: Text(
                  timer.name,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: KinfolkColors.sageGray,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              GestureDetector(
                onTap: () {
                  ref.read(timerProvider.notifier).cancelTimer(timer.id);
                },
                child: Icon(
                  Icons.close,
                  size: 16,
                  color: KinfolkColors.sageGray.withAlpha(153),
                ),
              ),
            ],
          ),
          const Spacer(),
          // Countdown + progress
          Row(
            children: [
              SizedBox(
                width: 32,
                height: 32,
                child: CircularProgressIndicator(
                  value: timer.progress,
                  strokeWidth: 3,
                  backgroundColor: KinfolkColors.sageGray.withAlpha(51),
                  valueColor: AlwaysStoppedAnimation<Color>(
                    isExpired
                        ? KinfolkColors.sunsetOrange
                        : KinfolkColors.warmClay,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Text(
                isExpired ? 'Done!' : timer.remainingDisplay,
                style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                  color:
                      isExpired
                          ? KinfolkColors.sunsetOrange
                          : KinfolkColors.softCream,
                  fontWeight: FontWeight.w600,
                  fontSize: 20,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
