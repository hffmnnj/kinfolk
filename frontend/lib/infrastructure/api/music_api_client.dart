import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../domain/entities/track.dart';

/// Client for the backend music API endpoints.
///
/// Communicates with the FastAPI backend which proxies Mopidy
/// via JSON-RPC. All playback control, search, and status
/// requests go through this client.
class MusicApiClient {
  final String baseUrl;

  const MusicApiClient({this.baseUrl = 'http://localhost:8080'});

  /// Fetch current playback status (current track, position, state).
  Future<MusicStatusResponse?> getStatus() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/music/status'),
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return MusicStatusResponse.fromJson(json);
      }

      debugPrint('MusicApiClient: status failed: ${response.statusCode}');
      return null;
    } catch (e) {
      debugPrint('MusicApiClient: status error: $e');
      return null;
    }
  }

  /// Start or resume playback. Optionally pass a track URI.
  Future<bool> play({String? uri}) async {
    try {
      final body = uri != null ? jsonEncode({'uri': uri}) : '{}';
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/music/play'),
        headers: {'Content-Type': 'application/json'},
        body: body,
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('MusicApiClient: play error: $e');
      return false;
    }
  }

  /// Pause playback.
  Future<bool> pause() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/music/pause'),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('MusicApiClient: pause error: $e');
      return false;
    }
  }

  /// Skip to next track.
  Future<bool> next() async {
    try {
      final response = await http.post(Uri.parse('$baseUrl/api/v1/music/next'));
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('MusicApiClient: next error: $e');
      return false;
    }
  }

  /// Go to previous track.
  Future<bool> previous() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/music/previous'),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('MusicApiClient: previous error: $e');
      return false;
    }
  }

  /// Set playback volume (0–100).
  Future<bool> setVolume(int volume) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/music/volume'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'volume': volume.clamp(0, 100)}),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('MusicApiClient: volume error: $e');
      return false;
    }
  }

  /// Toggle shuffle mode.
  Future<bool> toggleShuffle() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/music/shuffle'),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('MusicApiClient: shuffle error: $e');
      return false;
    }
  }

  /// Toggle repeat mode.
  Future<bool> toggleRepeat() async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/music/repeat'),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('MusicApiClient: repeat error: $e');
      return false;
    }
  }

  /// Search for tracks by query string.
  Future<List<Track>> search(String query) async {
    if (query.trim().isEmpty) return [];

    try {
      final response = await http.get(
        Uri.parse(
          '$baseUrl/api/v1/music/search?q=${Uri.encodeQueryComponent(query)}',
        ),
      );

      if (response.statusCode == 200) {
        final jsonList = jsonDecode(response.body) as List<dynamic>;
        return jsonList
            .map((item) => Track.fromJson(item as Map<String, dynamic>))
            .toList();
      }

      debugPrint('MusicApiClient: search failed: ${response.statusCode}');
      return [];
    } catch (e) {
      debugPrint('MusicApiClient: search error: $e');
      return [];
    }
  }
}

/// Parsed response from the music status endpoint.
class MusicStatusResponse {
  final Track? currentTrack;
  final bool isPlaying;
  final int volume;
  final bool shuffle;
  final bool repeat;
  final int positionMs;

  const MusicStatusResponse({
    this.currentTrack,
    this.isPlaying = false,
    this.volume = 50,
    this.shuffle = false,
    this.repeat = false,
    this.positionMs = 0,
  });

  factory MusicStatusResponse.fromJson(Map<String, dynamic> json) {
    final trackJson = json['current_track'] as Map<String, dynamic>?;

    return MusicStatusResponse(
      currentTrack: trackJson != null ? Track.fromJson(trackJson) : null,
      isPlaying: json['is_playing'] as bool? ?? false,
      volume: (json['volume'] as num?)?.toInt() ?? 50,
      shuffle: json['shuffle'] as bool? ?? false,
      repeat: json['repeat'] as bool? ?? false,
      positionMs: (json['position_ms'] as num?)?.toInt() ?? 0,
    );
  }
}
