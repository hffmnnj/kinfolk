import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/track.dart';
import '../../infrastructure/api/music_api_client.dart';

/// Immutable state for the music playback system.
class MusicState {
  final Track? currentTrack;
  final bool isPlaying;
  final int volume;
  final bool shuffle;
  final bool repeat;
  final int positionMs;
  final List<Track> searchResults;
  final bool isSearching;
  final bool isConnected;

  const MusicState({
    this.currentTrack,
    this.isPlaying = false,
    this.volume = 50,
    this.shuffle = false,
    this.repeat = false,
    this.positionMs = 0,
    this.searchResults = const [],
    this.isSearching = false,
    this.isConnected = false,
  });

  /// Whether there is an active track (playing or paused).
  bool get hasTrack => currentTrack != null;

  MusicState copyWith({
    Track? currentTrack,
    bool? clearTrack,
    bool? isPlaying,
    int? volume,
    bool? shuffle,
    bool? repeat,
    int? positionMs,
    List<Track>? searchResults,
    bool? isSearching,
    bool? isConnected,
  }) {
    return MusicState(
      currentTrack:
          clearTrack == true ? null : (currentTrack ?? this.currentTrack),
      isPlaying: isPlaying ?? this.isPlaying,
      volume: volume ?? this.volume,
      shuffle: shuffle ?? this.shuffle,
      repeat: repeat ?? this.repeat,
      positionMs: positionMs ?? this.positionMs,
      searchResults: searchResults ?? this.searchResults,
      isSearching: isSearching ?? this.isSearching,
      isConnected: isConnected ?? this.isConnected,
    );
  }
}

/// Notifier that manages music playback state and polls the backend
/// for status updates every 2 seconds.
class MusicNotifier extends StateNotifier<MusicState> {
  final MusicApiClient _client;
  Timer? _pollTimer;

  MusicNotifier({MusicApiClient? client})
    : _client = client ?? const MusicApiClient(),
      super(const MusicState()) {
    _startPolling();
  }

  void _startPolling() {
    // Fetch immediately, then every 2 seconds.
    _fetchStatus();
    _pollTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) => _fetchStatus(),
    );
  }

  Future<void> _fetchStatus() async {
    final status = await _client.getStatus();

    if (status != null) {
      state = state.copyWith(
        currentTrack: status.currentTrack,
        clearTrack: status.currentTrack == null,
        isPlaying: status.isPlaying,
        volume: status.volume,
        shuffle: status.shuffle,
        repeat: status.repeat,
        positionMs: status.positionMs,
        isConnected: true,
      );
    } else {
      state = state.copyWith(isConnected: false);
    }
  }

  /// Start or resume playback. Optionally play a specific track URI.
  Future<void> play({String? uri}) async {
    final success = await _client.play(uri: uri);
    if (success) {
      state = state.copyWith(isPlaying: true);
      // Refresh status to get the actual track info.
      await _fetchStatus();
    }
  }

  /// Pause playback.
  Future<void> pause() async {
    final success = await _client.pause();
    if (success) {
      state = state.copyWith(isPlaying: false);
    }
  }

  /// Skip to the next track.
  Future<void> skip() async {
    final success = await _client.next();
    if (success) {
      await _fetchStatus();
    }
  }

  /// Go to the previous track.
  Future<void> previous() async {
    final success = await _client.previous();
    if (success) {
      await _fetchStatus();
    }
  }

  /// Set playback volume (0–100).
  Future<void> setVolume(int volume) async {
    final clamped = volume.clamp(0, 100);
    // Optimistic update for responsive slider.
    state = state.copyWith(volume: clamped);
    await _client.setVolume(clamped);
  }

  /// Toggle shuffle mode.
  Future<void> toggleShuffle() async {
    final success = await _client.toggleShuffle();
    if (success) {
      state = state.copyWith(shuffle: !state.shuffle);
    }
  }

  /// Toggle repeat mode.
  Future<void> toggleRepeat() async {
    final success = await _client.toggleRepeat();
    if (success) {
      state = state.copyWith(repeat: !state.repeat);
    }
  }

  /// Search for tracks by query.
  Future<void> search(String query) async {
    if (query.trim().isEmpty) {
      state = state.copyWith(searchResults: [], isSearching: false);
      return;
    }

    state = state.copyWith(isSearching: true);
    final results = await _client.search(query);
    state = state.copyWith(searchResults: results, isSearching: false);
  }

  /// Clear search results.
  void clearSearch() {
    state = state.copyWith(searchResults: [], isSearching: false);
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}

/// Global music state provider — polls backend every 2 seconds.
final musicProvider = StateNotifierProvider<MusicNotifier, MusicState>((ref) {
  return MusicNotifier();
});
