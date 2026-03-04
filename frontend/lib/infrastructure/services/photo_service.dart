import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;

import '../../domain/entities/photo.dart';

/// Scans a local directory for image files and returns [Photo] entities
/// with best-effort metadata extracted from filenames.
///
/// Full EXIF parsing via the backend API is deferred to a later milestone;
/// for now, dates are inferred from common filename patterns
/// (e.g. `2025-06-15_sunset.jpg`, `IMG_20250615_120000.jpg`).
class PhotoService {
  static const _supportedExtensions = {
    '.jpg',
    '.jpeg',
    '.png',
    '.heic',
    '.webp',
  };

  /// Date patterns commonly embedded in photo filenames.
  static final _datePatterns = [
    // YYYY-MM-DD anywhere in the name
    RegExp(r'(\d{4})-(\d{2})-(\d{2})'),
    // YYYYMMDD (e.g. IMG_20250615_120000)
    RegExp(r'(\d{4})(\d{2})(\d{2})'),
  ];

  /// Scans [directoryPath] for supported image files.
  ///
  /// Returns an empty list when the directory does not exist or is
  /// inaccessible.  Runs the heavy I/O in an isolate via [compute].
  Future<List<Photo>> loadPhotos(String directoryPath) async {
    final resolved = directoryPath.replaceFirst(
      '~',
      Platform.environment['HOME'] ?? '',
    );
    final dir = Directory(resolved);

    if (!await dir.exists()) {
      debugPrint('PhotoService: directory not found: $resolved');
      return const [];
    }

    // Offload directory listing to an isolate to keep the UI thread free.
    final paths = await compute(_scanDirectory, resolved);
    return paths.map(_photoFromPath).toList();
  }

  /// Pure function executed in an isolate — lists image file paths.
  static List<String> _scanDirectory(String dirPath) {
    final dir = Directory(dirPath);
    final entries = <String>[];

    try {
      for (final entity in dir.listSync(recursive: true, followLinks: false)) {
        if (entity is File) {
          final ext = p.extension(entity.path).toLowerCase();
          if (_supportedExtensions.contains(ext)) {
            entries.add(entity.path);
          }
        }
      }
    } catch (e) {
      // Silently skip inaccessible sub-directories.
    }

    entries.sort();
    return entries;
  }

  /// Builds a [Photo] from a file path, extracting date from the filename.
  static Photo _photoFromPath(String filePath) {
    final basename = p.basenameWithoutExtension(filePath);
    final dateTaken = _extractDate(basename);
    final title = _humanTitle(basename);

    return Photo(path: filePath, dateTaken: dateTaken, title: title);
  }

  /// Attempts to extract a human-readable date from the filename.
  static String? _extractDate(String basename) {
    for (final pattern in _datePatterns) {
      final match = pattern.firstMatch(basename);
      if (match != null) {
        final year = match.group(1)!;
        final month = match.group(2)!;
        final day = match.group(3)!;

        // Basic sanity check
        final m = int.tryParse(month) ?? 0;
        final d = int.tryParse(day) ?? 0;
        if (m >= 1 && m <= 12 && d >= 1 && d <= 31) {
          return '$year-$month-$day';
        }
      }
    }
    return null;
  }

  /// Converts a filename into a friendlier display title.
  static String _humanTitle(String basename) {
    // Strip common camera prefixes
    var cleaned = basename
        .replaceAll(RegExp(r'^IMG_'), '')
        .replaceAll(RegExp(r'^DSC_?'), '')
        .replaceAll(RegExp(r'^DCIM_?'), '')
        .replaceAll(RegExp(r'^\d{8}_\d{6}_?'), '')
        .replaceAll(RegExp(r'^\d{4}-\d{2}-\d{2}_?'), '');

    // Replace underscores/hyphens with spaces
    cleaned = cleaned.replaceAll(RegExp(r'[_-]'), ' ').trim();

    if (cleaned.isEmpty) return basename;
    return cleaned;
  }
}
