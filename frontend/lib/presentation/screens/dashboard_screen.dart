import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../application/providers/voice_state_provider.dart';
import '../../domain/entities/voice_event.dart';
import '../screens/photo_frame_screen.dart';
import '../screens/voice_overlay_screen.dart';
import '../themes/kinfolk_colors.dart';
import '../widgets/clock_widget.dart';
import '../widgets/timer_widget.dart';
import '../widgets/voice_indicator_widget.dart';
import '../widgets/weather_widget.dart';

/// The main always-on family dashboard screen.
/// Designed for 1080×1920 portrait orientation.
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final voiceState = ref.watch(voiceStateProvider);
    final showOverlay = voiceState != VoiceState.idle;

    return Scaffold(
      backgroundColor: KinfolkColors.deepCharcoal,
      body: SafeArea(
        child: Stack(
          children: [
            // Main dashboard content
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: 24.0,
                vertical: 16.0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Top section: Clock & Date (~35%)
                  const Expanded(flex: 35, child: _ClockSection()),

                  const SizedBox(height: 8),
                  const _SectionDivider(),
                  const SizedBox(height: 8),

                  // Middle section: Weather (~20%)
                  const Expanded(flex: 20, child: _WeatherSection()),

                  const SizedBox(height: 8),
                  const _SectionDivider(),
                  const SizedBox(height: 8),

                  // Bottom section: Future widgets placeholder (~45%)
                  Expanded(flex: 45, child: _ComingSoonSection()),
                ],
              ),
            ),

            // Voice indicator — top-right corner
            const Positioned(top: 16, right: 16, child: VoiceIndicatorWidget()),

            // Voice overlay — shown when pipeline is active
            if (showOverlay) const VoiceOverlayScreen(),
          ],
        ),
      ),
    );
  }
}

class _ClockSection extends StatelessWidget {
  const _ClockSection();

  @override
  Widget build(BuildContext context) {
    return const Center(child: ClockWidget());
  }
}

class _WeatherSection extends StatelessWidget {
  const _WeatherSection();

  @override
  Widget build(BuildContext context) {
    return const Center(child: WeatherWidget());
  }
}

class _ComingSoonSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Active timers — only visible when timers are running
          const TimerWidget(),
          const SizedBox(height: 12),
          Text(
            'Coming Soon',
            style: Theme.of(
              context,
            ).textTheme.headlineLarge?.copyWith(color: KinfolkColors.sageGray),
          ),
          const SizedBox(height: 12),
          const _PlaceholderCard(
            icon: Icons.calendar_today,
            title: 'Calendar',
            subtitle: 'Shared family events',
          ),
          const SizedBox(height: 8),
          const _PlaceholderCard(
            icon: Icons.checklist,
            title: 'Tasks',
            subtitle: 'Shopping lists & to-dos',
          ),
          const SizedBox(height: 8),
          const _PlaceholderCard(
            icon: Icons.music_note,
            title: 'Music',
            subtitle: 'Now playing',
          ),
          const SizedBox(height: 8),
          _PhotoFrameCard(),
        ],
      ),
    );
  }
}

class _PhotoFrameCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute<void>(builder: (_) => const PhotoFrameScreen()),
        );
      },
      child: Card(
        color: KinfolkColors.darkCard,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
          child: Row(
            children: [
              const Icon(
                Icons.photo_library,
                color: KinfolkColors.warmClay,
                size: 24,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Photos',
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: KinfolkColors.softCream,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    Text(
                      'Family photo slideshow',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: KinfolkColors.sageGray,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(
                Icons.chevron_right,
                color: KinfolkColors.sageGray,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlaceholderCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _PlaceholderCard({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      color: KinfolkColors.darkCard,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
        child: Row(
          children: [
            Icon(icon, color: KinfolkColors.warmClay, size: 24),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: KinfolkColors.softCream,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: KinfolkColors.sageGray,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionDivider extends StatelessWidget {
  const _SectionDivider();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 1,
      color: KinfolkColors.sageGray.withAlpha(51), // 20% opacity
    );
  }
}
