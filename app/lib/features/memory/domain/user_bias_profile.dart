/// One pattern the system has detected about the user (docs/REALITY_ENGINE.md
/// Agente 5/12) — `bias` is free-form, human-readable text the LLM wrote
/// ("aversión a la pérdida", "sesgo de confirmación"), never a code, so it's
/// rendered as-is: no client-side translation table to keep in sync.
class BiasObservation {
  const BiasObservation({
    required this.bias,
    required this.score,
    required this.occurrences,
  });

  final String bias;
  final double score;
  final int occurrences;
}

/// Mirrors `UserBiasProfileResponse` (backend/src/core_api/memory/api/
/// schemas.py) field for field, as this app's own plain value type.
class UserBiasProfile {
  const UserBiasProfile({
    required this.biases,
    required this.calibrationScore,
    required this.updatedAt,
  });

  final List<BiasObservation> biases;
  final double calibrationScore;
  final DateTime? updatedAt;
}
