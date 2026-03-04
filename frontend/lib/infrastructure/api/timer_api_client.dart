import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../domain/entities/timer_entity.dart';

/// REST client for the backend timer API.
class TimerApiClient {
  final String baseUrl;

  TimerApiClient({this.baseUrl = 'http://localhost:8080'});

  /// Fetch all active timers with remaining seconds.
  Future<List<TimerEntity>> getTimers() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/v1/timers'));
      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        final data = body['data'] as List<dynamic>? ?? [];
        return data
            .map((e) => TimerEntity.fromJson(e as Map<String, dynamic>))
            .toList();
      }
      debugPrint('TimerApiClient: GET /timers failed: ${response.statusCode}');
      return [];
    } catch (e) {
      debugPrint('TimerApiClient: GET /timers error: $e');
      return [];
    }
  }

  /// Create a new timer with the given name and duration in seconds.
  Future<TimerEntity?> createTimer({
    required String name,
    required int durationSeconds,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/timers'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'name': name, 'duration_seconds': durationSeconds}),
      );
      if (response.statusCode == 201) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        final data = body['data'] as Map<String, dynamic>;
        return TimerEntity.fromJson(data);
      }
      debugPrint('TimerApiClient: POST /timers failed: ${response.statusCode}');
      return null;
    } catch (e) {
      debugPrint('TimerApiClient: POST /timers error: $e');
      return null;
    }
  }

  /// Cancel a timer by ID.
  Future<bool> cancelTimer(String timerId) async {
    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/api/v1/timers/$timerId'),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('TimerApiClient: DELETE /timers error: $e');
      return false;
    }
  }
}
