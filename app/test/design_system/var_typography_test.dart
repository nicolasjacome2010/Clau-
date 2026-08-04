import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:var_os_app/design_system/var_typography.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  // Never fetch fonts over the network in tests — assert on the requested
  // size/weight/color, not on which bytes google_fonts managed to load.
  GoogleFonts.config.allowRuntimeFetching = false;

  test('type scale matches docs/UX_DESIGN.md §1.2 (base 16px, ratio 1.25)', () {
    expect(VarTypography.scale, [12, 14, 16, 20, 25, 31, 39, 49]);
  });

  test('display/body/mono styles carry the requested size and color', () {
    const color = Color(0xFFF5F6FA);
    expect(VarTypography.display(25, color).fontSize, 25);
    expect(VarTypography.body(16, color).fontSize, 16);
    expect(VarTypography.mono(14, color).fontSize, 14);
    expect(VarTypography.display(25, color).color, color);
  });
}
