from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core_api.auth.token_verifier import StaticTokenVerifier, VerifiedIdentity
from core_api.billing.domain.entities import Subscription, SubscriptionStatus, SubscriptionTier
from core_api.dependencies import (
    get_decision_outcome_repository,
    get_decision_repository,
    get_goal_repository,
    get_memory_embedding_repository,
    get_simulation_repository,
    get_subscription_repository,
    get_token_verifier,
    get_user_bias_profile_repository,
    get_user_profile_repository,
    get_user_repository,
)
from core_api.identity.domain.entities import User
from core_api.main import create_app
from tests.unit.billing.fakes import InMemorySubscriptionRepository
from tests.unit.decisions.fakes import InMemoryDecisionRepository
from tests.unit.goals.fakes import InMemoryGoalRepository
from tests.unit.identity.fakes import InMemoryUserProfileRepository, InMemoryUserRepository
from tests.unit.memory.fakes import (
    InMemoryMemoryEmbeddingRepository,
    InMemoryUserBiasProfileRepository,
)
from tests.unit.simulations.fakes import (
    InMemoryDecisionOutcomeRepository,
    InMemorySimulationRepository,
)

AUTH = {"Authorization": "Bearer valid-token"}
USER_ID = uuid4()


@pytest.fixture
def users() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def subscriptions() -> InMemorySubscriptionRepository:
    return InMemorySubscriptionRepository()


@pytest.fixture
def client(
    users: InMemoryUserRepository, subscriptions: InMemorySubscriptionRepository
) -> Iterator[TestClient]:
    app = create_app()

    identity = VerifiedIdentity(id=USER_ID, email="alejandro@example.com")
    verifier = StaticTokenVerifier({"valid-token": identity})

    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_user_profile_repository] = InMemoryUserProfileRepository
    app.dependency_overrides[get_goal_repository] = InMemoryGoalRepository
    app.dependency_overrides[get_decision_repository] = InMemoryDecisionRepository
    app.dependency_overrides[get_simulation_repository] = InMemorySimulationRepository
    app.dependency_overrides[get_decision_outcome_repository] = InMemoryDecisionOutcomeRepository
    app.dependency_overrides[get_user_bias_profile_repository] = InMemoryUserBiasProfileRepository
    app.dependency_overrides[get_memory_embedding_repository] = InMemoryMemoryEmbeddingRepository
    app.dependency_overrides[get_subscription_repository] = lambda: subscriptions
    app.dependency_overrides[get_token_verifier] = lambda: verifier

    with TestClient(app) as test_client:
        yield test_client


async def _create_user(users: InMemoryUserRepository) -> User:
    now = datetime.now(UTC)
    return await users.create(
        User(
            id=USER_ID,
            email="alejandro@example.com",
            display_name=None,
            locale="es",
            onboarding_completed_at=None,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.mark.asyncio
async def test_export_returns_every_section(
    client: TestClient, users: InMemoryUserRepository
) -> None:
    await _create_user(users)

    response = client.get("/v1/privacy/export", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "alejandro@example.com"
    for section in ("goals", "decisions", "simulations", "decision_outcomes", "memories"):
        assert body[section] == []
    assert body["profile"] is None
    # The export names its own edges rather than quietly omitting things.
    assert len(body["notes"]) >= 3


@pytest.mark.asyncio
async def test_export_requires_authentication(client: TestClient) -> None:
    assert client.get("/v1/privacy/export").status_code == 401


@pytest.mark.asyncio
async def test_export_of_a_user_that_was_never_provisioned_is_404(
    client: TestClient,
) -> None:
    # A valid token whose user row doesn't exist yet: there is genuinely
    # nothing to export, and saying so beats an empty document that looks
    # like data loss.
    assert client.get("/v1/privacy/export", headers=AUTH).status_code == 404


@pytest.mark.asyncio
async def test_erase_deletes_and_answers_204(
    client: TestClient, users: InMemoryUserRepository
) -> None:
    await _create_user(users)

    response = client.delete("/v1/privacy/data", headers=AUTH)

    assert response.status_code == 204
    assert await users.get_by_id(USER_ID) is None


@pytest.mark.asyncio
async def test_erase_is_idempotent(client: TestClient, users: InMemoryUserRepository) -> None:
    # "Delete my data" answered with 404 would be a strange thing to tell
    # someone whose data is, in fact, gone.
    await _create_user(users)

    assert client.delete("/v1/privacy/data", headers=AUTH).status_code == 204
    assert client.delete("/v1/privacy/data", headers=AUTH).status_code == 204


@pytest.mark.asyncio
async def test_erase_refuses_while_a_paid_plan_is_live(
    client: TestClient,
    users: InMemoryUserRepository,
    subscriptions: InMemorySubscriptionRepository,
) -> None:
    await _create_user(users)
    await subscriptions.upsert(
        Subscription(
            user_id=USER_ID,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=datetime.now(UTC),
        )
    )

    response = client.delete("/v1/privacy/data", headers=AUTH)

    assert response.status_code == 409
    assert await users.get_by_id(USER_ID) is not None


@pytest.mark.asyncio
async def test_erase_requires_authentication(client: TestClient) -> None:
    assert client.delete("/v1/privacy/data").status_code == 401
