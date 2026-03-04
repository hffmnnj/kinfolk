/// Voice event entity — domain layer.
/// Represents events received from the backend voice WebSocket.
library;

/// The current state of the voice interaction pipeline.
enum VoiceState { idle, listening, processing, responding }

/// A voice event received from the backend WebSocket.
class VoiceEvent {
  final String type;
  final String? keyword;
  final double? confidence;
  final String? text;
  final String? intent;
  final String? action;
  final DateTime timestamp;

  const VoiceEvent({
    required this.type,
    this.keyword,
    this.confidence,
    this.text,
    this.intent,
    this.action,
    required this.timestamp,
  });

  factory VoiceEvent.fromJson(Map<String, dynamic> json) {
    return VoiceEvent(
      type: json['type'] as String? ?? 'unknown',
      keyword: json['keyword'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
      text: json['text'] as String?,
      intent: json['intent'] as String?,
      action: json['action'] as String?,
      timestamp:
          json['timestamp'] != null
              ? DateTime.tryParse(json['timestamp'] as String) ?? DateTime.now()
              : DateTime.now(),
    );
  }
}
