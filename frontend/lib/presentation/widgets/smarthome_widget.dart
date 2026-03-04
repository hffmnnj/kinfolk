import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../application/providers/smarthome_provider.dart';
import '../../domain/entities/smart_device.dart';
import '../themes/kinfolk_colors.dart';

/// Compact smart home dashboard widget.
///
/// Shows a grid of device tiles with toggle controls and an offline
/// indicator when Home Assistant is disconnected.  Designed to sit
/// below the weather section on the 1080×1920 portrait display.
class SmarthomeWidget extends ConsumerWidget {
  const SmarthomeWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(smarthomeProvider);

    // Nothing to show while loading or when there are no devices
    if (state.isLoading) {
      return const SizedBox.shrink();
    }

    final toggleable = state.toggleableDevices;
    final scenes = state.scenes;

    // If no devices and not connected, show offline banner only
    if (toggleable.isEmpty && scenes.isEmpty && !state.connected) {
      return const _OfflineBanner();
    }

    // If no devices at all (HA configured but empty), hide
    if (toggleable.isEmpty && scenes.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Section header with connection indicator
        _SectionHeader(connected: state.connected),
        const SizedBox(height: 8),

        // Device tile grid
        if (toggleable.isNotEmpty) ...[
          _DeviceGrid(
            devices: toggleable,
            onToggle: (entityId) {
              ref.read(smarthomeProvider.notifier).toggleDevice(entityId);
            },
          ),
        ],

        // Scene chips
        if (scenes.isNotEmpty) ...[
          const SizedBox(height: 8),
          _SceneRow(
            scenes: scenes,
            onActivate: (sceneId) {
              ref.read(smarthomeProvider.notifier).activateScene(sceneId);
            },
          ),
        ],
      ],
    );
  }
}

// ------------------------------------------------------------------
// Section header
// ------------------------------------------------------------------

class _SectionHeader extends StatelessWidget {
  final bool connected;

  const _SectionHeader({required this.connected});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(Icons.home, color: KinfolkColors.warmClay, size: 20),
        const SizedBox(width: 8),
        Text(
          'Smart Home',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: KinfolkColors.softCream,
            fontWeight: FontWeight.w500,
          ),
        ),
        const Spacer(),
        // Connection dot
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color:
                connected
                    ? KinfolkColors.forestGreen
                    : KinfolkColors.sunsetOrange,
          ),
        ),
        const SizedBox(width: 6),
        Text(
          connected ? 'Connected' : 'Offline',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color:
                connected
                    ? KinfolkColors.forestGreen
                    : KinfolkColors.sunsetOrange,
          ),
        ),
      ],
    );
  }
}

// ------------------------------------------------------------------
// Offline banner (shown when HA is unreachable and no devices cached)
// ------------------------------------------------------------------

class _OfflineBanner extends StatelessWidget {
  const _OfflineBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: KinfolkColors.darkCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: KinfolkColors.sunsetOrange.withAlpha(77)),
      ),
      child: Row(
        children: [
          Icon(Icons.cloud_off, color: KinfolkColors.sunsetOrange, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Home Assistant offline',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: KinfolkColors.sunsetOrange,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ------------------------------------------------------------------
// Device grid
// ------------------------------------------------------------------

class _DeviceGrid extends StatelessWidget {
  final List<SmartDevice> devices;
  final ValueChanged<String> onToggle;

  const _DeviceGrid({required this.devices, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    // Show up to 6 devices in a 3-column grid
    final visible = devices.take(6).toList();

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children:
          visible.map((device) {
            return _DeviceTile(device: device, onToggle: onToggle);
          }).toList(),
    );
  }
}

class _DeviceTile extends StatelessWidget {
  final SmartDevice device;
  final ValueChanged<String> onToggle;

  const _DeviceTile({required this.device, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    final isOn = device.isOn;
    final brightness = device.brightnessPercent;

    return GestureDetector(
      onTap: () => onToggle(device.entityId),
      child: Container(
        width: 100,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color:
              isOn
                  ? KinfolkColors.warmClay.withAlpha(38)
                  : KinfolkColors.darkCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color:
                isOn
                    ? KinfolkColors.warmClay.withAlpha(102)
                    : KinfolkColors.sageGray.withAlpha(38),
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _iconForDomain(device.domain),
              color: isOn ? KinfolkColors.warmClay : KinfolkColors.sageGray,
              size: 24,
            ),
            const SizedBox(height: 6),
            Text(
              device.displayName,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: isOn ? KinfolkColors.softCream : KinfolkColors.sageGray,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.center,
            ),
            if (brightness != null) ...[
              const SizedBox(height: 4),
              Text(
                '$brightness%',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: KinfolkColors.sageGray,
                  fontSize: 10,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  static IconData _iconForDomain(String domain) {
    switch (domain) {
      case 'light':
        return Icons.lightbulb_outline;
      case 'switch':
        return Icons.power_settings_new;
      case 'fan':
        return Icons.air;
      case 'climate':
        return Icons.thermostat;
      case 'lock':
        return Icons.lock_outline;
      case 'cover':
        return Icons.blinds;
      case 'input_boolean':
        return Icons.toggle_on_outlined;
      default:
        return Icons.devices_other;
    }
  }
}

// ------------------------------------------------------------------
// Scene row
// ------------------------------------------------------------------

class _SceneRow extends StatelessWidget {
  final List<SmartDevice> scenes;
  final ValueChanged<String> onActivate;

  const _SceneRow({required this.scenes, required this.onActivate});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: scenes.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final scene = scenes[index];
          return ActionChip(
            label: Text(
              scene.displayName,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: KinfolkColors.softCream),
            ),
            backgroundColor: KinfolkColors.darkCard,
            side: BorderSide(color: KinfolkColors.sageGray.withAlpha(77)),
            onPressed: () => onActivate(scene.entityId),
          );
        },
      ),
    );
  }
}
