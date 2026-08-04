import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/local_stub_auth_repository.dart';
import '../../domain/auth_repository.dart';

enum AuthStatus { idle, submitting, success, error }

class AuthState {
  const AuthState({this.status = AuthStatus.idle, this.errorMessage});

  final AuthStatus status;
  final String? errorMessage;

  AuthState copyWith({AuthStatus? status, String? errorMessage}) {
    return AuthState(status: status ?? this.status, errorMessage: errorMessage);
  }
}

/// See `auth_repository.dart` for why this resolves to a stub today.
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => LocalStubAuthRepository(),
);

class AuthController extends Notifier<AuthState> {
  @override
  AuthState build() => const AuthState();

  Future<void> submitEmail(String email) async {
    state = state.copyWith(status: AuthStatus.submitting);
    try {
      await ref.read(authRepositoryProvider).signInWithEmail(email);
      state = state.copyWith(status: AuthStatus.success);
    } catch (error) {
      state = state.copyWith(
        status: AuthStatus.error,
        errorMessage: error.toString(),
      );
    }
  }

  Future<void> continueAnonymously() async {
    state = state.copyWith(status: AuthStatus.submitting);
    try {
      await ref.read(authRepositoryProvider).continueAnonymously();
      state = state.copyWith(status: AuthStatus.success);
    } catch (error) {
      state = state.copyWith(
        status: AuthStatus.error,
        errorMessage: error.toString(),
      );
    }
  }
}

final authControllerProvider = NotifierProvider<AuthController, AuthState>(
  AuthController.new,
);
