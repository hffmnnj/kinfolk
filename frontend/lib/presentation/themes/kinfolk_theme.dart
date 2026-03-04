import 'package:flutter/material.dart';
import 'kinfolk_colors.dart';
import 'kinfolk_typography.dart';

/// Kinfolk Material 3 theme with dark (primary) and light variants.
///
/// Dark theme: Deep Charcoal background, Warm Clay accent, Soft Cream text.
/// Light theme: Soft Cream background, Deep Charcoal text, Warm Clay accent.
class KinfolkTheme {
  KinfolkTheme._();

  static ThemeData get dark => _buildTheme(isDark: true);
  static ThemeData get light => _buildTheme(isDark: false);

  static ThemeData _buildTheme({required bool isDark}) {
    final background = isDark
        ? KinfolkColors.deepCharcoal
        : KinfolkColors.softCream;
    final surface = isDark ? KinfolkColors.darkCard : Colors.white;
    final onBackground = isDark
        ? KinfolkColors.softCream
        : KinfolkColors.deepCharcoal;
    final textColor = isDark
        ? KinfolkColors.softCream
        : KinfolkColors.deepCharcoal;

    final colorScheme = ColorScheme(
      brightness: isDark ? Brightness.dark : Brightness.light,
      primary: KinfolkColors.warmClay,
      onPrimary: Colors.white,
      secondary: KinfolkColors.forestGreen,
      onSecondary: Colors.white,
      error: KinfolkColors.sunsetOrange,
      onError: Colors.white,
      surface: surface,
      onSurface: onBackground,
      tertiary: KinfolkColors.skyBlue,
      onTertiary: Colors.white,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: background,
      textTheme: KinfolkTypography.buildTextTheme(primaryColor: textColor),

      // Card theme: 12px border radius, subtle elevation
      cardTheme: CardThemeData(
        color: surface,
        elevation: 2,
        shadowColor: Colors.black.withAlpha(51),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        margin: const EdgeInsets.all(8),
      ),

      // Primary button: Warm Clay fill, white text, 8px radius
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: KinfolkColors.warmClay,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        ),
      ),

      // Outlined button: transparent fill, Warm Clay border
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: KinfolkColors.warmClay,
          side: const BorderSide(color: KinfolkColors.warmClay),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),

      // AppBar: matches scaffold background, no elevation
      appBarTheme: AppBarTheme(
        backgroundColor: background,
        foregroundColor: textColor,
        elevation: 0,
        scrolledUnderElevation: 2,
      ),

      // Icons: Warm Clay accent
      iconTheme: const IconThemeData(color: KinfolkColors.warmClay, size: 24),

      // Dividers: subtle sage gray
      dividerTheme: DividerThemeData(
        color: KinfolkColors.sageGray.withAlpha(77),
        thickness: 1,
      ),
    );
  }
}
