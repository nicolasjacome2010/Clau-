from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core_api.auth.token_verifier import StaticTokenVerifier, VerifiedIdentity
from core_api.dependencies import (
    get_token_verifier,
    get_user_profile_repository,
    get_user_repository,
)
from core_api.main import create_app
from tests.unit.identity.fakes import InMemoryUserProfileRepository, InMemoryUserRepository


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()

    users = InMemoryUserRepository()
    profiles = InMemoryUserProfileRepository()
    identity = VerifiedIdentity(id=uuid4(), email="alejandro@example.com")
    verifier = StaticTokenVerifier({"valid-token": identity})

    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_user_profile_repository] = lambda: profiles
    app.dependency_overrides[get_token_verifier] = lambda: verifier

    with TestClient(app) as test_client:
        yield test_client


def test_get_me_creates_user_on_first_authenticated_call(client: TestClient) -> None:
    response = client.get("/v1/users/me", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "alejandro@example.com"
    assert body["risk_tolerance"] == 3  # default, no profile written yet


def test_get_me_without_token_is_rejected(client: TestClient) -> None:
    response = client.get("/v1/users/me")

    assert response.status_code in (401, 403)


def test_get_me_with_unknown_token_is_unauthorized(client: TestClient) -> None:
    response = client.get("/v1/users/me", headers={"Authorization": "Bearer nope"})

    assert response.status_code == 401


def test_update_profile_then_get_me_reflects_changes(client: TestClient) -> None:
    headers = {"Authorization": "Bearer valid-token"}
    client.get("/v1/users/me", headers=headers)

    patch_response = client.patch(
        "/v1/users/me/profile",
        headers=headers,
        json={"risk_tolerance": 5, "timezone": "Europe/Lisbon"},
    )
    get_response = client.get("/v1/users/me", headers=headers)

    assert patch_response.status_code == 200
    assert patch_response.json()["risk_tolerance"] == 5
    assert get_response.json()["timezone"] == "Europe/Lisbon"


def test_healthz_is_public() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
