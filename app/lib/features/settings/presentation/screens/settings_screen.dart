import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../design_system/var_palette.dart';
import '../../../../design_system/var_spacing.dart';
import '../../../../design_system/var_typography.dart';
import '../controllers/settings_controller.dart';

/// Pantalla 15 — Ajustes (docs/UX_DESIGN.md).
///
/// The spec lists four sections. Only appearance is actually wired, and the
/// other three say why rather than pretending: privacy needs data
/// export/delete endpoints the Core API doesn't have, close-the-loop
/// reminders need a notification service and a scheduler that don't exist,
/// and the language switch needs a localization pass this app hasn't had
/// (every string is Spanish, in source). Listing them as "próximamente" is
/// the honest shape of a settings screen mid-build — a switch that toggles
/// nothing would be worse than an absence.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeModeControllerProvider);

    return Scaffold(
      backgroundColor: context.varColors.bgPrimary,
      appBar: AppBar(
        backgroundColor: context.varColors.bgPrimary,
        title: Text(
          'Ajustes',
          style: VarTypography.body(16, context.varColors.textPrimary),
        ),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(VarSpacing.lg),
          children: [
            _SectionTitle('Apariencia'),
            themeMode.when(
              data: (mode) => _AppearanceChoice(
                selected: mode,
                onSelected: (next) =>
                    ref.read(themeModeControllerProvider.notifier).select(next),
              ),
              loading: () => const Padding(
                padding: EdgeInsets.all(VarSpacing.md),
                child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
              ),
              error: (error, _) => Text(
                'No pudimos leer tu preferencia guardada.',
                style: VarTypography.body(12, context.varColors.signalLow),
              ),
            ),
            const SizedBox(height: VarSpacing.lg),
            _SectionTitle('Suscripción'),
            _SettingsTile(
              title: 'Ver planes y facturación',
              subtitle: 'Tu plan actual, cambios y método de pago.',
              onTap: () => context.push(AppRoutes.subscription),
            ),
            const SizedBox(height: VarSpacing.lg),
            _SectionTitle('Privacidad'),
            const _PendingTile(
              title: 'Exportar mis datos',
              reason:
                  'Falta el endpoint de exportación en el backend. También '
                  'está en Memoria, donde el spec pide que sea visible.',
            ),
            const _PendingTile(
              title: 'Borrar todo mi historial',
              reason: 'Falta el endpoint de borrado en el backend.',
            ),
            const SizedBox(height: VarSpacing.lg),
            _SectionTitle('Notificaciones'),
            const _PendingTile(
              title: 'Recordatorios de cierre de ciclo',
              reason:
                  'Necesita un servicio de notificaciones y un planificador '
                  'que todavía no existen.',
            ),
            const SizedBox(height: VarSpacing.lg),
            _SectionTitle('Idioma'),
            const _PendingTile(
              title: 'Español',
              reason:
                  'La app está solo en español por ahora: cambiar de idioma '
                  'necesita una pasada de localización completa.',
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: VarSpacing.sm),
      child: Text(
        text,
        style: VarTypography.display(16, context.varColors.textPrimary),
      ),
    );
  }
}

class _AppearanceChoice extends StatelessWidget {
  const _AppearanceChoice({required this.selected, required this.onSelected});

  final ThemeMode selected;
  final ValueChanged<ThemeMode> onSelected;

  static const _labels = {
    ThemeMode.system: 'Como el sistema',
    ThemeMode.dark: 'Oscuro',
    ThemeMode.light: 'Claro',
  };

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SegmentedButton<ThemeMode>(
          segments: [
            for (final entry in _labels.entries)
              ButtonSegment<ThemeMode>(
                value: entry.key,
                label: Text(entry.value),
              ),
          ],
          selected: {selected},
          onSelectionChanged: (next) => onSelected(next.first),
          showSelectedIcon: false,
        ),
        const SizedBox(height: VarSpacing.sm),
        Text(
          'Recomendamos el modo oscuro: la app está diseñada primero para '
          'él, como un instrumento de navegación nocturna.',
          style: VarTypography.body(12, context.varColors.textSecondary),
        ),
      ],
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      onTap: onTap,
      title: Text(
        title,
        style: VarTypography.body(14, context.varColors.textPrimary),
      ),
      subtitle: Text(
        subtitle,
        style: VarTypography.body(12, context.varColors.textSecondary),
      ),
      trailing: Icon(
        Icons.chevron_right,
        color: context.varColors.textSecondary,
      ),
    );
  }
}

/// A setting the spec asks for that this build genuinely cannot perform,
/// shown with the reason instead of as a control that does nothing.
class _PendingTile extends StatelessWidget {
  const _PendingTile({required this.title, required this.reason});

  final String title;
  final String reason;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$title, no disponible todavía. $reason',
      child: Padding(
        padding: const EdgeInsets.only(bottom: VarSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: VarTypography.body(
                      14,
                      context.varColors.textSecondary,
                    ),
                  ),
                ),
                Text(
                  'Próximamente',
                  style: VarTypography.body(
                    12,
                    context.varColors.textSecondary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 2),
            Text(
              reason,
              style: VarTypography.body(12, context.varColors.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}
