import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/design_system/var_breakpoints.dart';

void main() {
  test('classifies widths per docs/UX_DESIGN.md §1.6', () {
    expect(VarBreakpoints.isMobile(599), isTrue);
    expect(VarBreakpoints.isMobile(600), isFalse);
    expect(VarBreakpoints.isTablet(600), isTrue);
    expect(VarBreakpoints.isTablet(1023), isTrue);
    expect(VarBreakpoints.isTablet(1024), isFalse);
    expect(VarBreakpoints.isDesktop(1024), isTrue);
  });
}
