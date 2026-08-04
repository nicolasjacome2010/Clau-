import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../design_system/var_colors.dart';
import '../../../../design_system/var_motion.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../shared/presentation/step_indicator.dart';
import '../controllers/onboarding_controller.dart';
import '../widgets/goal_selection_step.dart';
import '../widgets/intro_slide.dart';

/// Pantalla 2 — Onboarding (docs/UX_DESIGN.md §2): 3 steps, the last of
/// which captures initial life goals. Transition style is fade + slight
/// scale per spec ("no swipe horizontal genérico") — implemented here with
/// an `AnimatedSwitcher` rather than a `PageView`, since a `PageView`
/// implies the generic horizontal-swipe feel the spec explicitly rejects.
class OnboardingScreen extends ConsumerWidget {
  const OnboardingScreen({super.key});

  static const _headlines = [
    'No predecimos tu futuro. Simulamos tus posibles futuros para que\nelijas con claridad.',
    'Cada decisión abre líneas de tiempo distintas. Te ayudamos a\nverlas antes de elegir.',
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(onboardingControllerProvider);
    final controller = ref.read(onboardingControllerProvider.notifier);

    return Scaffold(
      backgroundColor: VarColors.bgPrimaryDark,
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: AnimatedSwitcher(
                duration: VarMotion.screenTransitionMax,
                switchInCurve: VarMotion.enter,
                switchOutCurve: VarMotion.exit,
                transitionBuilder: (child, animation) => FadeTransition(
                  opacity: animation,
                  child: ScaleTransition(
                    scale: Tween(begin: 0.98, end: 1.0).animate(animation),
                    child: child,
                  ),
                ),
                child: KeyedSubtree(
                  key: ValueKey(state.step),
                  child: state.step < _headlines.length
                      ? IntroSlide(headline: _headlines[state.step])
                      : const GoalSelectionStep(),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: VarSpacing.lg),
              child: StepIndicator(
                stepCount: OnboardingState.totalSteps,
                currentStep: state.step,
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: VarSpacing.xl,
                vertical: VarSpacing.md,
              ),
              child: ElevatedButton(
                onPressed: () {
                  if (state.isLastStep) {
                    context.go(AppRoutes.auth);
                  } else {
                    controller.nextStep();
                  }
                },
                child: Text(state.isLastStep ? 'Continuar' : 'Continuar →'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
