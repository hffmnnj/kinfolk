/// Photo entity — domain layer.
/// Represents a local photo with optional EXIF metadata.
library;

class Photo {
  final String path;
  final String? dateTaken;
  final String? location;
  final String? title;

  const Photo({required this.path, this.dateTaken, this.location, this.title});
}
