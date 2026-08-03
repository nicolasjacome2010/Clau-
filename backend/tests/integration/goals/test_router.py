from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core_api.auth.token_verifier import StaticTokenVerifier, VerifiedIdentity
from core_api.dependencies import get_goal_repository, get_token_verifier
from core_api.main import create_app
from tests.unit.goals.fakes import InMemoryGoalRepository


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()

    goals = InMemoryGoalRepository()
    identity = VerifiedIdentity(id=uuid4(), email="alejandro@example.com")
    other_identity = VerifiedIdentity(id=uuid4(), email="marina@example.com")
    verifier = StaticTokenVerifier({"valid-token": identity, "other-token": other_identity})

    app.dependency_overrides[get_goal_repository] = lambda: goals
    app.dependency_overrides[get_token_verifier] = lambda: verifier

    with TestClient(app) as test_client:
        yield test_client


AUTH = {"Authorization": "Bearer valid-token"}


def test_create_and_list_goal(client: TestClient) -> None:
    create_response = client.post(
        "/v1/goals", headers=AUTH, json={"name": "Crecimiento", "default_weight": 70}
    )
    list_response = client.get("/v1/goals", headers=AUTH)

    assert create_response.status_code == 201
    assert create_response.json()["name"] == "Crecimiento"
    assert list_response.status_code == 200
    assert [g["name"] for g in list_response.json()] == ["Crecimiento"]


def test_create_goal_rejects_empty_name(client: TestClient) -> None:
    response = client.post("/v1/goals", headers=AUTH, json={"name": ""})

    assert response.status_code == 422


def test_list_goals_is_scoped_to_caller(client: TestClient) -> None:
    client.post("/v1/goals", headers=AUTH, json={"name": "Mío"})

    other_list = client.get("/v1/goals", headers={"Authorization": "Bearer other-token"})

    assert other_list.status_code == 200
    assert other_list.json() == []


def test_update_goal(client: TestClient) -> None:
    created = client.post("/v1/goals", headers=AUTH, json={"name": "Original"}).json()

    response = client.patch(
        f"/v1/goals/{created['id']}", headers=AUTH, json={"default_weight": 90, "is_active": False}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["default_weight"] == 90
    assert body["is_active"] is False
    assert body["name"] == "Original"


def test_update_goal_owned_by_another_user_returns_404(client: TestClient) -> None:
    created = client.post("/v1/goals", headers=AUTH, json={"name": "Privado"}).json()

    response = client.patch(
        f"/v1/goals/{created['id']}",
        headers={"Authorization": "Bearer other-token"},
        json={"name": "hijack"},
    )

    assert response.status_code == 404


def test_update_nonexistent_goal_returns_404(client: TestClient) -> None:
    response = client.patch(f"/v1/goals/{uuid4()}", headers=AUTH, json={"name": "ghost"})

    assert response.status_code == 404
