import 'package:flutter/material.dart';

/// Kinfolk typography scale.
///
/// Primary font: Inter (bundled). Scale sourced from brand/BRAND.md.
/// Font files are bundled locally to avoid runtime network requests,
/// preserving user privacy and enabling fully offline operation.
class KinfolkTypography {
  KinfolkTypography._();

  static const String _fontFamily = 'Inter';

  static TextTheme buildTextTheme({Color? primaryColor}) {
    final color = primaryColor ?? const Color(0xFFF5F3ED);

    return TextTheme(
      // Display: 48px / 600 weight
      displayLarge: TextStyle(
        fontFamily: _fontFamily,
        fontSize: 48,
        fontWeight: FontWeight.w600,
        color: color,
        letterSpacing: -0.5,
      ),
      // H1: 36px / 600 weight
      displayMedium: TextStyle(
        fontFamily: _fontFamily,
        fontSize: 36,
        fontWeight: FontWeight.w600,
        color: color,
        letterSpacing: -0.25,
      ),
      // H2: 28px / 600 weight
      displaySmall: TextStyle(
        fontFamily: _fontFamily,
        fontSize: 28,
        fontWeight: FontWeight.w600,
        color: color,
      ),
      // H3: 22px / 500 weight
      headlineLarge: TextStyle(
        fontFamily: _fontFamily,
        fontSize: 22,
        fontWeight: FontWeight.w500,
        color: color,
      ),
      // Body: 16px / 400 weight
      bodyLarge: TextStyle(
        fontFamily: _fontFamily,
        fontSize: 16,
        fontWeight: FontWeight.w400,
        color: color,
        height: 1.5,
      ),
      // Small: 14px / 400 weight
      bodyMedium: TextStyle(
        fontFamily: _fontFamily,
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: color,
        height: 1.4,
      ),
      // Caption: 12px / 400 weight
      bodySmall: TextStyle(
        fontFamily: _fontFamily,
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: color.withAlpha(179),
        height: 1.3,
      ),
      // Button / Label: 14px / 500 weight
      labelLarge: TextStyle(
        fontFamily: _fontFamily,
        fontSize: 14,
        fontWeight: FontWeight.w500,
        color: color,
        letterSpacing: 0.1,
      ),
    );
  }
}
