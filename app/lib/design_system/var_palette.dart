import 'package:flutter/material.dart';

import 'var_colors.dart';

/// The semantic half of the color system, resolved per theme.
///
/// `VarColors` holds the raw values for both palettes; this is what screens
/// actually read, so a widget asks for "the secondary text color" and gets
/// whichever one the current theme calls for. Before this existed every
/// screen named the *dark* constant directly, which quietly made light mode
/// unusable — the tokens were there, nothing consumed them.
///
/// Flutter's `ColorScheme` covers surface/primary/error and no more; the
/// `signal.*` scale and the divider have no slot in it, so they ride along
/// in a `ThemeExtension` rather than being crammed into unrelated roles.
@immutable
class VarPalette extends ThemeExtension<VarPalette> {
  const VarPalette({
    required this.bgPrimary,
    required this.bgSurface,
    required this.bgElevated,
    required this.textPrimary,
    required this.textSecondary,
    required this.accentPrimary,
    required this.signalHigh,
    required this.signalMedium,
    required this.signalLow,
    required this.divider,
  });

  final Color bgPrimary;
  final Color bgSurface;
  final Color bgElevated;
  final Color textPrimary;
  final Color textSecondary;
  final Color accentPrimary;

  /// Never the only differentiator between states (docs/UX_DESIGN.md §1.5):
  /// every call site pairs these with shape, length or a numeric label.
  final Color signalHigh;
  final Color signalMedium;
  final Color signalLow;

  final Color divider;

  static const VarPalette dark = VarPalette(
    bgPrimary: VarColors.bgPrimaryDark,
    bgSurface: VarColors.bgSurfaceDark,
    bgElevated: VarColors.bgElevatedDark,
    textPrimary: VarColors.textPrimaryDark,
    textSecondary: VarColors.textSecondaryDark,
    accentPrimary: VarColors.accentPrimary,
    signalHigh: VarColors.signalHighDark,
    signalMedium: VarColors.signalMediumDark,
    signalLow: VarColors.signalLowDark,
    divider: VarColors.dividerDark,
  );

  static const VarPalette light = VarPalette(
    bgPrimary: VarColors.bgPrimaryLight,
    bgSurface: VarColors.bgSurfaceLight,
    bgElevated: VarColors.bgElevatedLight,
    textPrimary: VarColors.textPrimaryLight,
    textSecondary: VarColors.textSecondaryLight,
    accentPrimary: VarColors.accentPrimaryLight,
    signalHigh: VarColors.signalHighLight,
    signalMedium: VarColors.signalMediumLight,
    signalLow: VarColors.signalLowLight,
    divider: VarColors.dividerLight,
  );

  @override
  VarPalette copyWith({
    Color? bgPrimary,
    Color? bgSurface,
    Color? bgElevated,
    Color? textPrimary,
    Color? textSecondary,
    Color? accentPrimary,
    Color? signalHigh,
    Color? signalMedium,
    Color? signalLow,
    Color? divider,
  }) {
    return VarPalette(
      bgPrimary: bgPrimary ?? this.bgPrimary,
      bgSurface: bgSurface ?? this.bgSurface,
      bgElevated: bgElevated ?? this.bgElevated,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      accentPrimary: accentPrimary ?? this.accentPrimary,
      signalHigh: signalHigh ?? this.signalHigh,
      signalMedium: signalMedium ?? this.signalMedium,
      signalLow: signalLow ?? this.signalLow,
      divider: divider ?? this.divider,
    );
  }

  @override
  VarPalette lerp(ThemeExtension<VarPalette>? other, double t) {
    if (other is! VarPalette) return this;
    return VarPalette(
      bgPrimary: Color.lerp(bgPrimary, other.bgPrimary, t)!,
      bgSurface: Color.lerp(bgSurface, other.bgSurface, t)!,
      bgElevated: Color.lerp(bgElevated, other.bgElevated, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      accentPrimary: Color.lerp(accentPrimary, other.accentPrimary, t)!,
      signalHigh: Color.lerp(signalHigh, other.signalHigh, t)!,
      signalMedium: Color.lerp(signalMedium, other.signalMedium, t)!,
      signalLow: Color.lerp(signalLow, other.signalLow, t)!,
      divider: Color.lerp(divider, other.divider, t)!,
    );
  }
}

extension VarPaletteContext on BuildContext {
  /// The palette of the current theme.
  ///
  /// Falls back to the dark palette when no `VarTheme` is in scope — a
  /// widget test that wraps a screen in a bare `MaterialApp` still renders
  /// with the designed-first palette instead of throwing.
  VarPalette get varColors =>
      Theme.of(this).extension<VarPalette>() ?? VarPalette.dark;
}
