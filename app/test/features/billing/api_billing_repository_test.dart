import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:var_os_app/features/billing/data/api_billing_repository.dart';
import 'package:var_os_app/features/billing/domain/billing_repository.dart';

/// No real network — the same fake transport the other repository tests use.
class _FakeHttpClientAdapter implements HttpClientAdapter {
  _FakeHttpClientAdapter.json(this._body, {int status = 200})
    : _status = status;

  final String _body;
  final int _status;

  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return ResponseBody.fromString(
      _body,
      _status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Dio _dioWith(HttpClientAdapter adapter) {
  final dio = Dio(BaseOptions(baseUrl: 'http://test'));
  dio.httpClientAdapter = adapter;
  return dio;
}

void main() {
  test('parses the current subscription', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(
        jsonEncode({
          'tier': 'pro',
          'status': 'active',
          'current_period_end': '2026-09-01T00:00:00Z',
        }),
      ),
    );

    final subscription = await ApiBillingRepository(dio).getSubscription();

    expect(subscription.tier, 'pro');
    expect(subscription.status, 'active');
    expect(subscription.isFree, isFalse);
    expect(subscription.hasBillingRelationship, isTrue);
    expect(
      subscription.currentPeriodEnd,
      DateTime.parse('2026-09-01T00:00:00Z'),
    );
  });

  test(
    'reads the synthetic free row the backend returns for new users',
    () async {
      final dio = _dioWith(
        _FakeHttpClientAdapter.json(
          jsonEncode({
            'tier': 'free',
            'status': 'active',
            'current_period_end': null,
          }),
        ),
      );

      final subscription = await ApiBillingRepository(dio).getSubscription();

      expect(subscription.isFree, isTrue);
      expect(subscription.hasBillingRelationship, isFalse);
      expect(subscription.currentPeriodEnd, isNull);
    },
  );

  test('createCheckoutSession posts the price and returns the URL', () async {
    final adapter = _FakeHttpClientAdapter.json(
      jsonEncode({'checkout_url': 'https://checkout.stripe.com/abc'}),
    );
    final dio = _dioWith(adapter);

    final url = await ApiBillingRepository(dio).createCheckoutSession(
      priceId: 'price_pro',
      successUrl: 'https://varos.test/done',
      cancelUrl: 'https://varos.test/done',
    );

    expect(url, 'https://checkout.stripe.com/abc');
    expect(adapter.requests.single.method, 'POST');
    expect(adapter.requests.single.path, '/v1/billing/checkout-session');
    expect(adapter.requests.single.data, {
      'price_id': 'price_pro',
      'success_url': 'https://varos.test/done',
      'cancel_url': 'https://varos.test/done',
    });
  });

  test('createPortalSession posts the return URL', () async {
    final adapter = _FakeHttpClientAdapter.json(
      jsonEncode({'portal_url': 'https://billing.stripe.com/abc'}),
    );
    final dio = _dioWith(adapter);

    final url = await ApiBillingRepository(
      dio,
    ).createPortalSession(returnUrl: 'https://varos.test/done');

    expect(url, 'https://billing.stripe.com/abc');
    expect(adapter.requests.single.path, '/v1/billing/portal-session');
    expect(adapter.requests.single.data, {
      'return_url': 'https://varos.test/done',
    });
  });

  test('maps 503 to BillingUnavailableError', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'detail': 'down'}), status: 503),
    );

    expect(
      ApiBillingRepository(dio).createCheckoutSession(
        priceId: 'price_pro',
        successUrl: 'u',
        cancelUrl: 'u',
      ),
      throwsA(isA<BillingUnavailableError>()),
    );
  });

  test('maps 404 on the portal to NoSubscriptionToManageError', () async {
    final dio = _dioWith(
      _FakeHttpClientAdapter.json(jsonEncode({'detail': 'none'}), status: 404),
    );

    expect(
      ApiBillingRepository(dio).createPortalSession(returnUrl: 'u'),
      throwsA(isA<NoSubscriptionToManageError>()),
    );
  });

  test(
    'rejects a response missing the URL rather than returning empty',
    () async {
      final dio = _dioWith(
        _FakeHttpClientAdapter.json(jsonEncode({'ok': true})),
      );

      expect(
        ApiBillingRepository(dio).createPortalSession(returnUrl: 'u'),
        throwsA(isA<BillingRepositoryError>()),
      );
    },
  );
}
