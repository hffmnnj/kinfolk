import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/photo.dart';
import '../../infrastructure/services/photo_service.dart';

/// Transition style for the photo frame slideshow.
enum PhotoTransitionType { fade, slide }

/// Immutable state for the photo frame slideshow.
class PhotoFrameState {
  final List<Photo> photos;
  final int currentPhotoIndex;
  final bool isPlaying;
  final PhotoTransitionType transitionType;
  final int durationSeconds;
  final bool isLoading;
  final String? error;

  const PhotoFrameState({
    this.photos = const [],
    this.currentPhotoIndex = 0,
    this.isPlaying = false,
    this.transitionType = PhotoTransitionType.fade,
    this.durationSeconds = 30,
    this.isLoading = false,
    this.error,
  });

  PhotoFrameState copyWith({
    List<Photo>? photos,
    int? currentPhotoIndex,
    bool? isPlaying,
    PhotoTransitionType? transitionType,
    int? durationSeconds,
    bool? isLoading,
    String? error,
  }) {
    return PhotoFrameState(
      photos: photos ?? this.photos,
      currentPhotoIndex: currentPhotoIndex ?? this.currentPhotoIndex,
      isPlaying: isPlaying ?? this.isPlaying,
      transitionType: transitionType ?? this.transitionType,
      durationSeconds: durationSeconds ?? this.durationSeconds,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }

  /// The currently displayed photo, or null when the list is empty.
  Photo? get currentPhoto =>
      photos.isNotEmpty ? photos[currentPhotoIndex] : null;
}

/// Manages photo frame slideshow state: loading, auto-advance, and navigation.
class PhotoFrameNotifier extends StateNotifier<PhotoFrameState> {
  final PhotoService _photoService;
  Timer? _advanceTimer;

  PhotoFrameNotifier({PhotoService? photoService})
    : _photoService = photoService ?? PhotoService(),
      super(const PhotoFrameState());

  /// Load photos from the given directory and start the slideshow.
  Future<void> activate({
    String directory = '~/Pictures',
    PhotoTransitionType transitionType = PhotoTransitionType.fade,
    int durationSeconds = 30,
  }) async {
    // Clamp duration to the allowed range.
    final clampedDuration = durationSeconds.clamp(10, 60);

    state = state.copyWith(
      isLoading: true,
      transitionType: transitionType,
      durationSeconds: clampedDuration,
      error: null,
    );

    try {
      final photos = await _photoService.loadPhotos(directory);

      if (photos.isEmpty) {
        state = state.copyWith(
          isLoading: false,
          isPlaying: false,
          error: 'No photos found in $directory',
        );
        return;
      }

      state = state.copyWith(
        photos: photos,
        currentPhotoIndex: 0,
        isPlaying: true,
        isLoading: false,
      );

      _startAutoAdvance();
    } catch (e) {
      debugPrint('PhotoFrameNotifier: failed to load photos: $e');
      state = state.copyWith(
        isLoading: false,
        isPlaying: false,
        error: 'Failed to load photos: $e',
      );
    }
  }

  /// Stop the slideshow and reset state.
  void deactivate() {
    _stopAutoAdvance();
    state = const PhotoFrameState();
  }

  /// Advance to the next photo, looping back to the start.
  void nextPhoto() {
    if (state.photos.isEmpty) return;
    final nextIndex = (state.currentPhotoIndex + 1) % state.photos.length;
    state = state.copyWith(currentPhotoIndex: nextIndex);
    _restartAutoAdvance();
  }

  /// Go back to the previous photo, looping to the end.
  void previousPhoto() {
    if (state.photos.isEmpty) return;
    final prevIndex =
        (state.currentPhotoIndex - 1 + state.photos.length) %
        state.photos.length;
    state = state.copyWith(currentPhotoIndex: prevIndex);
    _restartAutoAdvance();
  }

  void _startAutoAdvance() {
    _stopAutoAdvance();
    _advanceTimer = Timer.periodic(
      Duration(seconds: state.durationSeconds),
      (_) => nextPhoto(),
    );
  }

  void _restartAutoAdvance() {
    if (state.isPlaying) {
      _startAutoAdvance();
    }
  }

  void _stopAutoAdvance() {
    _advanceTimer?.cancel();
    _advanceTimer = null;
  }

  @override
  void dispose() {
    _stopAutoAdvance();
    super.dispose();
  }
}

/// Global provider for the photo frame slideshow.
final photoFrameProvider =
    StateNotifierProvider<PhotoFrameNotifier, PhotoFrameState>((ref) {
      return PhotoFrameNotifier();
    });
