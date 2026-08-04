import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/api_memory_repository.dart';
import '../../domain/memory_repository.dart';
import '../../domain/user_bias_profile.dart';

final memoryRepositoryProvider = Provider<MemoryRepository>(
  (ref) => ApiMemoryRepository(ref.read(dioProvider)),
);

class BiasProfileController extends AsyncNotifier<UserBiasProfile> {
  @override
  Future<UserBiasProfile> build() => _fetch();

  Future<void> refresh() async {
    state = const AsyncLoading<UserBiasProfile>().copyWithPrevious(state);
    state = await AsyncValue.guard(_fetch);
  }

  Future<UserBiasProfile> _fetch() {
    return ref.read(memoryRepositoryProvider).getBiasProfile();
  }
}

final biasProfileControllerProvider =
    AsyncNotifierProvider<BiasProfileController, UserBiasProfile>(
      BiasProfileController.new,
    );
