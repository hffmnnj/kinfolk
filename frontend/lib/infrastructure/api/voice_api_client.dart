import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:http/http.dart' as http;

import '../../domain/entities/voice_event.dart';

/// Client for the backend voice API.
///
/// Provides a WebSocket stream of [VoiceEvent] objects and a REST method
/// for querying pipeline status. Handles auto-reconnect with exponential
/// backoff on WebSocket disconnection.
class VoiceApiClient {
  final String baseUrl;
  final String wsUrl;

  WebSocketChannel? _channel;
  StreamController<VoiceEvent>? _controller;
  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;
  bool _disposed = false;

  static const int _maxReconnectDelay = 30;

  VoiceApiClient({
    this.baseUrl = 'http://localhost:8080',
    this.wsUrl = 'ws://localhost:8080/api/v1/voice/ws',
  });

  /// Returns a broadcast stream of parsed [VoiceEvent] objects from the
  /// backend WebSocket. Automatically reconnects on disconnect.
  Stream<VoiceEvent> connectWebSocket() {
    _disposed = false;
    _controller = StreamController<VoiceEvent>.broadcast(onCancel: _disconnect);
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
            final event = VoiceEvent.fromJson(json);
            _controller?.add(event);
          } catch (e) {
            debugPrint('VoiceApiClient: failed to parse event: $e');
          }
        },
        onError: (Object error) {
          debugPrint('VoiceApiClient: WebSocket error: $error');
          _scheduleReconnect();
        },
        onDone: () {
          debugPrint('VoiceApiClient: WebSocket closed');
          _scheduleReconnect();
        },
        cancelOnError: false,
      );
    } catch (e) {
      debugPrint('VoiceApiClient: connection failed: $e');
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_disposed) return;

    _channel = null;
    _reconnectAttempts++;
    final delay = min(pow(2, _reconnectAttempts).toInt(), _maxReconnectDelay);
    debugPrint(
      'VoiceApiClient: reconnecting in ${delay}s '
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

  /// Fetches the current voice pipeline status from the REST endpoint.
  Future<Map<String, dynamic>> getStatus() async {
    final response = await http.get(Uri.parse('$baseUrl/api/v1/voice/status'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Voice status request failed: ${response.statusCode}');
  }

  /// Tears down the WebSocket connection and cancels pending reconnects.
  void dispose() {
    _disconnect();
    _controller?.close();
    _controller = null;
  }
}
