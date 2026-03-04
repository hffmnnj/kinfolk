import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../application/providers/photo_frame_provider.dart';
import '../../domain/entities/photo.dart';
import '../themes/kinfolk_colors.dart';

/// Full-screen photo frame slideshow.
///
/// Displays photos from a local directory with configurable fade or slide
/// transitions.  Tap anywhere to dismiss back to the dashboard.
/// EXIF metadata (date, location) is overlaid at the bottom-left.
class PhotoFrameScreen extends ConsumerStatefulWidget {
  final String directory;
  final PhotoTransitionType transitionType;
  final int durationSeconds;

  const PhotoFrameScreen({
    super.key,
    this.directory = '~/Pictures',
    this.transitionType = PhotoTransitionType.fade,
    this.durationSeconds = 30,
  });

  @override
  ConsumerState<PhotoFrameScreen> createState() => _PhotoFrameScreenState();
}

class _PhotoFrameScreenState extends ConsumerState<PhotoFrameScreen> {
  @override
  void initState() {
    super.initState();
    // Activate the slideshow after the first frame so the provider is ready.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(photoFrameProvider.notifier)
          .activate(
            directory: widget.directory,
            transitionType: widget.transitionType,
            durationSeconds: widget.durationSeconds,
          );
    });
  }

  @override
  void dispose() {
    // Deactivate when leaving the screen.
    // Use a microtask to avoid modifying provider state during dispose.
    Future.microtask(() {
      if (mounted) return;
      // Provider will be cleaned up by Riverpod when no longer watched.
    });
    super.dispose();
  }

  void _dismiss() {
    ref.read(photoFrameProvider.notifier).deactivate();
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(photoFrameProvider);

    return Scaffold(
      backgroundColor: Colors.black,
      body: GestureDetector(
        onTap: _dismiss,
        // Swipe left/right for manual navigation.
        onHorizontalDragEnd: (details) {
          if (details.primaryVelocity == null) return;
          if (details.primaryVelocity! < -100) {
            ref.read(photoFrameProvider.notifier).nextPhoto();
          } else if (details.primaryVelocity! > 100) {
            ref.read(photoFrameProvider.notifier).previousPhoto();
          }
        },
        behavior: HitTestBehavior.opaque,
        child: Stack(
          fit: StackFit.expand,
          children: [
            // Photo display with transitions
            if (state.isLoading)
              const Center(
                child: CircularProgressIndicator(color: KinfolkColors.warmClay),
              )
            else if (state.error != null)
              _ErrorDisplay(message: state.error!)
            else if (state.currentPhoto != null)
              _PhotoDisplay(
                photo: state.currentPhoto!,
                index: state.currentPhotoIndex,
                transitionType: state.transitionType,
              ),

            // EXIF metadata overlay — bottom-left
            if (state.currentPhoto != null &&
                !state.isLoading &&
                state.error == null)
              Positioned(
                left: 24,
                bottom: 48,
                child: _MetadataOverlay(photo: state.currentPhoto!),
              ),

            // Photo counter — bottom-right
            if (state.photos.isNotEmpty &&
                !state.isLoading &&
                state.error == null)
              Positioned(
                right: 24,
                bottom: 48,
                child: _PhotoCounter(
                  current: state.currentPhotoIndex + 1,
                  total: state.photos.length,
                ),
              ),

            // Tap hint — top-center, fades out
            const Positioned(top: 32, left: 0, right: 0, child: _TapHint()),
          ],
        ),
      ),
    );
  }
}

/// Displays the current photo with animated transitions.
class _PhotoDisplay extends StatelessWidget {
  final Photo photo;
  final int index;
  final PhotoTransitionType transitionType;

  const _PhotoDisplay({
    required this.photo,
    required this.index,
    required this.transitionType,
  });

  @override
  Widget build(BuildContext context) {
    final child = Image.file(
      File(photo.path),
      key: ValueKey(photo.path),
      fit: BoxFit.contain,
      width: double.infinity,
      height: double.infinity,
      errorBuilder: (context, error, stackTrace) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.broken_image_outlined,
                color: KinfolkColors.sageGray,
                size: 64,
              ),
              const SizedBox(height: 12),
              Text(
                'Unable to load image',
                style: TextStyle(color: KinfolkColors.sageGray, fontSize: 14),
              ),
            ],
          ),
        );
      },
    );

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 800),
      switchInCurve: Curves.easeInOut,
      switchOutCurve: Curves.easeInOut,
      transitionBuilder: (child, animation) {
        if (transitionType == PhotoTransitionType.slide) {
          return SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(1.0, 0.0),
              end: Offset.zero,
            ).animate(animation),
            child: child,
          );
        }
        // Default: fade
        return FadeTransition(opacity: animation, child: child);
      },
      child: child,
    );
  }
}

/// Semi-transparent overlay showing photo metadata.
class _MetadataOverlay extends StatelessWidget {
  final Photo photo;

  const _MetadataOverlay({required this.photo});

  @override
  Widget build(BuildContext context) {
    final hasDate = photo.dateTaken != null;
    final hasLocation = photo.location != null;
    final hasTitle = photo.title != null && photo.title!.isNotEmpty;

    if (!hasDate && !hasLocation && !hasTitle) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.black.withAlpha(153), // ~60% opacity
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (hasTitle)
            Text(
              photo.title!,
              style: const TextStyle(
                color: KinfolkColors.softCream,
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
          if (hasDate)
            Padding(
              padding: EdgeInsets.only(top: hasTitle ? 4 : 0),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.calendar_today,
                    color: KinfolkColors.sageGray,
                    size: 12,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    photo.dateTaken!,
                    style: const TextStyle(
                      color: KinfolkColors.sageGray,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          if (hasLocation)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.location_on,
                    color: KinfolkColors.sageGray,
                    size: 12,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    photo.location!,
                    style: const TextStyle(
                      color: KinfolkColors.sageGray,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// Displays the current photo number out of total.
class _PhotoCounter extends StatelessWidget {
  final int current;
  final int total;

  const _PhotoCounter({required this.current, required this.total});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withAlpha(153),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        '$current / $total',
        style: const TextStyle(color: KinfolkColors.sageGray, fontSize: 12),
      ),
    );
  }
}

/// A brief hint that fades out after a few seconds.
class _TapHint extends StatefulWidget {
  const _TapHint();

  @override
  State<_TapHint> createState() => _TapHintState();
}

class _TapHintState extends State<_TapHint>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    );
    _opacity = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.0), weight: 10),
      TweenSequenceItem(tween: ConstantTween(1.0), weight: 50),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.0), weight: 40),
    ]).animate(_controller);
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _opacity,
      child: const Center(
        child: Text(
          'Tap anywhere to exit',
          style: TextStyle(color: KinfolkColors.sageGray, fontSize: 14),
        ),
      ),
    );
  }
}

/// Shown when photos fail to load.
class _ErrorDisplay extends StatelessWidget {
  final String message;

  const _ErrorDisplay({required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.photo_library_outlined,
              color: KinfolkColors.sageGray,
              size: 64,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: KinfolkColors.sageGray,
                fontSize: 16,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Tap to go back',
              style: TextStyle(
                color: KinfolkColors.warmClay.withAlpha(179),
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
