import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Kinfolk typography scale.
///
/// Primary font: Inter. Scale sourced from brand/BRAND.md.
class KinfolkTypography {
  KinfolkTypography._();

  static TextTheme buildTextTheme({Color? primaryColor}) {
    final color = primaryColor ?? const Color(0xFFF5F3ED);

    return GoogleFonts.interTextTheme(
      TextTheme(
        // Display: 48px / 600 weight
        displayLarge: GoogleFonts.inter(
          fontSize: 48,
          fontWeight: FontWeight.w600,
          color: color,
          letterSpacing: -0.5,
        ),
        // H1: 36px / 600 weight
        displayMedium: GoogleFonts.inter(
          fontSize: 36,
          fontWeight: FontWeight.w600,
          color: color,
          letterSpacing: -0.25,
        ),
        // H2: 28px / 600 weight
        displaySmall: GoogleFonts.inter(
          fontSize: 28,
          fontWeight: FontWeight.w600,
          color: color,
        ),
        // H3: 22px / 500 weight
        headlineLarge: GoogleFonts.inter(
          fontSize: 22,
          fontWeight: FontWeight.w500,
          color: color,
        ),
        // Body: 16px / 400 weight
        bodyLarge: GoogleFonts.inter(
          fontSize: 16,
          fontWeight: FontWeight.w400,
          color: color,
          height: 1.5,
        ),
        // Small: 14px / 400 weight
        bodyMedium: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: FontWeight.w400,
          color: color,
          height: 1.4,
        ),
        // Caption: 12px / 400 weight
        bodySmall: GoogleFonts.inter(
          fontSize: 12,
          fontWeight: FontWeight.w400,
          color: color.withAlpha(179),
          height: 1.3,
        ),
        // Button / Label: 14px / 500 weight
        labelLarge: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: color,
          letterSpacing: 0.1,
        ),
      ),
    );
  }
}
