from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core_api.memory.domain.entities import BiasObservation, UserBiasProfile


def test_bias_observation_rejects_out_of_range_score() -> None:
    with pytest.raises(ValueError, match="score"):
        BiasObservation(bias="loss_aversion", score=1.5, occurrences=1)


def test_with_bias_observation_adds_new_bias() -> None:
    profile = UserBiasProfile(user_id=uuid4())

    updated = profile.with_bias_observation("loss_aversion", 0.8, at=datetime.now(UTC))

    assert len(updated.biases) == 1
    assert updated.biases[0].bias == "loss_aversion"
    assert updated.biases[0].score == 0.8
    assert updated.biases[0].occurrences == 1


def test_with_bias_observation_averages_existing_bias() -> None:
    now = datetime.now(UTC)
    profile = UserBiasProfile(
        user_id=uuid4(), biases=(BiasObservation(bias="loss_aversion", score=0.6, occurrences=2),)
    )

    updated = profile.with_bias_observation("loss_aversion", 0.9, at=now)

    # (0.6*2 + 0.9) / 3 = 0.7
    assert len(updated.biases) == 1
    assert updated.biases[0].occurrences == 3
    assert updated.biases[0].score == pytest.approx(0.7)


def test_with_bias_observation_leaves_other_biases_untouched() -> None:
    now = datetime.now(UTC)
    profile = UserBiasProfile(
        user_id=uuid4(),
        biases=(
            BiasObservation(bias="loss_aversion", score=0.5, occurrences=1),
            BiasObservation(bias="confirmation_bias", score=0.3, occurrences=1),
        ),
    )

    updated = profile.with_bias_observation("loss_aversion", 0.9, at=now)

    assert len(updated.biases) == 2
    other = next(b for b in updated.biases if b.bias == "confirmation_bias")
    assert other.score == 0.3
    assert other.occurrences == 1


def test_with_calibration_delta_moves_toward_delta() -> None:
    profile = UserBiasProfile(user_id=uuid4(), calibration_score=50.0)

    updated = profile.with_calibration_delta(80.0, at=datetime.now(UTC))

    # 50*0.8 + 80*0.2 = 56
    assert updated.calibration_score == pytest.approx(56.0)
