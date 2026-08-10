import 'package:var_os_app/features/onboarding/domain/pending_goals_store.dart';

/// In-memory stand-in for the device's key-value store — the same role
/// `SharedPreferences.setMockInitialValues` would play, but without tying
/// these tests to a plugin channel.
class FakePendingGoalsStore implements PendingGoalsStore {
  FakePendingGoalsStore({List<String>? pending}) : _pending = [...?pending];

  List<String> _pending;

  /// Every list this store was asked to persist, in order — lets a test
  /// assert that the queue shrank one goal at a time rather than being
  /// cleared in one go at the end.
  final List<List<String>> writes = [];

  @override
  Future<List<String>> read() async => [..._pending];

  @override
  Future<void> write(List<String> goalNames) async {
    writes.add([...goalNames]);
    _pending = [...goalNames];
  }
}
