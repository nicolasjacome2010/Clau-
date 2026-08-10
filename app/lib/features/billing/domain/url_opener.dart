/// Opens an external URL — Stripe Checkout or the Customer Portal.
///
/// A port rather than a direct `url_launcher` call so the screens stay
/// testable: `url_launcher` needs a platform channel, and a widget test has
/// no platform. Same Dependency Inversion the rest of the app uses for
/// anything that leaves the process.
abstract class UrlOpener {
  /// Returns false when the platform refused to open it (no browser, an
  /// unhandled scheme) — the caller must say so rather than leave the user
  /// staring at a button that did nothing.
  Future<bool> open(String url);
}
