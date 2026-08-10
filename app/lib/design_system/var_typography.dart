import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Typography tokens (docs/UX_DESIGN.md §1.2): a type scale of base 16px,
/// ratio 1.25 — `12/14/16/20/25/31/39/49`.
///
/// Font family notes: "Inter" (body) and "JetBrains Mono" (probability/
/// score figures, IDs) are used as specified. "Fragment" (display/
/// headlines) is not a freely redistributable family; Space Grotesk is
/// substituted as the closest openly-licensed geometric-display face — see
/// the deviation note in `pubspec.yaml` and `app/README.md`.
class VarTypography {
  const VarTypography._();

  static const List<double> scale = [12, 14, 16, 20, 25, 31, 39, 49];

  static TextStyle display(
    double size,
    Color color, {
    FontWeight weight = FontWeight.w600,
  }) => GoogleFonts.spaceGrotesk(
    fontSize: size,
    color: color,
    fontWeight: weight,
    height: 1.15,
  );

  static TextStyle body(
    double size,
    Color color, {
    FontWeight weight = FontWeight.w400,
  }) => GoogleFonts.inter(
    fontSize: size,
    color: color,
    fontWeight: weight,
    height: 1.4,
  );

  static TextStyle mono(
    double size,
    Color color, {
    FontWeight weight = FontWeight.w500,
  }) => GoogleFonts.jetBrainsMono(
    fontSize: size,
    color: color,
    fontWeight: weight,
    height: 1.2,
  );

  static TextTheme textTheme(Color primary, Color secondary) => TextTheme(
    displayLarge: display(scale[7], primary),
    displayMedium: display(scale[6], primary),
    displaySmall: display(scale[5], primary),
    headlineMedium: display(scale[4], primary),
    titleLarge: body(scale[3], primary, weight: FontWeight.w600),
    bodyLarge: body(scale[2], primary),
    bodyMedium: body(scale[1], secondary),
    bodySmall: body(scale[0], secondary),
  );
}
