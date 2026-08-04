from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core_api.auth.token_verifier import StaticTokenVerifier, VerifiedIdentity
from core_api.dependencies import (
    get_decision_repository,
    get_goal_repository,
    get_reality_engine_client,
    get_simulation_repository,
    get_token_verifier,
)
from core_api.main import create_app
from core_api.simulations.domain.reality_engine_port import (
    RealityEngineScenario,
    RealityEngineSimulationOutcome,
)
from tests.unit.decisions.fakes import InMemoryDecisionRepository
from tests.unit.goals.fakes import InMemoryGoalRepository
from tests.unit.simulations.fakes import FakeRealityEngineClient, InMemorySimulationRepository

AUTH = {"Authorization": "Bearer valid-token"}


def _safe_outcome() -> RealityEngineSimulationOutcome:
    return RealityEngineSimulationOutcome(
        safe_to_proceed=True,
        safety_gate_result={"risk_level": "none"},
        scenarios=[
            RealityEngineScenario(
                id="a",
                title="Aceptas",
                narrative="Podrías crecer.",
                assumptions=[],
                relative_probability=100.0,
                time_horizon_months=12,
                goal_alignment_scores=[],
                risk_score=20.0,
                reversibility_score=60.0,
                final_score=70.0,
                rank=1,
            )
        ],
        synthesis_text="texto",
        reflective_question="¿Y bien?",
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()

    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    reality_engine = FakeRealityEngineClient(responses=[_safe_outcome()])
    identity = VerifiedIdentity(id=uuid4(), email="alejandro@example.com")
    other_identity = VerifiedIdentity(id=uuid4(), email="marina@example.com")
    verifier = StaticTokenVerifier({"valid-token": identity, "other-token": other_identity})

    app.dependency_overrides[get_decision_repository] = lambda: decisions
    app.dependency_overrides[get_goal_repository] = lambda: goals
    app.dependency_overrides[get_simulation_repository] = lambda: simulations
    app.dependency_overrides[get_reality_engine_client] = lambda: reality_engine
    app.dependency_overrides[get_token_verifier] = lambda: verifier

    with TestClient(app) as test_client:
        yield test_client


def _create_decision(client: TestClient) -> str:
    response = client.post(
        "/v1/decisions", headers=AUTH, json={"raw_input": "¿Debo aceptar?", "vertical": "career"}
    )
    result: str = response.json()["id"]
    return result


def test_run_simulation_returns_completed_result(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.post(f"/v1/decisions/{decision_id}/simulations", headers=AUTH)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["scenarios"]) == 1
    assert body["synthesis_text"] == "texto"

    decision_after = client.get(f"/v1/decisions/{decision_id}", headers=AUTH).json()
    assert decision_after["status"] == "completed"


def test_run_simulation_on_nonexistent_decision_returns_404(client: TestClient) -> None:
    response = client.post(f"/v1/decisions/{uuid4()}/simulations", headers=AUTH)

    assert response.status_code == 404


def test_run_simulation_on_another_users_decision_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.post(
        f"/v1/decisions/{decision_id}/simulations", headers={"Authorization": "Bearer other-token"}
    )

    assert response.status_code == 404


def test_list_simulations_for_decision(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/v1/decisions/{decision_id}/simulations", headers=AUTH)

    response = client.get(f"/v1/decisions/{decision_id}/simulations", headers=AUTH)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_simulation_detail(client: TestClient) -> None:
    decision_id = _create_decision(client)
    created = client.post(f"/v1/decisions/{decision_id}/simulations", headers=AUTH).json()

    response = client.get(f"/v1/simulations/{created['id']}", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_simulation_owned_by_another_user_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)
    created = client.post(f"/v1/decisions/{decision_id}/simulations", headers=AUTH).json()

    response = client.get(
        f"/v1/simulations/{created['id']}", headers={"Authorization": "Bearer other-token"}
    )

    assert response.status_code == 404
