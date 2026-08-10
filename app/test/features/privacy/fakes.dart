import 'package:var_os_app/features/auth/domain/auth_repository.dart';
import 'package:var_os_app/features/privacy/domain/export_sharer.dart';
import 'package:var_os_app/features/privacy/domain/privacy_repository.dart';

class FakePrivacyRepository implements PrivacyRepository {
  FakePrivacyRepository({
    this.export = '{"user": {}}',
    this.exportError,
    this.eraseError,
  });

  final String export;
  final PrivacyRepositoryError? exportError;
  final PrivacyRepositoryError? eraseError;

  int exportCalls = 0;
  int eraseCalls = 0;

  @override
  Future<String> exportMyData() async {
    exportCalls += 1;
    if (exportError != null) throw exportError!;
    return export;
  }

  @override
  Future<void> eraseMyData() async {
    eraseCalls += 1;
    if (eraseError != null) throw eraseError!;
  }
}

class FakeExportSharer implements ExportSharer {
  FakeExportSharer({this.succeeds = true});

  final bool succeeds;
  final List<({String filename, String content})> shared = [];

  @override
  Future<bool> share({
    required String filename,
    required String content,
  }) async {
    shared.add((filename: filename, content: content));
    return succeeds;
  }
}

class RecordingAuthRepository implements AuthRepository {
  int signOuts = 0;

  @override
  Future<void> signOut() async {
    signOuts += 1;
  }

  @override
  Future<void> signInWithEmail(String email) async {}

  @override
  Future<void> continueAnonymously() async {}

  @override
  String? get currentAccessToken => null;

  @override
  Stream<String?> get accessTokenChanges => const Stream<String?>.empty();
}
