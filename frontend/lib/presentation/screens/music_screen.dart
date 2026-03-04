import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../application/providers/music_provider.dart';
import '../../domain/entities/track.dart';
import '../themes/kinfolk_colors.dart';
import '../widgets/music_player_widget.dart';

/// Full-screen music experience with now-playing controls, search,
/// and library browsing.
class MusicScreen extends ConsumerStatefulWidget {
  const MusicScreen({super.key});

  @override
  ConsumerState<MusicScreen> createState() => _MusicScreenState();
}

class _MusicScreenState extends ConsumerState<MusicScreen> {
  final _searchController = TextEditingController();
  final _searchFocusNode = FocusNode();

  @override
  void dispose() {
    _searchController.dispose();
    _searchFocusNode.dispose();
    super.dispose();
  }

  void _onSearch(String query) {
    ref.read(musicProvider.notifier).search(query);
  }

  void _clearSearch() {
    _searchController.clear();
    _searchFocusNode.unfocus();
    ref.read(musicProvider.notifier).clearSearch();
  }

  @override
  Widget build(BuildContext context) {
    final music = ref.watch(musicProvider);

    return Scaffold(
      backgroundColor: KinfolkColors.deepCharcoal,
      appBar: AppBar(
        backgroundColor: KinfolkColors.deepCharcoal,
        foregroundColor: KinfolkColors.softCream,
        elevation: 0,
        title: Text(
          'Music',
          style: Theme.of(context).textTheme.displaySmall?.copyWith(
            color: KinfolkColors.softCream,
            fontWeight: FontWeight.w600,
          ),
        ),
        leading: IconButton(
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.arrow_back),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Now-playing widget
              const MusicPlayerWidget(),
              const SizedBox(height: 32),

              // Search bar
              _SearchBar(
                controller: _searchController,
                focusNode: _searchFocusNode,
                onSearch: _onSearch,
                onClear: _clearSearch,
              ),
              const SizedBox(height: 16),

              // Search results or library browse
              if (music.isSearching)
                const _LoadingIndicator()
              else if (music.searchResults.isNotEmpty)
                _SearchResults(tracks: music.searchResults)
              else if (_searchController.text.isEmpty)
                const _LibraryBrowse(),
            ],
          ),
        ),
      ),
    );
  }
}

class _SearchBar extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final ValueChanged<String> onSearch;
  final VoidCallback onClear;

  const _SearchBar({
    required this.controller,
    required this.focusNode,
    required this.onSearch,
    required this.onClear,
  });

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      focusNode: focusNode,
      style: Theme.of(
        context,
      ).textTheme.bodyLarge?.copyWith(color: KinfolkColors.softCream),
      decoration: InputDecoration(
        hintText: 'Search tracks, artists, albums...',
        hintStyle: Theme.of(
          context,
        ).textTheme.bodyLarge?.copyWith(color: KinfolkColors.sageGray),
        prefixIcon: const Icon(Icons.search, color: KinfolkColors.sageGray),
        suffixIcon:
            controller.text.isNotEmpty
                ? IconButton(
                  onPressed: onClear,
                  icon: const Icon(Icons.close, color: KinfolkColors.sageGray),
                )
                : null,
        filled: true,
        fillColor: KinfolkColors.darkCard,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
      ),
      textInputAction: TextInputAction.search,
      onSubmitted: onSearch,
    );
  }
}

class _SearchResults extends ConsumerWidget {
  final List<Track> tracks;

  const _SearchResults({required this.tracks});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${tracks.length} result${tracks.length == 1 ? '' : 's'}',
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: KinfolkColors.sageGray),
        ),
        const SizedBox(height: 8),
        ...tracks.map(
          (track) => _TrackListTile(
            track: track,
            onTap: () {
              ref.read(musicProvider.notifier).play(uri: track.uri);
            },
          ),
        ),
      ],
    );
  }
}

class _TrackListTile extends StatelessWidget {
  final Track track;
  final VoidCallback onTap;

  const _TrackListTile({required this.track, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
        child: Row(
          children: [
            // Small album art placeholder
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: KinfolkColors.warmClay.withAlpha(38),
                borderRadius: BorderRadius.circular(8),
              ),
              child:
                  track.albumArtUrl != null
                      ? ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.network(
                          track.albumArtUrl!,
                          width: 44,
                          height: 44,
                          fit: BoxFit.cover,
                          errorBuilder:
                              (_, __, ___) => const Icon(
                                Icons.music_note,
                                color: KinfolkColors.warmClay,
                                size: 22,
                              ),
                        ),
                      )
                      : const Icon(
                        Icons.music_note,
                        color: KinfolkColors.warmClay,
                        size: 22,
                      ),
            ),
            const SizedBox(width: 12),
            // Track info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    track.title,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: KinfolkColors.softCream,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    '${track.artist} — ${track.album}',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: KinfolkColors.sageGray,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            // Duration
            Text(
              track.durationDisplay,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: KinfolkColors.sageGray),
            ),
          ],
        ),
      ),
    );
  }
}

class _LibraryBrowse extends StatelessWidget {
  const _LibraryBrowse();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Library',
          style: Theme.of(context).textTheme.headlineLarge?.copyWith(
            color: KinfolkColors.softCream,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 12),
        _LibraryTile(
          icon: Icons.queue_music,
          title: 'Spotify',
          subtitle: 'Search and play from Spotify',
        ),
        _LibraryTile(
          icon: Icons.folder,
          title: 'Local Files',
          subtitle: 'MP3, FLAC, OGG from local library',
        ),
      ],
    );
  }
}

class _LibraryTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _LibraryTile({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      color: KinfolkColors.darkCard,
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Icon(icon, color: KinfolkColors.warmClay, size: 24),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: KinfolkColors.softCream,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: KinfolkColors.sageGray,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.chevron_right,
              color: KinfolkColors.sageGray,
              size: 20,
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadingIndicator extends StatelessWidget {
  const _LoadingIndicator();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 32),
      child: Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(KinfolkColors.warmClay),
          strokeWidth: 2,
        ),
      ),
    );
  }
}
