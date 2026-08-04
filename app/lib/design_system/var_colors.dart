import 'package:flutter/material.dart';

/// Color tokens for the "VAR Design System" (docs/UX_DESIGN.md §1.1).
///
/// Dark is the default, designed-first palette ("el producto se percibe
/// mejor en dark mode, como un instrumento de navegación nocturna") — light
/// is a derived adjustment of contrast/shadows, not a naive inversion.
/// `signal.*` tokens are never the only differentiator between states: every
/// call site must pair them with shape/length and a numeric label (§1.5
/// Accesibilidad), this class only supplies the color half of that pairing.
class VarColors {
  const VarColors._();

  static const ColorScheme dark = ColorScheme(
    brightness: Brightness.dark,
    primary: accentPrimary,
    onPrimary: Color(0xFF0A0B0F),
    secondary: accentPrimary,
    onSecondary: Color(0xFF0A0B0F),
    error: signalLowDark,
    onError: Color(0xFF0A0B0F),
    surface: bgSurfaceDark,
    onSurface: textPrimaryDark,
  );

  static const ColorScheme light = ColorScheme(
    brightness: Brightness.light,
    primary: accentPrimaryLight,
    onPrimary: Color(0xFFFFFFFF),
    secondary: accentPrimaryLight,
    onSecondary: Color(0xFFFFFFFF),
    error: signalLowLight,
    onError: Color(0xFFFFFFFF),
    surface: bgSurfaceLight,
    onSurface: textPrimaryLight,
  );

  // bg.*
  static const Color bgPrimaryDark = Color(0xFF0A0B0F);
  static const Color bgPrimaryLight = Color(0xFFFFFFFF);
  static const Color bgSurfaceDark = Color(0xFF14151C);
  static const Color bgSurfaceLight = Color(0xFFF5F5F7);
  static const Color bgElevatedDark = Color(0xFF1E202B);
  static const Color bgElevatedLight = Color(0xFFFFFFFF);

  // text.*
  static const Color textPrimaryDark = Color(0xFFF5F6FA);
  static const Color textPrimaryLight = Color(0xFF0A0B0F);
  static const Color textSecondaryDark = Color(0xFF9295A6);
  static const Color textSecondaryLight = Color(0xFF5B5E6E);

  // accent.*
  static const Color accentPrimary = Color(0xFF5B8CFF);
  static const Color accentPrimaryLight = Color(0xFF3D6BE0);
  static const List<Color> accentGradient = [
    Color(0xFF5B8CFF),
    Color(0xFFB37BFF),
  ];

  // signal.* — always pair with shape + numeric text, never color alone.
  static const Color signalHighDark = Color(0xFF3DDC97);
  static const Color signalHighLight = Color(0xFF1FA871);
  static const Color signalMediumDark = Color(0xFFF5B942);
  static const Color signalMediumLight = Color(0xFFC98F1E);
  static const Color signalLowDark = Color(0xFFFF6B6B);
  static const Color signalLowLight = Color(0xFFE14A4A);

  static const Color dividerDark = Color(0xFF2A2C38);
  static const Color dividerLight = Color(0xFFE4E4E8);
}
