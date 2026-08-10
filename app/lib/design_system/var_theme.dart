import 'package:flutter/material.dart';

import 'var_colors.dart';
import 'var_palette.dart';
import 'var_typography.dart';

/// Assembles the design tokens (`VarColors`, `VarTypography`) into Flutter's
/// `ThemeData` — the only place in the app that should construct a
/// `ThemeData` directly; screens consume tokens via `Theme.of(context)`,
/// never by re-hardcoding hex values (docs/UX_DESIGN.md §1.1: colors
/// represent probability/alignment, never "gratuitous decoration").
class VarTheme {
  const VarTheme._();

  static ThemeData get dark =>
      _build(VarColors.dark, VarColors.bgPrimaryDark, VarPalette.dark);

  static ThemeData get light =>
      _build(VarColors.light, VarColors.bgPrimaryLight, VarPalette.light);

  static ThemeData _build(
    ColorScheme scheme,
    Color scaffoldBackground,
    VarPalette palette,
  ) {
    final textTheme = VarTypography.textTheme(
      scheme.onSurface,
      scheme.onSurface,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      // Everything `ColorScheme` has no slot for — the signal scale, the
      // divider, the elevated surface — rides here (see `VarPalette`).
      extensions: [palette],
      scaffoldBackgroundColor: scaffoldBackground,
      textTheme: textTheme,
      dividerColor: palette.divider,
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size.fromHeight(44), // VarSpacing.minTouchTarget
          backgroundColor: scheme.primary,
          foregroundColor: scheme.onPrimary,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    );
  }
}
