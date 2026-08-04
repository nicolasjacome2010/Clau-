from __future__ import annotations

from fastapi.testclient import TestClient

from reality_engine.main import create_app


def test_safety_check_without_configured_provider_fails_safe() -> None:
    """No OPENAI_API_KEY set anywhere in this test process, so the safety
    tier has zero providers and the endpoint must fail safe (see
    config.py and pipeline/agents/safety_gate.py).
    """
    with TestClient(create_app()) as client:
        response = client.post("/v1/safety-check", json={"raw_input": "algo neutral"})

    assert response.status_code == 200
    body = response.json()
    assert body["recommended_action"] == "halt_and_refer"


def test_safety_check_deterministic_pattern_short_circuits() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/safety-check", json={"raw_input": "quiero quitarme la vida"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "acute_risk"
    assert body["safe_to_proceed"] is False


def test_safety_check_rejects_empty_input() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/safety-check", json={"raw_input": ""})

    assert response.status_code == 422


def test_analyze_without_configured_provider_fails_safe_and_skips_extraction() -> None:
    """Same posture as /v1/safety-check: without OPENAI_API_KEY, Agent 0
    fails safe and the pipeline never reaches Agents 1-6.
    """
    with TestClient(create_app()) as client:
        response = client.post("/v1/analyze", json={"raw_input": "algo neutral"})

    assert response.status_code == 200
    body = response.json()
    assert body["safety"]["recommended_action"] == "halt_and_refer"
    assert body["comprehension"] is None
    assert body["summary"] is None


def test_analyze_deterministic_risk_pattern_short_circuits() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/analyze", json={"raw_input": "quiero quitarme la vida"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["safety"]["risk_level"] == "acute_risk"
    assert body["comprehension"] is None


def test_analyze_rejects_empty_input() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/analyze", json={"raw_input": ""})

    assert response.status_code == 422


def test_analyze_rejects_too_many_declared_goals() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/analyze",
            json={"raw_input": "algo", "declared_goals": ["a", "b", "c", "d", "e", "f"]},
        )

    assert response.status_code == 422


def test_simulate_without_configured_provider_fails_safe() -> None:
    """/v1/simulate shares Agent 0 with /v1/safety-check and /v1/analyze —
    without OPENAI_API_KEY it must fail safe and never reach Agents 1-10.
    """
    with TestClient(create_app()) as client:
        response = client.post("/v1/simulate", json={"raw_input": "algo neutral"})

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["safety"]["recommended_action"] == "halt_and_refer"
    assert body["scenarios"] is None
    assert body["synthesis"] is None


def test_simulate_deterministic_risk_pattern_short_circuits() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/simulate", json={"raw_input": "quiero quitarme la vida"})

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["safety"]["risk_level"] == "acute_risk"
    assert body["scenarios"] is None


def test_simulate_rejects_empty_input() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/simulate", json={"raw_input": ""})

    assert response.status_code == 422


def _three_scenarios() -> list[dict[str, object]]:
    return [
        {
            "id": f"s{i}",
            "title": f"Escenario {i}",
            "narrative": "Podrías crecer profesionalmente.",
            "relative_probability": 33.3,
            "time_horizon_months": 12,
        }
        for i in range(3)
    ]


def test_calibrate_without_configured_provider_returns_503() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/calibrate",
            json={
                "reported_outcome": "Acepté y me tomó 3 meses adaptarme",
                "original_scenarios": _three_scenarios(),
                "original_ranking": [],
            },
        )

    assert response.status_code == 503


def test_calibrate_rejects_too_few_scenarios() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/calibrate",
            json={
                "reported_outcome": "algo",
                "original_scenarios": _three_scenarios()[:2],
                "original_ranking": [],
            },
        )

    assert response.status_code == 422


def test_calibrate_rejects_empty_outcome() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/calibrate",
            json={
                "reported_outcome": "",
                "original_scenarios": _three_scenarios(),
                "original_ranking": [],
            },
        )

    assert response.status_code == 422


def test_healthz_is_public() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
