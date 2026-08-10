/// Hands the export document to the operating system so the user can put
/// it wherever they want — Files, Drive, an email to themselves.
///
/// A port for the same reason as `UrlOpener`: the real implementation is a
/// platform channel, and a widget test has no platform. It is also the
/// seam where "receive a copy of your data" could later become a download
/// on web without any screen changing.
abstract class ExportSharer {
  /// Returns false when the platform refused (no share target, user
  /// dismissed at the OS level) so the screen can say so rather than
  /// leave a button that appeared to do nothing.
  Future<bool> share({required String filename, required String content});
}
