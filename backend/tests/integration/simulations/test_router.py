from __future__ import annotations

import json
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core_api.auth.token_verifier import StaticTokenVerifier, VerifiedIdentity
from core_api.dependencies import (
    get_decision_outcome_repository,
    get_decision_repository,
    get_goal_repository,
    get_memory_embedding_repository,
    get_reality_engine_client,
    get_simulation_repository,
    get_token_verifier,
    get_user_bias_profile_repository,
)
from core_api.main import create_app
from core_api.simulations.domain.reality_engine_port import (
    RealityEngineCalibrationOutcome,
    RealityEngineScenario,
    RealityEngineSimulationOutcome,
    RealityEngineStageEvent,
)
from tests.unit.decisions.fakes import InMemoryDecisionRepository
from tests.unit.goals.fakes import InMemoryGoalRepository
from tests.unit.memory.fakes import (
    InMemoryMemoryEmbeddingRepository,
    InMemoryUserBiasProfileRepository,
)
from tests.unit.simulations.fakes import (
    FakeRealityEngineClient,
    InMemoryDecisionOutcomeRepository,
    InMemorySimulationRepository,
)

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
def reality_engine() -> FakeRealityEngineClient:
    return FakeRealityEngineClient(
        responses=[_safe_outcome(), _safe_outcome(), _safe_outcome()],
        calibrate_responses=[
            RealityEngineCalibrationOutcome(
                closest_scenario_id="a",
                calibration_delta=15.0,
                system_errors_identified=["overconfidence"],
                user_bias_profile_update={"optimism_bias": 0.7},
            )
        ],
        stream_events=[
            RealityEngineStageEvent(stage="safety_gate", status="started"),
            RealityEngineStageEvent(stage="safety_gate", status="completed"),
        ],
    )


@pytest.fixture
def client(reality_engine: FakeRealityEngineClient) -> Iterator[TestClient]:
    app = create_app()

    decisions = InMemoryDecisionRepository()
    goals = InMemoryGoalRepository()
    simulations = InMemorySimulationRepository()
    memories = InMemoryMemoryEmbeddingRepository()
    outcomes = InMemoryDecisionOutcomeRepository()
    profiles = InMemoryUserBiasProfileRepository()
    identity = VerifiedIdentity(id=uuid4(), email="alejandro@example.com")
    other_identity = VerifiedIdentity(id=uuid4(), email="marina@example.com")
    verifier = StaticTokenVerifier({"valid-token": identity, "other-token": other_identity})

    app.dependency_overrides[get_decision_repository] = lambda: decisions
    app.dependency_overrides[get_goal_repository] = lambda: goals
    app.dependency_overrides[get_simulation_repository] = lambda: simulations
    app.dependency_overrides[get_memory_embedding_repository] = lambda: memories
    app.dependency_overrides[get_decision_outcome_repository] = lambda: outcomes
    app.dependency_overrides[get_user_bias_profile_repository] = lambda: profiles
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


def _ndjson_lines(body: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in body.splitlines() if line.strip()]


