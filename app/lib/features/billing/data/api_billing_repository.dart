import 'package:dio/dio.dart';

import '../domain/billing_repository.dart';
import '../domain/subscription.dart';

/// Real adapter over `GET /v1/billing/subscription`,
/// `POST /v1/billing/checkout-session` and `POST /v1/billing/portal-session`.
class ApiBillingRepository implements BillingRepository {
  ApiBillingRepository(this._dio);

  final Dio _dio;

  @override
  Future<Subscription> getSubscription() async {
    final Response<dynamic> response;
    try {
      response = await _dio.get<dynamic>('/v1/billing/subscription');
    } on DioException catch (exc) {
      throw BillingRepositoryError(
        'Failed to load subscription: ${exc.message}',
      );
    }

    final data = response.data;
    if (data is! Map) {
      throw BillingRepositoryError('Unexpected subscription response shape');
    }
    final periodEnd = data['current_period_end'] as String?;

    return Subscription(
      tier: data['tier'] as String,
      status: data['status'] as String,
      currentPeriodEnd: periodEnd != null ? DateTime.parse(periodEnd) : null,
    );
  }

  @override
  Future<String> createCheckoutSession({
    required String priceId,
    required String successUrl,
    required String cancelUrl,
  }) async {
    final Response<dynamic> response;
    try {
      response = await _dio.post<dynamic>(
        '/v1/billing/checkout-session',
        data: {
          'price_id': priceId,
          'success_url': successUrl,
          'cancel_url': cancelUrl,
        },
      );
    } on DioException catch (exc) {
      throw _mapError(exc, 'Failed to create checkout session');
    }
    return _requireUrl(response.data, 'checkout_url');
  }

  @override
  Future<String> createPortalSession({required String returnUrl}) async {
    final Response<dynamic> response;
    try {
      response = await _dio.post<dynamic>(
        '/v1/billing/portal-session',
        data: {'return_url': returnUrl},
      );
    } on DioException catch (exc) {
      throw _mapError(exc, 'Failed to create portal session');
    }
    return _requireUrl(response.data, 'portal_url');
  }

  BillingRepositoryError _mapError(DioException exc, String context) {
    // Typed per status so the screen can say something true: 503 means
    // Stripe is unreachable (or this deployment has no keys — it fails
    // closed), 404 means there is no Stripe customer to manage yet.
    switch (exc.response?.statusCode) {
      case 503:
        return BillingUnavailableError('Stripe is temporarily unavailable');
      case 404:
        return NoSubscriptionToManageError('No subscription to manage');
      default:
        return BillingRepositoryError('$context: ${exc.message}');
    }
  }

  String _requireUrl(Object? data, String key) {
    if (data is! Map || data[key] is! String) {
      throw BillingRepositoryError('Unexpected response shape: missing $key');
    }
    return data[key] as String;
  }
}
