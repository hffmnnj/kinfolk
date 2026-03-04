/// Timer domain entity — avoids Dart `Timer` naming conflict.
///
/// Represents a named countdown timer or alarm from the backend.
library;

/// Immutable timer value object.
class TimerEntity {
  final String id;
  final String name;
  final int? durationSeconds;
  final DateTime startedAt;
  final DateTime fireAt;
  final bool completed;
  final bool cancelled;
  final String? userId;
  final int remainingSeconds;

  const TimerEntity({
    required this.id,
    required this.name,
    this.durationSeconds,
    required this.startedAt,
    required this.fireAt,
    this.completed = false,
    this.cancelled = false,
    this.userId,
    this.remainingSeconds = 0,
  });

  /// Parse from JSON map returned by the backend API.
  factory TimerEntity.fromJson(Map<String, dynamic> json) {
    return TimerEntity(
      id: json['id'] as String,
      name: json['name'] as String,
      durationSeconds: json['duration_seconds'] as int?,
      startedAt: DateTime.parse(json['started_at'] as String),
      fireAt: DateTime.parse(json['fire_at'] as String),
      completed: json['completed'] as bool? ?? false,
      cancelled: json['cancelled'] as bool? ?? false,
      userId: json['user_id'] as String?,
      remainingSeconds: json['remaining_seconds'] as int? ?? 0,
    );
  }

  /// Whether this timer is still actively counting down.
  bool get isActive => !completed && !cancelled && remainingSeconds > 0;

  /// Format remaining time as MM:SS.
  String get remainingDisplay {
    final minutes = remainingSeconds ~/ 60;
    final seconds = remainingSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:'
        '${seconds.toString().padLeft(2, '0')}';
  }

  /// Progress fraction (0.0 = just started, 1.0 = done).
  double get progress {
    if (durationSeconds == null || durationSeconds == 0) return 1.0;
    final elapsed = durationSeconds! - remainingSeconds;
    return (elapsed / durationSeconds!).clamp(0.0, 1.0);
  }
}
