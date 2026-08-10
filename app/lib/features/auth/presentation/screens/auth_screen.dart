import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../controllers/auth_controller.dart';

/// Pantalla 3 — Auth (docs/UX_DESIGN.md §2): minimalist email + OAuth
/// login, with a secondary "Probar una simulación primero" path that skips
/// straight to using the product anonymously — the spec is explicit that
/// there must never be a login wall before showing value.
class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  final _emailController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(authControllerProvider, (previous, next) {
      if (next.status == AuthStatus.success) {
        context.go(AppRoutes.home);
      }
    });
    final state = ref.watch(authControllerProvider);
    final controller = ref.read(authControllerProvider.notifier);
    final isSubmitting = state.status == AuthStatus.submitting;

    return Scaffold(
      backgroundColor: context.varColors.bgPrimary,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: VarSpacing.xl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Entra a VAR OS',
                textAlign: TextAlign.center,
                style: VarTypography.display(25, context.varColors.textPrimary),
              ),
              const SizedBox(height: VarSpacing.lg),
              TextField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                style: VarTypography.body(16, context.varColors.textPrimary),
                decoration: const InputDecoration(hintText: 'tu@email.com'),
              ),
              if (state.status == AuthStatus.error) ...[
                const SizedBox(height: VarSpacing.sm),
                Text(
                  state.errorMessage ?? 'Algo salió mal',
                  style: VarTypography.body(12, context.varColors.signalLow),
                ),
              ],
              const SizedBox(height: VarSpacing.md),
              ElevatedButton(
                onPressed: isSubmitting
                    ? null
                    : () => controller.submitEmail(_emailController.text),
                child: const Text('Continuar con email'),
              ),
              const SizedBox(height: VarSpacing.sm),
              OutlinedButton(
                onPressed: isSubmitting
                    ? null
                    : () => controller.submitEmail('oauth-google@stub'),
                child: const Text('Continuar con Google'),
              ),
              const SizedBox(height: VarSpacing.lg),
              TextButton(
                onPressed: isSubmitting ? null : controller.continueAnonymously,
                child: Text(
                  'Probar una simulación primero',
                  style: VarTypography.body(
                    14,
                    context.varColors.textSecondary,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
