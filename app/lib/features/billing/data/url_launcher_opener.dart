import 'package:url_launcher/url_launcher.dart';

import '../domain/url_opener.dart';

/// Production `UrlOpener`.
///
/// `LaunchMode.externalApplication` on purpose: Stripe Checkout must run in
/// a real browser, where the user can see the address bar and the padlock.
/// Rendering someone's card form inside an in-app webview hides exactly the
/// signals they'd use to tell a payment page from a phishing page.
class UrlLauncherOpener implements UrlOpener {
  const UrlLauncherOpener();

  @override
  Future<bool> open(String url) {
    final uri = Uri.tryParse(url);
    if (uri == null) return Future.value(false);
    return launchUrl(uri, mode: LaunchMode.externalApplication);
  }
}
