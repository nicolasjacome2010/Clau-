from __future__ import annotations

import pytest

from core_api.memory.domain.similarity import cosine_similarity


def test_identical_vectors_have_similarity_1() -> None:
    assert cosine_similarity((1.0, 2.0, 3.0), (1.0, 2.0, 3.0)) == pytest.approx(1.0)


def test_orthogonal_vectors_have_similarity_0() -> None:
    assert cosine_similarity((1.0, 0.0), (0.0, 1.0)) == pytest.approx(0.0)


def test_opposite_vectors_have_similarity_minus_1() -> None:
    assert cosine_similarity((1.0, 0.0), (-1.0, 0.0)) == pytest.approx(-1.0)


def test_zero_vector_returns_0_instead_of_dividing_by_zero() -> None:
    assert cosine_similarity((0.0, 0.0), (1.0, 1.0)) == 0.0


def test_mismatched_dimensions_raise() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        cosine_similarity((1.0, 2.0), (1.0, 2.0, 3.0))
