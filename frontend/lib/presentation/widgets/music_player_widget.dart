import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../application/providers/music_provider.dart';
import '../../domain/entities/track.dart';
import '../themes/kinfolk_colors.dart';

/// Full now-playing widget with album art, track info, playback controls,
/// volume slider, and progress bar.
///
/// Designed for use on the [MusicScreen] as the primary player display.
class MusicPlayerWidget extends ConsumerWidget {
  const MusicPlayerWidget({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final music = ref.watch(musicProvider);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Album art
        _AlbumArt(track: music.currentTrack),
        const SizedBox(height: 24),

        // Track info
        _TrackInfo(track: music.currentTrack),
        const SizedBox(height: 16),

        // Progress bar
        _ProgressBar(
          positionMs: music.positionMs,
          durationMs: music.currentTrack?.durationMs ?? 0,
        ),
        const SizedBox(height: 16),

        // Playback controls
        _PlaybackControls(
          isPlaying: music.isPlaying,
          shuffle: music.shuffle,
          repeat: music.repeat,
        ),
        const SizedBox(height: 20),

        // Volume slider
        _VolumeSlider(volume: music.volume),
      ],
    );
  }
}

class _AlbumArt extends StatelessWidget {
  final Track? track;

  const _AlbumArt({this.track});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 200,
      height: 200,
      decoration: BoxDecoration(
        color: KinfolkColors.warmClay.withAlpha(38),
        borderRadius: BorderRadius.circular(16),
      ),
      child:
          track?.albumArtUrl != null
              ? ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.network(
                  track!.albumArtUrl!,
                  width: 200,
                  height: 200,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const _AlbumArtPlaceholder(),
                ),
              )
              : const _AlbumArtPlaceholder(),
    );
  }
}

class _AlbumArtPlaceholder extends StatelessWidget {
  const _AlbumArtPlaceholder();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Icon(Icons.music_note, color: KinfolkColors.warmClay, size: 64),
    );
  }
}

class _TrackInfo extends StatelessWidget {
  final Track? track;

  const _TrackInfo({this.track});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          track?.title ?? 'No Track',
          style: Theme.of(context).textTheme.headlineLarge?.copyWith(
            color: KinfolkColors.softCream,
            fontWeight: FontWeight.w600,
          ),
          textAlign: TextAlign.center,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 4),
        Text(
          track != null ? '${track!.artist} — ${track!.album}' : '',
          style: Theme.of(
            context,
          ).textTheme.bodyLarge?.copyWith(color: KinfolkColors.sageGray),
          textAlign: TextAlign.center,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }
}

class _ProgressBar extends StatelessWidget {
  final int positionMs;
  final int durationMs;

  const _ProgressBar({required this.positionMs, required this.durationMs});

  @override
  Widget build(BuildContext context) {
    final progress =
        durationMs > 0 ? (positionMs / durationMs).clamp(0.0, 1.0) : 0.0;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 4,
              backgroundColor: KinfolkColors.sageGray.withAlpha(51),
              valueColor: const AlwaysStoppedAnimation<Color>(
                KinfolkColors.warmClay,
              ),
            ),
          ),
          const SizedBox(height: 4),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _formatMs(positionMs),
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: KinfolkColors.sageGray),
              ),
              Text(
                _formatMs(durationMs),
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: KinfolkColors.sageGray),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatMs(int ms) {
    final totalSeconds = ms ~/ 1000;
    final minutes = totalSeconds ~/ 60;
    final seconds = totalSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }
}

class _PlaybackControls extends ConsumerWidget {
  final bool isPlaying;
  final bool shuffle;
  final bool repeat;

  const _PlaybackControls({
    required this.isPlaying,
    required this.shuffle,
    required this.repeat,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(musicProvider.notifier);

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // Shuffle toggle
        IconButton(
          onPressed: notifier.toggleShuffle,
          icon: Icon(
            Icons.shuffle,
            color:
                shuffle
                    ? KinfolkColors.warmClay
                    : KinfolkColors.sageGray.withAlpha(153),
            size: 22,
          ),
          tooltip: 'Shuffle',
        ),
        const SizedBox(width: 8),

        // Previous
        IconButton(
          onPressed: notifier.previous,
          icon: const Icon(
            Icons.skip_previous,
            color: KinfolkColors.softCream,
            size: 32,
          ),
          tooltip: 'Previous',
        ),
        const SizedBox(width: 8),

        // Play / Pause
        Container(
          decoration: const BoxDecoration(
            color: KinfolkColors.warmClay,
            shape: BoxShape.circle,
          ),
          child: IconButton(
            onPressed: () {
              if (isPlaying) {
                notifier.pause();
              } else {
                notifier.play();
              }
            },
            icon: Icon(
              isPlaying ? Icons.pause : Icons.play_arrow,
              color: KinfolkColors.deepCharcoal,
              size: 36,
            ),
            tooltip: isPlaying ? 'Pause' : 'Play',
          ),
        ),
        const SizedBox(width: 8),

        // Skip
        IconButton(
          onPressed: notifier.skip,
          icon: const Icon(
            Icons.skip_next,
            color: KinfolkColors.softCream,
            size: 32,
          ),
          tooltip: 'Next',
        ),
        const SizedBox(width: 8),

        // Repeat toggle
        IconButton(
          onPressed: notifier.toggleRepeat,
          icon: Icon(
            Icons.repeat,
            color:
                repeat
                    ? KinfolkColors.warmClay
                    : KinfolkColors.sageGray.withAlpha(153),
            size: 22,
          ),
          tooltip: 'Repeat',
        ),
      ],
    );
  }
}

class _VolumeSlider extends ConsumerWidget {
  final int volume;

  const _VolumeSlider({required this.volume});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        children: [
          Icon(
            volume == 0 ? Icons.volume_off : Icons.volume_down,
            color: KinfolkColors.sageGray,
            size: 20,
          ),
          Expanded(
            child: SliderTheme(
              data: SliderTheme.of(context).copyWith(
                activeTrackColor: KinfolkColors.warmClay,
                inactiveTrackColor: KinfolkColors.sageGray.withAlpha(51),
                thumbColor: KinfolkColors.warmClay,
                overlayColor: KinfolkColors.warmClay.withAlpha(38),
                trackHeight: 3,
                thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
              ),
              child: Slider(
                value: volume.toDouble(),
                min: 0,
                max: 100,
                onChanged: (value) {
                  ref.read(musicProvider.notifier).setVolume(value.round());
                },
              ),
            ),
          ),
          const Icon(Icons.volume_up, color: KinfolkColors.sageGray, size: 20),
        ],
      ),
    );
  }
}
