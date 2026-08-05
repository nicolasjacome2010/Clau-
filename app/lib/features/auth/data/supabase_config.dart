/// Supabase project credentials, injected at build time exactly like
/// `API_BASE_URL` (docs/ARCHITECTURE.md §3: never hardcoded per
/// environment).
///
/// ```
/// flutter run \
///   --dart-define=SUPABASE_URL=https://xxxx.supabase.co \
///   --dart-define=SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
/// ```
///
/// This key is public by design — it is safe in a client binary (row-level
/// security is what protects data, and the Core API verifies the JWT
/// itself). The *service role* key never belongs in this app.
library;

const String supabaseUrl = String.fromEnvironment('SUPABASE_URL');

const String _publishableKey = String.fromEnvironment(
  'SUPABASE_PUBLISHABLE_KEY',
);

/// Supabase renamed this key from "anon" to "publishable"; both spellings
/// are accepted so an existing `SUPABASE_ANON_KEY` in someone's launch
/// config keeps working instead of silently producing an unconfigured
/// build.
const String supabasePublishableKey = _publishableKey != ''
    ? _publishableKey
    : String.fromEnvironment('SUPABASE_ANON_KEY');

/// Whether this build can talk to a real Supabase project.
///
/// When false the app binds `LocalStubAuthRepository` instead, which issues
/// no token — so every Core API call goes out unauthenticated and comes
/// back 401, and each screen shows its real error state. That is the
/// intended behaviour: a build without credentials should look broken in
/// the way it *is* broken, rather than simulate a logged-in user whose
/// requests all fail for reasons the UI can't explain.
const bool isSupabaseConfigured =
    supabaseUrl != '' && supabasePublishableKey != '';
