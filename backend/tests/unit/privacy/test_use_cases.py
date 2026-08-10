from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from core_api.billing.domain.entities import Subscription, SubscriptionStatus, SubscriptionTier
from core_api.decisions.domain.entities import Decision, DecisionStatus, DecisionVertical
from core_api.goals.domain.entities import Goal
from core_api.identity.domain.entities import User, UserProfile
from core_api.memory.domain.entities import MemoryEmbedding, UserBiasProfile
from core_api.privacy.application.use_cases import (
    EraseUserDataUseCase,
    ExportUserDataUseCase,
    PrivacyRepositories,
)
from core_api.privacy.domain.exceptions import ActiveSubscriptionError, UserNotFoundError
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


def _repositories() -> PrivacyRepositories:
    return PrivacyRepositories(
        users=InMemoryUserRepository(),
        profiles=InMemoryUserProfileRepository(),
        goals=InMemoryGoalRepository(),
        decisions=InMemoryDecisionRepository(),
        simulations=InMemorySimulationRepository(),
        outcomes=InMemoryDecisionOutcomeRepository(),
        bias_profiles=InMemoryUserBiasProfileRepository(),
        memories=InMemoryMemoryEmbeddingRepository(),
        subscriptions=InMemorySubscriptionRepository(),
    )


async def _make_user(repos: PrivacyRepositories) -> User:
    now = datetime.now(UTC)
    return await repos.users.create(
        User(
            id=uuid4(),
            email="alejandro@example.com",
            display_name=None,
            locale="es",
            onboarding_completed_at=None,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.mark.asyncio
async def test_export_gathers_every_context() -> None:
    repos = _repositories()
    user = await _make_user(repos)
    now = datetime.now(UTC)

    await repos.profiles.upsert(UserProfile(user_id=user.id, risk_tolerance=4))
    await repos.goals.create(
        Goal(
            id=uuid4(),
            user_id=user.id,
            name="Crecimiento",
            default_weight=50,
            is_active=True,
            created_at=now,
        )
    )
    await repos.decisions.create(
        Decision(
            id=uuid4(),
            user_id=user.id,
            title="¿Debo aceptar?",
            vertical=DecisionVertical.CAREER,
            status=DecisionStatus.DRAFT,
            raw_input="¿Debo aceptar la oferta?",
            created_at=now,
            updated_at=now,
        )
    )
    await repos.bias_profiles.upsert(
        UserBiasProfile(user_id=user.id, calibration_score=12.5, updated_at=now)
    )
    await repos.memories.create(
        MemoryEmbedding(
            id=uuid4(),
            user_id=user.id,
            decision_id=None,
            summary_text="Tiende a subestimar plazos.",
            embedding=(0.1, 0.2),
            created_at=now,
        )
    )

    export = await ExportUserDataUseCase(repos).execute(user.id)

    assert export.user["email"] == "alejandro@example.com"
    assert export.profile is not None
    assert export.profile["risk_tolerance"] == 4
    assert [goal["name"] for goal in export.goals] == ["Crecimiento"]
    # The user's own words come back in plaintext, not as ciphertext they
    # have no key for.
    assert export.decisions[0]["raw_input"] == "¿Debo aceptar la oferta?"
    assert export.bias_profile is not None
    assert export.bias_profile["calibration_score"] == 12.5
    assert export.memories[0]["summary_text"] == "Tiende a subestimar plazos."
    # The vector is deliberately absent — see `UserDataExport.notes`.
    assert "embedding" not in export.memories[0]
    assert export.notes


@pytest.mark.asyncio
async def test_export_includes_goals_the_user_retired() -> None:
    # An export is not a product view: a deactivated goal is still
    # something the system holds about them.
    repos = _repositories()
    user = await _make_user(repos)
    await repos.goals.create(
        Goal(
            id=uuid4(),
            user_id=user.id,
            name="Estabilidad",
            default_weight=30,
            is_active=False,
            created_at=datetime.now(UTC),
        )
    )

    export = await ExportUserDataUseCase(repos).execute(user.id)

    assert [goal["name"] for goal in export.goals] == ["Estabilidad"]


@pytest.mark.asyncio
async def test_export_does_not_leak_another_users_data() -> None:
    repos = _repositories()
    user = await _make_user(repos)
    now = datetime.now(UTC)
    await repos.decisions.create(
        Decision(
            id=uuid4(),
            user_id=uuid4(),
            title="De otra persona",
            vertical=DecisionVertical.CAREER,
            status=DecisionStatus.DRAFT,
            raw_input="ajeno",
            created_at=now,
            updated_at=now,
        )
    )

    export = await ExportUserDataUseCase(repos).execute(user.id)

    assert export.decisions == []


@pytest.mark.asyncio
async def test_export_raises_for_an_unknown_user() -> None:
    with pytest.raises(UserNotFoundError):
        await ExportUserDataUseCase(_repositories()).execute(uuid4())


@pytest.mark.asyncio
async def test_erase_deletes_the_user() -> None:
    repos = _repositories()
    user = await _make_user(repos)

    await EraseUserDataUseCase(repos).execute(user.id)

    assert await repos.users.get_by_id(user.id) is None


@pytest.mark.asyncio
async def test_erase_refuses_while_a_paid_plan_is_live() -> None:
    # Erasing here would drop our copy while Stripe keeps charging the
    # card — the user would pay for an account that no longer exists.
    repos = _repositories()
    user = await _make_user(repos)
    await repos.subscriptions.upsert(
        Subscription(
            user_id=user.id,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=datetime.now(UTC),
        )
    )

    with pytest.raises(ActiveSubscriptionError):
        await EraseUserDataUseCase(repos).execute(user.id)

    assert await repos.users.get_by_id(user.id) is not None


@pytest.mark.asyncio
async def test_erase_proceeds_once_the_plan_is_canceled() -> None:
    # A canceled subscription bills nothing further, so it is no reason to
    # hold someone's data.
    repos = _repositories()
    user = await _make_user(repos)
    await repos.subscriptions.upsert(
        Subscription(
            user_id=user.id,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            tier=SubscriptionTier.PRO,
            status=SubscriptionStatus.CANCELED,
            current_period_end=None,
            updated_at=datetime.now(UTC),
        )
    )

    await EraseUserDataUseCase(repos).execute(user.id)

    assert await repos.users.get_by_id(user.id) is None


@pytest.mark.asyncio
async def test_erase_raises_for_an_unknown_user() -> None:
    with pytest.raises(UserNotFoundError):
        await EraseUserDataUseCase(_repositories()).execute(uuid4())
