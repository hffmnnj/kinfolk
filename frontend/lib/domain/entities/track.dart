/// Track entity — domain layer.
/// Represents a music track from the Mopidy backend.
library;

/// Immutable track value object.
class Track {
  final String id;
  final String title;
  final String artist;
  final String album;
  final int durationMs;
  final String uri;
  final String? albumArtUrl;

  const Track({
    required this.id,
    required this.title,
    required this.artist,
    required this.album,
    required this.durationMs,
    required this.uri,
    this.albumArtUrl,
  });

  /// Duration formatted as M:SS or H:MM:SS.
  String get durationDisplay {
    final totalSeconds = durationMs ~/ 1000;
    final hours = totalSeconds ~/ 3600;
    final minutes = (totalSeconds % 3600) ~/ 60;
    final seconds = totalSeconds % 60;

    if (hours > 0) {
      return '$hours:${minutes.toString().padLeft(2, '0')}'
          ':${seconds.toString().padLeft(2, '0')}';
    }
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  factory Track.fromJson(Map<String, dynamic> json) {
    return Track(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? 'Unknown Track',
      artist: json['artist'] as String? ?? 'Unknown Artist',
      album: json['album'] as String? ?? 'Unknown Album',
      durationMs: (json['duration_ms'] as num?)?.toInt() ?? 0,
      uri: json['uri'] as String? ?? '',
      albumArtUrl: json['album_art_url'] as String?,
    );
  }
}
