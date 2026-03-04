import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/smart_device.dart';
import '../../infrastructure/api/smarthome_api_client.dart';

/// Aggregate smart home state exposed to the UI.
class SmarthomeState {
  /// All known devices keyed by entity_id.
  final Map<String, SmartDevice> devices;

  /// Whether the backend reports an active HA connection.
  final bool connected;

  /// True while the initial snapshot has not yet arrived.
  final bool isLoading;

  /// Last error message, if any.
  final String? error;

  const SmarthomeState({
    this.devices = const {},
    this.connected = false,
    this.isLoading = true,
    this.error,
  });

  SmarthomeState copyWith({
    Map<String, SmartDevice>? devices,
    bool? connected,
    bool? isLoading,
    String? error,
  }) {
    return SmarthomeState(
      devices: devices ?? this.devices,
      connected: connected ?? this.connected,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }

  /// Convenience: devices filtered to toggleable entities (lights, switches, fans).
  List<SmartDevice> get toggleableDevices =>
      devices.values.where((d) => d.isToggleable).toList();

  /// Convenience: scene entities.
  List<SmartDevice> get scenes =>
      devices.values.where((d) => d.isScene).toList();

  /// Convenience: climate entities.
  List<SmartDevice> get climateDevices =>
      devices.values.where((d) => d.isClimate).toList();
}

/// Notifier that maintains a WebSocket connection to the backend
/// smart home proxy and keeps device state in sync.
class SmarthomeNotifier extends StateNotifier<SmarthomeState> {
  final SmarthomeApiClient _client;
  StreamSubscription<SmarthomeWsMessage>? _subscription;

  SmarthomeNotifier({SmarthomeApiClient? client})
    : _client = client ?? SmarthomeApiClient(),
      super(const SmarthomeState()) {
    _connectWebSocket();
  }

  void _connectWebSocket() {
    final stream = _client.connectWebSocket();
    _subscription = stream.listen(
      _onMessage,
      onError: (Object error) {
        debugPrint('SmarthomeNotifier: stream error: $error');
        if (mounted) {
          state = state.copyWith(connected: false, error: error.toString());
        }
      },
    );
  }

  void _onMessage(SmarthomeWsMessage msg) {
    if (!mounted) return;

    switch (msg.type) {
      case 'snapshot':
        final deviceMap = <String, SmartDevice>{};
        for (final device in msg.entities ?? <SmartDevice>[]) {
          deviceMap[device.entityId] = device;
        }
        state = SmarthomeState(
          devices: deviceMap,
          connected: msg.connected ?? false,
          isLoading: false,
        );

      case 'state_changed':
        if (msg.device != null) {
          final updated = Map<String, SmartDevice>.from(state.devices);
          updated[msg.device!.entityId] = msg.device!;
          state = state.copyWith(devices: updated);
        }

      case 'status':
        state = state.copyWith(
          connected: msg.connected ?? false,
          isLoading: false,
        );
    }
  }

  /// Toggle a device on/off via the REST API and optimistically
  /// update local state.
  Future<void> toggleDevice(String entityId) async {
    final device = state.devices[entityId];
    if (device == null || !device.isToggleable) return;

    final turnOn = !device.isOn;

    // Optimistic update
    final updated = Map<String, SmartDevice>.from(state.devices);
    updated[entityId] = device.copyWith(state: turnOn ? 'on' : 'off');
    state = state.copyWith(devices: updated);

    final ok = await _client.toggleDevice(entityId, turnOn: turnOn);
    if (!ok && mounted) {
      // Revert on failure
      final reverted = Map<String, SmartDevice>.from(state.devices);
      reverted[entityId] = device;
      state = state.copyWith(devices: reverted);
    }
  }

  /// Activate a Home Assistant scene.
  Future<void> activateScene(String sceneId) async {
    await _client.activateScene(sceneId);
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _subscription = null;
    _client.dispose();
    super.dispose();
  }
}

/// Global smart home state provider.
final smarthomeProvider =
    StateNotifierProvider<SmarthomeNotifier, SmarthomeState>((ref) {
      return SmarthomeNotifier();
    });
