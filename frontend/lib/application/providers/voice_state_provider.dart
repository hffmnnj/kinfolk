import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/voice_event.dart';
import '../../infrastructure/api/voice_api_client.dart';

/// Manages the voice interaction state machine and listens to backend
/// WebSocket events for wake-word activations and pipeline transitions.
class VoiceStateNotifier extends StateNotifier<VoiceState> {
  final VoiceApiClient _client;
  StreamSubscription<VoiceEvent>? _subscription;
  Timer? _autoResetTimer;

  VoiceStateNotifier({VoiceApiClient? client})
    : _client = client ?? VoiceApiClient(),
      super(VoiceState.idle) {
    _connectWebSocket();
  }

  void _connectWebSocket() {
    _subscription = _client.connectWebSocket().listen(
      _handleEvent,
      onError: (Object error) {
        debugPrint('VoiceStateNotifier: stream error: $error');
      },
    );
  }

  void _handleEvent(VoiceEvent event) {
    switch (event.type) {
      case 'wake_word':
        startListening();
      case 'stt_result':
        setProcessing();
      case 'intent_result':
        setResponding();
      case 'tts_done':
        resetToIdle();
      default:
        debugPrint('VoiceStateNotifier: unhandled event type: ${event.type}');
    }
  }

  /// Transitions to the listening state (wake word detected or manual tap).
  void startListening() {
    state = VoiceState.listening;
    _cancelAutoReset();
    _scheduleAutoReset(const Duration(seconds: 15));
  }

  /// Transitions to the processing state (speech captured, awaiting intent).
  void setProcessing() {
    state = VoiceState.processing;
    _cancelAutoReset();
    _scheduleAutoReset(const Duration(seconds: 30));
  }

  /// Transitions to the responding state (TTS playback in progress).
  void setResponding() {
    state = VoiceState.responding;
    _cancelAutoReset();
    _scheduleAutoReset(const Duration(seconds: 30));
  }

  /// Returns to idle (pipeline complete or user dismissal).
  void resetToIdle() {
    state = VoiceState.idle;
    _cancelAutoReset();
  }

  void _scheduleAutoReset(Duration timeout) {
    _autoResetTimer = Timer(timeout, () {
      if (mounted) {
        state = VoiceState.idle;
      }
    });
  }

  void _cancelAutoReset() {
    _autoResetTimer?.cancel();
    _autoResetTimer = null;
  }

  @override
  void dispose() {
    _cancelAutoReset();
    _subscription?.cancel();
    _client.dispose();
    super.dispose();
  }
}

/// Global provider for the voice interaction state.
final voiceStateProvider =
    StateNotifierProvider<VoiceStateNotifier, VoiceState>((ref) {
      return VoiceStateNotifier();
    });
