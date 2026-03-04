import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../application/providers/voice_state_provider.dart';
import '../../domain/entities/voice_event.dart';
import '../themes/kinfolk_colors.dart';

/// Persistent microphone indicator displayed on the dashboard.
///
/// Shows a mic icon that changes color based on voice state and plays a
/// concentric-circle pulse animation when the pipeline is active.
/// Tap to toggle listening mode.
class VoiceIndicatorWidget extends ConsumerWidget {
  const VoiceIndicatorWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final voiceState = ref.watch(voiceStateProvider);

    return GestureDetector(
      onTap: () {
        final notifier = ref.read(voiceStateProvider.notifier);
        if (voiceState == VoiceState.idle) {
          notifier.startListening();
        } else {
          notifier.resetToIdle();
        }
      },
      child: SizedBox(
        width: 48,
        height: 48,
        child:
            voiceState == VoiceState.idle
                ? _StaticIndicator(color: _colorForState(voiceState))
                : _PulsingIndicator(color: _colorForState(voiceState)),
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
}

class _StaticIndicator extends StatelessWidget {
  final Color color;

  const _StaticIndicator({required this.color});

  @override
  Widget build(BuildContext context) {
    return Center(child: Icon(Icons.mic, color: color, size: 28));
  }
}

/// Animated mic indicator with expanding concentric circles.
class _PulsingIndicator extends StatefulWidget {
  final Color color;

  const _PulsingIndicator({required this.color});

  @override
  State<_PulsingIndicator> createState() => _PulsingIndicatorState();
}

class _PulsingIndicatorState extends State<_PulsingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final CurvedAnimation _curve;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
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
    return AnimatedBuilder(
      animation: _curve,
      builder: (context, child) {
        return CustomPaint(
          painter: _PulseRingPainter(
            progress: _curve.value,
            color: widget.color,
          ),
          child: child,
        );
      },
      child: Center(child: Icon(Icons.mic, color: widget.color, size: 28)),
    );
  }
}

/// Paints two concentric expanding rings that fade out as they grow.
class _PulseRingPainter extends CustomPainter {
  final double progress;
  final Color color;

  _PulseRingPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width / 2;

    // First ring
    _drawRing(canvas, center, maxRadius, progress);

    // Second ring offset by half a cycle
    final secondProgress = (progress + 0.5) % 1.0;
    _drawRing(canvas, center, maxRadius, secondProgress);
  }

  void _drawRing(Canvas canvas, Offset center, double maxRadius, double t) {
    final radius = maxRadius * t;
    final alpha = ((1.0 - t) * 128).round();
    if (alpha <= 0) return;

    final paint =
        Paint()
          ..color = color.withAlpha(alpha)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.0;

    canvas.drawCircle(center, radius, paint);
  }

  @override
  bool shouldRepaint(_PulseRingPainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.color != color;
  }
}
