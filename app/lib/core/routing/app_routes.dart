/// Route paths, centralized so screens navigate by name, never by
/// hand-typed string literals scattered across the codebase.
abstract final class AppRoutes {
  static const splash = '/';
  static const onboarding = '/onboarding';
  static const auth = '/auth';
  static const home = '/home';

  /// Pushed on top of Home with the captured decision text as `extra`.
  static const clarification = '/clarification';

  /// Pushed with a `DecisionRef` (id + title) as `extra`.
  static const decisionResult = '/decision-result';
}
