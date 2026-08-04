import 'package:flutter/animation.dart';

/// Motion tokens (docs/UX_DESIGN.md §1.4).
///
/// Principle: every animation must communicate system state, never be
/// purely decorative — consistent with the PRD's "no engagement loops"
/// stance. `pipelineStreaming` is the one deliberate exception to the
/// duration ceiling below, because a long-running animation there
/// communicates real work (the Reality Engine pipeline), not decoration.
class VarMotion {
  const VarMotion._();

  /// "ease-out expresivo" — entrances.
  static const Curve enter = Cubic(0.22, 1, 0.36, 1);

  /// Exits.
  static const Curve exit = Cubic(0.4, 0, 1, 1);

  static const Duration microMin = Duration(milliseconds: 120);
  static const Duration microMax = Duration(milliseconds: 180);
  static const Duration screenTransitionMin = Duration(milliseconds: 250);
  static const Duration screenTransitionMax = Duration(milliseconds: 350);

  /// Ceiling most animations should respect — see class doc for the one
  /// documented exception (pipeline streaming, up to ~20s).
  static const Duration nonStreamingCeiling = screenTransitionMax;
}
