import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/main.dart';

void main() {
  testWidgets('app boots into the Splash screen showing the wordmark', (
    tester,
  ) async {
    await tester.pumpWidget(const ProviderScope(child: VarOsApp()));
    await tester.pump();

    expect(find.text('VAR OS'), findsOneWidget);
  });
}
