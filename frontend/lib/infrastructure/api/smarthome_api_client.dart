import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../domain/entities/smart_device.dart';

/// Combined REST + WebSocket client for the smart home backend.
///
/// REST endpoints handle device commands and scene activation.
/// The WebSocket stream delivers real-time state updates from
/// Home Assistant via the backend proxy.
class SmarthomeApiClient {
  final String baseUrl;
  final String wsUrl;

  WebSocketChannel? _channel;
  StreamController<SmarthomeWsMessage>? _controller;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  bool _disposed = false;

  static const int _maxReconnectDelay = 30;

  SmarthomeApiClient({
    this.baseUrl = 'http://localhost:8080',
    this.wsUrl = 'ws://localhost:8080/api/v1/smarthome/ws',
  });

  // ------------------------------------------------------------------
  // WebSocket — real-time state stream
  // ------------------------------------------------------------------

  /// Returns a broadcast stream of parsed WebSocket messages.
  /// Automatically reconnects on disconnect.
  Stream<SmarthomeWsMessage> connectWebSocket() {
    _disposed = false;
    _controller = StreamController<SmarthomeWsMessage>.broadcast(
      onCancel: _disconnect,
    );
    _connect();
    return _controller!.stream;
  }

  void _connect() {
    if (_disposed) return;

    try {
      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));
      _reconnectAttempts = 0;

      _channel!.stream.listen(
        (data) {
          try {
            final json = jsonDecode(data as String) as Map<String, dynamic>;
            final msg = SmarthomeWsMessage.fromJson(json);
            _controller?.add(msg);
          } catch (e) {
            debugPrint('SmarthomeApiClient: failed to parse WS message: $e');
          }
        },
        onError: (Object error) {
          debugPrint('SmarthomeApiClient: WebSocket error: $error');
          _scheduleReconnect();
        },
        onDone: () {
          debugPrint('SmarthomeApiClient: WebSocket closed');
          _scheduleReconnect();
        },
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('SmarthomeApiClient: connection failed: $e');
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_disposed) return;

    _channel = null;
    _reconnectAttempts++;
    final delay = min(pow(2, _reconnectAttempts).toInt(), _maxReconnectDelay);
    debugPrint(
      'SmarthomeApiClient: reconnecting in ${delay}s '
      '(attempt $_reconnectAttempts)',
    );

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: delay), _connect);
  }

  void _disconnect() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _channel?.sink.close();
    _channel = null;
  }

  // ------------------------------------------------------------------
  // REST — device commands
  // ------------------------------------------------------------------

  /// Toggle a device on or off.
  Future<bool> toggleDevice(String entityId, {required bool turnOn}) async {
    final command = turnOn ? 'turn_on' : 'turn_off';
    return _sendCommand(entityId, command);
  }

  /// Activate a Home Assistant scene.
  Future<bool> activateScene(String sceneId) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/smarthome/scenes/$sceneId/activate'),
        headers: {'Content-Type': 'application/json'},
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('SmarthomeApiClient: activateScene error: $e');
      return false;
    }
  }

  /// Send a device command via the REST API.
  Future<bool> _sendCommand(
    String entityId,
    String command, {
    Map<String, dynamic> params = const {},
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/smarthome/devices/$entityId/command'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'command': command, 'params': params}),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('SmarthomeApiClient: command error: $e');
      return false;
    }
  }

  /// Fetch the device list via REST (fallback when WS unavailable).
  Future<List<SmartDevice>> getDevices() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/smarthome/devices'),
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final data = json['data'] as Map<String, dynamic>? ?? {};
        final devices = data['devices'] as List<dynamic>? ?? [];
        return devices
            .map((d) => SmartDevice.fromJson(d as Map<String, dynamic>))
            .toList();
      }

      return [];
    } catch (e) {
      debugPrint('SmarthomeApiClient: getDevices error: $e');
      return [];
    }
  }

  /// Tear down the WebSocket connection and cancel pending reconnects.
  void dispose() {
    _disconnect();
    _controller?.close();
    _controller = null;
  }
}

// ------------------------------------------------------------------
// WebSocket message types
// ------------------------------------------------------------------

/// Parsed message from the smarthome WebSocket.
class SmarthomeWsMessage {
  final String type; // "snapshot" | "state_changed" | "status"
  final bool? connected;
  final List<SmartDevice>? entities; // present on "snapshot"
  final SmartDevice? device; // present on "state_changed"

  const SmarthomeWsMessage({
    required this.type,
    this.connected,
    this.entities,
    this.device,
  });

  factory SmarthomeWsMessage.fromJson(Map<String, dynamic> json) {
    final type = json['type'] as String? ?? 'unknown';

    if (type == 'snapshot') {
      final entityList = json['entities'] as List<dynamic>? ?? [];
      return SmarthomeWsMessage(
        type: type,
        connected: json['connected'] as bool? ?? false,
        entities:
            entityList
                .map((e) => SmartDevice.fromJson(e as Map<String, dynamic>))
                .toList(),
      );
    }

    if (type == 'state_changed') {
      return SmarthomeWsMessage(type: type, device: SmartDevice.fromJson(json));
    }

    // "status" or unknown
    return SmarthomeWsMessage(
      type: type,
      connected: json['connected'] as bool? ?? false,
    );
  }
}
