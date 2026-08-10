from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core_api.auth.token_verifier import StaticTokenVerifier, VerifiedIdentity
from core_api.dependencies import get_decision_repository, get_token_verifier
from core_api.main import create_app
from tests.unit.decisions.fakes import InMemoryDecisionRepository


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()

    decisions = InMemoryDecisionRepository()
    identity = VerifiedIdentity(id=uuid4(), email="alejandro@example.com")
    other_identity = VerifiedIdentity(id=uuid4(), email="marina@example.com")
    verifier = StaticTokenVerifier({"valid-token": identity, "other-token": other_identity})

    app.dependency_overrides[get_decision_repository] = lambda: decisions
    app.dependency_overrides[get_token_verifier] = lambda: verifier

    with TestClient(app) as test_client:
        yield test_client


AUTH = {"Authorization": "Bearer valid-token"}


def test_create_decision_returns_detail_with_raw_input(client: TestClient) -> None:
    response = client.post(
        "/v1/decisions",
        headers=AUTH,
        json={"raw_input": "¿Debo aceptar la oferta?", "vertical": "career"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["vertical"] == "career"
    assert body["raw_input"] == "¿Debo aceptar la oferta?"


def test_create_decision_rejects_invalid_vertical(client: TestClient) -> None:
    response = client.post(
        "/v1/decisions", headers=AUTH, json={"raw_input": "algo", "vertical": "not-a-vertical"}
    )

    assert response.status_code == 422


def test_list_decisions_is_scoped_to_caller(client: TestClient) -> None:
    client.post("/v1/decisions", headers=AUTH, json={"raw_input": "Mío", "vertical": "career"})

    other_list = client.get("/v1/decisions", headers={"Authorization": "Bearer other-token"})

    assert other_list.status_code == 200
    assert other_list.json() == []


def test_get_decision_detail(client: TestClient) -> None:
    created = client.post(
        "/v1/decisions", headers=AUTH, json={"raw_input": "detalle", "vertical": "finance"}
    ).json()

    response = client.get(f"/v1/decisions/{created['id']}", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["raw_input"] == "detalle"


def test_get_decision_owned_by_another_user_returns_404(client: TestClient) -> None:
    created = client.post(
        "/v1/decisions", headers=AUTH, json={"raw_input": "privado", "vertical": "career"}
    ).json()

    response = client.get(
        f"/v1/decisions/{created['id']}", headers={"Authorization": "Bearer other-token"}
    )

    assert response.status_code == 404


def test_update_status_valid_transition(client: TestClient) -> None:
    created = client.post(
        "/v1/decisions", headers=AUTH, json={"raw_input": "x", "vertical": "career"}
    ).json()

    response = client.patch(
        f"/v1/decisions/{created['id']}/status", headers=AUTH, json={"status": "clarifying"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "clarifying"


def test_update_status_invalid_transition_returns_409(client: TestClient) -> None:
    created = client.post(
        "/v1/decisions", headers=AUTH, json={"raw_input": "x", "vertical": "career"}
    ).json()

    response = client.patch(
        f"/v1/decisions/{created['id']}/status", headers=AUTH, json={"status": "completed"}
    )

    assert response.status_code == 409


def test_update_status_of_nonexistent_decision_returns_404(client: TestClient) -> None:
    response = client.patch(
        f"/v1/decisions/{uuid4()}/status", headers=AUTH, json={"status": "clarifying"}
    )

    assert response.status_code == 404
