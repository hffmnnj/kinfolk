/// Smart home device entity — domain layer.
///
/// Represents a single Home Assistant entity with its current state
/// and attributes.  Domain-pure: no infrastructure imports.
library;

/// Immutable smart device value object.
class SmartDevice {
  final String entityId;
  final String name;
  final String state; // "on" | "off" | temperature value | etc.
  final String domain; // "light" | "switch" | "climate" | "scene" | ...
  final Map<String, dynamic> attributes;

  const SmartDevice({
    required this.entityId,
    required this.name,
    required this.state,
    required this.domain,
    this.attributes = const {},
  });

  /// Whether the device is currently in an "on" state.
  bool get isOn => state == 'on';

  /// Whether this entity supports toggle (on/off) control.
  bool get isToggleable =>
      domain == 'light' ||
      domain == 'switch' ||
      domain == 'fan' ||
      domain == 'input_boolean';

  /// Whether this entity is a scene.
  bool get isScene => domain == 'scene';

  /// Whether this entity is a climate device.
  bool get isClimate => domain == 'climate';

  /// Friendly display name — falls back to entity_id.
  String get displayName {
    final friendly = attributes['friendly_name'];
    if (friendly is String && friendly.isNotEmpty) return friendly;
    // Strip domain prefix and humanise underscores
    final raw = entityId.contains('.') ? entityId.split('.').last : entityId;
    return raw.replaceAll('_', ' ');
  }

  /// Current temperature for climate entities.
  double? get currentTemperature {
    final temp = attributes['current_temperature'];
    if (temp is num) return temp.toDouble();
    return null;
  }

  /// Brightness percentage (0–100) for lights.
  int? get brightnessPercent {
    final brightness = attributes['brightness'];
    if (brightness is num) {
      return (brightness.toDouble() / 255.0 * 100).round();
    }
    return null;
  }

  /// Create from a JSON map (backend WebSocket payload).
  factory SmartDevice.fromJson(Map<String, dynamic> json) {
    final entityId = json['entity_id'] as String? ?? '';
    final attrs = json['attributes'] as Map<String, dynamic>? ?? {};
    final domain =
        json['domain'] as String? ??
        (entityId.contains('.') ? entityId.split('.').first : 'unknown');

    return SmartDevice(
      entityId: entityId,
      name: (attrs['friendly_name'] as String?) ?? entityId,
      state: json['state'] as String? ?? 'unknown',
      domain: domain,
      attributes: attrs,
    );
  }

  /// Create an updated copy with a new state value.
  SmartDevice copyWith({String? state, Map<String, dynamic>? attributes}) {
    return SmartDevice(
      entityId: entityId,
      name: name,
      state: state ?? this.state,
      domain: domain,
      attributes: attributes ?? this.attributes,
    );
  }
}