def test_run_simulation_stream_reports_stages_and_ends_with_a_result(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.post(f"/v1/decisions/{decision_id}/simulations/stream", headers=AUTH)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")

    events = _ndjson_lines(response.text)
    assert events[0] == {"type": "stage", "stage": "safety_gate", "status": "started"}
    assert events[1] == {"type": "stage", "stage": "safety_gate", "status": "completed"}
    assert events[-1]["type"] == "result"
    result = events[-1]["result"]
    assert isinstance(result, dict)
    assert result["status"] == "completed"
    assert len(result["scenarios"]) == 1

    decision_after = client.get(f"/v1/decisions/{decision_id}", headers=AUTH).json()
    assert decision_after["status"] == "completed"


def test_run_simulation_stream_is_valid_ndjson_line_by_line(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.post(f"/v1/decisions/{decision_id}/simulations/stream", headers=AUTH)

    for line in response.text.splitlines():
        assert json.loads(line)["type"] in {"stage", "result", "error"}


def test_run_simulation_stream_on_nonexistent_decision_returns_404(client: TestClient) -> None:
    response = client.post(f"/v1/decisions/{uuid4()}/simulations/stream", headers=AUTH)

    assert response.status_code == 404


def test_run_simulation_stream_on_another_users_decision_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.post(
        f"/v1/decisions/{decision_id}/simulations/stream",
        headers={"Authorization": "Bearer other-token"},
    )

    assert response.status_code == 404


def test_run_simulation_stream_reports_a_mid_stream_failure_in_band(client: TestClient) -> None:
    decision_id = _create_decision(client)
    # The fixture's `reality_engine` only has 3 canned `responses`; two other
    # tests in this module don't touch it, but this one drains it on its own
    # by using a client with none at all, so the stream fails only *after*
    # its 200 has already gone out — exactly the case `_stream_lines`'
    # broad `except Exception` exists for.
    client.app.dependency_overrides[get_reality_engine_client] = lambda: FakeRealityEngineClient(
        stream_events=[RealityEngineStageEvent(stage="safety_gate", status="started")]
    )

    response = client.post(f"/v1/decisions/{decision_id}/simulations/stream", headers=AUTH)

    assert response.status_code == 200
    events = _ndjson_lines(response.text)
    assert events[0] == {"type": "stage", "stage": "safety_gate", "status": "started"}
    assert events[-1]["type"] == "result"
    result = events[-1]["result"]
    assert isinstance(result, dict)
    assert result["status"] == "failed"


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


def test_report_decision_outcome_returns_calibration(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/v1/decisions/{decision_id}/simulations", headers=AUTH)

    response = client.post(
        f"/v1/decisions/{decision_id}/outcome",
        headers=AUTH,
        json={"reported_outcome": "Acepté la oferta y me fue bien."},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["calibration_delta"] == 15.0
    assert body["system_errors_identified"] == ["overconfidence"]
    assert body["closest_scenario_id"] is not None


def test_report_decision_outcome_on_another_users_decision_returns_404(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/v1/decisions/{decision_id}/simulations", headers=AUTH)

    response = client.post(
        f"/v1/decisions/{decision_id}/outcome",
        headers={"Authorization": "Bearer other-token"},
        json={"reported_outcome": "x"},
    )

    assert response.status_code == 404


def test_report_decision_outcome_without_completed_simulation_returns_409(
    client: TestClient,
) -> None:
    decision_id = _create_decision(client)

    response = client.post(
        f"/v1/decisions/{decision_id}/outcome",
        headers=AUTH,
        json={"reported_outcome": "x"},
    )

    assert response.status_code == 409


def test_report_decision_outcome_twice_returns_409(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/v1/decisions/{decision_id}/simulations", headers=AUTH)
    payload = {"reported_outcome": "Acepté la oferta y me fue bien."}

    first = client.post(f"/v1/decisions/{decision_id}/outcome", headers=AUTH, json=payload)
    second = client.post(f"/v1/decisions/{decision_id}/outcome", headers=AUTH, json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert client.get("/v1/outcomes", headers=AUTH).json() == [first.json()]


def test_list_outcomes_returns_the_callers_closed_loops(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/v1/decisions/{decision_id}/simulations", headers=AUTH)
    client.post(
        f"/v1/decisions/{decision_id}/outcome",
        headers=AUTH,
        json={"reported_outcome": "Acepté la oferta y me fue bien."},
    )

    response = client.get("/v1/outcomes", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["decision_id"] == decision_id


def test_list_outcomes_does_not_leak_another_users_outcomes(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/v1/decisions/{decision_id}/simulations", headers=AUTH)
    client.post(
        f"/v1/decisions/{decision_id}/outcome",
        headers=AUTH,
        json={"reported_outcome": "Acepté la oferta y me fue bien."},
    )

    response = client.get("/v1/outcomes", headers={"Authorization": "Bearer other-token"})

    assert response.status_code == 200
    assert response.json() == []


def test_list_outcomes_is_empty_before_any_loop_is_closed(client: TestClient) -> None:
    _create_decision(client)

    response = client.get("/v1/outcomes", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == []


def test_list_outcomes_requires_authentication(client: TestClient) -> None:
    assert client.get("/v1/outcomes").status_code == 401
