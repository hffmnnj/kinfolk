import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/timer_entity.dart';
import '../../infrastructure/api/timer_api_client.dart';

/// Notifier that polls the backend for active timers every second
/// and exposes the current list for the UI.
class TimerNotifier extends StateNotifier<List<TimerEntity>> {
  final TimerApiClient _client;
  Timer? _pollTimer;

  TimerNotifier({TimerApiClient? client})
    : _client = client ?? TimerApiClient(),
      super(const []) {
    _startPolling();
  }

  void _startPolling() {
    // Fetch immediately, then every second
    _fetch();
    _pollTimer = Timer.periodic(const Duration(seconds: 1), (_) => _fetch());
  }

  Future<void> _fetch() async {
    final timers = await _client.getTimers();
    if (mounted) {
      state = timers;
    }
  }

  /// Request a new timer from the backend.
  Future<void> createTimer({
    required String name,
    required int durationSeconds,
  }) async {
    await _client.createTimer(name: name, durationSeconds: durationSeconds);
    await _fetch();
  }

  /// Cancel a timer by ID.
  Future<void> cancelTimer(String timerId) async {
    await _client.cancelTimer(timerId);
    await _fetch();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _pollTimer = null;
    super.dispose();
  }
}

/// Global provider for the list of active timers.
final timerProvider = StateNotifierProvider<TimerNotifier, List<TimerEntity>>((
  ref,
) {
  return TimerNotifier();
});
