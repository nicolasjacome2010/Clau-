from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core_api.auth.token_verifier import StaticTokenVerifier, VerifiedIdentity
from core_api.dependencies import (
    get_decision_repository,
    get_memory_embedding_repository,
    get_token_verifier,
    get_user_bias_profile_repository,
)
from core_api.main import create_app
from tests.unit.decisions.fakes import InMemoryDecisionRepository
from tests.unit.memory.fakes import (
    InMemoryMemoryEmbeddingRepository,
    InMemoryUserBiasProfileRepository,
)

AUTH = {"Authorization": "Bearer valid-token"}


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()

    profiles = InMemoryUserBiasProfileRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    decisions = InMemoryDecisionRepository()
    identity = VerifiedIdentity(id=uuid4(), email="alejandro@example.com")
    other_identity = VerifiedIdentity(id=uuid4(), email="marina@example.com")
    verifier = StaticTokenVerifier({"valid-token": identity, "other-token": other_identity})

    app.dependency_overrides[get_user_bias_profile_repository] = lambda: profiles
    app.dependency_overrides[get_memory_embedding_repository] = lambda: memories
    app.dependency_overrides[get_decision_repository] = lambda: decisions
    app.dependency_overrides[get_token_verifier] = lambda: verifier

    with TestClient(app) as test_client:
        yield test_client


def test_get_bias_profile_defaults_when_empty(client: TestClient) -> None:
    response = client.get("/v1/memory/bias-profile", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["biases"] == []
    assert body["calibration_score"] == 0.0


def test_record_bias_observation_and_read_back(client: TestClient) -> None:
    response = client.post(
        "/v1/memory/bias-observations",
        headers=AUTH,
        json={"bias": "loss_aversion", "confidence": 0.7},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["biases"] == [{"bias": "loss_aversion", "score": 0.7, "occurrences": 1}]

    follow_up = client.get("/v1/memory/bias-profile", headers=AUTH)
    assert follow_up.json()["biases"][0]["occurrences"] == 1


def test_record_calibration(client: TestClient) -> None:
    response = client.post(
        "/v1/memory/calibration", headers=AUTH, json={"calibration_delta": 100.0}
    )

    assert response.status_code == 200
    assert response.json()["calibration_score"] == pytest.approx(20.0)


def test_bias_profile_is_scoped_to_caller(client: TestClient) -> None:
    client.post(
        "/v1/memory/bias-observations",
        headers=AUTH,
        json={"bias": "loss_aversion", "confidence": 0.9},
    )

    other = client.get("/v1/memory/bias-profile", headers={"Authorization": "Bearer other-token"})

    assert other.json()["biases"] == []


def test_store_and_list_memory(client: TestClient) -> None:
    response = client.post(
        "/v1/memory/embeddings",
        headers=AUTH,
        json={"summary_text": "resumen", "embedding": [0.1, 0.2, 0.3]},
    )

    assert response.status_code == 201
    assert response.json()["summary_text"] == "resumen"
    assert "embedding" not in response.json()

    listing = client.get("/v1/memory/embeddings", headers=AUTH)
    assert len(listing.json()) == 1


def test_store_memory_with_nonexistent_decision_returns_404(client: TestClient) -> None:
    response = client.post(
        "/v1/memory/embeddings",
        headers=AUTH,
        json={"summary_text": "resumen", "embedding": [0.1], "decision_id": str(uuid4())},
    )

    assert response.status_code == 404


def test_search_memories_ranks_by_similarity(client: TestClient) -> None:
    client.post(
        "/v1/memory/embeddings",
        headers=AUTH,
        json={"summary_text": "cercano", "embedding": [0.9, 0.1]},
    )
    client.post(
        "/v1/memory/embeddings",
        headers=AUTH,
        json={"summary_text": "lejano", "embedding": [0.0, 1.0]},
    )

    response = client.post(
        "/v1/memory/embeddings/search",
        headers=AUTH,
        json={"embedding": [1.0, 0.0], "top_k": 1},
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["summary_text"] == "cercano"
    assert results[0]["similarity"] > 0.9


def test_memory_endpoints_require_auth(client: TestClient) -> None:
    response = client.get("/v1/memory/bias-profile")

    assert response.status_code in (401, 403)
