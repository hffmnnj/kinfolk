import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../application/providers/voice_state_provider.dart';
import '../../domain/entities/voice_event.dart';
import '../themes/kinfolk_colors.dart';

/// Full-screen semi-transparent overlay shown during active voice interaction.
///
/// Displays a large pulse animation at the center with a state label
/// ("Listening...", "Processing...", "Responding..."). Dismisses on tap
/// outside the central area or when the pipeline returns to idle.
class VoiceOverlayScreen extends ConsumerWidget {
  const VoiceOverlayScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final voiceState = ref.watch(voiceStateProvider);

    return GestureDetector(
      onTap: () {
        ref.read(voiceStateProvider.notifier).resetToIdle();
      },
      child: Container(
        color: KinfolkColors.deepCharcoal.withAlpha(217), // 85% opacity
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _LargePulseAnimation(color: _colorForState(voiceState)),
              const SizedBox(height: 32),
              Text(
                _labelForState(voiceState),
                style: Theme.of(context).textTheme.displaySmall?.copyWith(
                  color: KinfolkColors.softCream,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  static Color _colorForState(VoiceState state) {
    switch (state) {
      case VoiceState.idle:
        return KinfolkColors.sageGray;
      case VoiceState.listening:
        return KinfolkColors.warmClay;
      case VoiceState.processing:
        return KinfolkColors.skyBlue;
      case VoiceState.responding:
        return KinfolkColors.forestGreen;
    }
  }

  static String _labelForState(VoiceState state) {
    switch (state) {
      case VoiceState.idle:
        return '';
      case VoiceState.listening:
        return 'Listening...';
      case VoiceState.processing:
        return 'Processing...';
      case VoiceState.responding:
        return 'Responding...';
    }
  }
}

/// Large centered pulse animation with three concentric expanding rings.
class _LargePulseAnimation extends StatefulWidget {
  final Color color;

  const _LargePulseAnimation({required this.color});

  @override
  State<_LargePulseAnimation> createState() => _LargePulseAnimationState();
}

class _LargePulseAnimationState extends State<_LargePulseAnimation>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final CurvedAnimation _curve;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();
    _curve = CurvedAnimation(parent: _controller, curve: Curves.easeOut);
  }

  @override
  void dispose() {
    _curve.dispose();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 200,
      height: 200,
      child: AnimatedBuilder(
        animation: _curve,
        builder: (context, child) {
          return CustomPaint(
            painter: _LargePulseRingPainter(
              progress: _curve.value,
              color: widget.color,
            ),
            child: child,
          );
        },
        child: Center(
          child: Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: widget.color.withAlpha(51), // 20% fill
            ),
            child: Icon(Icons.mic, color: widget.color, size: 40),
          ),
        ),
      ),
    );
  }
}

/// Paints three concentric expanding rings for the large overlay animation.
class _LargePulseRingPainter extends CustomPainter {
  final double progress;
  final Color color;

  _LargePulseRingPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width / 2;

    for (int i = 0; i < 3; i++) {
      final t = (progress + i * 0.33) % 1.0;
      final radius = maxRadius * t;
      final alpha = ((1.0 - t) * 153).round();
      if (alpha <= 0) continue;

      final paint =
          Paint()
            ..color = color.withAlpha(alpha)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2.5;

      canvas.drawCircle(center, radius, paint);
    }
  }

  @override
  bool shouldRepaint(_LargePulseRingPainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.color != color;
  }
}
