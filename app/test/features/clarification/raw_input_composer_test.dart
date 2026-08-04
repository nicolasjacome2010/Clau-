import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/clarification/domain/raw_input_composer.dart';

void main() {
  test('appends answered context below the untouched original text', () {
    final result = composeRawInput(
      originalInput: '¿Debo aceptar la oferta?',
      answers: const {
        'vertical': 'career',
        'timeframe': 'Menos de 1 semana',
        'options_in_mind': 'Dos o más opciones',
      },
    );

    expect(
      result,
      '¿Debo aceptar la oferta?\n\n'
      'Contexto de clarificación:\n'
      '- Plazo para decidir: Menos de 1 semana\n'
      '- Opciones concretas que ya considera: Dos o más opciones',
    );
  });

  test('never echoes the vertical into the context block', () {
    final result = composeRawInput(
      originalInput: 'Texto',
      answers: const {'vertical': 'finance'},
    );

    expect(result, 'Texto');
    expect(result, isNot(contains('finance')));
  });

  test('trims the original input', () {
    expect(
      composeRawInput(originalInput: '  Texto  ', answers: const {}),
      'Texto',
    );
  });
}
