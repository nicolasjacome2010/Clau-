from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.billing.domain.entities import Subscription, SubscriptionStatus, SubscriptionTier
from core_api.billing.infrastructure.models import SubscriptionModel
from core_api.billing.infrastructure.repository import SqlAlchemySubscriptionRepository
from core_api.crypto import FernetFieldEncryptor
from core_api.decisions.domain.entities import Decision, DecisionStatus, DecisionVertical
from core_api.decisions.infrastructure.models import DecisionModel
from core_api.decisions.infrastructure.repository import SqlAlchemyDecisionRepository
from core_api.goals.domain.entities import Goal
from core_api.goals.infrastructure.models import GoalModel
from core_api.goals.infrastructure.repository import SqlAlchemyGoalRepository
from core_api.identity.domain.entities import User, UserProfile
from core_api.identity.infrastructure.models import UserProfileModel
from core_api.identity.infrastructure.repository import (
    SqlAlchemyUserProfileRepository,
    SqlAlchemyUserRepository,
)
from core_api.memory.domain.entities import MemoryEmbedding, UserBiasProfile
from core_api.memory.infrastructure.models import MemoryEmbeddingModel, UserBiasProfileModel
from core_api.memory.infrastructure.repository import (
    SqlAlchemyMemoryEmbeddingRepository,
    SqlAlchemyUserBiasProfileRepository,
)
from core_api.simulations.domain.entities import (
    DecisionOutcome,
    Simulation,
    SimulationScenario,
    SimulationStatus,
)
from core_api.simulations.infrastructure.models import (
    DecisionOutcomeModel,
    SimulationModel,
    SimulationScenarioModel,
)
from core_api.simulations.infrastructure.repository import (
    SqlAlchemyDecisionOutcomeRepository,
    SqlAlchemySimulationRepository,
)


async def _count(session: AsyncSession, model: type) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


async def _seed_full_user(session: AsyncSession) -> User:
    """One user with a row in every table that hangs off them."""
    now = datetime.now(UTC)
    user = await SqlAlchemyUserRepository(session).create(
        User(
            id=uuid4(),
            email=f"{uuid4()}@example.com",
            display_name=None,
            locale="es",
            onboarding_completed_at=None,
            created_at=now,
            updated_at=now,
        )
    )
    await SqlAlchemyUserProfileRepository(session).upsert(UserProfile(user_id=user.id))
    await SqlAlchemyGoalRepository(session).create(
        Goal(
            id=uuid4(),
            user_id=user.id,
            name="Crecimiento",
            default_weight=50,
            is_active=True,
            created_at=now,
        )
    )
    encryptor = FernetFieldEncryptor(Fernet.generate_key().decode())
    decision = await SqlAlchemyDecisionRepository(session, encryptor).create(
        Decision(
            id=uuid4(),
            user_id=user.id,
            title="¿Debo aceptar?",
            vertical=DecisionVertical.CAREER,
            status=DecisionStatus.COMPLETED,
            raw_input="texto",
            created_at=now,
            updated_at=now,
        )
    )
    scenario = SimulationScenario(
        id=uuid4(),
        external_id="a",
        title="Aceptar",
        narrative="n",
        assumptions=["s"],
        relative_probability=40.0,
        time_horizon_months=12,
        goal_alignment_scores=[],
        risk_score=30.0,
        reversibility_score=70.0,
        final_score=60.0,
        rank=1,
    )
    await SqlAlchemySimulationRepository(session).create(
        Simulation(
            id=uuid4(),
            decision_id=decision.id,
            status=SimulationStatus.COMPLETED,
            pipeline_version="v1",
            safety_gate_result={},
            scenarios=(scenario,),
            synthesis_text="s",
            reflective_question="¿Y?",
            started_at=now,
            completed_at=now,
        )
    )
    await SqlAlchemyDecisionOutcomeRepository(session).create(
        DecisionOutcome(
            id=uuid4(),
            decision_id=decision.id,
            reported_outcome="pasó esto",
            closest_scenario_id=None,
            calibration_delta=0.0,
            system_errors_identified=[],
            reported_at=now,
        )
    )
    await SqlAlchemyUserBiasProfileRepository(session).upsert(
        UserBiasProfile(user_id=user.id, calibration_score=5.0, updated_at=now)
    )
    await SqlAlchemyMemoryEmbeddingRepository(session).create(
        MemoryEmbedding(
            id=uuid4(),
            user_id=user.id,
            decision_id=decision.id,
            summary_text="resumen",
            embedding=(0.1, 0.2),
            created_at=now,
        )
    )
    await SqlAlchemySubscriptionRepository(session).upsert(
        Subscription(
            user_id=user.id,
            stripe_customer_id=f"cus_{uuid4()}",
            stripe_subscription_id=None,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=None,
            updated_at=now,
        )
    )
    return user


_OWNED_TABLES = [
    UserProfileModel,
    GoalModel,
    DecisionModel,
    SimulationModel,
    SimulationScenarioModel,
    DecisionOutcomeModel,
    UserBiasProfileModel,
    MemoryEmbeddingModel,
    SubscriptionModel,
]


@pytest.mark.asyncio
async def test_deleting_a_user_cascades_to_every_owned_table(
    sqlite_session: AsyncSession,
) -> None:
    """The whole reason erasure is one `delete`, not nine.

    If a future table hangs off `users.id` without `ON DELETE CASCADE`,
    this test fails — which is exactly when someone needs to know.
    """
    user = await _seed_full_user(sqlite_session)
    for model in _OWNED_TABLES:
        assert await _count(sqlite_session, model) == 1, model.__name__

    deleted = await SqlAlchemyUserRepository(sqlite_session).delete(user.id)

    assert deleted is True
    for model in _OWNED_TABLES:
        assert await _count(sqlite_session, model) == 0, model.__name__


@pytest.mark.asyncio
async def test_deleting_one_user_leaves_another_untouched(
    sqlite_session: AsyncSession,
) -> None:
    mine = await _seed_full_user(sqlite_session)
    await _seed_full_user(sqlite_session)

    await SqlAlchemyUserRepository(sqlite_session).delete(mine.id)

    for model in _OWNED_TABLES:
        assert await _count(sqlite_session, model) == 1, model.__name__


@pytest.mark.asyncio
async def test_deleting_a_missing_user_reports_it(sqlite_session: AsyncSession) -> None:
    assert await SqlAlchemyUserRepository(sqlite_session).delete(uuid4()) is False
