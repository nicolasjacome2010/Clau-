/// Spacing tokens. Not explicitly enumerated in docs/UX_DESIGN.md, so this
/// follows the same base-4 rhythm implied by the type scale (§1.2) — kept
/// as a small, closed set rather than arbitrary magic numbers scattered
/// across widgets.
class VarSpacing {
  const VarSpacing._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;

  /// docs/UX_DESIGN.md §1.5: minimum touch target size.
  static const double minTouchTarget = 44;
}
