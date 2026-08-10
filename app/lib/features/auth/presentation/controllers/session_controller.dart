import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../data/local_stub_auth_repository.dart';
import '../../data/supabase_auth_repository.dart';
import '../../data/supabase_config.dart';
import '../../domain/auth_repository.dart';

/// Binds the real adapter when the build carries a Supabase project, and
/// the loudly-named stub when it doesn't (see `supabase_config.dart` for
/// why that fallback issues no token rather than faking one).
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  if (!isSupabaseConfigured) return LocalStubAuthRepository();
  return SupabaseAuthRepository(Supabase.instance.client);
});

/// The current access token, following the Supabase session.
///
/// `main.dart` overrides `core`'s `accessTokenProvider` with this, which is
/// how a feature reaches the Dio interceptor without `core/` ever importing
/// a `features/` type — the same one-way rule the rest of the app follows,
/// resolved at composition root instead of by an upward import.
class SessionController extends Notifier<String?> {
  @override
  String? build() {
    final repository = ref.watch(authRepositoryProvider);
    final subscription = repository.accessTokenChanges.listen((token) {
      state = token;
    });
    ref.onDispose(subscription.cancel);
    // A session persisted by the SDK is already restored by the time this
    // reads it, so a returning user never flashes through a signed-out
    // state on launch.
    return repository.currentAccessToken;
  }
}

final sessionControllerProvider = NotifierProvider<SessionController, String?>(
  SessionController.new,
);
