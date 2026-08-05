import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/design_system/var_colors.dart';
import 'package:var_os_app/design_system/var_palette.dart';
import 'package:var_os_app/design_system/var_theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<VarPalette> paletteUnder(WidgetTester tester, ThemeData theme) async {
    late VarPalette resolved;
    await tester.pumpWidget(
      MaterialApp(
        theme: theme,
        home: Builder(
          builder: (context) {
            resolved = context.varColors;
            return const SizedBox.shrink();
          },
        ),
      ),
    );
    return resolved;
  }

  testWidgets('resolves the dark palette under the dark theme', (tester) async {
    final palette = await paletteUnder(tester, VarTheme.dark);

    expect(palette.textPrimary, VarColors.textPrimaryDark);
    expect(palette.bgPrimary, VarColors.bgPrimaryDark);
    expect(palette.signalLow, VarColors.signalLowDark);
  });

  testWidgets('resolves the light palette under the light theme', (
    tester,
  ) async {
    // The whole point of the extension: before it existed every screen named
    // the dark constant directly, so light mode rendered dark-on-light.
    final palette = await paletteUnder(tester, VarTheme.light);

    expect(palette.textPrimary, VarColors.textPrimaryLight);
    expect(palette.bgPrimary, VarColors.bgPrimaryLight);
    expect(palette.signalLow, VarColors.signalLowLight);
  });

  testWidgets('falls back to the designed-first palette with no VarTheme', (
    tester,
  ) async {
    // A widget test that wraps a screen in a bare `MaterialApp` still
    // renders, instead of throwing on a missing extension.
    final palette = await paletteUnder(tester, ThemeData());

    expect(palette.textPrimary, VarColors.textPrimaryDark);
  });

  test('lerp moves every token, so a theme switch animates as one', () {
    final midpoint = VarPalette.dark.lerp(VarPalette.light, 1.0);

    expect(midpoint.textPrimary, VarColors.textPrimaryLight);
    expect(midpoint.divider, VarColors.dividerLight);
    expect(midpoint.accentPrimary, VarColors.accentPrimaryLight);
  });
}
