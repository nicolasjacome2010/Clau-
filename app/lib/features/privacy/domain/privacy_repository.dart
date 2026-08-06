/// Port over the backend's `privacy` bounded context
/// (backend/src/core_api/privacy/api/router.py) — the two rights
/// docs/UX_DESIGN.md Pantalla 12 puts on screen rather than hiding in a
/// support inbox.
abstract class PrivacyRepository {
  /// The export exactly as the server produced it, still serialized.
  ///
  /// Returned as a JSON string rather than a parsed object on purpose:
  /// this is the user's copy of their own records, and re-parsing it into
  /// client types only to serialize it again would risk the app quietly
  /// dropping fields it doesn't happen to know about.
  Future<String> exportMyData();

  Future<void> eraseMyData();
}

class PrivacyRepositoryError implements Exception {
  PrivacyRepositoryError(this.message);

  final String message;

  @override
  String toString() => 'PrivacyRepositoryError: $message';
}

/// The backend's 404 on `GET /v1/privacy/export`: this account has no rows
/// yet (provisioning happens on the first authenticated request). Nothing
/// went wrong — there is simply nothing to export.
class NothingToExportError extends PrivacyRepositoryError {
  NothingToExportError(super.message);
}

/// The backend's 409 on `DELETE /v1/privacy/data`: a paid plan is still
/// live, and erasing the local rows would leave Stripe billing a card for
/// an account that no longer exists there.
class ActiveSubscriptionError extends PrivacyRepositoryError {
  ActiveSubscriptionError(super.message);
}
