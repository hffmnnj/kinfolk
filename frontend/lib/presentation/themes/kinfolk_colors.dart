import 'package:flutter/material.dart';

/// Kinfolk brand color palette.
///
/// All hex values sourced from brand/BRAND.md.
class KinfolkColors {
  KinfolkColors._();

  // Primary colors
  static const Color warmClay = Color(0xFFD4A574);
  static const Color deepCharcoal = Color(0xFF2A2A2E);
  static const Color softCream = Color(0xFFF5F3ED);

  // Dark mode card surface
  static const Color darkCard = Color(0xFF35353A);

  // Secondary colors
  static const Color forestGreen = Color(0xFF4A7C59);
  static const Color skyBlue = Color(0xFF7BA7BC);
  static const Color sunsetOrange = Color(0xFFE07856);
  static const Color sageGray = Color(0xFF9CA3A8);

  // Semantic aliases
  static const Color success = forestGreen;
  static const Color info = skyBlue;
  static const Color warning = sunsetOrange;
  static const Color secondary = sageGray;
}

/// Kinfolk spacing constants built on a 4px base unit.
class KinfolkSpacing {
  KinfolkSpacing._();

  static const double xxs = 4.0;
  static const double xs = 8.0;
  static const double sm = 12.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;
  static const double xxxl = 64.0;
}
