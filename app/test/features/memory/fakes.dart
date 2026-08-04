import 'package:var_os_app/features/memory/domain/memory_repository.dart';
import 'package:var_os_app/features/memory/domain/user_bias_profile.dart';

class FakeMemoryRepository implements MemoryRepository {
  FakeMemoryRepository({UserBiasProfile? profile, this.error})
    : profile =
          profile ??
          const UserBiasProfile(
            biases: [],
            calibrationScore: 0,
            updatedAt: null,
          );

  final UserBiasProfile profile;
  final MemoryRepositoryError? error;

  @override
  Future<UserBiasProfile> getBiasProfile() async {
    if (error != null) throw error!;
    return profile;
  }
}
