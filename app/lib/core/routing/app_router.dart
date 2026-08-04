import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/screens/auth_screen.dart';
import '../../features/clarification/presentation/screens/clarification_screen.dart';
import '../../features/decisions/domain/decision_ref.dart';
import '../../features/home/presentation/screens/home_screen.dart';
import '../../features/onboarding/presentation/screens/onboarding_screen.dart';
import '../../features/simulations/presentation/screens/decision_result_screen.dart';
import '../../features/splash/presentation/splash_screen.dart';
import 'app_routes.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: AppRoutes.splash,
    routes: [
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: AppRoutes.onboarding,
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: AppRoutes.auth,
        builder: (context, state) => const AuthScreen(),
      ),
      GoRoute(
        path: AppRoutes.home,
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: AppRoutes.decisionResult,
        builder: (context, state) {
          final decision = state.extra! as DecisionRef;
          return DecisionResultScreen(
            decisionId: decision.id,
            title: decision.title,
          );
        },
      ),
      GoRoute(
        path: AppRoutes.clarification,
        builder: (context, state) =>
            ClarificationScreen(rawInput: state.extra! as String),
      ),
    ],
  );
});
