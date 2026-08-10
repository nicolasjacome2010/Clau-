/// A suggested starter goal, offered both in Onboarding's Paso 3
/// (docs/UX_DESIGN.md Pantalla 2) and in Perfil de Objetivos (Pantalla 13,
/// whose spec says "mismos que onboarding") — which is why it lives in
/// `goals/` rather than inside either screen's feature.
///
/// These mirror the seed goal names the backend's `goals` bounded context
/// expects (docs/DATABASE.md §2.3) — kept as a plain value type here, not a
/// backend model import, since this app never imports backend code across
/// the network boundary (same "own DTOs" convention as every backend
/// service-to-service port in this repo).
class GoalOption {
  const GoalOption({required this.id, required this.label});

  final String id;
  final String label;

  static const List<GoalOption> seedOptions = [
    GoalOption(id: 'financial_stability', label: 'Estabilidad financiera'),
    GoalOption(id: 'career_growth', label: 'Crecimiento profesional'),
    GoalOption(id: 'relationships', label: 'Relaciones'),
    GoalOption(id: 'freedom_autonomy', label: 'Libertad/autonomía'),
    GoalOption(id: 'health_wellbeing', label: 'Salud/bienestar'),
  ];
}
