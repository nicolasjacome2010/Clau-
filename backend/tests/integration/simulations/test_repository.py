from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from core_api.crypto import FernetFieldEncryptor
from core_api.decisions.domain.entities import Decision, DecisionStatus, DecisionVertical
from core_api.decisions.infrastructure.repository import SqlAlchemyDecisionRepository
from core_api.identity.domain.entities import User
from core_api.identity.infrastructure.repository import SqlAlchemyUserRepository
from core_api.simulations.domain.entities import Simulation, SimulationScenario, SimulationStatus
from core_api.simulations.infrastructure.repository import SqlAlchemySimulationRepository


async def _make_decision(session: AsyncSession) -> Decision:
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
    encryptor = FernetFieldEncryptor(Fernet.generate_key().decode())
    return await SqlAlchemyDecisionRepository(session, encryptor).create(
        Decision(
            id=uuid4(),
            user_id=user.id,
            title="t",
            vertical=DecisionVertical.CAREER,
            status=DecisionStatus.DRAFT,
            raw_input="¿Debo aceptar?",
            created_at=now,
            updated_at=now,
        )
    )


def _scenario(rank: int) -> SimulationScenario:
    return SimulationScenario(
        id=uuid4(),
        external_id=f"scenario-{rank}",
        title=f"Escenario {rank}",
        narrative="Podrías crecer profesionalmente.",
        assumptions=["supuesto A"],
        relative_probability=50.0,
        time_horizon_months=12,
        goal_alignment_scores=[{"goal": "Estabilidad", "score": 70, "justification": "x"}],
        risk_score=30.0,
        reversibility_score=60.0,
        final_score=65.0,
        rank=rank,
    )


@pytest.mark.asyncio
async def test_create_and_get_simulation_round_trips_with_scenarios(
    sqlite_session: AsyncSession,
) -> None:
    decision = await _make_decision(sqlite_session)
    repo = SqlAlchemySimulationRepository(sqlite_session)
    now = datetime.now(UTC)
    simulation = Simulation(
        id=uuid4(),
        decision_id=decision.id,
        status=SimulationStatus.COMPLETED,
        pipeline_version="v1",
        safety_gate_result={"risk_level": "none"},
        scenarios=(_scenario(1), _scenario(2)),
        synthesis_text="síntesis",
        reflective_question="¿Y bien?",
        started_at=now,
        completed_at=now,
    )

    created = await repo.create(simulation)
    fetched = await repo.get_by_id(simulation.id)

    assert created.status == SimulationStatus.COMPLETED
    assert fetched is not None
    assert len(fetched.scenarios) == 2
    assert [s.rank for s in fetched.scenarios] == [1, 2]
    assert fetched.scenarios[0].goal_alignment_scores[0]["goal"] == "Estabilidad"
    assert fetched.synthesis_text == "síntesis"


@pytest.mark.asyncio
async def test_list_for_decision_orders_by_most_recent_first(sqlite_session: AsyncSession) -> None:
    decision = await _make_decision(sqlite_session)
    repo = SqlAlchemySimulationRepository(sqlite_session)
    older = Simulation(
        id=uuid4(),
        decision_id=decision.id,
        status=SimulationStatus.FAILED,
        pipeline_version="v1",
        safety_gate_result={},
        scenarios=(),
        synthesis_text=None,
        reflective_question=None,
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = Simulation(
        id=uuid4(),
        decision_id=decision.id,
        status=SimulationStatus.COMPLETED,
        pipeline_version="v1",
        safety_gate_result={},
        scenarios=(),
        synthesis_text=None,
        reflective_question=None,
        started_at=datetime(2026, 2, 1, tzinfo=UTC),
        completed_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    await repo.create(older)
    await repo.create(newer)

    result = await repo.list_for_decision(decision.id)

    assert [s.id for s in result] == [newer.id, older.id]


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(sqlite_session: AsyncSession) -> None:
    repo = SqlAlchemySimulationRepository(sqlite_session)

    assert await repo.get_by_id(uuid4()) is None
